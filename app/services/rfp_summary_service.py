import json
import logging
import re
from typing import Dict, List, Tuple

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.services.prompts_v2 import (
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
    """Async service for summarizing RFPs and estimating costs."""

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

    async def identify_main_rfp(
        self, documents_with_filenames: List[Tuple[str, str]]
    ) -> Dict:
        """Async: Identify which document is the main RFP from a list of documents."""
        logger.info("Starting RFP identification")
        logger.info(f"Number of documents to analyze: {len(documents_with_filenames)}")

        if not documents_with_filenames:
            logger.error("No documents provided for RFP identification")
            return {
                "identified_rfp_filename": "",
                "confidence_level": "low",
                "reasoning": "No documents provided",
            }

        if len(documents_with_filenames) == 1:
            logger.info("Only one document provided, using it as RFP")
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
            logger.info("Invoking LLM for RFP identification...")
            response = await chain.ainvoke({"documents_with_filenames": formatted_docs})

            logger.info("Raw LLM response for identification received")
            logger.info(f"Response: {response}")

            result = self._parse_identification_response(response)

            filenames = [doc[0] for doc in documents_with_filenames]
            if result["identified_rfp_filename"] not in filenames:
                logger.warning(
                    f"LLM identified filename not in document list: {result['identified_rfp_filename']}"
                )
                result["identified_rfp_filename"] = filenames[0]
                result["confidence_level"] = "low"
                result["reasoning"] = (
                    "LLM identified unknown filename, defaulted to first document"
                )

            logger.info(f"Identified RFP: {result['identified_rfp_filename']}")
            return result

        except Exception as e:
            logger.error(f"Error identifying RFP: {e}", exc_info=True)
            return {
                "identified_rfp_filename": documents_with_filenames[0][0],
                "confidence_level": "low",
                "reasoning": f"Error during identification, defaulted to first document: {str(e)}",
            }

    def _parse_identification_response(self, response: str) -> Dict:
        """Parse the JSON response from RFP identification."""
        if not response:
            raise ValueError("Empty response from LLM")

        try:
            result = json.loads(response.strip())
            logger.info("Successfully parsed identification JSON directly")
            return self._validate_identification_result(result)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parsing failed: {e}")

        try:
            json_match = re.search(
                r'\{[^{}]*"identified_rfp_filename"[^{}]*\}',
                response,
                re.DOTALL,
            )
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                logger.info("Successfully parsed extracted identification JSON")
                return self._validate_identification_result(result)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Regex JSON extraction failed: {e}")

        logger.error("Failed to parse identification response")
        raise ValueError(f"Could not parse identification response: {response}")

    def _validate_identification_result(self, result: Dict) -> Dict:
        """Validate and clean the identification result."""
        if not isinstance(result, dict):
            raise ValueError(f"Result is not a dictionary: {type(result)}")

        if "identified_rfp_filename" not in result:
            result["identified_rfp_filename"] = ""

        if "confidence_level" not in result:
            result["confidence_level"] = "low"

        if "reasoning" not in result:
            result["reasoning"] = "No reasoning provided"

        valid_confidence = ["low", "medium", "high"]
        if result["confidence_level"] not in valid_confidence:
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
        """Async: Summarize RFP and estimate cost with single LLM call using ainvoke."""
        logger.info("Starting RFP summarization and cost estimation")
        logger.info(f"RFP text length: {len(rfp_text)} characters")

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
            input_variables=["rfp_text"],
            template=summary_and_budget_template,
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            rfp_truncated = rfp_text[:8000]

            logger.info(f"Truncated RFP length: {len(rfp_truncated)}")

            logger.info("Invoking LLM for RFP summarization and cost estimation...")
            response = await chain.ainvoke({"rfp_text": rfp_truncated})

            logger.info("Raw LLM response received")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response length: {len(str(response))}")
            logger.info(f"Raw response: {repr(response)}")

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

        try:
            result = json.loads(response.strip())
            logger.info("Successfully parsed JSON directly")
            return self._validate_result(result)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parsing failed: {e}")

        try:
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

        if "rfp_summary" not in result:
            result["rfp_summary"] = ["No summary available"]

        if not isinstance(result["rfp_summary"], list):
            result["rfp_summary"] = [str(result["rfp_summary"])]

        result["rfp_summary"] = [
            str(item).strip() for item in result["rfp_summary"] if str(item).strip()
        ]

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

        try:
            range_low = int(cost_estimate.get("range_low", 0))
            range_high = int(cost_estimate.get("range_high", 0))

            range_low = max(0, range_low)
            range_high = max(range_low, range_high)

            cost_estimate["range_low"] = range_low
            cost_estimate["range_high"] = range_high
        except (ValueError, TypeError):
            cost_estimate["range_low"] = 0
            cost_estimate["range_high"] = 0

        valid_confidence = ["low", "medium", "high"]
        confidence = cost_estimate.get("confidence_level", "low")
        if confidence not in valid_confidence:
            confidence = "low"
        cost_estimate["confidence_level"] = confidence

        if not isinstance(cost_estimate.get("basis_of_estimate"), str):
            cost_estimate["basis_of_estimate"] = "No basis provided"

        result["estimated_cost"] = cost_estimate

        return result
