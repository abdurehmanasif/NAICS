from typing import List, Optional

from pydantic import BaseModel, Field


class ScoreProposalRequest(BaseModel):
    """Request schema for proposal scoring API"""

    rfp_file_url: str = Field(..., description="HttpUrl to the RFP file")
    proposal_file_url: str = Field(..., description="HttpUrl to the proposal file")
    naics_code: Optional[str] = Field(None, description="NAICS industry code")
    naics_code_description: Optional[str] = Field(
        None, description="NAICS code description"
    )


class ScoreProposalResponse(BaseModel):
    """Response schema for proposal scoring API"""

    score: float = Field(..., description="Proposal score between 0-10")
    suggestion: str = Field(
        ..., description="Detailed feedback and suggestions for improvement"
    )


class GenerateProposalRequest(BaseModel):
    """Request schema for proposal generation API"""

    rfp_file_urls: List[str] = Field(
        ..., description="List of HttpUrls to the RFP files"
    )
    knowledge_base_files_urls: Optional[List[str]] = Field(
        default=[], description="List of HttpUrls to the knowledge base files"
    )
    naics_code: Optional[str] = Field(None, description="NAICS industry code")
    naics_code_description: Optional[str] = Field(
        None, description="NAICS code description"
    )


class GenerateProposalResponse(BaseModel):
    """Response schema for proposal generation API"""

    public_url: str = Field(
        ..., description="Public URL to the generated proposal DOCX file"
    )
    message: str = Field(..., description="Success message")


class SummarizeRFPRequest(BaseModel):
    """Request schema for RFP summarization and budget estimation API"""

    rfp_file_urls: List[str] = Field(
        ..., description="List of HttpUrls to potential RFP files"
    )


class RFPSummary(BaseModel):
    """Schema for RFP summary bullet points"""

    summary_points: List[str] = Field(
        ..., description="List of key summary points about the RFP"
    )


class CostEstimate(BaseModel):
    """Schema for cost estimation"""

    range_low: int = Field(..., description="Lower bound of estimated cost range")
    range_high: int = Field(..., description="Upper bound of estimated cost range")
    confidence_level: str = Field(..., description="Confidence level: low/medium/high")
    basis_of_estimate: str = Field(
        ..., description="Explanation of how the estimate was derived"
    )


class SummarizeRFPResponse(BaseModel):
    """Response schema for RFP summarization and budget estimation API"""

    identified_rfp_filename: str = Field(
        ..., description="Filename of the document identified as the main RFP"
    )
    rfp_summary: List[str] = Field(
        ..., description="Key summary points of RFP requirements"
    )
    estimated_cost: CostEstimate = Field(
        ..., description="Estimated cost range and basis"
    )


class ErrorResponse(BaseModel):
    """Error response schema"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
