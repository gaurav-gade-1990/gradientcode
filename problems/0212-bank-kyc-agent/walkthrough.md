## 1. What the problem is really asking

Strip the story and this is an **evidence-assembly system under legal constraints**. Analysts spend about 25 minutes per alert gathering evidence from six systems, then close 95 percent of alerts as false positives. The US backlog hit 41 days and the regulator noticed. The model's real job is to write: turn a sourced evidence pack into a narrative an analyst can read in minutes. Everything else (which evidence to gather, the risk score, the decision) stays deterministic or human.

The core tension is **speed against explainability**. The fastest design on paper lets the model close false positives on its own. That's the design no validator or regulator will accept in year one, and it fails the requirement that any decision be explainable to three regulators seven years later. The strong answer gets its speed from better evidence packs and drafts, and it gets its safety from structure: the model has no disposition tools, and every sentence cites an evidence id.

Three decisions carry the design:

- **Three full stacks, one per jurisdiction.** Residency is the law, so it's the topology. Nothing raw crosses a border. Group risk travels as one legally approved bit ("related case in another entity: yes or no, and a contact").
- **Code computes, the model writes.** Transaction aggregates are SQL, the risk score is the bank's validated scorecard, and the steps are a fixed plan. A validator can test SQL; it can't test arithmetic done in a prompt.
- **Every case is a replayable, write-once record.** Inputs, draft, model and prompt version hashes, and the analyst's edits, hash-chained in S3 Object Lock, so an examiner in 2033 can see exactly what happened in 2027.

The model answer's one idea: the model writes the narrative from sourced evidence; the scorecard sets the risk, the analyst decides, and the record proves who did what with which version.

## 2. The numbers that drive the design

**Daily case volume.**

- KYC: 1.5M cases a year / 365 ≈ **4,100 a day**.
- Alerts: **6,000 a day**.
- Total: about **10,100 cases a day**. That's well under one model call a second. Say so: the weight here is evidence and records, not traffic.

**Analyst time, the business case.**

- 6,000 alerts × 25 minutes = 150,000 minutes = **2,500 analyst hours a day** on alerts.
- Halving it (the target is 25 → 12 minutes) frees about 1,250 hours a day, which at an 8-hour day is **about 160 analysts' capacity** out of 450.

**Cases a month for the cost table.** Alerts 6,000 × 30 = 180,000, plus KYC 1.5M / 12 = 125,000, gives **305,000 cases a month**. The periodic reviews alone are 900,000 / 12 = **75,000 a month**, and they aren't urgent, so they can go to the batch API at half price.

**The lever table.** Reveal the model answer for the full table. The way to reason through it:

| Step | What changes | Monthly cost |
|---|---|---|
| Start | Opus 5.5 on every case with all 80k raw tokens. The input alone is 80,000 × $4/M = $0.32 a case, plus output | **$106.8k** |
| Model mix | Sonnet 5.5 at half Opus's prices, with Opus only for the 5 percent escalated. Sonnet input is 80,000 × $2/M = $0.16 a case | **$56.1k** (saves $50.7k) |
| Retrieval trimming | SQL aggregates shrink the pack from 80k to 25k tokens; Sonnet input drops to 25,000 × $2/M = $0.05 | **$20.7k** (saves $35.4k) |
| Prompt caching | The 6k procedure prefix per entity read at $0.20 instead of $2 (Sonnet) or $4 (Opus) | **$17.2k** (saves $3.5k) |
| Batch API | 75,000 periodic reviews a month at half price | **$15.1k** (saves $2.1k) |

Notice which lever is biggest after model mix: **trimming**, not caching. That's because 80k raw tokens is mostly 90 days of transactions, which SQL turns into a handful of features plus the 50 flagged transactions. Caching only touches the 6k prefix.

**GPUs.** A fine-tuned DeBERTa classifies adverse media at about 2 articles a second. That's small, but each region needs its own and needs availability, so 2 L4 per region, 6 in all: 6 × an assumed $0.85/h × 730 h ≈ **$3.7k a month**.

**Total.** Assumed infra of about $29k a month per region, $87k for three, plus GPUs $3.7k, plus models $15.1k ≈ **$106k a month**. Infrastructure dominates, because you're running three complete stacks. Screening and data vendors are existing contracts.

