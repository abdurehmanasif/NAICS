from fastapi import APIRouter, HTTPException
import logging
import uuid

from ..models.requests import ScoreProposalRequest, ScoreProposalResponse, ErrorResponse
from ..services.rfp_workflow_service import RFPWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scoring", tags=["scoring"])

# Global service instance (could be dependency injected in production)
workflow_service = RFPWorkflowService()


@router.post(
    "/score-proposal",
    response_model=ScoreProposalResponse,
    responses={
        200: {"model": ScoreProposalResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Score a proposal against an RFP",
    description="Analyze and score how well a proposal addresses the requirements in an RFP document. Returns a score from 0-10 with detailed feedback.",
)
async def score_proposal(request: ScoreProposalRequest) -> ScoreProposalResponse:
    """
    Score a proposal against an RFP document.

    This endpoint:
    - Extracts text from both RFP and proposal documents
    - Uses AI to evaluate how well the proposal addresses RFP requirements
    - Considers NAICS code relevance if provided
    - Returns a numerical score (0-10) and detailed suggestions
    """
    try:
        logger.info(
            f"Received scoring request for RFP: {request.rfp_file_url}, Proposal: {request.proposal_file_url}"
        )
        project_id = uuid.uuid4()

        # Call the workflow service
        result = workflow_service.score_proposal(
            project_id=project_id,
            rfp_file_url=request.rfp_file_url,
            proposal_file_url=request.proposal_file_url,
            naics_code=request.naics_code or "",
            naics_code_description=request.naics_code_description or "",
        )

        # Check if there was an error in the scoring
        if result["score"] == 0 and "Error" in result["suggestion"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Scoring failed", "detail": result["suggestion"]},
            )

        return ScoreProposalResponse(
            score=result["score"], suggestion=result["suggestion"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in score_proposal: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Internal server error", "detail": str(e)}
        )
