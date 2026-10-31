# Healthcare Prior Authorization Agents: model answer

## 1. Scenario

The user is a prior-authorization specialist who today spends 25 minutes per request on copy and paste; the agent does the gathering, submitting and chasing so the specialist handles exceptions and appeals. The ordering clinician is the second user: they need to know at order time what the payer will ask for.

| What | Number | What it forces |
|---|---|---|
| Requests | 3,200 a day, about 96,000 a month | Tiny QPS; the hard part is 40 payers and two EHRs |
| Specialist time | 3,200 x 25 minutes = 1,333 hours a day | At 10 minutes, about 800 hours a day move to appeals and denials |
| Paths | FHIR 45 percent, X12 278 35, portals 20 by volume | One workflow, three submitters |
| Deadlines | Submit in 4 h urgent, 24 h standard; payers decide in 72 h or 7 days | Every request carries a clock |
| Order-time check | Under 1 s inside the EHR | Rules and cached tables, no model call |

**How:**
1. Pull 6 months of requests per entity: payer, service, path, minutes, outcome and denial reason.
2. Baselines: 11 percent denied, 18 percent of denials for missing documentation, 25 minutes per request.
3. Agree with the CMO that clinical judgments stay with licensed clinicians, and with Compliance that every payer disclosure is logged.
4. Out of scope: pharmacy benefit prior auth, and changing any order.

**Decision.** Automate the paperwork and leave the medicine to clinicians, because the denial problem is missing documents, not wrong decisions.

**Trap.** Letting the agent decide that a request "will not meet criteria" and drop it. That is a clinical and access decision made by software.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| EHR hooks | CDS Hooks `order-sign` from Epic; HL7 v2 ORM orders from the physician group's EHR through the Rhapsody interface engine. Hands over an order event | Two EHRs, one trigger |
| Requirement rules | Payer and service requirement tables, gold-card exemptions, Da Vinci CRD calls. Hands over "PA needed, these documents" | The order-time answer in under 1 s |
| Case workflow | Temporal, self-hosted, one workflow per request with its deadline. Hands over steps and human tasks | Requests live for days with legal clocks |
| Chart access | FHIR R4 from Epic, a HAPI FHIR facade over the legacy EHR's HL7 v2 feed. Hands over the resources the criteria name | Minimum necessary starts with what is fetched |
| Extraction model | Sonnet 5.5 answers DTR questionnaires with citations; Haiku 5.5 classifies faxes. Hands over answers with evidence and confidence | Notes are free text |
| Clinical review | Nurse reviewer queue in the work queue specialists already use. Hands over approved answers and signed attestations | A clinician owns every clinical statement |
| Submitters | Da Vinci PAS over FHIR, X12 278 via the clearinghouse, Playwright bots for portals. Hand over a payer reference number | 40 payers, three channels |
| Inbound | Payer responses, PAS status, 278 responses, OCR'd faxes. Hands over status and requests for information | Status arrives every way at once |
| Record store | Packet sent, disclosure log, versions, per entity. Hands over a 10-year audit trail | HIPAA and payer disputes |

**The one idea to hold:** rules decide whether a request is needed, the model only drafts answers with citations, a clinician signs, and the workflow owns the clock.

## 3. Data Sources

Each source is read per entity, and only for the criteria in front of it.

**How:**
1. **Epic** (hospitals): FHIR R4 Condition, Procedure, Observation, DiagnosticReport and DocumentReference, via a backend-services SMART app.
2. **Legacy EHR** (physician group): HL7 v2 ORM, ORU and MDM through Rhapsody into a HAPI FHIR store per entity.
3. **Payer rules**: requirement tables from payer policies, refreshed weekly; CRD and DTR endpoints for the 12 FHIR payers.
4. **Inbound faxes**: about 900 pages a day through a HIPAA-eligible OCR service.

**Decision.** Wrap the legacy EHR as FHIR once, in the interface engine, so the workflow speaks one model of the chart.

**Trap.** Writing a second extraction path for HL7 v2. Two code paths drift and the physician group's requests fail more.

## 4. Processing

Code decides what is fetched; the model reads only that.

**How:**
1. From the payer's DTR questionnaire or our requirement table, compute the FHIR queries the criteria need (for an MRI: conservative therapy dates, imaging, neurological findings).
2. Pull those resources and the note sections that match, trimming 60,000 tokens of chart to about 15,000.
3. Drop any record tagged 42 CFR Part 2 unless a consent resource is on file.
4. Classify inbound faxes with Haiku 5.5 into approval, denial, request for information or noise, and match them to a case by member and reference number.

**Decision.** Minimum necessary is enforced at the fetch, because data the model never saw cannot leak into a packet.

**Trap.** Sending the whole chart to the model and asking it to pick. The payer then receives things it never asked for.

