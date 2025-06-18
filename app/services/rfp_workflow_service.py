import os
from typing import Dict
import logging
from pathlib import Path
from fastapi import HTTPException
import mimetypes
import urllib.parse
import re
import uuid

from .document_processor_service import DocumentProcessorService
from .proposal_scorer_service import ProposalScorerService
from .proposal_generator_service import ProposalGeneratorService
from .boto_service import BotoService
from ..config import OUTPUT_DIR

logger = logging.getLogger(__name__)

DOCX = ".docx"
PDF = ".pdf"
DOC = ".doc"


class RFPWorkflowService:
    """Simplified RFP workflow with minimal LLM calls."""

    def __init__(self):
        logger.info("Initializing RFPWorkflowService")
        self.doc_processor = DocumentProcessorService()
        self.scorer = ProposalScorerService()
        self.generator = ProposalGeneratorService()
        self.boto_service = BotoService()
        logger.info("RFPWorkflowService initialized successfully")

    def _get_ext_from_url(self, url: str) -> str:
        """
        Extract file extension from URL, handling S3 URLs and common cases.
        """
        try:
            # Parse URL and remove query parameters
            parsed_url = urllib.parse.urlparse(url)
            clean_path = urllib.parse.unquote(parsed_url.path)

            # Get extension from clean path
            ext = Path(clean_path).suffix.lower()

            # Check if we have a supported extension
            supported_extensions = {PDF, DOCX, DOC}
            if ext in supported_extensions:
                logger.debug(f"Found extension {ext} from URL path")
                return ext

            # Try mimetype guessing on the clean path
            mime, _ = mimetypes.guess_type(clean_path)
            if mime:
                logger.debug(f"Detected MIME type: {mime}")
                if "pdf" in mime.lower():
                    return PDF
                elif (
                    "wordprocessingml" in mime.lower()
                    or "openxmlformats" in mime.lower()
                ):
                    return DOCX
                elif "msword" in mime.lower():
                    return DOC

            # Check if filename is in query parameters
            if "filename=" in url:
                filename_match = re.search(r"filename=([^&]+)", url)
                if filename_match:
                    filename = urllib.parse.unquote(filename_match.group(1))
                    param_ext = Path(filename).suffix.lower()
                    if param_ext in supported_extensions:
                        logger.debug(
                            f"Found extension {param_ext} from filename parameter"
                        )
                        return param_ext

            # If path suggests a document, default to docx
            if any(
                keyword in clean_path.lower()
                for keyword in ["proposal", "rfp", "document", "doc"]
            ):
                logger.warning(
                    f"No extension found for {url}, defaulting to .docx based on path content"
                )
                return DOCX

            # If all else fails, raise an error instead of guessing
            raise ValueError(f"Cannot determine supported file type from URL: {url}")

        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
            raise ValueError(f"Error processing URL {url}: {e}")

    def _get_safe_filename(self, url: str, prefix: str = "file") -> str:
        """
        Generate a safe filename from URL, handling encoding and special characters.
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            clean_path = urllib.parse.unquote(parsed_url.path)

            # Get the filename without extension
            filename = Path(clean_path).stem

            # Clean the filename to make it filesystem-safe
            safe_filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
            safe_filename = re.sub(r"\s+", "_", safe_filename)
            safe_filename = safe_filename.strip("._")

            # Ensure filename isn't empty and isn't too long
            if not safe_filename or len(safe_filename) < 3:
                safe_filename = f"{prefix}_{uuid.uuid4().hex[:8]}"
            elif len(safe_filename) > 100:
                safe_filename = safe_filename[:100]

            return safe_filename

        except Exception:
            return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def score_proposal(
        self,
        project_id: str,
        rfp_file_url: str,
        proposal_file_url: str,
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> Dict:
        """Score proposal - single LLM call."""
        logger.info("=" * 50)
        logger.info("STARTING PROPOSAL SCORING")
        logger.info("=" * 50)
        logger.info(f"RFP file: {rfp_file_url}")
        logger.info(f"Proposal file: {proposal_file_url}")
        logger.info(f"NAICS code: {naics_code}")
        logger.info(f"NAICS code description: {naics_code_description}")
        logger.info(f"Project ID: {project_id}")

        # Create project directory
        project_dir = f"{OUTPUT_DIR}/{project_id}"
        os.makedirs(project_dir, exist_ok=True)

        try:
            rfp_ext = self._get_ext_from_url(rfp_file_url)
            proposal_ext = self._get_ext_from_url(proposal_file_url)

            # Create safe filenames
            rfp_safe_name = self._get_safe_filename(rfp_file_url, "rfp")
            proposal_safe_name = self._get_safe_filename(proposal_file_url, "proposal")

            rfp_file_path = f"{project_dir}/{rfp_safe_name}{rfp_ext}"
            proposal_file_path = f"{project_dir}/{proposal_safe_name}{proposal_ext}"

            # Download files from S3
            logger.info("Downloading RFP file from S3...")
            self.boto_service.download_user_file(
                public_url=rfp_file_url,
                download_path=rfp_file_path,
            )
            logger.info("Downloading proposal file from S3...")
            self.boto_service.download_user_file(
                public_url=proposal_file_url,
                download_path=proposal_file_path,
            )

            # Validate file paths
            if (
                not Path(rfp_file_path).exists()
                or not Path(proposal_file_path).exists()
            ):
                logger.error(f"RFP file not found: {rfp_file_path}")
                raise HTTPException(
                    status_code=400,
                    detail=f"RFP file not found: {rfp_file_path}",
                )

            # Extract text from files
            logger.info("Extracting RFP text...")
            rfp_text = self.doc_processor.extract_rfp_text(rfp_file_path)

            logger.info("Extracting proposal text...")
            proposal_text = self.doc_processor.extract_rfp_text(proposal_file_path)

            # Score with single LLM call
            logger.info("Scoring proposal with LLM...")
            result = self.scorer.score_proposal(
                rfp_text, proposal_text, naics_code, naics_code_description
            )

            logger.info("=" * 50)
            logger.info("SCORING COMPLETE")
            logger.info(f"Final Score: {result['score']}/10")
            logger.info(f"Suggestion: {result['suggestion']}")

            if not result["score"] or not result["suggestion"]:
                raise HTTPException(
                    status_code=400,
                    detail="Scoring failed. Please try again. If the problem persists, please contact support.",
                )

            logger.info("=" * 50)

            return result

        except ValueError as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"File processing error: {e}",
            )
        except Exception as e:
            logger.error(f"Error in score_proposal: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error in scoring workflow: {e}",
            )
        finally:
            try:
                if "rfp_file_path" in locals() and Path(rfp_file_path).exists():
                    os.remove(rfp_file_path)
                if (
                    "proposal_file_path" in locals()
                    and Path(proposal_file_path).exists()
                ):
                    os.remove(proposal_file_path)
                logger.debug("Cleaned up temporary files")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup files: {cleanup_error}")

    def generate_proposal(
        self,
        project_id: str,
        rfp_file_url: str,
        knowledge_base_files_urls: list = [],
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> str:
        """Generate proposal - single LLM call."""
        logger.info("=" * 50)
        logger.info("STARTING PROPOSAL GENERATION")
        logger.info("=" * 50)
        logger.info(f"RFP file: {rfp_file_url}")
        logger.info(f"Knowledge base files: {knowledge_base_files_urls}")
        logger.info(f"Project ID: {project_id}")

        # Create project directory
        project_dir = f"{OUTPUT_DIR}/{project_id}"
        os.makedirs(project_dir, exist_ok=True)

        downloaded_files = []
        try:
            rfp_ext = self._get_ext_from_url(rfp_file_url)
            rfp_safe_name = self._get_safe_filename(rfp_file_url, "rfp")
            rfp_file_path = f"{project_dir}/{rfp_safe_name}{rfp_ext}"
            downloaded_files.append(rfp_file_path)

            # Download files from S3
            logger.info("Downloading RFP file from S3...")
            self.boto_service.download_user_file(
                public_url=rfp_file_url,
                download_path=rfp_file_path,
            )
            kb_file_paths = []
            for i, kb_file_url in enumerate(knowledge_base_files_urls):
                logger.info(
                    f"Processing knowledge base file {i+1}/{len(knowledge_base_files_urls)}"
                )

                kb_ext = self._get_ext_from_url(kb_file_url)
                kb_safe_name = self._get_safe_filename(kb_file_url, f"kb_{i+1}")
                kb_file_path = f"{project_dir}/{kb_safe_name}{kb_ext}"
                downloaded_files.append(kb_file_path)

                logger.info("Downloading knowledge base file from S3...")
                self.boto_service.download_user_file(
                    public_url=kb_file_url,
                    download_path=kb_file_path,
                )
                kb_file_paths.append(kb_file_path)

            # Extract RFP text
            logger.info("Extracting RFP text...")
            rfp_text = self.doc_processor.extract_rfp_text(rfp_file_path)

            # Extract knowledge base text if provided
            kb_text = ""
            if kb_file_paths:
                logger.info("Loading knowledge base documents...")
                kb_docs = self.doc_processor.load_documents(kb_file_paths)
                kb_text = "\n\n".join([doc.page_content for doc in kb_docs])
                logger.info(f"Knowledge base text length: {len(kb_text)} characters")

            # Generate proposal with single LLM call
            logger.info("Generating proposal with LLM...")
            proposal = self.generator.generate_proposal(
                rfp_text, kb_text, naics_code, naics_code_description
            )

            # Save proposal
            output_file = OUTPUT_DIR / "generated_proposal.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(proposal)

            logger.info("=" * 50)
            logger.info("PROPOSAL GENERATION COMPLETE")
            logger.info(f"Proposal saved to: {output_file}")
            logger.info("=" * 50)

            return str(output_file)

        except ValueError as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"File processing error: {e}",
            )
        except Exception as e:
            logger.error(f"Error in generate_proposal: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error in generate_proposal: {e}",
            )
        finally:
            # Clean up downloaded files
            for file_path in downloaded_files:
                try:
                    if Path(file_path).exists():
                        os.remove(file_path)
                        logger.debug(f"Cleaned up: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {file_path}: {cleanup_error}")
