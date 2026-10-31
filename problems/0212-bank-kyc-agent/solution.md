# Bank KYC and AML Case Agent: model answer

## 1. Scenario

The user is a financial-crime analyst who must decide an alert or a KYC case; the agent's job is to hand them a complete, sourced evidence pack and a draft narrative so the decision takes 12 minutes instead of 25. The second user is the examiner, who must be able to replay any decision years later.

| What | Number | What it forces |
|---|---|---|
| Cases | 6,000 alerts and about 4,100 KYC cases a day, about 10,100 in all | Low QPS (under 1 model call a second); the weight is evidence, not traffic |
| Analyst time | 6,000 x 25 minutes = 2,500 hours a day on alerts | Halving it frees about 160 analysts' capacity |
| Entities | 3, each with its own regulator and residency | Three stacks, not one with regional routing |
| Deadlines | SAR in 30 days; low-risk onboarding in 10 minutes | Backlog is a compliance breach, not a nuisance |
| Retention | 7 years, replayable | Every input, version and decision written as a record |

**How:**
1. Map every decision in the alert and KYC workflows and label it: model may draft, rules decide, or human decides.
2. Baseline per entity: minutes per alert from Actimize case timestamps, backlog age, and SAR conversion rate.
3. Agree with Compliance and Model Risk that the agent's output is a draft, and that its use is a model under each entity's policy.
4. Out of scope: replacing Actimize rules, filing SARs, customer contact.

**Decision.** The agent prepares and recommends; rules and humans decide, because a SAR decision and an account exit are legal judgments the bank must own by name.

**Trap.** Pitching auto-closure of false positives. It is the biggest saving on paper and the one no validator or regulator will accept in year one.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Sources | Actimize alerts, the US mainframe via DB2 change data capture, Temenos in the UK and Germany, screening vendors, company registries. Hand over raw records per entity | The evidence already exists in 6 systems |
| Regional stack | One full deployment each in US, UK and EU regions. Hands over nothing raw across a border | Residency is the law, so it is the topology |
| Case workflow | Temporal per case, one cluster per region. Hands over steps, deadlines and the analyst task | Cases last days and SAR clocks run in calendar days |
| Evidence facades | MCP servers over each system with typed, read-only tools. Hand over sourced evidence items | Every fact in a narrative needs a source id |
| Feature layer | SQL aggregates over transactions (velocity, counterparties, cash share). Hands over deterministic numbers | Numbers are computed, not read by the model |
| Risk rules | The bank's validated risk-rating scorecard and typology rules. Hands over a score and reason codes | The score is explainable and already validated |
| Drafting model | Sonnet 5.5 in region, Opus 5.5 for escalated cases, pinned versions. Hands over a narrative citing evidence ids | Analysts read prose faster than raw records |
| Analyst desk | Actimize case manager with the draft attached as "AI-prepared". Hands over the disposition and edits | The human decision is recorded where it always was |
| Record store | Hash-chained, write-once evidence packs and decisions per region. Hands over a replayable case file | The examiner's 7-year question |
| Group signal | A legal-approved facade answering "related case in another entity: yes or no, contact". Hands over one bit and a name | Group risk without moving customer data |

**The one idea to hold:** the model writes the narrative from sourced evidence; the scorecard sets the risk, the analyst decides, and the record proves who did what with which version.

## 3. Data Sources

Each entity reads only its own systems; cross-entity knowledge is one derived bit.

**How:**
1. **Alerts**: Actimize alert and case APIs per entity, polled every minute.
2. **US core**: DB2 on z/OS streamed by IBM InfoSphere CDC into the US Kafka; no new load on the mainframe's batch window.
3. **UK and German core**: Temenos events into each region's Kafka.
4. **Screening**: sanctions and PEP vendor APIs; Companies House and the German Handelsregister for ownership chains, cached 30 days.
5. **Adverse media**: a news vendor feed indexed in each region's OpenSearch.

**Decision.** Read the mainframe through CDC, never through new CICS transactions, because the core's batch window is the bank's most protected resource.

**Trap.** Copying German customer data to the US "for the group view". That is an unlawful transfer, and the group view only needs one bit.

## 4. Processing

Evidence is assembled by code into a pack; the model sees summaries and flagged items, not raw history.

**How:**
1. A Temporal workflow per case gathers evidence through the facades in parallel, each item stamped with source system, record id and fetch time.
2. Compute transaction features in SQL: 90-day volume, cash share, new counterparties, round amounts, high-risk geographies; the top 50 flagged transactions go in raw.
3. Resolve entities (name, date of birth, address) against screening hits with a deterministic matcher, and attach the match score.
4. Classify adverse media articles for relevance on a fine-tuned DeBERTa model: about 2 articles a second, 2 L4 GPUs per region for availability, 6 in all.
5. The pack shrinks from 80,000 raw tokens to about 25,000.

