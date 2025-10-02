import logging
import uuid

from fastapi import APIRouter, HTTPException

from ..models.requests import (
    ErrorResponse,
    SummarizeRFPRequest,
    SummarizeRFPResponse,
)
from ..services.rfp_workflow_service import RFPWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summarization", tags=["summarization"])


@router.post(
    "/summarize-rfp",
    response_model=SummarizeRFPResponse,
    responses={
        200: {"model": SummarizeRFPResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Summarize RFP requirements and estimate costs from multiple documents",
    description="Analyze multiple documents to identify the main RFP, provide a concise summary of requirements, and estimate the total contract cost. Optionally include proposal documents for enhanced analysis.",
)
async def summarize_rfp(
    request: SummarizeRFPRequest,
) -> SummarizeRFPResponse:
    """
    Summarize RFP requirements and estimate costs from multiple documents.

    This endpoint:
    - Extracts text from multiple potential RFP documents
    - Uses AI to identify which document is the main RFP
    - Optionally loads multiple proposal documents for context
    - Creates a concise executive summary of RFP requirements
    - Provides a realistic cost estimate based on industry standards
    - Returns the identified RFP filename, confidence level and basis for the estimate
    """
    try:
        if not request.rfp_file_urls:
            raise HTTPException(
                status_code=400,
                detail={"error": "At least one RFP file URL is required"},
            )
        workflow_service = RFPWorkflowService()
        logger.info(
            f"Received summarization request for RFP files: {request.rfp_file_urls}"
        )
        project_id = str(uuid.uuid4())

        # Call the workflow service
        result = workflow_service.summarize_rfp(
            project_id=project_id,
            rfp_file_urls=request.rfp_file_urls,
        )

        # Check if there was an error in the summarization
        if not result.get("rfp_summary") or not result.get("estimated_cost"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Summarization failed",
                    "detail": "Unable to generate summary or cost estimate",
                },
            )

        return SummarizeRFPResponse(
            identified_rfp_filename=result.get("identified_rfp_filename", ""),
            rfp_summary=result["rfp_summary"],
            estimated_cost=result["estimated_cost"],
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=400, detail={"error": "File not found", "detail": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error in summarize_rfp: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Internal server error", "detail": str(e)}
        )
