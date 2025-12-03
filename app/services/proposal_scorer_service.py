import json
import logging
import re
from typing import Dict

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.prompts_v2 import scoring_template

from ..config import (
    DEFAULT_LLM_MODEL_GOOGLE,
    DEFAULT_LLM_MODEL_OPENAI,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)


class ProposalScorerService:
    """Async proposal scorer with single LLM call."""

    def __init__(self):
        logger.info(f"Initializing ProposalScorerService with provider: {LLM_PROVIDER}")

        if LLM_PROVIDER == "openai":
            logger.info(f"Using OpenAI model: {DEFAULT_LLM_MODEL_OPENAI}")
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_OPENAI,
                model_provider="openai",
                temperature=0.1,
                api_key=OPENAI_API_KEY,
            )
        elif LLM_PROVIDER == "google_genai":
            logger.info(f"Using Google model: {DEFAULT_LLM_MODEL_GOOGLE}")
            self.llm = init_chat_model(
                model=DEFAULT_LLM_MODEL_GOOGLE,
                model_provider="google_genai",
                temperature=0.1,
                api_key=GOOGLE_API_KEY,
            )

        logger.info("ProposalScorerService initialized successfully")

    async def score_proposal(
        self,
        rfp_text: str,
        proposal_text: str,
        naics_code: str = "",
        naics_code_description: str = "",
    ) -> Dict:
        """Async: Score proposal with single LLM call using ainvoke."""
        logger.info("Starting proposal scoring")
        logger.info(f"RFP text length: {len(rfp_text)} characters")
        logger.info(f"Proposal text length: {len(proposal_text)} characters")

        if not rfp_text or not rfp_text.strip():
            logger.error("RFP text is empty or None")
            return {"score": 0, "suggestion": "Error: RFP text is empty"}

        if not proposal_text or not proposal_text.strip():
            logger.error("Proposal text is empty or None")
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
            rfp_truncated = rfp_text[:8000]
            proposal_truncated = proposal_text[:12000]

            logger.info(f"Truncated RFP length: {len(rfp_truncated)}")
            logger.info(f"Truncated proposal length: {len(proposal_truncated)}")

            logger.info("Invoking LLM for scoring...")
            response = await chain.ainvoke(
                {
                    "rfp_text": rfp_truncated,
                    "proposal_text": proposal_truncated,
                    "naics_code": naics_code,
                    "naics_code_description": naics_code_description,
                }
            )

            logger.info("Raw LLM response received")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response length: {len(str(response))}")
            logger.info(f"Raw response: {repr(response)}")

            result = self._parse_json_response(response)

            logger.info(f"Parsed result: {result}")
            logger.info(f"Final score: {result['score']}/10")

            return result

        except Exception as e:
            logger.error(f"Error scoring proposal: {e}", exc_info=True)
            return {
                "score": 0,
                "suggestion": f"Error occurred during scoring: {e}",
            }

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON response with fallback methods."""
        if not response:
            logger.error("Empty response from LLM")
            raise ValueError("Empty response from LLM")

        # Method 1: Direct JSON parsing
        try:
            result = json.loads(response.strip())
            logger.info("Successfully parsed JSON directly")
            return self._validate_result(result)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parsing failed: {e}")

        # Method 2: Extract JSON from response using regex
        try:
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.info(f"Extracted JSON: {json_str}")
                result = json.loads(json_str)
                logger.info("Successfully parsed extracted JSON")
                return self._validate_result(result)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Regex JSON extraction failed: {e}")

        # Method 3: Fallback - try to extract score and suggestion manually
        try:
            score_match = re.search(
                r'"?score"?\s*:\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE
            )
            suggestion_match = re.search(
                r'"?suggestion"?\s*:\s*"([^"]*)"', response, re.IGNORECASE | re.DOTALL
            )

            if score_match:
                score = float(score_match.group(1))
                suggestion = (
                    suggestion_match.group(1)
                    if suggestion_match
                    else "No specific suggestion provided"
                )

                result = {"score": score, "suggestion": suggestion}
                logger.info("Successfully extracted score and suggestion manually")
                return self._validate_result(result)
        except Exception as e:
            logger.warning(f"Manual extraction failed: {e}")

        # Method 4: Final fallback - create default response
        logger.error("All parsing methods failed, using default response")
        logger.error(f"Problematic response: {repr(response)}")

        return {
            "score": 5,
            "suggestion": f"Unable to parse LLM response. Raw response: {response[:200]}...",
        }

    def _validate_result(self, result: Dict) -> Dict:
        """Validate and clean the parsed result."""
        if not isinstance(result, dict):
            raise ValueError(f"Result is not a dictionary: {type(result)}")

        if "score" not in result:
            raise ValueError("Missing 'score' field in result")

        if "suggestion" not in result:
            result["suggestion"] = "No suggestion provided"

        try:
            score = float(result["score"])
            result["score"] = max(0, min(10, score))  # Clamp between 0-10
        except (ValueError, TypeError):
            logger.warning(f"Invalid score format: {result['score']}, defaulting to 0")
            result["score"] = 0

        if not isinstance(result["suggestion"], str):
            result["suggestion"] = str(result["suggestion"])

        return result
