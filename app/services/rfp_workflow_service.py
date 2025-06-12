import os
from typing import Dict
import logging
from pathlib import Path
from fastapi import HTTPException

from .document_processor_service import DocumentProcessorService
from .proposal_scorer_service import ProposalScorerService
from .proposal_generator_service import ProposalGeneratorService
from .boto_service import BotoService
from ..config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class RFPWorkflowService:
    """Simplified RFP workflow with minimal LLM calls."""

    def __init__(self):
        logger.info("Initializing RFPWorkflowService")
        self.doc_processor = DocumentProcessorService()
        self.scorer = ProposalScorerService()
        self.generator = ProposalGeneratorService()
        self.boto_service = BotoService()
        logger.info("RFPWorkflowService initialized successfully")

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
        rfp_file_path = f"{project_dir}/rfp.pdf"
        proposal_file_path = f"{project_dir}/proposal.pdf"

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

        try:
            # Validate file paths
            if not Path(rfp_file_path).exists():
                logger.error(f"RFP file not found: {rfp_file_path}")
                return {
                    "score": 0,
                    "suggestion": f"RFP file not found: {rfp_file_path}",
                }

            if not Path(proposal_file_path).exists():
                logger.error(f"Proposal file not found: {proposal_file_path}")
                return {
                    "score": 0,
                    "suggestion": f"Proposal file not found: {proposal_file_path}",
                }

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
                logger.error("Scoring failed")
                raise HTTPException(
                    status_code=400,
                    detail="Scoring failed. Please try again.",
                )
            logger.info("=" * 50)

            return result

        except Exception as e:
            logger.error(f"Error in score_proposal: {e}", exc_info=True)
            return {"score": 0, "suggestion": f"Error in scoring workflow: {e}"}

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

        try:
            # Create project directory
            project_dir = f"{OUTPUT_DIR}/{project_id}"
            os.makedirs(project_dir, exist_ok=True)
            rfp_file_path = f"{project_dir}/rfp.pdf"
            kb_file_paths = []

            # Download files from S3
            logger.info("Downloading RFP file from S3...")
            self.boto_service.download_user_file(
                public_url=rfp_file_url,
                download_path=rfp_file_path,
            )
            for kb_file_url in knowledge_base_files_urls:
                logger.info("Downloading knowledge base file from S3...")
                self.boto_service.download_user_file(
                    public_url=kb_file_url,
                    download_path=f"{project_dir}/kb_{kb_file_url.split('/')[-1]}",
                )
                kb_file_paths.append(f"{project_dir}/kb_{kb_file_url.split('/')[-1]}")

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

        except Exception as e:
            logger.error(f"Error in generate_proposal: {e}", exc_info=True)
            raise