**Record storage.** 305,000 cases a month × 400 KB × 84 months ≈ **10 TB over 7 years** across regions.

**Onboarding latency.** The p95 stages: ID verification 120 s + screening 10 s + ownership chain 90 s + adverse media 60 s + scorecard 2 s + draft note 45 s ≈ **5.5 minutes**, inside the 10-minute target. The p50 is about 1.5 minutes. The vendors dominate, not the model.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–6 | Read the prompt. Write 2,500 hours a day, 305,000 cases a month, 80k → 25k tokens. Circle "never files a SAR" and "three regulators." |
| 6–18 | **Pillar A.** Analysts decide, agent drafts. Examiner as a user. Ten layers with three regional stacks and the group-signal facade. |
| 18–40 | **Pillar B.** CDC from the mainframe, SQL features, fixed step plan, the lever table, per-case memory, read-only tools with no disposition tool. |
| 40–55 | **Pillar C.** Scorecard-first onboarding with the latency table, no screening cache, Object Lock stores and the $106k total, replay bundle. |
| 55–70 | **Pillar D.** Article 22, tipping off, below-the-line testing, holdout, no cross-region failover, one entity at a time. |
| 70–75 | Check no tool, prompt or path lets the model make a disposition. |

This is a Hard problem, and the marks lean on regulatory reasoning more than on the cost table. Spend time on Single View, MCP Tool Servers and Guardrails.

## 4. Pillar A: Frame

### Scenario

**The question:** who decides, what does the agent do for them, and which numbers shape it?

The analyst decides every alert and case. The agent hands them a complete, sourced evidence pack and a draft narrative so the decision takes 12 minutes instead of 25. The **second user is the examiner**, who must be able to replay any decision from the last 7 years.

How to reason to it: map every decision in the alert and KYC workflows and label each one "model may draft," "rules decide," or "human decides." Then name the hard deadlines as constraints: **SAR filing within 30 calendar days** of detection, and **low-risk onboarding in 10 minutes**. A backlog here is a compliance breach, not a nuisance.

Baselines per entity: minutes per alert from Actimize timestamps, backlog age, SAR conversion rate. Out of scope: replacing Actimize rules, filing SARs, customer contact.

**The trap:** pitching auto-closure of false positives. It's the biggest saving on paper and the one no validator or regulator will accept in year one.

**Rubric:** analysts make every disposition (1.1), 2,500 hours and the capacity saving (1.2), the SAR clock and onboarding target (1.3), and the examiner as a user with 7-year replay (1.4).

### Single View

**The question:** draw the system across three entities and the legacy systems.

The model answer has ten layers, which is the upper limit for a Hard problem. The ones that carry marks:

- **Regional stack: one full deployment each in US, UK and EU.** The alternative, one stack with regional routing, still has a single control plane, shared logs and shared workflow history, all of which hold customer data. Three stacks is the only topology where nothing raw crosses a border.
- **Feature layer and risk rules apart from the drafting model.** The scorecard is already validated and explainable; the model only writes prose around it.
- **A write-once record store** for the examiner's 7-year question.
- **Group signal:** a legal-approved facade answering "related case in another entity: yes or no, contact." That's how cross-entity risk is shared without moving customer data.

The analyst desk is the existing Actimize case manager, with the draft attached as "AI-prepared." Analysts don't learn a new tool.

**The trap:** a single global stack with a "residency router." The router is the first thing to fail open.

**Rubric:** a full stack per jurisdiction (2.1), rules separate from the drafting model (2.2), a write-once record store (2.3), and cross-entity risk without moving data (2.4).

## 5. Pillar B: Build the core

### Data Sources

**The question:** how does evidence reach the agent from Actimize, the mainframe, Temenos and vendors?

Each entity reads only its own systems. Actimize alerts are polled every minute. The US core (DB2 on z/OS) streams through **IBM InfoSphere CDC** into the US Kafka. UK and German Temenos events go into each region's Kafka. Sanctions and PEP vendors are called live. Companies House and the Handelsregister give ownership chains, cached 30 days. Adverse media comes from a news vendor indexed in each region's OpenSearch.

