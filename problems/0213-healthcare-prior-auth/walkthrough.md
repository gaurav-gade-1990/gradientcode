## 1. What the problem is really asking

Read the denial numbers carefully: 11 percent of requests are denied, and 18 percent of those denials are for **missing documentation that was in the chart all along**. The payer isn't wrong about the medicine. The paperwork is incomplete. So this is a **document-assembly and deadline-tracking system**, not a clinical decision system. The agents gather, fill, submit and chase; licensed clinicians keep every clinical judgment and every signature.

The core tension is **automation against clinical and legal accountability**. A specialist spends 25 minutes per request copying chart notes into 40 payers' portals. Automating that is the whole point. But a questionnaire answer like "patient has failed 6 weeks of conservative therapy" is a clinical statement, and the attestation on the packet is a legal one. The design automates everything up to the statement, makes the model prove each answer with a verbatim quote, and puts a nurse or physician on anything that's judgment.

Three decisions carry the design:

- **Rules decide whether PA is needed; the model only reads notes.** The order-time check is a CDS Hooks service on cached requirement tables, answering in under 1 second with no model call.
- **Minimum necessary is enforced at the fetch.** Code turns the payer's criteria into FHIR queries, so the model sees 15,000 tokens of relevant chart, not 60,000, and data it never saw can't leak into a packet. 42 CFR Part 2 records are dropped without consent.
- **One workflow, three submitters, a clock per request.** Two EHRs (Epic on FHIR, a legacy EHR on HL7 v2 wrapped as FHIR) feed one Temporal workflow, which submits by Da Vinci PAS, X12 278 or a portal bot and owns the deadline.

The model answer's one idea: rules decide whether a request is needed, the model only drafts answers with citations, a clinician signs, and the workflow owns the clock.

## 2. The numbers that drive the design

**Volume.** 3,200 requests a day × 30 = **96,000 a month**. That's a tiny request rate. The hard part is 40 payers, three submission paths and two EHRs, not throughput.

**Specialist time.**

- Today: 3,200 × 25 minutes = 80,000 minutes = **1,333 hours a day**.
- At the 10-minute target: 3,200 × 10 = 533 hours a day, so about **800 hours a day** move from copy-and-paste to appeals and denials.

**Denial baseline.** 11 percent denied means **89 percent first-pass approval**. 18 percent of denials are missing documentation. The target is 94 percent first-pass and missing-documentation denials under 5 percent of denials.

