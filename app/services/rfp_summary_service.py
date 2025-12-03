import json
import logging
import re
from typing import Dict, List, Tuple

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.prompts.prompts_v3 import (
    rfp_identification_template,
    summary_and_budget_template,
)

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

    async def identify_main_rfp(
        self, documents_with_filenames: List[Tuple[str, str]]
    ) -> Dict:
        """Identify which document is the main RFP from a list of documents."""
        if not documents_with_filenames:
            return {
                "identified_rfp_filename": "",
                "confidence_level": "low",
                "reasoning": "No documents provided",
            }

        if len(documents_with_filenames) == 1:
            return {
                "identified_rfp_filename": documents_with_filenames[0][0],
                "confidence_level": "high",
                "reasoning": "Only one document provided",
            }

        formatted_docs = ""
        for filename, content in documents_with_filenames:
            truncated_content = content[:2000] if content else ""
            formatted_docs += (
                f"\n\nFILENAME: {filename}\nCONTENT:\n{truncated_content}\n"
            )
            formatted_docs += "=" * 80

        prompt = PromptTemplate(
            input_variables=["documents_with_filenames"],
            template=rfp_identification_template,
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = await chain.ainvoke({"documents_with_filenames": formatted_docs})
            result = self._parse_identification_response(response)

            filenames = [doc[0] for doc in documents_with_filenames]
            if result["identified_rfp_filename"] not in filenames:
                result["identified_rfp_filename"] = filenames[0]
                result["confidence_level"] = "low"
                result["reasoning"] = "LLM identified unknown filename, defaulted to first document"

            return result

        except Exception as e:
            logger.error(f"Error identifying RFP: {e}")
            return {
                "identified_rfp_filename": documents_with_filenames[0][0],
                "confidence_level": "low",
                "reasoning": f"Error during identification: {str(e)}",
            }

    def _parse_identification_response(self, response: str) -> Dict:
        """Parse the JSON response from RFP identification."""
        if not response:
            raise ValueError("Empty response from LLM")

        try:
            result = json.loads(response.strip())
            return self._validate_identification_result(result)
        except json.JSONDecodeError:
            pass

        try:
            json_match = re.search(
                r'\{[^{}]*"identified_rfp_filename"[^{}]*\}',
                response,
                re.DOTALL,
            )
            if json_match:
                result = json.loads(json_match.group())
                return self._validate_identification_result(result)
        except (json.JSONDecodeError, AttributeError):
            pass

        raise ValueError(f"Could not parse identification response: {response}")

    def _validate_identification_result(self, result: Dict) -> Dict:
        """Validate and clean the identification result."""
        if not isinstance(result, dict):
            raise ValueError(f"Result is not a dictionary: {type(result)}")

        result.setdefault("identified_rfp_filename", "")
        result.setdefault("confidence_level", "low")
        result.setdefault("reasoning", "No reasoning provided")

        if result["confidence_level"] not in ["low", "medium", "high"]:
            result["confidence_level"] = "low"

        return result

    async def summarize_multiple_docs_and_estimate_cost(
        self,
        rfp_documents: List[Tuple[str, str]],
    ) -> Dict:
        """Async: Identify main RFP from multiple documents, then summarize and estimate cost."""
        logger.info("Starting multi-document RFP analysis")

        if not rfp_documents:
            logger.error("No RFP documents provided")
            return {
                "identified_rfp_filename": "",
                "rfp_summary": ["Error: No RFP documents provided"],
                "estimated_cost": {
                    "range_low": 0,
                    "range_high": 0,
                    "confidence_level": "low",
                    "basis_of_estimate": "No documents provided for analysis",
                },
            }

        identification_result = await self.identify_main_rfp(rfp_documents)
        identified_filename = identification_result["identified_rfp_filename"]

        rfp_text = ""
        for filename, content in rfp_documents:
            if filename == identified_filename:
                rfp_text = content
                break

        if not rfp_text:
            logger.error(
                f"Could not find content for identified RFP: {identified_filename}"
            )
            return {
                "identified_rfp_filename": identified_filename,
                "rfp_summary": ["Error: Could not find content for identified RFP"],
                "estimated_cost": {
                    "range_low": 0,
                    "range_high": 0,
                    "confidence_level": "low",
                    "basis_of_estimate": "Could not access identified RFP content",
                },
            }

        summary_result = await self.summarize_rfp_and_estimate_cost(rfp_text)

        result = {
            "identified_rfp_filename": identified_filename,
            "rfp_summary": summary_result["rfp_summary"],
            "estimated_cost": summary_result["estimated_cost"],
        }

        logger.info(
            f"Multi-document analysis complete. Identified RFP: {identified_filename}"
        )
        return result

    async def summarize_rfp_and_estimate_cost(
        self,
        rfp_text: str,
    ) -> Dict:
        """Summarize RFP and estimate cost with single LLM call."""
        if not rfp_text or not rfp_text.strip():
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
            input_variables=["rfp_text"],
            template=summary_and_budget_template,
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = await chain.ainvoke({"rfp_text": rfp_text[:8000]})
            return self._parse_summary_response(response)

        except Exception as e:
            logger.error(f"Error summarizing RFP: {e}")
            return {
                "rfp_summary": [f"Error occurred during summarization: {str(e)}"],
                "estimated_cost": {
                    "range_low": 0,
                    "range_high": 0,
                    "confidence_level": "low",
                    "basis_of_estimate": f"Unable to estimate due to error: {str(e)}",
                },
            }

    def _parse_summary_response(self, response: str) -> Dict:
        """Parse LLM response for summary and cost estimation."""
        if not response:
            return self._default_summary_response("Empty response from LLM")

        # Try direct JSON parsing
        try:
            result = json.loads(response.strip())
            return self._validate_summary_result(result)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON block
        try:
            json_match = re.search(
                r'\{[^{}]*"rfp_summary"[^{}]*"estimated_cost"[^{}]*\}',
                response,
                re.DOTALL,
            )
            if json_match:
                result = json.loads(json_match.group())
                return self._validate_summary_result(result)
        except (json.JSONDecodeError, AttributeError):
            pass

        # Manual extraction fallback
        try:
            rfp_summary_match = re.search(
                r'"rfp_summary"\s*:\s*\[([^\]]*)\]', response, re.DOTALL
            )
            cost_match = re.search(
                r'"estimated_cost"\s*:\s*\{([^{}]*)\}', response, re.DOTALL
            )

            if rfp_summary_match and cost_match:
                summary_content = rfp_summary_match.group(1)
                summary_items = re.findall(r'"([^"]*)"', summary_content)
                rfp_summary = [item.strip() for item in summary_items if item.strip()]

                cost_content = cost_match.group(1)
                range_low_match = re.search(r'"range_low"\s*:\s*(\d+)', cost_content)
                range_high_match = re.search(r'"range_high"\s*:\s*(\d+)', cost_content)
                confidence_match = re.search(r'"confidence_level"\s*:\s*"([^"]*)"', cost_content)
                basis_match = re.search(r'"basis_of_estimate"\s*:\s*"([^"]*)"', cost_content, re.DOTALL)

                estimated_cost = {
                    "range_low": int(range_low_match.group(1)) if range_low_match else 0,
                    "range_high": int(range_high_match.group(1)) if range_high_match else 0,
                    "confidence_level": confidence_match.group(1) if confidence_match else "low",
                    "basis_of_estimate": basis_match.group(1) if basis_match else "Manual extraction fallback",
                }

                result = {"rfp_summary": rfp_summary, "estimated_cost": estimated_cost}
                return self._validate_summary_result(result)
        except Exception:
            pass

        return self._default_summary_response(f"Unable to parse response: {response[:200]}...")

    def _default_summary_response(self, error_msg: str) -> Dict:
        """Return default response for parsing failures."""
        return {
            "rfp_summary": [error_msg],
            "estimated_cost": {
                "range_low": 0,
                "range_high": 0,
                "confidence_level": "low",
                "basis_of_estimate": "Unable to parse LLM response",
            },
        }

    def _validate_summary_result(self, result: Dict) -> Dict:
        """Validate and clean the summary result."""
        if not isinstance(result, dict):
            return self._default_summary_response("Invalid result format")

        # Validate summary
        if "rfp_summary" not in result or not isinstance(result["rfp_summary"], list):
            result["rfp_summary"] = ["No summary available"]
        
        result["rfp_summary"] = [
            str(item).strip() for item in result["rfp_summary"] if str(item).strip()
        ]

        # Validate cost estimate
        if "estimated_cost" not in result or not isinstance(result["estimated_cost"], dict):
            result["estimated_cost"] = {
                "range_low": 0,
                "range_high": 0,
                "confidence_level": "low",
                "basis_of_estimate": "No cost estimate available",
            }

        cost_estimate = result["estimated_cost"]
        
        # Validate numeric ranges
        try:
            range_low = max(0, int(cost_estimate.get("range_low", 0)))
            range_high = max(range_low, int(cost_estimate.get("range_high", 0)))
            cost_estimate["range_low"] = range_low
            cost_estimate["range_high"] = range_high
        except (ValueError, TypeError):
            cost_estimate["range_low"] = 0
            cost_estimate["range_high"] = 0

        # Validate confidence level
        if cost_estimate.get("confidence_level") not in ["low", "medium", "high"]:
            cost_estimate["confidence_level"] = "low"

        # Ensure basis is string
        if not isinstance(cost_estimate.get("basis_of_estimate"), str):
            cost_estimate["basis_of_estimate"] = "No basis provided"

        return result