The reasoning for CDC: the alternative is new CICS transactions against the mainframe, which add load to the core's batch window, the bank's most protected resource. CDC reads the log and adds no new load.

**The trap:** copying German customer data to the US "for the group view." That's an unlawful transfer, and the group view only needs one bit.

**Rubric:** CDC with no new core load (3.1), each entity in its own region (3.2), and live sanctions and PEP screening (3.3).

### Processing

**The question:** how is a case's evidence assembled, and what does the model see?

A Temporal workflow per case gathers evidence through the facades in parallel, and **every item is stamped with source system, record id and fetch time**. Transaction features are computed in SQL: 90-day volume, cash share, new counterparties, round amounts, high-risk geographies. Only the top 50 flagged transactions go in raw. A deterministic matcher resolves name, date of birth and address against screening hits and attaches the match score. A fine-tuned DeBERTa classifies adverse media on 2 L4 GPUs per region.

The result: the pack shrinks from **80,000 raw tokens to about 25,000**.

The reasoning: a validator can test a SQL feature against known inputs. A model counting transactions in its context can't be validated, and it miscounts.

**The trap:** sending 90 days of raw transactions to the model. It costs about three times more and the model miscounts.

**Rubric:** aggregates in SQL (4.1), source, record id and fetch time on every item (4.2), the 80k → 25k pack (4.3), and GPUs sized per region (4.4).

### Agents

**The question:** what does the model do, how is it constrained, and what does it cost?

One drafting agent per case type with a **fixed step plan**: gather, compute, screen, draft. The workflow runs the steps; the model only drafts. Every factual sentence must cite an evidence id, and a checker removes uncited sentences. The recommendation comes from a **fixed list with typology reason codes**.

The alternative is a research agent that decides which systems to query. It sounds more capable, but two runs on one case then produce different evidence, and the model can't be validated under SR 11-7, SS1/23 or MaRisk. Repeatability is a regulatory requirement here, not a nicety.

Then the lever table from section 2: $106.8k → $15.1k.

**The trap:** the free-form research agent.

**Rubric:** levers in order with savings at the given prices (5.1), a fixed step plan (5.2), evidence ids on every factual sentence (5.3), and a fixed recommendation list with reason codes (5.4).

### Memory

**The question:** what's remembered, and what must never carry across customers?

Memory is **per case only**. Case state lives in the Temporal workflow and the region's Postgres until closure. Prior cases on the same customer are *evidence*: fetched through a facade and cited, never remembered by the model. Procedure and typology text is versioned by Financial Crime Compliance, with each version hash written on the case. Analyst edits are stored as labels for evaluation, not fed back automatically.

The decision: learning from analyst edits goes through a **validated release**, because an unreviewed feedback loop is an unvalidated model change.

**The trap:** a vector memory of past narratives used as examples. Customer facts from one case then appear in another customer's file.

**Rubric:** per-case memory only (6.1), prior cases as cited evidence (6.2), and learning through a validated release (6.3).

### MCP Tool Servers

**The question:** which tools exist, and which deliberately don't?

Each region runs its own facades on the MCP SDK. Read tools: `get_profile`, `get_txn_features`, `get_flagged_txns`, `screen_party`, `get_ownership_chain`, `search_media`, `get_prior_cases`. One write tool: `attach_draft(case_id)`, labeled "AI-prepared" in Actimize. `group_signal` returns the one bit and a contact. Each facade has its own service identity and is reachable only from its region.

The most important line in this section is what's missing: **no close, escalate or file tool exists.** A capability the model doesn't have can't be prompted into use.

**The trap:** a `close_alert` tool guarded by "only after analyst approval" in the prompt. That's a control in a prompt.

**Rubric:** typed read-only tools per region (7.1), no disposition tools (7.2), and drafts labeled AI-prepared (7.3).

## 6. Pillar C: Serve and store

### Endpoints

**The question:** how do analysts, onboarding and examiners interact with the system, and how fast is onboarding?

Analysts never call the agent. It runs on case events (alert created, KYC case opened or due, analyst reopen) and lands in the case manager they already use, through a plug-in calling `GET /v1/cases/{id}/pack`. Examiners' liaison calls `GET /v1/exam/cases/{id}` for the replay bundle, in region.

