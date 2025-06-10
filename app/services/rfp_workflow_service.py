from typing import Dict
import logging
from pathlib import Path
from fastapi import HTTPException

from .document_processor_service import DocumentProcessorService
from .proposal_scorer_service import ProposalScorerService
from .proposal_generator_service import ProposalGeneratorService
from ..config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class RFPWorkflowService:
    """Simplified RFP workflow with minimal LLM calls."""

    def __init__(self):
        logger.info("Initializing RFPWorkflowService")
        self.doc_processor = DocumentProcessorService()
        self.scorer = ProposalScorerService()
        self.generator = ProposalGeneratorService()
        logger.info("RFPWorkflowService initialized successfully")

    def score_proposal(
        self,
        rfp_file: str,
        proposal_file: str,
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> Dict:
        """Score proposal - single LLM call."""
        logger.info("=" * 50)
        logger.info("STARTING PROPOSAL SCORING")
        logger.info("=" * 50)
        logger.info(f"RFP file: {rfp_file}")
        logger.info(f"Proposal file: {proposal_file}")
        logger.info(f"NAICS code: {naics_code}")
        logger.info(f"NAICS code description: {naics_code_description}")

        try:
            # Validate file paths
            if not Path(rfp_file).exists():
                logger.error(f"RFP file not found: {rfp_file}")
                return {"score": 0, "suggestion": f"RFP file not found: {rfp_file}"}

            if not Path(proposal_file).exists():
                logger.error(f"Proposal file not found: {proposal_file}")
                return {
                    "score": 0,
                    "suggestion": f"Proposal file not found: {proposal_file}",
                }

            # Extract text from files
            logger.info("Extracting RFP text...")
            rfp_text = self.doc_processor.extract_rfp_text(rfp_file)

            logger.info("Extracting proposal text...")
            proposal_text = self.doc_processor.extract_rfp_text(proposal_file)

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
        rfp_file: str,
        knowledge_base_files: list = [],
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> str:
        """Generate proposal - single LLM call."""
        logger.info("=" * 50)
        logger.info("STARTING PROPOSAL GENERATION")
        logger.info("=" * 50)
        logger.info(f"RFP file: {rfp_file}")
        logger.info(f"Knowledge base files: {knowledge_base_files}")

        try:
            # Extract RFP text
            logger.info("Extracting RFP text...")
            rfp_text = self.doc_processor.extract_rfp_text(rfp_file)

            # Extract knowledge base text if provided
            kb_text = ""
            if knowledge_base_files:
                logger.info("Loading knowledge base documents...")
                kb_docs = self.doc_processor.load_documents(knowledge_base_files)
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