## 5. Agents

One fixed workflow per request; the model fills forms with evidence, it does not plan.

| Lever, in order | Model cost a month | Saving a month |
|---|---|---|
| Start: Opus 5.5 on 96,000 requests, 60k raw tokens each | $26.9k | |
| Model mix: Sonnet 5.5 for questionnaires, Haiku 5.5 for faxes | $13.4k | $13.4k |
| Retrieval trimming: criteria-driven FHIR queries, 15k tokens | $4.8k | $8.6k |
| Prompt caching of the 5k payer-criteria prefix | $3.9k | $0.9k |

**How:**
1. Each questionnaire answer carries the quoted evidence and resource id; an answer whose quote is not found verbatim in the source is marked unsure.
2. Unsure answers, and any answer to a clinical judgment question, go to a nurse.
3. Appeals for denials are drafted on Opus 5.5 with the denial letter and the chart excerpt, about $1.2k a month, and a physician signs.

**Decision.** The model answers with quotes, not conclusions, because a reviewer can check a quote in seconds.

**Trap.** Accepting the model's yes or no on "has the patient failed 6 weeks of conservative therapy". Without the dated notes it is a guess.

## 6. Memory

Memory is the case; nothing about one patient informs another.

**How:**
1. Case state in the Temporal workflow and a Postgres case table per entity: request, packet version, answers, reviewer, status, clock.
2. Payer knowledge as versioned tables: requirement rules, portal flows, response times, denial reasons, from outcomes.
3. Gold-card status per clinician and service, refreshed from payer notices.
4. No conversational memory and no vector store of past patients.

**Decision.** Learnings are payer rules, not patient memories, because "this payer always asks for PT notes" is reusable and safe.

**Trap.** Retrieving similar past requests as examples. Another patient's PHI then enters this patient's prompt.

## 7. MCP Tool Servers

Not an agent loop: the workflow calls these as typed services. MCP servers wrap them so the model can read evidence during drafting, and only that.

**How:**
1. Read tools for the model: `get_resources(type, filters)`, `get_note_sections(criteria)`, scoped to one patient, one entity and the request's criteria.
2. Submission services are not model tools: `submit_pas`, `submit_278` and portal bots are called by the workflow after a clinician signs.
3. Each entity's server has its own credentials; the ASC joint venture cannot read hospital charts.
4. We would add a model-driven step only for portals with no stable flow, and only to propose, never to submit.

**Decision.** Submission is never a model tool, because a sent packet is a disclosure that cannot be recalled.

**Trap.** Letting a browser agent "figure out" a portal. It will submit somewhere, and an unlogged disclosure is a HIPAA incident.

## 8. Endpoints

The order-time check is a CDS Hooks service with a hard budget; everything after it runs on the request's clock.

| Stage, order-sign check | p50 | p95 |
|---|---|---|
| CDS Hooks request to service | 20 ms | 60 ms |
| Requirement table and gold-card lookup, in memory | 2 ms | 5 ms |
| Payer CRD call, when supported, cut off at 600 ms | 300 ms | 600 ms |
| Card rendered | 20 ms | 50 ms |
| **Total** | **about 350 ms** | **about 720 ms** |

**How:**
1. `POST /cds-services/pa-check` for Epic; the HL7 v2 path posts the same check and returns a task to the order inbox.
2. Urgent budget, 4 hours: gather and draft 5 minutes, nurse review p95 2 hours, submission 1 minute by FHIR or 10 minutes by portal.
3. `GET /v1/cases/{id}` for specialists; `POST /v1/cases/{id}/review` for nurses.
4. PAS status by subscription where supported; otherwise polled every 4 hours.

**Decision.** The CRD call is cut off at 600 ms and the local table answers, because a slow payer must not slow the clinician's order.

**Trap.** Calling a model in the order-sign hook. It blows the 1 second budget and clinicians turn the hook off.

## 9. Caching

Caching is for rules and sessions; chart data is refetched when it could have changed.

**How:**
1. Payer requirement tables and gold-card status in memory, refreshed weekly and on notice.
2. FHIR resources per case for the life of the case, refetched before submission if older than 24 h.
3. Prompt-cache the payer criteria and questionnaire prefix.
4. Portal sessions per bot, never across entities.

**Decision.** Refetch the chart before submission, because a result filed this morning can change the answer.

**Trap.** Caching requirement tables for months. Payers change policies quarterly and denials rise silently.

## 10. Data Stores

PHI lives in one HIPAA account, separated by entity, with packets kept exactly as sent.