Low-risk onboarding is the subtle one. The latency table sums to about 5.5 minutes at p95. But the key decision is that **straight-through approval runs on the validated scorecard, not the model**. The draft note is filed after the decision, so the 10-minute target never depends on a model call.

**The trap:** waiting on the model narrative before approving low-risk customers. A provider slowdown then stops onboarding.

**Rubric:** drafts in the existing case manager (8.1), a stage budget under 10 minutes (8.2), scorecard approval without waiting on the model (8.3), and an in-region replay endpoint (8.4).

### Caching

**The question:** what may be cached when stale evidence is a compliance error?

Very little. Prompt-cache the 6k per-entity procedure prefix. Cache registry ownership chains for 30 days, **with the fetch date in the evidence item**. Cache media classification per article id and classifier version. And **never cache screening**: every case screens live.

The reasoning for showing fetch dates: the analyst and the examiner can both see how old each fact was, which turns a caching decision into something auditable.

**The trap:** caching sanctions screening for speed. A customer designated yesterday passes today.

**Rubric:** no screening cache (9.1), fetch dates shown (9.2), and the procedure prefix cached (9.3).

### Data Stores

**The question:** where does each entity's data live, how much, and what does it cost?

Per region: Kafka (14 days of CDC and alert events), Postgres (case state, evidence index and labels, about 2 TB over 7 years), OpenSearch (adverse media, about 3 TB), and **S3 Object Lock in compliance mode** holding the evidence pack, prompt, model id, output and decision for 7 years, about 10 TB in all (section 2). Each case file is hash-chained to the previous one in its region (problem hash-chained-audit-log).

**Temporal is self-hosted in each region**, because workflow history contains customer data. The same logic applies to logs: a global observability tool receiving prompts is a cross-border transfer.

Cost: about $106k a month, with infra prices labeled assumed.

**The trap:** a global observability tool receiving prompts.

**Rubric:** record store sized from cases and bytes (10.1), Object Lock compliance mode (10.2), workflow history and logs in region (10.3), and a total with assumed labels (10.4).

### Output

**The question:** what does the analyst receive, and what does the examiner receive?

The analyst gets an **evidence pack** (each item with source, record id and fetch time, features with their SQL version) and a **draft narrative** (who, what, when, why it matters, each sentence citing evidence ids, a recommendation with reason codes). The system records the **decision**: analyst id, disposition, edits, time spent. The examiner gets a **replay bundle** with all of that plus model id and prompt and procedure hashes, re-renderable in 2033.

The decision: keep the analyst's edits **as a diff against the draft**, because the examiner will ask what the human changed.

**The trap:** storing only the final narrative. Nobody can tell which words the model wrote.

**Rubric:** narrative cites evidence ids (11.1), edits as a diff (11.2), and version hashes in the replay bundle (11.3).

## 7. Pillar D: Run it safely

### Guardrails

**The question:** which controls satisfy the regulators and protect customers?

- No disposition tools. SAR filing, exit and escalation happen only in the case manager by a named analyst.
- **GDPR Article 22 and UK GDPR:** adverse decisions have meaningful human review. The scorecard can approve, never decline.
- **Tipping off:** drafts never reach customer-facing channels, and the agent has no outbound messaging.
- Uncited sentences, and instructions found inside documents or articles, are stripped. Adverse media is untrusted text.
- Model changes go through each entity's model risk process, with versions pinned per region.

The decision that separates strong answers: **below-the-line testing every month.** Analysts blindly review 500 alerts the agent rated low risk, to prove nothing SAR-worthy is being buried.

**The trap:** validating only on agreement with past analyst decisions. Past decisions include the backlog's mistakes.

**Rubric:** meaningful human review of adverse decisions (12.1), no customer channel (12.2), model changes through model risk with pinned versions (12.3), and below-the-line testing (12.4).

### Key Impact

**The question:** how do you prove analysts are faster without missing suspicious activity?

Five metrics: minutes per alert (25 → 12, with a **randomized 10 percent holdout**), US backlog age (41 days → under 10), SAR-worthy cases missed (0 in 500 a month below the line), narrative QA pass (95 percent on 200 a month), and examiner replay time (days → under 1 hour).

