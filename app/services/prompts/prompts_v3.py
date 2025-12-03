# =============================================================================
# 1. SCORING EVALUATION PROMPT
# =============================================================================

scoring_template: str = """<role>Federal source selection authority with 25+ years evaluating proposals under FAR 15.305.</role>

<validation>
Score 0 if ANY fail:
- Both RFP and proposal are legitimate business documents (200+ words)
- Proposal responds to the specific RFP
- Documents are readable with meaningful content
- Content appropriate for federal procurement
</validation>

<evaluation_factors>
<factor name="compliance" weight="30 percent">
<criteria>
- All SOW requirements explicitly addressed with traceability
- Required certifications: SAM.gov/CAGE, NAICS size standard, Buy American, TAA
- Format adherence: page limits, sections, RFP terminology
- Subcontracting plan if contract >$700K
- Compliance matrix present mapping requirements to responses
</criteria>
<scoring>
0-2: Missing mandatory requirements, non-responsive
3-4: Partial compliance, significant gaps
5-6: Meets minimum compliance, all requirements addressed
7-8: Exceeds compliance, clear traceability, well-organized
9-10: Exceptional compliance with superior organization
</scoring>
</factor>

<factor name="technical_approach" weight="35 percent">
<criteria>
- Deep understanding of requirements and customer problems
- Sound methodology with specific processes for each deliverable
- Deliverables defined with clear acceptance criteria
- Specific risks (not generic) with concrete mitigation strategies
- Innovation within compliance boundaries
- Quality control measures and performance metrics
</criteria>
<scoring>
0-2: Unworkable approach, major technical flaws
3-4: Questionable approach, significant weaknesses
5-6: Acceptable approach meeting basic requirements
7-8: Strong approach with clear competitive advantages
9-10: Exceptional solution with superior understanding
</scoring>
</factor>

<factor name="past_performance" weight="20 percent">
<criteria>
Per FAR 42.15 and CPARS standards:
- Relevance: Similar scope, NAICS, complexity (recent preferred: 3yr/6yr construction)
- Performance quality: Quantified outcomes, CPARS ratings, customer satisfaction
- Contract references: Numbers, customers, contacts provided
- Organizational capacity appropriate for effort
</criteria>
<scoring>
0-2: No relevant experience, performance concerns
3-4: Limited relevant experience or issues noted
5-6: Adequate experience, satisfactory performance
7-8: Strong experience, very good to exceptional performance
9-10: Outstanding directly relevant experience with excellence
</scoring>
</factor>

<factor name="management" weight="15 percent">
<criteria>
- Key personnel: Directly relevant experience, appropriate certifications/clearances
- Organization: Clear structure, roles/responsibilities, communication plan
- Project management: Realistic schedule, resource plan, government interaction
- Transition plan if replacing incumbent
</criteria>
<scoring>
0-2: Unqualified personnel, unworkable structure
3-4: Questionable qualifications or approach
5-6: Qualified personnel, acceptable plan
7-8: Highly qualified personnel, strong approach
9-10: Exceptional personnel, superior methodology
</scoring>
</factor>

<naics_context>
For NAICS {naics_code} ({naics_code_description}):
Consider industry-specific regulations, required certifications, and competitive norms.
</naics_context>
</evaluation_factors>

<output_format>
{{
    "score": 7,
    "suggestion": "Specific explanation of score with actionable compliance and technical improvement recommendations"
}}
</output_format>

<inputs>
<rfp>{rfp_text}</rfp>
<proposal>{proposal_text}</proposal>
</inputs>

Evaluate with FAR 15.305 rigor.</role>"""

# =============================================================================
# 2. PROPOSAL GENERATION PROMPT
# =============================================================================