**Deadlines.** Submit within **4 hours urgent, 24 hours standard** (the health system's targets). Payers must decide within **72 hours expedited, 7 calendar days standard** under CMS-0057-F. Every request carries a clock.

**The lever table.** Reveal the model answer for its full table. The reasoning step by step:

| Step | What changes | Monthly cost |
|---|---|---|
| Start | Opus 5.5 on 96,000 requests with the full 60k-token chart. Input alone is 60,000 × $4/M = $0.24 a request, plus output | **$26.9k** |
| Model mix | Sonnet 5.5 for questionnaires (half Opus's prices: 60,000 × $2/M = $0.12 input), Haiku 5.5 for fax classification | **$13.4k** (saves $13.4k) |
| Retrieval trimming | Criteria-driven FHIR queries cut 60k to 15k tokens: 15,000 × $2/M = $0.03 input | **$4.8k** (saves $8.6k) |
| Prompt caching | The 5k payer-criteria prefix read at $0.20 instead of $2: 5,000 × $1.80/M × 96,000 | **$3.9k** (saves $0.9k) |

Add Opus 5.5 appeal drafts at about $1.2k a month and models total **$5.1k**.

**Clearinghouse.** X12 is 35 percent of volume: 96,000 × 0.35 × 2 transactions × an assumed $0.10 = **$6.7k a month**, more than the models.

**Total.** Models $5.1k + assumed OCR $1.4k + clearinghouse $6.7k + portal bot compute $2k (8 Playwright workers) + infra $27k ≈ **$42k a month** against $150k. Model cost is a rounding error once retrieval is trimmed. The budget isn't the constraint; accountability is.

**Archive.** 96,000 packets a month × 1.5 MB × 120 months ≈ **17 TB** over 10 years in S3 Object Lock.

**Order-time latency.** CDS Hooks request 60 ms + table lookup 5 ms + payer CRD call cut off at 600 ms + card 50 ms ≈ **720 ms at p95**, about 350 ms at p50. The cutoff is what guarantees the 1-second budget.

**Urgent path.** Gather and draft 5 minutes + nurse review p95 2 hours + submission 1 minute (FHIR) or 10 minutes (portal) is well inside 4 hours. The nurse is the long pole.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–6 | Read the prompt. Write 1,333 hours a day, 96,000 a month, 60k → 15k tokens. Circle "18 percent missing documentation" and "never changes or cancels an order." |
| 6–18 | **Pillar A.** Clinicians keep judgment. Nine layers: two EHR inputs, rules, workflow, chart access, model, nurse review, three submitters. |
| 18–40 | **Pillar B.** HL7 v2 wrapped as FHIR, criteria-driven fetch, Part 2 exclusion, quotes not conclusions, payer rules as memory, no submission tool. |
| 40–55 | **Pillar C.** CDS Hooks under 1 s, the urgent budget, refetch before submit, the 17 TB archive and BAAs, packets stored as sent. |
| 55–70 | **Pillar D.** Minimum necessary in the fetch layer, no auto-signed attestations, per-payer holdout, portal assertions, FHIR first. |
| 70–75 | Check no path lets the model submit, sign or change an order. |

## 4. Pillar A: Frame

### Scenario

**The question:** who are the users, what stays with clinicians, and which numbers shape it?

The prior-authorization specialist is the main user. The agent does the gathering, submitting and chasing so the specialist handles exceptions and appeals. The ordering clinician is the second user: they need to know at order time what the payer will ask for.

How to reason to the boundary: look at *why* requests fail. 18 percent of denials are missing documents that were in the chart. That's a paperwork problem, so automate the paperwork and leave the medicine to clinicians. Agree it explicitly with the CMO, and agree with Compliance that every payer disclosure is logged.

Name the deadlines as constraints (4 h and 24 h submission; 72 h and 7 days payer decision). Pull 6 months of history per entity for baselines. Out of scope: pharmacy benefit prior auth, and changing any order.

**The trap:** letting the agent decide a request "will not meet criteria" and drop it. That's a clinical and access decision made by software.

**Rubric:** clinical judgment with clinicians (1.1), 1,333 hours and the saving (1.2), deadlines and CMS-0057-F windows (1.3), and missing documentation as the cause (1.4).

### Single View

**The question:** draw the path from an order in either EHR to a payer decision.

Nine layers: EHR hooks (CDS Hooks `order-sign` from Epic; HL7 v2 ORM from the legacy EHR through Rhapsody) → Requirement rules → Case workflow (Temporal, self-hosted) → Chart access (FHIR R4 from Epic, a HAPI FHIR facade over the legacy feed) → Extraction model (Sonnet for questionnaires, Haiku for faxes) → Clinical review (a nurse queue in the existing work queue) → Submitters (PAS, X12 278, Playwright portal bots) → Inbound (statuses, 278 responses, OCR'd faxes) → Record store.

The reasoning that earns marks:

- **Two EHRs, one trigger.** Both produce an order event into the same workflow.
- **Rules before the model.** "Is PA needed, and what documents?" comes from requirement tables and Da Vinci CRD, not from a model.
- **A clinical review layer** as its own box, because a clinician owns every clinical statement.
- **Three submission paths** behind one workflow step.

**The trap:** drawing one "agent" box that reads the chart, decides and submits.

**Rubric:** both EHRs into one workflow (2.1), rules separate from model extraction (2.2), a clinician review layer (2.3), and three submission paths (2.4).

## 5. Pillar B: Build the core

### Data Sources

**The question:** where do chart data and payer knowledge come from?

Epic gives FHIR R4 (Condition, Procedure, Observation, DiagnosticReport, DocumentReference) through a backend-services SMART app. The legacy EHR's HL7 v2 ORM, ORU and MDM messages go through **Rhapsody into a HAPI FHIR store per entity**. Payer requirement tables are built from payer policies and **refreshed weekly**; the 12 FHIR payers also expose CRD and DTR endpoints. About 900 fax pages a day go through a HIPAA-eligible OCR service.

The decision: wrap the legacy EHR as FHIR **once**, in the interface engine, so the workflow speaks one model of the chart. The alternative, a second extraction path for HL7 v2, drifts from the first, and the physician group's requests fail more.

**The trap:** a second extraction path for HL7 v2.

**Rubric:** HL7 v2 to FHIR once (3.1), versioned requirement tables on a schedule (3.2), and faxes with OCR (3.3).

### Processing

**The question:** how is the chart narrowed to what a payer needs?

From the payer's DTR questionnaire or the requirement table, **code computes the FHIR queries the criteria need**. For an MRI, that's conservative therapy dates, prior imaging and neurological findings. It pulls those resources and the matching note sections, trimming **60,000 tokens to about 15,000**. Any record tagged 42 CFR Part 2 is dropped unless a consent resource is on file. Haiku 5.5 classifies inbound faxes (approval, denial, request for information, noise) and they're matched to a case by member and reference number.

The reasoning: minimum necessary is a HIPAA rule, and the strongest place to enforce it is the fetch. Data the model never saw can't leak into a packet.

**The trap:** sending the whole chart to the model and asking it to pick. The payer then receives things it never asked for.

**Rubric:** queries derived from the criteria (4.1), Part 2 excluded without consent (4.2), and raw and trimmed token counts (4.3).

### Agents

**The question:** what does the model do, what does a nurse do, and what does it cost?

One fixed workflow per request; the model fills forms with evidence, it doesn't plan. Every questionnaire answer carries **a verbatim quote and resource id**, and an answer whose quote isn't found verbatim in the source is marked unsure (problem grounded-answer-check). Unsure answers and **any clinical-judgment question go to a nurse**. Appeals are drafted on Opus 5.5 with the denial letter and chart excerpt, and **a physician signs**.

The reasoning for quotes over conclusions: a reviewer can check a quote in seconds. A model's yes or no on "has the patient failed 6 weeks of conservative therapy?" without the dated notes is a guess.

Then the cost table from section 2: $26.9k → $3.9k, plus appeals, $5.1k.

**The trap:** accepting the model's yes or no.

**Rubric:** levers in order with savings (5.1), quote and resource id per answer (5.2), uncertain and clinical answers to a nurse (5.3), and physician-signed appeals (5.4).

### Memory

**The question:** what does the system learn over time without mixing patients?

Case state lives in the Temporal workflow and a per-entity Postgres case table: request, packet version, answers, reviewer, status and **clock**. What the system learns is stored as **payer knowledge in versioned tables**: requirement rules, portal flows, response times, denial reasons. Gold-card status per clinician and service is refreshed from payer notices. There's no conversational memory and no vector store of past patients.

The reasoning: "this payer always asks for PT notes" is reusable and contains no PHI. A similar past request contains another patient's PHI.

**The trap:** retrieving similar past requests as examples.

**Rubric:** learnings as payer rules (6.1), case state with its clock (6.2), and no other patients' requests as examples (6.3).

### MCP Tool Servers

**The question:** which tools can the model call, and which actions are reserved for the workflow?

The model answer says plainly that this is **not an agent loop**: the workflow calls typed services. MCP servers wrap read access so the model can read evidence while drafting, and only that: `get_resources(type, filters)` and `get_note_sections(criteria)`, scoped to one patient, one entity and the request's criteria.

Submission (`submit_pas`, `submit_278`, portal bots) is **not a model tool**. The workflow calls it after a clinician signs. Each entity's server has its own credentials, so the ASC joint venture can't read hospital charts. You'd add a model-driven step only for portals with no stable flow, and only to propose.

The reasoning: a sent packet is a disclosure that can't be recalled.

**The trap:** a browser agent that "figures out" a portal. It will submit somewhere, and an unlogged disclosure is a HIPAA incident.

**Rubric:** read tools scoped to patient, entity and criteria (7.1), no submission tool (7.2), and credentials per entity (7.3).

## 6. Pillar C: Serve and store

### Endpoints

**The question:** how does the order-time check meet 1 second, and how does an urgent request meet 4 hours?

`POST /cds-services/pa-check` serves Epic's `order-sign` hook. The HL7 v2 path posts the same check and returns a task to the order inbox. Then show two budgets:

- **Order-sign:** about 720 ms at p95 (section 2), with the payer CRD call **cut off at 600 ms** and the local table answering if the payer is slow.
- **Urgent, 4 hours:** gather and draft 5 minutes, nurse review p95 2 hours, submission 1 to 10 minutes.

Specialists read `GET /v1/cases/{id}`, nurses post reviews, and PAS status comes by subscription where supported, otherwise polled every 4 hours.

**The trap:** calling a model in the order-sign hook. It blows the 1-second budget and clinicians turn the hook off.

**Rubric:** CDS Hooks without a model call (8.1), a sub-second budget with a cutoff (8.2), and a 4-hour urgent budget including nurse review (8.3).

### Caching

**The question:** what's cached, and what must be refetched?

Requirement tables and gold-card status live in memory, refreshed weekly and on notice. FHIR resources are cached per case but **refetched before submission if older than 24 h**, because a result filed this morning can change the answer. The payer criteria prefix is prompt-cached. Portal sessions are per bot and **never shared across entities**.

**The trap:** caching requirement tables for months. Payers change policies quarterly and denials rise silently.

**Rubric:** tables cached with a refresh (9.1), chart refetched when stale (9.2), and no cross-entity portal sessions (9.3).

### Data Stores

**The question:** where does PHI live, for how long, and what does it cost?

One HIPAA account, separated by entity: Postgres per entity schema (about 300 GB over 10 years), the HAPI FHIR store (about 2 TB), **S3 Object Lock** for submitted packets, faxes and the disclosure log (about 17 TB over 10 years, from section 2), and Kafka for 7 days of events.

Every store and service holding PHI needs a BAA, **including logs and workflow history**. That's why Temporal is self-hosted in the HIPAA account. Cost: about $42k a month with non-model prices assumed. No GPUs, since models and OCR are HIPAA-eligible APIs under BAAs.

**The trap:** shipping prompts to a logging tool without a BAA. Logs are PHI.

**Rubric:** archive sized from packets and bytes (10.1), BAAs everywhere including logs and workflow (10.2), and a total with assumed labels (10.3).

### Output

**The question:** what do clinicians, specialists and payers receive?

Four outputs, one per audience: the **order-time card** (PA needed, required documents, gold-card exemption), the **packet** (answers with cited resources, attachments, signed attestation, only what the criteria name), the **specialist view** (status, clock, next action, payer reference), and the **appeal draft** for physician signature.

The decision: **store every packet exactly as sent**. A payer dispute is then answered with the bytes, not a reconstruction.

**The trap:** storing inputs and regenerating the packet on request. The regenerated packet isn't what the payer saw.

**Rubric:** packets stored as sent (11.1), only what criteria name with citations (11.2), and a specialist view with deadline and next action (11.3).

## 7. Pillar D: Run it safely

### Guardrails

**The question:** which controls protect patients and PHI, and where do they live?

- **Minimum necessary in the fetch layer**, with Part 2 excluded without consent.
- **Entity separation** by schema, credentials and FHIR scopes.
- A nurse signs uncertain answers and every clinical judgment; a physician signs appeals.
- **The agent can't change, cancel or delay an order**; it can only flag.
- **A disclosure log** per packet: who, what, which payer, when.

The decision: **confidence never auto-approves a clinical attestation**, because the signature is a legal statement by a licensed person.

**The trap:** auto-submitting when confidence is high. A wrong attestation is then fraud signed by nobody.

**Rubric:** minimum necessary in the fetch (12.1), no auto-signing at any confidence (12.2), no order changes (12.3), and every disclosure logged (12.4).

### Key Impact

**The question:** how do you prove denials fell because of the system?

Five metrics: specialist minutes (25 → 10), missing-documentation denials (18 percent of denials → under 5), first-pass approval (89 → 94 percent, holdout vs treated), urgent submitted in 4 h (98 percent), and rescheduled procedures (halved).

The method: **hold out 10 percent of requests per payer for 8 weeks**, so a payer's policy change hits both arms. Report per payer. And say the confounder out loud: part of any denial drop is CMS-0057-F pushing payers to faster, clearer decisions.

**The trap:** claiming the whole denial drop, or using a before-and-after chart.

**Rubric:** holdout within each payer (13.1), missing-doc denials and first-pass approval (13.2), and payer changes as a confounder (13.3).

### Failure Modes

**The question:** what breaks, and how is it caught before a deadline?

- **Portal layout changes:** bots **assert expected page elements**; a failure moves the case to a specialist with 20 hours left, not 2.
- **Clearinghouse outage:** X12 requests queue; urgent ones go to portal or phone.
- **Legacy feed lag:** Rhapsody lag over 30 minutes flags that entity's cases.
- **Payer silence** past 72 h or 7 days: an escalation task and complaint template.
- **Misfiled fax:** unmatched faxes reach a queue within 1 hour.

The decision: **every request carries its own deadline timer** in Temporal, so a stuck dependency becomes a human task with time left.

**The trap:** monitoring bot uptime. Bots can be up and submitting into a changed form.

**Rubric:** page-element assertions (14.1), per-request deadline timers (14.2), and clearinghouse and legacy feed outages (14.3).

### Build Order

**The question:** in what order do you build it in 12 months?

Workflow, requirement tables and the Epic order-sign hook (months 1–3, PA-needed accuracy on 1,000 orders); FHIR gathering and questionnaires **in shadow** for the top 3 payers (4–5, nurse-agreed answers); PAS and X12 submission with nurse review (6–7, specialist minutes); the legacy EHR and physician group (8–9, their first-pass rate); portal bots, faxes, appeals and the ASC entity (10–12, urgent within 4 h).

The reasoning: FHIR payers first, because 45 percent of volume on stable APIs proves the workflow before portals add noise.

**The trap:** starting with portal bots because portals hurt most. They're the least stable path and teach nothing about the workflow.

**Rubric:** stable FHIR and highest volume first (15.1), shadow extraction with nurse agreement (15.2), and a number per phase (15.3).

## 8. The decisions that separate strong answers

**Criteria-driven fetch vs whole-chart prompt.** Sending the chart and asking the model to pick looks simpler. It costs four times the tokens, and it violates minimum necessary in the one place you can't take back: the packet. Code that turns criteria into FHIR queries is both cheaper and the compliance control.

**Quotes vs conclusions.** The weak answer has the model answer "yes" to the questionnaire. The strong one requires a verbatim quote and resource id, marks an answer unsure if the quote isn't in the source, and sends judgment questions to a nurse. The nurse's job shrinks from reading the chart to checking quotes.

**Workflow submits vs agent submits.** Giving the model a submit tool, or a browser agent for portals, makes the agent look capable. But a sent packet is an irreversible disclosure. Strong answers keep submission in the workflow, after a signature, with a disclosure log.

## 9. Common mistakes

- Calling a model in the order-sign hook.
- Building a separate extraction path for the HL7 v2 EHR.
- Sending the whole chart to the model.
- Forgetting 42 CFR Part 2.
- Auto-signing attestations above a confidence threshold.
- One set of credentials for all three entities.
- Logs or workflow history in a service without a BAA.
- Measuring denials before and after with no holdout.
- Monitoring portal bots by uptime.

## 10. Follow-ups an interviewer might ask

- *A payer changes its MRI criteria mid-quarter.* Requirement tables are versioned data refreshed weekly and on notice; the holdout catches the effect on both arms; denial reasons feed back into the table.
- *The model's answer cites a note that doesn't contain the quote.* The verbatim check fails, the answer is marked unsure, and a nurse reviews it.
- *How do you handle a payer that asks for more information by fax?* Haiku 5.5 classifies the fax as a request for information, it's matched by member and reference number, and the workflow reopens gathering with the case's clock still running.
- *A portal submission half-succeeds.* The workflow records the step, asserts the confirmation page, and either compensates or hands to a specialist (problem saga-compensation).
- *How do you get structured questionnaire answers reliably?* Validate the model's JSON against the questionnaire schema and repair or retry (problem structured-output-repair).