| Store | Holds | Size |
|---|---|---|
| Postgres, per entity schema | Cases, answers, reviews, payer tables | About 300 GB over 10 years |
| HAPI FHIR store | Legacy EHR data as FHIR | About 2 TB |
| S3 Object Lock | Submitted packets, faxes, disclosure log, 10 years | 96,000 packets a month x 1.5 MB, about 17 TB |
| Kafka | Orders, statuses, inbound events, 7 days | Under 50 GB |

**How:**
1. Monthly cost: models $5.1k with appeals; assumed prices for OCR $1.4k, clearinghouse $6.7k (two transactions per X12 request at $0.10), portal bot compute $2k (8 Playwright workers), and infra $27k (EKS, RDS, Kafka, self-hosted Temporal, FHIR store, logging): about $42k against $150k.
2. No GPUs: models and OCR are HIPAA-eligible API services under BAAs.

**Decision.** Self-host Temporal in the HIPAA account, because workflow history holds PHI and every store of PHI needs a BAA.

**Trap.** Shipping prompts to a logging tool without a BAA. Logs are PHI.

## 11. Output

Four outputs, one per audience: clinician, payer, specialist and physician.

**How:**
1. **Order-time card**: PA needed or not, required documents, gold-card exemption if it applies.
2. **Packet**: questionnaire answers with cited resources, attachments, signed attestation; only what the criteria name.
3. **Specialist view**: status, clock, next action, payer reference.
4. **Appeal draft**: denial reason, rebuttal with chart citations, for physician signature.

**Decision.** Every packet is stored exactly as sent, so a payer dispute is answered with the bytes, not a reconstruction.

**Trap.** Storing the inputs and regenerating the packet when asked. The regenerated packet is not what the payer saw.

## 12. Guardrails

Every limit that protects patients and PHI lives in code and in human sign-off, never in a prompt.

**How:**
1. Minimum necessary in the fetch layer; Part 2 records excluded without consent.
2. Entity separation by schema, credentials and FHIR scopes per entity.
3. A nurse signs uncertain answers and every clinical judgment; a physician signs appeals.
4. The agent cannot change, cancel or delay an order; it can only flag.
5. Disclosure log per packet: who, what, which payer, when.

**Decision.** Confidence never auto-approves a clinical attestation, because the signature is a legal statement by a licensed person.

**Trap.** Auto-submitting when confidence is high. A wrong attestation is now fraud signed by nobody.

## 13. Key Impact

The business metric is first-pass approval, measured against a holdout.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Specialist minutes per request | 25 | 10 | Work queue timestamps |
| Denials for missing documentation | 18 percent of denials | Under 5 percent | Denial reason codes |
| First-pass approval | 89 percent | 94 percent | Payer responses, holdout vs treated |
| Urgent submitted in 4 h | Unknown | 98 percent | Workflow clocks |
| Rescheduled procedures for PA | Baseline month | Half | Scheduling system |

**How:**
1. Hold out 10 percent of requests per payer for 8 weeks, so payer policy changes hit both arms.
2. Report per payer; a payer's own change shows up in the holdout too.

**Decision.** Compare against a same-payer holdout, because payers change rules every quarter and a before-and-after chart lies.

**Trap.** Claiming the whole denial drop. Part of it is CMS-0057-F pushing payers to faster, clearer decisions.

## 14. Failure Modes

Each failure is caught before the deadline, not after.

**How:**
1. **Portal changes layout**: bots assert expected page elements; a failure moves the case to a specialist with 20 hours left, not 2.
2. **Clearinghouse outage**: X12 requests queue; urgent ones go to portal or phone.
3. **Legacy EHR feed lag**: Rhapsody lag over 30 minutes flags cases from that entity.
4. **Payer silence past 72 h or 7 days**: escalation task and complaint template.
5. **Fax misfiled**: unmatched faxes go to a queue within 1 hour.

**Decision.** Every request carries its own deadline timer in Temporal, so a stuck dependency becomes a human task with time left.

**Trap.** Monitoring bot uptime. Bots can be up and submitting into a changed form.

## 15. Build Order

Twelve months, highest-volume path first.

**How:**
1. **Months 1-3**: workflow, requirement tables, order-sign hook for Epic. Measure: PA-needed accuracy on 1,000 orders.
2. **Months 4-5**: FHIR gathering and questionnaires in shadow for the top 3 payers. Measure: nurse-agreed answers.
3. **Months 6-7**: PAS and X12 submission with nurse review. Measure: specialist minutes.
4. **Months 8-9**: legacy EHR through Rhapsody and the physician group. Measure: their first-pass rate.
5. **Months 10-12**: portal bots, fax intake, appeals, ASC entity. Measure: urgent within 4 h.

**Decision.** FHIR payers first, because 45 percent of volume on stable APIs proves the workflow before portals add noise.

**Trap.** Starting with portal bots because portals hurt most. They are the least stable path and teach nothing about the workflow.