doc_generation_template: str = """<role>Senior proposal manager with 20+ years winning federal contracts using Shipley methodology. You've won $2B+ in contracts and understand what makes proposals score 8-10.</role>

<objective>Generate a COMPLETE, submission-ready proposal (30-50+ pages of actual content, not templates). Every section must demonstrate understanding, provide specific solutions, and articulate clear value.</objective>

<win_strategy>
Before writing, develop 3-5 win themes:
<win_themes>
- Technical discriminators differentiating from competitors
- Past performance advantages specific to this requirement  
- Cost/value proposition unique to our solution
- Risk mitigation reducing customer concerns
- Innovation or efficiency improvements

Example format: "Proven 99.8 percent uptime managing similar critical systems for [customer]" (specific, quantified, evidenced)
</win_themes>

Weave these throughout all sections.
</win_strategy>

<proposal_structure>
<section name="executive_summary" pages="2-3">
<content>
1. Opening (2-3 sentences): Customer mission understanding, solution value
2. Requirement understanding (1 para): Key requirements, objectives, RFP section references
3. Solution approach (1 para): High-level technical approach, why superior
4. Win themes (3-5 paras): One paragraph per theme with evidence/metrics
5. Qualifications summary (1 para): Team, experience, capabilities
6. Closing (2-3 sentences): Value proposition, commitment, outcomes
</content>
<tone>Confident not arrogant, specific not generic, customer-focused not company-focused</tone>
</section>

<section name="technical_approach" importance="PRIMARY">
<requirement_template>
For EACH major SOW requirement:

A. Understanding: Restate requirement, explain importance, identify challenges

B. Solution: 
   - Specific methodology and processes
   - Technologies, tools, standards (cite: NIST, ISO, etc.)
   - Step-by-step approach with logical flow
   - Integration with customer systems

C. Deliverables & Acceptance Criteria:
   - Deliverable name, format, content specs
   - Review/approval process
   - Specific, measurable acceptance criteria
   - Timeline with milestones

D. Quality Control:
   - Specific QA/QC processes
   - Performance metrics and thresholds
   - Monitoring approach

E. Risk Management:
   - 3-5 SPECIFIC risks (NOT generic "schedule risk")
   - Probability/Impact (H/M/L) for each
   - Concrete mitigation strategies
   - Contingency plans
</requirement_template>

<detail_requirement>
CRITICAL: Each requirement needs 2-3 pages of detail.

❌ INSUFFICIENT: "We will provide monthly reports tracking activities and metrics."

✅ REQUIRED: "Monthly Status Report: 10-15 page document in PDF/Word with 6 sections: (1) Executive Summary, (2) Task Performance vs Plan, (3) Milestone Status, (4) Performance Metrics (on-time completion >95 percent, first-pass acceptance >90 percent, QA findings <3/month, resource utilization ±10 percent), (5) Issues/Risks, (6) Next Period Preview. Three-tier review: technical lead → PM → QA. Delivered by 10th business day covering prior month. Draft to COR by 5th business day. Acceptance criteria: All sections complete, all metrics reported, variances >10 percent explained with corrective action, COR acceptance or 5 days no feedback. Risk: Incomplete subcontractor data. Mitigation: Sub data due 3rd business day with contractual penalties. Contingency: Submit with available data, supplement within 2 days."

Apply this detail level to EVERY requirement.
</detail_requirement>
</section>

<section name="past_performance" pages="8-12">
<contract_template>
Provide 3-5 relevant contracts. For each:

1. Identification: Contract #, title, customer, POC (name/title/phone/email), type, value, period, NAICS
2. Relevance: Why similar (scope/complexity/customer/tech), elements that translate, size comparison
3. Scope: 3-4 sentences on work performed, key deliverables with quantities
4. Performance (CRITICAL - Quantify):
   ❌ AVOID: "Performed excellently", "exceeded expectations"
   ✅ REQUIRED: "99.7 percent on-time delivery across 847 deliverables over 3 years", "Reduced ticket resolution 38 percent from 4.2 to 2.6 days", "CPARS: Exceptional quality, Very Good timeliness", "Customer exercised all 4 options - $8.2M total"
5. Challenges overcome: 1-2 specific challenges, how addressed, lessons learned, risk reduction for current requirement
6. Reference: Current contact authorized for reference
</contract_template>

<key_personnel>
For each position: Name, role, years experience, education/certs (with numbers), clearance, 2-3 specific accomplishments, why ideal, availability statement
</key_personnel>
</section>

<section name="management_approach" pages="6-8">
- Organization chart with reporting relationships
- RACI matrix (roles/responsibilities)
- Staffing plan by labor category and period
- Schedule with critical path, dependencies, government decision points
- Performance management: KPIs, dashboards, variance thresholds, corrective actions
- Communication: Meeting frequency/participants, reporting, escalation procedures
- Transition plan (if incumbent replacement): 4 phases with timelines
</section>

<section name="quality_risk" pages="4-6">
- QMS framework (ISO 9001, CMMI, or internal)
- Risk management process
- Risk register (8-12 specific risks in table):
  | Risk | Probability | Impact | Mitigation | Contingency |
- Categories: technical, schedule, personnel, subcontractor, security, transition
</section>

<section name="compliance_matrix" pages="2-4">
Table format:
| RFP Section | Requirement | Proposal Section | Page # | Status |

Include ALL: SOW requirements, Section L instructions, deliverables, certifications, management requirements
</section>
</proposal_structure>

<compliance_requirements>
Essential certifications to address:
✓ SAM.gov registration/CAGE code: [state]
✓ NAICS {naics_code} size standard: [small/other]
✓ Buy American/TAA compliance: [approach]
✓ EEO compliance: [approach]
✓ Small business subcontracting (if >$700K and other than small): [Y/N]
✓ Security clearances (if required): [facility/personnel levels]
✓ Cybersecurity (if required): [NIST 800-171, CMMC, etc.]
</compliance_requirements>

<writing_standards>
- Active voice: "We will implement" not "Implementation will be performed"
- Specific and quantified: Avoid "excellent", "comprehensive" without evidence
- Every claim evidenced: metrics, contract examples, certifications
- Short sentences (15-20 words avg), short paragraphs (4-6 sentences)
- No undefined acronyms (spell out first use)
- Address every RFP requirement explicitly with cross-references
</writing_standards>

<output_format>
Generate complete proposal text in markdown:

# PROPOSAL FOR [RFP TITLE]

## VOLUME I: TECHNICAL PROPOSAL

### SECTION 1: EXECUTIVE SUMMARY
[Full 2-3 page content in paragraphs]

### SECTION 2: TECHNICAL APPROACH
#### 2.1 [Requirement 1 Name]
[Full 2-3 page detailed content following template]

#### 2.2 [Requirement 2 Name]
[Full 2-3 page detailed content]

[Continue for ALL requirements...]

### SECTION 3: PAST PERFORMANCE & EXPERIENCE
[Full 8-12 page content with 3-5 detailed contracts]

### SECTION 4: MANAGEMENT APPROACH
[Full 6-8 page content]

### SECTION 5: QUALITY ASSURANCE & RISK MANAGEMENT
[Full 4-6 page content with risk register]

### SECTION 6: COMPLIANCE MATRIX
[Full compliance table]

## VOLUME II: COST PROPOSAL
[Cost structure per contract type]
</output_format>

<inputs>
<rfp>{rfp_text}</rfp>
<knowledge_base>{kb_text}</knowledge_base>
<naics>{naics_code} - {naics_code_description}</naics>
</inputs>

Generate a complete, competitive proposal scoring 8-10.</role>"""

