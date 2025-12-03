import asyncio
import logging
import mimetypes
import os
import re
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple

from docx import Document
from fastapi import HTTPException

from ..config import OUTPUT_DIR
from .boto_service import BotoService
from .document_processor_service import DocumentProcessorService
from .proposal_generator_service import ProposalGeneratorService
from .proposal_scorer_service import ProposalScorerService
from .rfp_summary_service import RFPSummaryService

logger = logging.getLogger(__name__)

DOCX_EXT = ".docx"
PDF = ".pdf"
DOC = ".doc"

# Thread pool for blocking file I/O operations
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("THREAD_POOL_SIZE", "4")))


class RFPWorkflowService:
    """RFP workflow with parallel processing support."""

    def __init__(self):
        self.doc_processor = DocumentProcessorService()
        self.scorer = ProposalScorerService()
        self.generator = ProposalGeneratorService()
        self.summary_service = RFPSummaryService()
        self.boto_service = BotoService()

    def _get_ext_from_url(self, url: str) -> str:
        """Extract file extension from URL, handling S3 URLs and common cases."""
        try:
            parsed_url = urllib.parse.urlparse(url)
            clean_path = urllib.parse.unquote(parsed_url.path)

            ext = Path(clean_path).suffix.lower()

            supported_extensions = {PDF, DOCX_EXT, DOC}
            if ext in supported_extensions:
                logger.debug(f"Found extension {ext} from URL path")
                return ext

            mime, _ = mimetypes.guess_type(clean_path)
            if mime:
                logger.debug(f"Detected MIME type: {mime}")
                if "pdf" in mime.lower():
                    return PDF
                elif "wordprocessingml" in mime.lower() or "openxmlformats" in mime.lower():
                    return DOCX_EXT
                elif "msword" in mime.lower():
                    return DOC

            if "filename=" in url:
                filename_match = re.search(r"filename=([^&]+)", url)
                if filename_match:
                    filename = urllib.parse.unquote(filename_match.group(1))
                    param_ext = Path(filename).suffix.lower()
                    if param_ext in supported_extensions:
                        logger.debug(f"Found extension {param_ext} from filename parameter")
                        return param_ext

            if any(
                keyword in clean_path.lower()
                for keyword in ["proposal", "rfp", "document", "doc"]
            ):
                logger.warning(
                    f"No extension found for {url}, defaulting to .docx based on path content"
                )
                return DOCX_EXT

            raise ValueError(f"Cannot determine supported file type from URL: {url}")

        except Exception as e:
            logger.error(f"Error parsing URL {url}: {e}")
            raise ValueError(f"Error processing URL {url}: {e}")

    def _get_safe_filename(self, url: str, prefix: str = "file") -> str:
        """Generate a safe filename from URL, handling encoding and special characters."""
        try:
            parsed_url = urllib.parse.urlparse(url)
            clean_path = urllib.parse.unquote(parsed_url.path)

            filename = Path(clean_path).stem

            safe_filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
            safe_filename = re.sub(r"\s+", "_", safe_filename)
            safe_filename = safe_filename.strip("._")

            if not safe_filename or len(safe_filename) < 3:
                safe_filename = f"{prefix}_{uuid.uuid4().hex[:8]}"
            elif len(safe_filename) > 100:
                safe_filename = safe_filename[:100]

            return safe_filename

        except Exception:
            return f"{prefix}_{uuid.uuid4().hex[:8]}"

    async def _download_file(self, url: str, download_path: str) -> bool:
        """Download a single file from S3."""
        return await self.boto_service.download_user_file(
            public_url=url, download_path=download_path
        )

    async def _download_and_extract(
        self, url: str, project_dir: str, prefix: str, index: int
    ) -> Tuple[str, str, str]:
        """Download file and extract text. Returns (filename, text, file_path)."""
        file_path = ""
        try:
            ext = self._get_ext_from_url(url)
            safe_name = self._get_safe_filename(url, f"{prefix}_{index + 1}")
            file_path = f"{project_dir}/{safe_name}{ext}"

            logger.info(f"Downloading {prefix} file {index + 1} from S3...")
            success = await self.boto_service.download_user_file(
                public_url=url, download_path=file_path
            )

            if not success or not Path(file_path).exists():
                logger.error(f"Failed to download file: {url}")
                return ("", "", file_path)

            logger.info(f"Extracting text from {prefix} file {index + 1}...")
            text = await self.doc_processor.extract_rfp_text(file_path)

            filename = Path(file_path).name
            return (filename, text, file_path)

        except Exception as e:
            logger.warning(f"Failed to process {prefix} file {url}: {e}")
            return ("", "", file_path)

    async def _create_docx_in_executor(
        self, content: str, output_path: str
    ) -> None:
        """Create DOCX file in thread executor to avoid blocking."""
        loop = asyncio.get_event_loop()

        def _create_docx():
            document = Document()
            for paragraph in content.split("\n\n"):
                document.add_paragraph(paragraph)
            document.save(output_path)

        await loop.run_in_executor(_executor, _create_docx)

    async def score_proposal(
        self,
        project_id: str,
        rfp_file_url: str,
        proposal_file_url: str,
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> Dict:
        """Score proposal with parallel file downloads."""
        project_dir = f"{OUTPUT_DIR}/{project_id}"
        os.makedirs(project_dir, exist_ok=True)
        rfp_file_path = None
        proposal_file_path = None

        try:
            rfp_ext = self._get_ext_from_url(rfp_file_url)
            proposal_ext = self._get_ext_from_url(proposal_file_url)

            rfp_safe_name = self._get_safe_filename(rfp_file_url, "rfp")
            proposal_safe_name = self._get_safe_filename(proposal_file_url, "proposal")

            rfp_file_path = f"{project_dir}/{rfp_safe_name}{rfp_ext}"
            proposal_file_path = f"{project_dir}/{proposal_safe_name}{proposal_ext}"

            # Parallel download of both files
            download_results = await asyncio.gather(
                self._download_file(rfp_file_url, rfp_file_path),
                self._download_file(proposal_file_url, proposal_file_path),
            )

            if not all(download_results):
                raise HTTPException(
                    status_code=400,
                    detail="Failed to download one or more files",
                )

            if not Path(rfp_file_path).exists() or not Path(proposal_file_path).exists():
                raise HTTPException(
                    status_code=400,
                    detail="RFP or proposal file not found after download",
                )

            # Parallel text extraction
            rfp_text, proposal_text = await asyncio.gather(
                self.doc_processor.extract_rfp_text(rfp_file_path),
                self.doc_processor.extract_rfp_text(proposal_file_path),
            )

            # Score with LLM
            result = await self.scorer.score_proposal(
                rfp_text, proposal_text, naics_code, naics_code_description
            )

            if result["score"] is None or result["suggestion"] is None:
                raise HTTPException(
                    status_code=400,
                    detail="Scoring failed. Please try again.",
                )

            return result

        except ValueError as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(status_code=400, detail=f"File processing error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in score_proposal: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error in scoring workflow: {e}")
        finally:
            try:
                for path in [rfp_file_path, proposal_file_path]:
                    if path and Path(path).exists():
                        os.remove(path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup files: {cleanup_error}")

    async def generate_proposal(
        self,
        project_id: str,
        rfp_file_urls: List[str],
        knowledge_base_files_urls: List[str] = None,
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> str:
        """Generate proposal with parallel file processing."""
        knowledge_base_files_urls = knowledge_base_files_urls or []

        if not rfp_file_urls:
            raise HTTPException(
                status_code=400,
                detail="At least one RFP file URL is required",
            )

        project_dir = f"{OUTPUT_DIR}/{project_id}"
        os.makedirs(project_dir, exist_ok=True)

        downloaded_files = []
        docx_path = None

        try:
            # Parallel download and extraction of all RFP files
            rfp_tasks = [
                self._download_and_extract(url, project_dir, "rfp", i)
                for i, url in enumerate(rfp_file_urls)
            ]
            rfp_results = await asyncio.gather(*rfp_tasks)

            rfp_documents = []
            for filename, text, file_path in rfp_results:
                if file_path:
                    downloaded_files.append(file_path)
                if filename and text:
                    rfp_documents.append((filename, text))

            if not rfp_documents:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to process any RFP files",
                )

            # Identify main RFP
            identification_result = await self.summary_service.identify_main_rfp(
                rfp_documents
            )
            identified_filename = identification_result["identified_rfp_filename"]

            rfp_text = ""
            for filename, content in rfp_documents:
                if filename == identified_filename:
                    rfp_text = content
                    break

            if not rfp_text:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not find content for identified RFP: {identified_filename}",
                )

            # Parallel download and extraction of KB files
            kb_text = ""
            if knowledge_base_files_urls:
                kb_tasks = [
                    self._download_and_extract(url, project_dir, "kb", i)
                    for i, url in enumerate(knowledge_base_files_urls)
                ]
                kb_results = await asyncio.gather(*kb_tasks)

                kb_texts = []
                for filename, text, file_path in kb_results:
                    if file_path:
                        downloaded_files.append(file_path)
                    if text:
                        kb_texts.append(text)

                kb_text = "\n\n".join(kb_texts)

            # Generate proposal with LLM
            proposal = await self.generator.generate_proposal(
                rfp_text, kb_text, naics_code, naics_code_description
            )

            # Create DOCX in thread executor
            docx_path = f"{project_dir}/generated_proposal.docx"
            await self._create_docx_in_executor(proposal, docx_path)

            # Upload to S3
            success, public_url = await self.boto_service.upload_user_file(
                file_name=docx_path,
                user_id=str(project_id),
                feature_name="proposal_generation",
                project_id=str(project_id),
                object_name=Path(docx_path).name,
            )

            if not success or not public_url:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload generated proposal to storage.",
                )

            return public_url

        except ValueError as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(status_code=400, detail=f"File processing error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in generate_proposal: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error in generate_proposal: {e}")
        finally:
            cleanup_files = downloaded_files + ([docx_path] if docx_path else [])
            for file_path in cleanup_files:
                try:
                    if file_path and Path(file_path).exists():
                        os.remove(file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {file_path}: {cleanup_error}")

    async def summarize_rfp(
        self,
        project_id: str,
        rfp_file_urls: List[str],
    ) -> Dict:
        """Async: Summarize RFP with parallel file processing."""
        logger.info("=" * 50)
        logger.info("STARTING MULTI-DOCUMENT RFP SUMMARIZATION AND COST ESTIMATION")
        logger.info("=" * 50)
        logger.info(f"RFP files: {rfp_file_urls}")
        logger.info(f"Project ID: {project_id}")

        if not rfp_file_urls:
            raise HTTPException(
                status_code=400,
                detail="At least one RFP file URL is required",
            )

        project_dir = f"{OUTPUT_DIR}/{project_id}"
        os.makedirs(project_dir, exist_ok=True)

        downloaded_files = []

        try:
            # Parallel download and extraction of all RFP files
            logger.info("Downloading and extracting RFP files in parallel...")
            rfp_tasks = [
                self._download_and_extract(url, project_dir, "rfp", i)
                for i, url in enumerate(rfp_file_urls)
            ]
            rfp_results = await asyncio.gather(*rfp_tasks)

            rfp_documents = []
            for filename, text, file_path in rfp_results:
                if file_path:
                    downloaded_files.append(file_path)
                if filename and text:
                    rfp_documents.append((filename, text))

            if not rfp_documents:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to process any RFP files",
                )

            # Analyze documents with LLM
            logger.info("Analyzing documents with LLM...")
            result = await self.summary_service.summarize_multiple_docs_and_estimate_cost(
                rfp_documents
            )

            logger.info("=" * 50)
            logger.info("MULTI-DOCUMENT SUMMARIZATION AND COST ESTIMATION COMPLETE")
            logger.info(f"Identified RFP: {result.get('identified_rfp_filename', 'N/A')}")
            logger.info(f"Summary points: {len(result.get('rfp_summary', []))}")
            if result.get("estimated_cost"):
                logger.info(
                    f"Cost range: ${result['estimated_cost']['range_low']} - ${result['estimated_cost']['range_high']}"
                )
                logger.info(f"Confidence: {result['estimated_cost']['confidence_level']}")

            if not result.get("rfp_summary") or not result.get("estimated_cost"):
                raise HTTPException(
                    status_code=400,
                    detail="Summarization failed. Please try again.",
                )

            logger.info("=" * 50)
            return result

        except ValueError as e:
            logger.error(f"File processing error: {e}")
            raise HTTPException(status_code=400, detail=f"File processing error: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in summarize_rfp: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error in summarization workflow: {e}"
            )
        finally:
            for file_path in downloaded_files:
                try:
                    if file_path and Path(file_path).exists():
                        os.remove(file_path)
                        logger.debug(f"Cleaned up: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {file_path}: {cleanup_error}")
