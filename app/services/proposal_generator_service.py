from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging

from ..config import (
    DEFAULT_LLM_MODEL_OPENAI,
    DEFAULT_LLM_MODEL_GOOGLE,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    GOOGLE_API_KEY,
)

logger = logging.getLogger(__name__)


class ProposalGeneratorService:
    """Simple proposal generator with single LLM call."""

    def __init__(self):
        if LLM_PROVIDER == "openai":
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_OPENAI,
                model_provider="openai",
                temperature=0.3,
                api_key=OPENAI_API_KEY,
            )
        elif LLM_PROVIDER == "google_genai":
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_GOOGLE,
                model_provider="google_genai",
                temperature=0.3,
                api_key=GOOGLE_API_KEY,
            )

    def generate_proposal(
        self,
        rfp_text: str,
        knowledge_base_text: str = "",
        naics_code: str = None,
        naics_code_description: str = None,
    ) -> str:
        """Generate proposal with single LLM call."""

        prompt = PromptTemplate(
            input_variables=[
                "rfp_text",
                "kb_text",
                "naics_code",
                "naics_code_description",
            ],
            template="""You are an expert proposal writer. Create a comprehensive proposal response to the RFP.

RFP Requirements:
{rfp_text}

Company/Knowledge Base Information:
{kb_text}

NAICS Code: {naics_code}
NAICS Description: {naics_code_description}

Instructions:
- Create a complete, professional proposal in markdown format
- Address all key RFP requirements
- Use the knowledge base information to demonstrate capabilities
- Include: Executive Summary, Technical Approach, Company Qualifications, Implementation Plan, Cost Considerations
- Make it compelling and well-structured
- If knowledge base is limited, use reasonable assumptions for a qualified company

Generate the complete proposal:""",
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            proposal = chain.invoke(
                {
                    "rfp_text": rfp_text[:10000],  # Limit to avoid token limits
                    "kb_text": knowledge_base_text[:8000],
                    "naics_code": naics_code,
                    "naics_code_description": naics_code_description,
                }
            )

            return proposal

        except Exception as e:
            logger.error(f"Error generating proposal: {e}")
            raise