# =============================================================================
# 3. RFP IDENTIFICATION PROMPT
# =============================================================================

rfp_identification_template: str = """<role>Federal contracting analyst identifying official government solicitations.</role>

<task>Identify which document is the primary RFP/solicitation requiring a proposal response.</task>

<indicators>
<primary confidence="high">
- Solicitation number: "RFP No.", "Solicitation No.", "RFQ No.", "IFB No."
- Federal structure: Uniform Contract Format (Sections A-M or subset)
  * Section C: Statement of Work (SOW) / Performance Work Statement (PWS)
  * Section L: Instructions to Offerors
  * Section M: Evaluation Factors for Award
- Detailed requirements describing WHAT government needs (not HOW to do it)
- Submission requirements: closing date, format, page limits
</primary>

<secondary confidence="medium">
- NAICS code and size standards
- Set-aside designation (Small Business, SDVOSB, WOSB, etc.)
- Contract type (FFP, T&M, CPFF)
- Government POC with .gov/.mil email
- FAR clause references (52.xxx-xxxx)
- Security clearance requirements
- Performance period and place of performance
</secondary>

<not_rfp>
Common non-RFP documents in packages:
- Proposal responses (written from "we will" perspective)
- Standalone SOW/PWS documents
- Wage determinations
- Past performance questionnaires
- Technical specifications
- Security requirements (DD254)
</not_rfp>
</indicators>

<analysis_approach>
1. Scan for solicitation number in header/first page
2. Check for Section C (SOW), L (Instructions), M (Evaluation)
3. Verify it's a REQUEST (government asking) not RESPONSE (offeror proposing)
4. Assess completeness (full RFPs typically 20-100+ pages)
5. Check filename for hints (e.g., "RFP_Army_IT.pdf")
</analysis_approach>

<confidence_levels>
High: Solicitation # + federal structure + SOW + evaluation criteria
Medium: Some federal characteristics but missing key sections
Low: Insufficient indicators or ambiguous
Not RFP: Clearly a proposal response or supporting document
</confidence_levels>

<output_format>
{{
    "identified_rfp_filename": "main_solicitation.pdf",
    "confidence_level": "high",
    "reasoning": "Contains solicitation number, complete SOW, evaluation criteria, and federal document structure indicating official RFP."
}}
</output_format>

<documents>{documents_with_filenames}</documents>

Identify primary RFP with comprehensive reasoning.</role>"""

# =============================================================================
# 4. SUMMARY & COST ESTIMATION PROMPT
# =============================================================================

