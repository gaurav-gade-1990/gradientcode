### Context

A health system in Texas and Louisiana has three legal entities: a hospital company (4 hospitals on Epic), an affiliated physician group (380 physicians on an older on-premises EHR that only speaks HL7 v2), and an ambulatory surgery center joint venture with outside surgeons. 180 prior-authorization specialists spend about 25 minutes per request copying chart notes into 40 payers' portals, faxes and phone calls. 11 percent of requests are denied, and 18 percent of those denials are for missing documentation that was in the chart all along. Procedures get rescheduled, patients wait, and the revenue cycle team wants agents that do the gathering, submitting and tracking while clinicians keep every clinical judgment.

### Requirements

- At order time, tell the ordering clinician whether prior authorization is needed and what documentation the payer requires.
- Gather documentation from the EHRs, fill the payer's questionnaire, assemble the packet and submit through the payer's API, X12 278, or portal.
- Track status, respond to requests for more information, and draft appeals for denials.
- A licensed clinician reviews any questionnaire answer the agent is not certain of, and signs every clinical attestation. The agent never changes or cancels an order.
- Only the minimum necessary PHI goes to each payer; substance use disorder records under 42 CFR Part 2 are excluded without patient consent.
- Each entity's PHI is kept separate; all PHI stays in the US under a BAA with every vendor, including the model provider.

### Scale and constraints

- 3,200 requests a day (imaging 45 percent, surgery 30, specialty infusions 25); top 8 payers are 75 percent of volume.
- 12 payers support the Da Vinci FHIR APIs (CRD, DTR, PAS), 15 accept X12 278 through a clearinghouse, and 13 are portal-only; about 900 pages of payer faxes arrive a day.
- Under CMS-0057-F, impacted payers must decide within 72 hours for expedited and 7 calendar days for standard requests; the health system wants submission within 4 hours for urgent and 24 hours for standard orders.
- The order-time check must answer inside the EHR in under 1 second.
- A patient chart excerpt for a request is about 60,000 tokens of notes and results.
- Models via a HIPAA-eligible cloud endpoint at Anthropic list prices per million tokens: Sonnet 5.5 $2 input, $10 output, $0.20 cache reads; Opus 5.5 $4 and $20; Haiku 5.5 $0.10 and $0.50.
- Team: 15 engineers, 12 months; budget $150,000 a month. Records retained 10 years.

### What a strong answer covers

- Which steps are deterministic, which use a model, and which need a clinician.
- How three integration paths (FHIR, X12, portals) and two EHRs share one workflow.
- How minimum necessary and entity separation are enforced, and where.
- How an RPA bot failing on a changed portal is detected before a deadline is missed.
- The monthly cost of models, bots and infrastructure, with the levers applied.
- How you measure that denials fell because of the system, not because payers changed.