**Decision.** Aggregates are computed in SQL and only cited by the model, because a validator can test a SQL feature and cannot test arithmetic done in a prompt.

**Trap.** Sending 90 days of raw transactions to the model. It costs three times more and the model miscounts.

## 5. Agents

One drafting agent per case type, with a fixed step plan; the model writes, it does not choose what to look at.

| Lever, in order | Model cost a month | Saving a month |
|---|---|---|
| Start: Opus 5.5 on 305,000 cases, 80k raw tokens each | $106.8k | |
| Model mix: Sonnet 5.5, Opus 5.5 only for the 5 percent escalated | $56.1k | $50.7k |
| Retrieval trimming: SQL aggregates, 25k tokens | $20.7k | $35.4k |
| Prompt caching of the 6k procedure prefix per entity (cache reads $0.20 on Sonnet and Opus) | $17.2k | $3.5k |
| Batch API for the 75,000 periodic reviews a month | $15.1k | $2.1k |

**How:**
1. Steps are fixed by case type in the workflow: gather, compute, screen, draft; the model only drafts.
2. The draft must cite an evidence id for every factual sentence; uncited sentences fail a checker and are removed.
3. The recommendation is chosen from a fixed list with typology reason codes.

**Decision.** No free-form tool loop, because a validator needs the same case to gather the same evidence every time.

**Trap.** A research agent that decides which systems to query. Two runs of one case then produce different evidence, and the model cannot be validated.

## 6. Memory

Memory is per case only; nothing about one customer informs another customer's draft.

**How:**
1. Case state lives in the Temporal workflow and the region's Postgres case store until closure.
2. Prior cases on the same customer are evidence, fetched through a facade and cited, never remembered by the model.
3. Typology and procedure text is versioned by Financial Crime Compliance, with each version hash written on the case.
4. Analyst edits to drafts are stored as labels for evaluation, not fed back automatically.

**Decision.** Learning from analyst edits goes through a validated release, because an unreviewed feedback loop is an unvalidated model change.

**Trap.** A vector memory of past narratives used as examples. Customer facts from one case then appear in another customer's file.

## 7. MCP Tool Servers

Each region runs its own facades on the MCP SDK; tools are typed and almost all read-only.

**How:**
1. Read tools: `get_profile`, `get_txn_features(window)`, `get_flagged_txns(limit)`, `screen_party`, `get_ownership_chain`, `search_media`, `get_prior_cases`.
2. One write tool: `attach_draft(case_id)` into Actimize, labeled "AI-prepared"; no close, escalate or file tool exists.
3. `group_signal(customer_ref)` returns related-case yes or no and a contact, approved by legal in each entity.
4. Each facade has its own service identity and is reachable only from its own region.

**Decision.** Dispositions are not tools, because a capability the model does not have cannot be prompted into use.

**Trap.** A `close_alert` tool guarded by "only after analyst approval" in the prompt. That is a control in a prompt.

## 8. Endpoints

Analysts never call the agent; it runs on case events and lands in the case manager they already use.

| Stage, low-risk onboarding | p50 | p95 |
|---|---|---|
| ID verification vendor | 40 s | 120 s |
| Sanctions and PEP screening | 3 s | 10 s |
| Ownership chain, cached or live registry | 5 s | 90 s |
| Adverse media search and classify | 15 s | 60 s |
| Risk scorecard | 1 s | 2 s |
| Draft file note | 20 s | 45 s |
| **To decision** | **about 1.5 min** | **about 5.5 min** |

**How:**
1. Event triggers: Actimize alert created, KYC case opened or due, analyst reopen.
2. `GET /v1/cases/{id}/pack` returns the evidence pack and draft to the case manager plug-in.
3. `GET /v1/exam/cases/{id}` returns the full replay bundle to examiners' liaison, in region.
4. Low-risk onboarding with no hits is approved by the scorecard; the draft note is filed after the decision.

**Decision.** Straight-through approval runs on the validated scorecard, not on the model, so the 10 minute target never depends on a model call.

**Trap.** Waiting on the model narrative before approving low-risk customers. A provider slowdown then stops onboarding.

## 9. Caching

Caching is narrow, because stale evidence is a compliance error.

**How:**
1. Prompt-cache the per-entity procedure and typology prefix, 6k tokens.
2. Cache registry ownership chains 30 days, with the fetch date in the evidence item.
3. Never cache screening results: every case screens live against the current list.
4. Cache media classification per article id and classifier version.

**Decision.** Every cached item shows its fetch date in the pack, so the analyst and the examiner can see how old each fact was.

**Trap.** Caching sanctions screening for speed. A customer designated yesterday passes today.

## 10. Data Stores

Each region holds its own complete set; only aggregate metrics leave a region.