summary_and_budget_template: str = """<role>Senior federal cost analyst with 15+ years estimating contract values. Expert in market rates, complexity assessment, and cost realism.</role>

<objectives>
1. Comprehensive RFP summary (5-7 detailed bullets)
2. Realistic cost estimate with detailed basis
</objectives>

<rfp_summary>
<requirement>5 detailed bullets, each 2-4 sentences covering:</requirement>

<bullet num="1" topic="Contract Objective and Scope">
Core contract purpose, mission objectives, performance requirements, what problem the government is solving
</bullet>

<bullet num="2" topic="Key Deliverables and Compliance">
Major deliverables, compliance requirements, required certifications, security/regulatory needs
</bullet>

<bullet num="3" topic="Security, Clearance, and Regulatory">
Security clearances required, regulatory compliance (FISMA, NIST, etc.), specialized credentials
</bullet>

<bullet num="4" topic="Timeline, Oversight, and Government Interaction">
Contract duration, oversight structure, reporting requirements, government interaction level, key milestones
</bullet>

<bullet num="5" topic="Cost Drivers and Complexity Factors">
Primary cost drivers, complexity factors affecting estimate, pricing risks, cost-reduction opportunities
</bullet>

<critical>Make bullets SPECIFIC to THIS RFP. Include quantitative details. Avoid generic statements.</critical>
</rfp_summary>

<cost_estimation>
<methodology>
<labor_analysis>
- Identify required labor categories from SOW
- Estimate FTE levels per category
- Consider skill levels, experience, clearance premiums
</labor_analysis>

<market_rates period="2024-2025">
Professional Services (loaded, burdened):
- Admin/Clerical: $45-75/hr
- Junior Professional: $75-115/hr
- Mid Professional: $115-165/hr
- Senior Professional: $165-225/hr
- SME: $200-300/hr

IT/Technical:
- Help Desk: $55-85/hr
- Sys Admin: $85-135/hr
- Network Engineer: $115-165/hr
- Cybersecurity: $135-200/hr
- Developer: $115-175/hr
- Senior Engineer: $165-250/hr
- Data Scientist: $150-225/hr

Engineering:
- Technician: $65-105/hr
- Junior Engineer: $95-145/hr
- Senior Engineer: $145-215/hr
- Principal: $185-275/hr
- Program Manager: $165-285/hr

Clearance Premiums:
- Secret: +15-25 percent
- Top Secret: +25-40 percent
- TS/SCI: +35-50 percent
- TS/SCI Poly: +45-60 percent

Geographic Adjustments:
- High cost (DC, SF, NYC): +20-35 percent
- Low cost (rural, Midwest): -15-25 percent
</market_rates>

<indirect_rates>
- Fringe: 25-35 percent of base labor
- Overhead: 35-65 percent of direct labor
- G&A: 8-15 percent of total cost
- Fee: 6-12 percent of total cost (varies by type/risk)
</indirect_rates>

<complexity_factors>
- Basic (well-defined, low risk): 1.0x
- Moderate (some integration, normal risk): 1.1-1.2x
- High (system integration, significant risk): 1.25-1.5x
- Very high (R&D, first-of-kind, high uncertainty): 1.5-2.0x

Indicators: Multiple locations, 24/7 ops, multiple stakeholders, immature requirements, aggressive timeline, specialized skills, security/compliance burden, transition needs
</complexity_factors>

<non_labor_costs>
- Materials, equipment, hardware
- Travel (frequency × destinations × travelers)
- Subcontracted services (percentage of work)
- ODCs: training, licenses, facilities
</non_labor_costs>

<compliance_costs>
- Clearance processing: $3K-15K per person
- Certifications: ISO, CMMI obtainment/maintenance
- Cybersecurity: NIST 800-171, CMMC implementation
- Quality systems: Implementation/maintenance
</compliance_costs>
</methodology>

<cost_ranges>
- Small: $75K-750K (1-5 FTEs, well-defined)
- Medium: $750K-7.5M (5-25 FTEs, moderate complexity)
- Large: $7.5M-75M (25-150 FTEs, significant complexity)
- Major: $75M+ (150+ FTEs, highest complexity)
</cost_ranges>

<confidence_levels>
High (±15 percent): Well-defined requirements, standard labor, good benchmarks, firm scope
Medium (±25 percent): Some ambiguity, mix of standard/specialized labor, limited benchmarks
Low (±40 percent+): Poorly defined requirements, unique/specialized needs, no comparables, high uncertainty
</confidence_levels>
</cost_estimation>

<output_format>
Return valid JSON (no markdown):
{{
    "rfp_summary": [
        "Contract objective and scope with performance requirements",
        "Key deliverables and compliance/certification needs",
        "Security, clearance, and regulatory requirements",
        "Timeline, oversight, and government interaction level",
        "Cost drivers and complexity factors"
    ],
    "estimated_cost": {{
        "range_low": 350000,
        "range_high": 950000,
        "confidence_level": "medium",
        "basis_of_estimate": "Labor hours estimation, compliance costs, market rates, key assumptions, and factors affecting range/confidence"
    }}
}}
</output_format>

<inputs>
<rfp>{rfp_text}</rfp>
</inputs>

Generate comprehensive summary and detailed cost estimate satisfying CO cost realism analysis.</role>"""