The reasoning: speed and detection have to be reported together. Run the holdout for 8 weeks per entity before claiming minutes saved, and report SAR conversion per 1,000 alerts, so faster decisions that miss more show up as a loss.

**The trap:** reporting draft acceptance rate. Analysts under backlog pressure accept drafts they didn't read.

**Rubric:** minutes per alert with a holdout (13.1), a detection measure alongside (13.2), and backlog age against the regulator's finding (13.3).

### Failure Modes

**The question:** what breaks, and what does the bank do?

Every failure degrades to the manual process the bank already runs:

- **Screening vendor outage:** onboarding queues. **Screening is never skipped.**
- **Model endpoint outage in one region:** **no failover to another region.** Cases go to analysts without drafts.
- **Mainframe CDC lag:** the pack shows data age; over 24 h, the case is flagged.
- **Model version retired:** pinned versions plus 6 months of revalidation lead time in the contract.
- **Backlog spike:** the workflow orders by **SAR deadline**, then risk score.

**The trap:** retrying a failed draft forever. The SAR clock keeps running while the case waits on a model.

**Rubric:** no cross-region failover (14.1), no skipped screening (14.2), and backlog ordered by SAR deadline (14.3).

### Build Order

**The question:** in what order do you build across three regulators in 12 months?

US first: stack, CDC and evidence packs **without a model** (months 1–3, measured by minutes per alert with packs alone); drafts in shadow (months 4–5, QA pass on 1,000 drafts); SR 11-7 validation then production with holdout (month 6). Then the UK under SS1/23 (months 7–9), then Germany under MaRisk with batch periodic reviews and an examiner drill (months 10–12).

The reasoning: evidence packs save time on their own and give validators a deterministic baseline. And validation is sequential per regulator, so building three regions in parallel gives you three half-validated stacks.

**The trap:** building all three regions in parallel.

**Rubric:** packs before the model (15.1), validation before production per entity (15.2), and one entity at a time with a number per phase (15.3).

## 8. The decisions that separate strong answers

**Three stacks vs one stack with routing.** One stack is cheaper; the model answer's infrastructure is $87k of its $106k precisely because there are three. But one stack has shared logs, shared workflow history and a shared control plane, all of which carry customer data. The strong answer accepts the cost and says why: residency is the law, so it's the topology.

**Fixed step plan vs research agent.** A research agent might find more. It also gathers different evidence on two runs of the same case, which can't be validated. The fixed plan gives repeatability, and SQL features give arithmetic a validator can test. The model's freedom is limited to prose, where it's most useful.

**Below-the-line testing vs agreement with past decisions.** Agreement is the easy metric and it's circular: the backlog's mistakes are in the labels. Blind review of 500 alerts a month that the agent rated low risk is what directly answers "does the agent bury suspicious activity?"

## 9. Common mistakes

- Letting the model close false positives, even "with a confidence threshold."
- One global stack with regional routing, or a global log pipeline.
- Querying the mainframe with new transactions instead of CDC.
- Sending raw transaction history to the model.
- Caching screening results.
- A disposition tool guarded by a prompt instruction.
- Storing only the final narrative, so the model's words and the analyst's can't be told apart.
- Failing over to another region during an outage.
- No plan for model version retirement by the provider.

## 10. Follow-ups an interviewer might ask

- *The UK analyst wants to know if a US customer is risky.* The group-signal facade returns yes or no and a contact. Anything more goes through the legal channel between entities, not the system.
- *The provider retires the Sonnet version you validated.* Versions are pinned per region, and the contract gives 6 months of revalidation lead time. The new version goes through each entity's model risk process before use.
- *An examiner asks about a 2027 case in 2033.* The replay endpoint returns the bundle from Object Lock: evidence with fetch times, the draft, model id, prompt and procedure hashes, and the analyst's diff.
- *How would you ever automate closures?* Only after below-the-line results stay clean across validated releases, and only through each entity's model risk process. Not in year one.
- *How do you stop PII leaking into logs?* Redact before logging, and keep logs in region (problem pii-redaction-vault).
