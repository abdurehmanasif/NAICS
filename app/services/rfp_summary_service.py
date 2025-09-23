import json
import logging
import re
from typing import Dict

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.prompts import summary_and_budget_template

from ..config import (
    DEFAULT_LLM_MODEL_GOOGLE,
    DEFAULT_LLM_MODEL_OPENAI,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)


class RFPSummaryService:
    """Service for summarizing RFPs and estimating costs."""

    def __init__(self):
        logger.info(f"Initializing RFPSummaryService with provider: {LLM_PROVIDER}")

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

        logger.info("RFPSummaryService initialized successfully")

    def summarize_rfp_and_estimate_cost(
        self,
        rfp_text: str,
        proposal_text: str = "",
    ) -> Dict:
        """Summarize RFP and estimate cost with single LLM call."""
        logger.info("Starting RFP summarization and cost estimation")
        logger.info(f"RFP text length: {len(rfp_text)} characters")
        logger.info(f"Proposal text length: {len(proposal_text)} characters")

        # Validate inputs
        if not rfp_text or not rfp_text.strip():
            logger.error("RFP text is empty or None")
            return {
                "rfp_summary": ["Error: RFP text is empty"],
                "estimated_cost": {
                    "range_low": 0,
                    "range_high": 0,
                    "confidence_level": "low",
                    "basis_of_estimate": "Unable to process due to empty RFP text",
                },
            }

        prompt = PromptTemplate(
            input_variables=[
                "rfp_text",
                "proposal_text",
            ],
            template=summary_and_budget_template,
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            # Truncate inputs to avoid token limits
            rfp_truncated = rfp_text[:8000]
            proposal_truncated = proposal_text[:4000] if proposal_text else ""

            logger.info(f"Truncated RFP length: {len(rfp_truncated)}")
            logger.info(f"Truncated proposal length: {len(proposal_truncated)}")

            logger.info("Invoking LLM for RFP summarization and cost estimation...")
            response = chain.invoke(
                {
                    "rfp_text": rfp_truncated,
                    "proposal_text": proposal_truncated,
                }
            )

            logger.info("Raw LLM response received")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response length: {len(str(response))}")
            logger.info(f"Raw response: {repr(response)}")

            # Clean and parse JSON response
            result = self._parse_json_response(response)

            logger.info(f"Parsed result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error summarizing RFP: {e}", exc_info=True)
            return {
                "rfp_summary": [f"Error occurred during summarization: {str(e)}"],
                "estimated_cost": {
                    "range_low": 0,
                    "range_high": 0,
                    "confidence_level": "low",
                    "basis_of_estimate": f"Unable to estimate due to error: {str(e)}",
                },
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
            # Look for JSON object with rfp_summary and estimated_cost fields
            json_match = re.search(
                r'\{[^{}]*"rfp_summary"[^{}]*"estimated_cost"[^{}]*\}',
                response,
                re.DOTALL,
            )
            if json_match:
                json_str = json_match.group()
                logger.info(f"Extracted JSON: {json_str}")
                result = json.loads(json_str)
                logger.info("Successfully parsed extracted JSON")
                return self._validate_result(result)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Regex JSON extraction failed: {e}")

        # Method 3: Fallback - try to extract components manually
        try:
            # Extract rfp_summary array
            rfp_summary_match = re.search(
                r'"rfp_summary"\s*:\s*\[([^\]]*)\]', response, re.DOTALL
            )

            # Extract estimated_cost object
            cost_match = re.search(
                r'"estimated_cost"\s*:\s*\{([^{}]*)\}', response, re.DOTALL
            )

            if rfp_summary_match and cost_match:
                # Parse rfp_summary
                summary_content = rfp_summary_match.group(1)
                summary_items = re.findall(r'"([^"]*)"', summary_content)
                rfp_summary = [item.strip() for item in summary_items if item.strip()]

                # Parse estimated_cost
                cost_content = cost_match.group(1)
                range_low_match = re.search(r'"range_low"\s*:\s*(\d+)', cost_content)
                range_high_match = re.search(r'"range_high"\s*:\s*(\d+)', cost_content)
                confidence_match = re.search(
                    r'"confidence_level"\s*:\s*"([^"]*)"', cost_content
                )
                basis_match = re.search(
                    r'"basis_of_estimate"\s*:\s*"([^"]*)"', cost_content, re.DOTALL
                )

                estimated_cost = {
                    "range_low": int(range_low_match.group(1))
                    if range_low_match
                    else 0,
                    "range_high": int(range_high_match.group(1))
                    if range_high_match
                    else 0,
                    "confidence_level": confidence_match.group(1)
                    if confidence_match
                    else "low",
                    "basis_of_estimate": basis_match.group(1)
                    if basis_match
                    else "Manual extraction fallback",
                }

                result = {"rfp_summary": rfp_summary, "estimated_cost": estimated_cost}

                logger.info("Successfully extracted components manually")
                return self._validate_result(result)
        except Exception as e:
            logger.warning(f"Manual extraction failed: {e}")

        # Method 4: Final fallback - create default response
        logger.error("All parsing methods failed, using default response")
        logger.error(f"Problematic response: {repr(response)}")

        return {
            "rfp_summary": [
                f"Unable to parse LLM response. Raw response: {response[:200]}..."
            ],
            "estimated_cost": {
                "range_low": 0,
                "range_high": 0,
                "confidence_level": "low",
                "basis_of_estimate": "Unable to parse LLM response",
            },
        }

    def _validate_result(self, result: Dict) -> Dict:
        """Validate and clean the parsed result."""
        if not isinstance(result, dict):
            raise ValueError(f"Result is not a dictionary: {type(result)}")

        # Validate rfp_summary
        if "rfp_summary" not in result:
            result["rfp_summary"] = ["No summary available"]

        if not isinstance(result["rfp_summary"], list):
            result["rfp_summary"] = [str(result["rfp_summary"])]

        # Ensure summary items are strings and not empty
        result["rfp_summary"] = [
            str(item).strip() for item in result["rfp_summary"] if str(item).strip()
        ]

        # Validate estimated_cost
        if "estimated_cost" not in result:
            result["estimated_cost"] = {
                "range_low": 0,
                "range_high": 0,
                "confidence_level": "low",
                "basis_of_estimate": "No cost estimate available",
            }

        cost_estimate = result["estimated_cost"]
        if not isinstance(cost_estimate, dict):
            cost_estimate = {
                "range_low": 0,
                "range_high": 0,
                "confidence_level": "low",
                "basis_of_estimate": "Invalid cost estimate format",
            }

        # Validate and sanitize cost ranges
        try:
            range_low = int(cost_estimate.get("range_low", 0))
            range_high = int(cost_estimate.get("range_high", 0))

            # Ensure ranges are non-negative and logical
            range_low = max(0, range_low)
            range_high = max(range_low, range_high)  # Ensure high >= low

            cost_estimate["range_low"] = range_low
            cost_estimate["range_high"] = range_high
        except (ValueError, TypeError):
            cost_estimate["range_low"] = 0
            cost_estimate["range_high"] = 0

        # Validate confidence level
        valid_confidence = ["low", "medium", "high"]
        confidence = cost_estimate.get("confidence_level", "low")
        if confidence not in valid_confidence:
            confidence = "low"
        cost_estimate["confidence_level"] = confidence

        # Ensure basis_of_estimate is a string
        if not isinstance(cost_estimate.get("basis_of_estimate"), str):
            cost_estimate["basis_of_estimate"] = "No basis provided"

        result["estimated_cost"] = cost_estimate

        return result
