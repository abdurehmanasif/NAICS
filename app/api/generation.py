import logging
import uuid

from fastapi import APIRouter, HTTPException

from ..models.requests import (
    ErrorResponse,
    GenerateProposalRequest,
    GenerateProposalResponse,
)
from ..services.rfp_workflow_service import RFPWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post(
    "/generate-proposal",
    response_model=GenerateProposalResponse,
    responses={
        200: {"model": GenerateProposalResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate a proposal for an RFP",
    description="Generate a comprehensive proposal document based on RFP requirements and optional knowledge base documents.",
)
async def generate_proposal(
    request: GenerateProposalRequest,
) -> GenerateProposalResponse:
    """
    Generate a proposal for an RFP document.

    This endpoint:
    - Extracts text from the RFP document
    - Optionally loads knowledge base documents for company information
    - Uses AI to generate a comprehensive proposal response
    - Considers NAICS code relevance if provided
    - Saves the generated proposal to a markdown file
    """
    try:
        workflow_service = RFPWorkflowService()
        logger.info(f"Received generation request for RFP: {request.rfp_file_urls}")
        logger.info(f"Knowledge base files: {request.knowledge_base_files_urls}")
        project_id = str(uuid.uuid4())

        # Call the async workflow service
        public_url = await workflow_service.generate_proposal(
            project_id=project_id,
            rfp_file_urls=request.rfp_file_urls,
            knowledge_base_files_urls=request.knowledge_base_files_urls or [],
            naics_code=request.naics_code or "",
            naics_code_description=request.naics_code_description or "",
        )

        return GenerateProposalResponse(
            public_url=public_url,
            message=f"Proposal successfully generated and uploaded. Access it here: {public_url}",
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=400, detail={"error": "File not found", "detail": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error in generate_proposal: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Internal server error", "detail": str(e)}
        )
