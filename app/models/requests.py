from pydantic import BaseModel, Field
from typing import List, Optional


class ScoreProposalRequest(BaseModel):
    """Request schema for proposal scoring API"""

    rfp_file: str = Field(..., description="HttpUrl to the RFP file")
    proposal_file: str = Field(..., description="HttpUrl to the proposal file")
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

    rfp_file: str = Field(..., description="HttpUrl to the RFP file")
    knowledge_base_files: Optional[List[str]] = Field(
        default=[], description="List of HttpUrls to the knowledge base files"
    )
    naics_code: Optional[str] = Field(None, description="NAICS industry code")
    naics_code_description: Optional[str] = Field(
        None, description="NAICS code description"
    )


class GenerateProposalResponse(BaseModel):
    """Response schema for proposal generation API"""

    output_file_path: str = Field(
        ..., description="HttpUrl to the generated proposal file"
    )
    message: str = Field(..., description="Success message")


class ErrorResponse(BaseModel):
    """Error response schema"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
