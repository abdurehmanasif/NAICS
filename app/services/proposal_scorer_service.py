import json
import logging
import re
from typing import Dict

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.prompts.prompts_v3 import scoring_template

from ..config import (
    DEFAULT_LLM_MODEL_GOOGLE,
    DEFAULT_LLM_MODEL_OPENAI,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)


class ProposalScorerService:
    """Scores proposals against RFP requirements using LLM evaluation."""

    def __init__(self):
        if LLM_PROVIDER == "openai":
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_OPENAI,
                model_provider="openai",
                temperature=0.1,
                api_key=OPENAI_API_KEY,
            )
        elif LLM_PROVIDER == "google_genai":
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_GOOGLE,
                model_provider="google_genai",
                temperature=0.1,
                api_key=GOOGLE_API_KEY,
            )

    async def score_proposal(
        self,
        rfp_text: str,
        proposal_text: str,
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> Dict:
        """Score proposal against RFP requirements."""
        if not rfp_text or not rfp_text.strip():
            return {"score": 0, "suggestion": "Error: RFP text is empty"}

        if not proposal_text or not proposal_text.strip():
            return {"score": 0, "suggestion": "Error: Proposal text is empty"}

        prompt = PromptTemplate(
            input_variables=[
                "rfp_text",
                "proposal_text",
                "naics_code",
                "naics_code_description",
            ],
            template=scoring_template,
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = await chain.ainvoke(
                {
                    "rfp_text": rfp_text[:8000],
                    "proposal_text": proposal_text[:12000],
                    "naics_code": naics_code,
                    "naics_code_description": naics_code_description,
                }
            )

            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Error scoring proposal: {e}")
            return {
                "score": 0,
                "suggestion": f"Error occurred during scoring: {e}",
            }

    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response with multiple fallback strategies."""
        if not response:
            return {"score": 0, "suggestion": "Empty response from LLM"}

        # Try direct JSON parsing
        try:
            result = json.loads(response.strip())
            return self._validate_result(result)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON block
        try:
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return self._validate_result(result)
        except (json.JSONDecodeError, AttributeError):
            pass

        # Extract score and suggestion manually
        try:
            score_match = re.search(r'"?score"?\s*:\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE)
            suggestion_match = re.search(r'"?suggestion"?\s*:\s*"([^"]*)"', response, re.IGNORECASE | re.DOTALL)

            if score_match:
                score = float(score_match.group(1))
                suggestion = suggestion_match.group(1) if suggestion_match else "No specific suggestion provided"
                return self._validate_result({"score": score, "suggestion": suggestion})
        except Exception:
            pass

        # Final fallback
        return {
            "score": 5,
            "suggestion": f"Unable to parse response: {response[:200]}...",
        }

    def _validate_result(self, result: Dict) -> Dict:
        """Validate and normalize the result."""
        if not isinstance(result, dict) or "score" not in result:
            return {"score": 0, "suggestion": "Invalid result format"}

        try:
            score = max(0, min(10, float(result["score"])))
        except (ValueError, TypeError):
            score = 0

        suggestion = str(result.get("suggestion", "No suggestion provided"))

        return {"score": score, "suggestion": suggestion}