| Store, per region | Holds | Size |
|---|---|---|
| Kafka | CDC and alert events, 14 days | US about 200 GB |
| Postgres | Case state, evidence index, labels | About 2 TB over 7 years |
| OpenSearch | Adverse media index | About 3 TB |
| S3 Object Lock, compliance mode | Evidence pack, prompt, model id, output, decision, 7 years | 305,000 cases a month x 400 KB, about 10 TB over 7 years in all |

**How:**
1. Each case file is hash-chained to the previous one in its region, with the prompt, procedure and model version hashes.
2. Infra cost, assumed list prices: about $29k a month per region (EKS, Postgres, Kafka, OpenSearch, self-hosted Temporal, logging), $87k for three, plus 6 L4 GPUs at an assumed $0.85 an hour, $3.7k.
3. Total with models: about $106k a month; screening and data vendor licenses are existing contracts.

**Decision.** Self-host Temporal in each region, because workflow history contains customer data and must stay in jurisdiction.

**Trap.** A global observability tool receiving prompts. Logs are a cross-border transfer too.

## 11. Output

The analyst receives a pack and a draft; the examiner receives a replay.

**How:**
1. **Evidence pack**: every item with source, record id and fetch time; features with their SQL version.
2. **Draft narrative**: who, what, when, why it matters, each sentence citing evidence ids; a recommendation with typology reason codes.
3. **Decision record**: analyst id, disposition, edits to the draft, time spent.
4. **Replay bundle**: all of the above plus model id, prompt and procedure hashes, re-renderable in 2033.

**Decision.** The analyst's edits are kept as a diff against the draft, because the examiner will ask what the human changed.

**Trap.** Storing only the final narrative. Nobody can then tell which words the model wrote and which the analyst did.

## 12. Guardrails

The controls that protect customers and the bank live in code and process, never in a prompt.

**How:**
1. No disposition tools; SAR filing, exit and escalation happen only in the case manager by a named analyst.
2. Under GDPR Article 22 and UK GDPR, adverse decisions have meaningful human review; the scorecard can approve, never decline.
3. Tipping-off control: drafts never reach customer-facing channels; the agent has no outbound messaging.
4. Uncited sentences and instructions found inside documents or articles are stripped; adverse media is untrusted text.
5. Model changes go through each entity's model risk process; versions are pinned per region.

**Decision.** Below-the-line testing every month: analysts review 500 alerts the agent rated low risk, blind, to prove nothing SAR-worthy is being buried.

**Trap.** Validating only on agreement with past analyst decisions. Past decisions include the backlog's mistakes.

## 13. Key Impact

The business metric is analyst minutes per alert at no loss of detection.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Minutes per alert | 25 | 12 | Case manager timestamps, randomized 10 percent holdout |
| US backlog age | 41 days | Under 10 days | Oldest open alert, daily |
| SAR-worthy cases missed | Unknown | 0 in 500 a month below the line | Blind analyst review |
| Narrative QA pass | Unknown | 95 percent | QA team sample of 200 a month |
| Examiner replay time | Days | Under 1 hour | Quarterly drill |

**How:**
1. Run the holdout for 8 weeks per entity before claiming minutes saved.
2. Report SAR conversion per 1,000 alerts, so faster decisions that miss more show up as a loss.

**Decision.** Minutes saved are reported with the below-the-line result beside them, because speed without detection is what regulators fine.

**Trap.** Reporting draft acceptance rate. Analysts under backlog pressure accept drafts they did not read.

## 14. Failure Modes

Every failure below degrades to the manual process the bank already runs.

**How:**
1. **Screening vendor outage**: onboarding queues; screening is never skipped.
2. **Model endpoint outage in one region**: no failover to another region; cases go to analysts without drafts.
3. **Mainframe CDC lag**: the pack shows transaction data age; over 24 h, the case is flagged.
4. **Model version retired by the provider**: pinned versions plus 6 months of revalidation lead time in the contract.
5. **Backlog spike**: the workflow orders by SAR deadline, then risk score.

**Decision.** No cross-region failover ever, because a residency breach during an outage is worse than a slow day.

**Trap.** Retrying a failed draft forever. The SAR clock keeps running while the case waits on a model.

## 15. Build Order

Twelve months, one entity at a time, each phase ending in a number.

**How:**
1. **Months 1-3**: US stack, CDC from DB2, facades, evidence packs without a model. Measure: minutes per alert with packs alone.
2. **Months 4-5**: drafts in shadow on US alerts. Measure: QA pass rate on 1,000 drafts.
3. **Month 6**: SR 11-7 validation, then US production with holdout. Measure: minutes per alert and below-the-line result.
4. **Months 7-9**: UK stack and SS1/23 validation. Measure: UK minutes per alert.
5. **Months 10-12**: German stack under MaRisk, KYC periodic reviews in batch, examiner drill. Measure: replay time.

**Decision.** Ship evidence packs before any model, because they save time on their own and give validators a deterministic baseline.

**Trap.** Building all three regions in parallel. Validation is sequential per regulator, and three half-validated stacks help nobody.
