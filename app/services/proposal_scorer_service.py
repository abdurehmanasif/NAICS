from typing import Dict
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging
import json
import re

from ..config import (
    DEFAULT_LLM_MODEL_OPENAI,
    DEFAULT_LLM_MODEL_GOOGLE,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    GOOGLE_API_KEY,
)

logger = logging.getLogger(__name__)


class ProposalScorerService:
    """Simple proposal scorer with single LLM call."""

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

    def score_proposal(
        self,
        rfp_text: str,
        proposal_text: str,
        naics_code: str = None,
        naics_code_description: str = None,
    ) -> Dict:
        """Score proposal with single LLM call."""
        logger.info("Starting proposal scoring")
        logger.info(f"RFP text length: {len(rfp_text)} characters")
        logger.info(f"Proposal text length: {len(proposal_text)} characters")

        # Validate inputs
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
            template="""You are a senior government contracting officer and proposal evaluator with 25+ years of experience evaluating federal solicitations. You have expertise in FAR/DFARS requirements, industry standards, and competitive analysis across all federal agencies.

EVALUATION CONTEXT:
NAICS Code: {naics_code}
NAICS Description: {naics_code_description}

RFP/SOLICITATION REQUIREMENTS:
{rfp_text}

PROPOSAL TO EVALUATE:
{proposal_text}

COMPREHENSIVE EVALUATION FRAMEWORK:

Execute a thorough evaluation using these weighted criteria (simulate actual government evaluation):

1. COMPLIANCE ANALYSIS (25% weight):
   - Verify ALL mandatory requirements are addressed explicitly
   - Check for required certifications, representations, and documentation
   - Assess adherence to submission format and page limits
   - Identify any non-responsive elements that could cause rejection
   - Evaluate use of RFP terminology and cross-referencing

2. TECHNICAL APPROACH (35% weight):
   - Assess technical soundness and feasibility of proposed solution
   - Evaluate methodology depth and industry best practices
   - Check for innovation and value-added approaches
   - Analyze risk identification and mitigation strategies
   - Review quality control and performance measurement plans
   - Assess understanding of government requirements and constraints

3. PAST PERFORMANCE & QUALIFICATIONS (20% weight):
   - Evaluate relevance and recency of cited experience
   - Assess contract performance history and customer satisfaction
   - Review technical capabilities and organizational capacity
   - Check for progressive capability development
   - Evaluate subcontractor qualifications if applicable

4. PERSONNEL & MANAGEMENT (10% weight):
   - Assess key personnel qualifications and availability
   - Review organizational structure and reporting relationships
   - Evaluate management approach and oversight procedures
   - Check for appropriate staffing levels and skill mix
   - Assess succession planning and personnel retention

5. COST/PRICE REALISM (10% weight):
   - Evaluate cost structure and pricing strategy
   - Assess basis of estimate and cost build-up logic
   - Review value proposition and cost-effectiveness
   - Check for competitive positioning within market range
   - Evaluate cost control measures and efficiencies

INDUSTRY-SPECIFIC EVALUATION (NAICS-focused):
- Assess compliance with industry-specific regulations and standards
- Evaluate understanding of sector-specific challenges and solutions
- Check for appropriate certifications and qualifications
- Review adherence to industry best practices and benchmarks
- Assess competitive positioning within the specific NAICS sector

COMPETITIVE ANALYSIS BENCHMARKS:
Consider these factors when scoring:
- How does this proposal compare to typical submissions in this NAICS sector?
- Does it demonstrate superior understanding of customer needs?
- Are there clear differentiators that would make this proposal stand out?
- Does it address evaluator concerns proactively?
- Is the risk profile acceptable for the proposed approach?

EVALUATION METHODOLOGY:
1. Identify RFP evaluation criteria and their weights (if specified)
2. Map proposal content to each evaluation criterion
3. Assess strengths and weaknesses in each area
4. Consider discriminators that separate this from competitors
5. Evaluate overall win probability and competitive positioning

SCORING CALIBRATION:
- 0-2: UNACCEPTABLE - Major deficiencies, non-responsive, high risk of rejection
- 3-4: POOR - Significant weaknesses, marginal responsiveness, needs major revision
- 5-6: ACCEPTABLE - Adequate response, meets minimums, competitive but not standout
- 7-8: GOOD - Strong response, exceeds some requirements, competitive advantage
- 9-10: EXCEPTIONAL - Outstanding response, exceeds most requirements, clear winner

CRITICAL EVALUATION AREAS:
Focus particularly on:
- Compliance gaps that could cause automatic rejection
- Technical approach weaknesses that increase performance risk
- Past performance deficiencies that reduce confidence
- Cost/price issues that affect competitiveness
- Presentation quality that impacts evaluator perception

CRITICAL VALIDATION CHECKS (Perform BEFORE evaluation):

1. DOCUMENT TYPE VALIDATION:
   - Verify the proposal_text contains an actual business proposal/bid response
   - Check if RFP_text contains solicitation requirements, not random content
   - Ensure documents are business-related and appropriate for evaluation

2. EDGE CASE HANDLING:
   - If proposal_text is clearly not a proposal (e.g., personal documents, random text, code, recipes, etc.), return score 0
   - If RFP_text is not a solicitation/RFP (e.g., novels, articles, personal content), return score 0
   - If documents are in wrong language or corrupted/unreadable, return score 0
   - If proposal_text is empty or contains only placeholder text, return score 0
   - If content appears to be malicious, inappropriate, or irrelevant, return score 0

3. QUALITY THRESHOLDS:
   - If proposal is less than 200 words, likely incomplete - maximum score 3
   - If proposal doesn't address any RFP requirements, maximum score 2
   - If proposal is generic template without customization, maximum score 4

You MUST respond with valid JSON in this exact format (no additional text before or after):
{{
    "score": 7,
    "suggestion": "Brief explanation of the score and specific suggestions for improvement"
}}

EDGE CASE RESPONSES:
- If not a proposal: {{"score": 0, "suggestion": "The submitted document does not appear to be a business proposal. Please submit an actual proposal document for evaluation."}}
- If not an RFP: {{"score": 0, "suggestion": "The RFP document does not appear to be a valid solicitation. Please provide a proper RFP or solicitation document."}}
- If inappropriate content: {{"score": 0, "suggestion": "The submitted content is not appropriate for proposal evaluation. Please submit relevant business documents."}}
- If empty/minimal: {{"score": 0, "suggestion": "The proposal appears to be empty or contains insufficient content for evaluation. Please submit a complete proposal."}}
- If corrupted/unreadable: {{"score": 0, "suggestion": "The document appears to be corrupted or unreadable. Please resubmit in a readable format."}}

EVALUATION STANDARDS:
- Base evaluation on actual government contracting standards
- Consider typical competition level in this NAICS sector
- Apply industry-specific technical and regulatory knowledge
- Focus on actionable, specific feedback for improvement
- Provide realistic win probability assessment
- Consider both technical merit and competitive positioning

Execute this evaluation with the rigor of an actual government source selection evaluation board.""",
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            # Truncate inputs to avoid token limits
            rfp_truncated = rfp_text[:8000]
            proposal_truncated = proposal_text[:12000]

            logger.info(f"Truncated RFP length: {len(rfp_truncated)}")
            logger.info(f"Truncated proposal length: {len(proposal_truncated)}")

            logger.info("Invoking LLM for scoring...")
            response = chain.invoke(
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

            # Clean and parse JSON response
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

        # Ensure score is a number between 0-10
        try:
            score = float(result["score"])
            result["score"] = max(0, min(10, score))  # Clamp between 0-10
        except (ValueError, TypeError):
            logger.warning(f"Invalid score format: {result['score']}, defaulting to 0")
            result["score"] = 0

        # Ensure suggestion is a string
        if not isinstance(result["suggestion"], str):
            result["suggestion"] = str(result["suggestion"])

        return result
