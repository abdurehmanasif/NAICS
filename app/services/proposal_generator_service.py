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
            template="""You are an expert federal government proposal writer with 20+ years of experience winning competitive solicitations. Create a comprehensive, compelling proposal response that maximizes win probability.

RFP Requirements:
{rfp_text}

Company/Knowledge Base Information:
{kb_text}

NAICS Code: {naics_code}
NAICS Description: {naics_code_description}

CRITICAL INSTRUCTIONS FOR WINNING PROPOSALS:

1. COMPLIANCE FIRST:
   - Address EVERY requirement explicitly with clear headers
   - Use exact terminology from the RFP
   - Include all required certifications, representations, and documentation references
   - Cross-reference RFP sections (e.g., "As required in Section 3.2...")

2. STRUCTURE (Use this exact format):
   - Executive Summary (2-3 pages max)
   - Technical Approach (most critical section)
   - Past Performance & Company Qualifications
   - Personnel & Management Plan
   - Implementation Timeline & Project Management
   - Quality Control & Risk Management
   - Cost/Price Analysis & Value Proposition
   - Conclusion

3. TECHNICAL APPROACH REQUIREMENTS:
   - Lead with understanding of the requirement
   - Provide detailed methodology for each deliverable
   - Include specific processes, procedures, and protocols
   - Address potential challenges and mitigation strategies
   - Demonstrate innovation and best practices
   - Use active voice and confident language
   - Include technical specifications and standards compliance

4. PAST PERFORMANCE:
   - Provide 3-5 highly relevant contract examples
   - Include contract numbers, values, dates, and customer contacts
   - Quantify achievements (cost savings, performance metrics, schedule adherence)
   - Address any performance issues proactively
   - Demonstrate progressive capability growth

5. PERSONNEL SECTION:
   - Include detailed resumes for key personnel
   - Highlight relevant certifications and clearances
   - Show organizational chart and reporting structure
   - Demonstrate personnel availability and commitment
   - Include succession planning for key roles

6. IMPLEMENTATION PLAN:
   - Provide detailed project schedule with milestones
   - Include resource allocation and staffing plans
   - Address transition planning and startup activities
   - Show phase-gate approach with deliverables
   - Include contingency planning

7. QUALITY CONTROL:
   - Detailed Quality Control Plan (QCP) with specific procedures
   - Include inspection and testing protocols
   - Define performance metrics and KPIs
   - Address corrective action procedures
   - Include customer satisfaction measurement

8. COST STRATEGY:
   - Provide detailed cost breakdowns by CLIN
   - Include basis of estimate explanations
   - Demonstrate cost realism and competitiveness
   - Address cost control measures
   - Include value engineering opportunities

9. WRITING STYLE:
   - Use government contracting terminology correctly
   - Write in active voice with confident assertions
   - Include specific metrics and quantifiable benefits
   - Use bullet points for readability but maintain narrative flow
   - Include relevant regulations and standards (FAR, DFARS, etc.)

10. DIFFERENTIATORS:
    - Clearly articulate unique value proposition
    - Include innovative approaches or technologies
    - Demonstrate superior understanding of customer needs
    - Show cost-effective solutions
    - Include relevant partnerships or teaming arrangements

11. RISK MANAGEMENT:
    - Identify potential risks and mitigation strategies
    - Include contingency planning
    - Address schedule, technical, and cost risks
    - Show proactive risk monitoring approaches

12. COMPLIANCE MATRIX:
    - Create a compliance matrix showing RFP requirement and proposal response location
    - Ensure no requirements are missed

ADDITIONAL GUIDANCE:
- If knowledge base is limited, create realistic but impressive capabilities
- Use industry best practices and standards
- Include relevant case studies and success stories
- Ensure all claims are supportable and realistic
- Create a compelling narrative that flows logically
- Use professional formatting with clear headings and subheadings
- Include appendices for supporting documentation references

TONE AND APPROACH:
- Professional, confident, and authoritative
- Customer-focused with clear understanding of their needs
- Results-oriented with emphasis on outcomes
- Collaborative while demonstrating independence
- Compliant while showing innovation

WINNING STRATEGIES:
- Demonstrate deep understanding of the requirement
- Show how you'll exceed minimum requirements
- Include value-added services at no additional cost
- Highlight relevant experience and lessons learned
- Show commitment to long-term partnership
- Include local hiring and small business utilization where applicable

Generate a complete, professional proposal that follows all these guidelines and maximizes the probability of contract award. The proposal should be detailed enough to serve as a blueprint for contract execution while being compelling enough to win against strong competition.

IMPORTANT: Address every RFP requirement explicitly and provide specific, actionable responses rather than generic statements. Use the knowledge base information strategically to demonstrate capabilities and past performance.""",
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
