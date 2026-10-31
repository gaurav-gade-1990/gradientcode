# Agent Evals and Observability: model answer

## 1. Scenario

The users are 12 agent teams who need to know within minutes whether a change made their agent worse, and the leadership who need one quality number per agent they can trust. The platform turns every run into a trace, scores a slice of them, blocks bad changes in CI, and turns failures into new test cases.

| What | Number | What it forces |
|---|---|---|
| Spans | 42M a day, 486/s average, 1,500/s peak | Async export and sampling; no synchronous writes in the agent path |
| Raw content | 42M x 6 KB = 252 GB a day | Keep metadata for all, content for a slice |
| Detection | Page within 30 minutes | Online signals per 15 minute window, not a weekly CSAT export |
| Changes | 40 a week, gate under 20 minutes | Golden sets must be small, parallel and statistically honest |
| Budget | $50k a month | Judging every run would cost $788k a month on Sonnet 5.5, and $39k even on Haiku 5.5 |

**How:**
1. Inventory the 30 agents: owner, model, prompt version, current success signal, and whether a golden set exists (today 7 do).
2. Define one success metric per agent with its owner, such as resolved without escalation for support.
3. Set baselines: 8 days to detect the last regression, 0 percent of thumbs-down reviewed, 0 changes gated.
4. Out of scope: building the agents, and model training.

**Decision.** Every agent gets the same trace schema and the same gate, because a quality number computed 12 different ways cannot be compared or trusted.

**Trap.** Starting with a dashboard. Without versioned traces and a calibrated judge the dashboard charts noise.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Agent SDK | OpenTelemetry with the GenAI semantic conventions, batched async export. Hands over spans tagged with run id, tenant, agent, prompt, model and tool versions | Under 1 ms per span in the request path |
| Collector | OTel Collector tier with trace-id load balancing and tail sampling. Hands over full metadata and sampled content | Sampling decisions need the whole trace |
| Event log | Kafka topics for spans, feedback and eval results. Hands over one ordered stream per tenant partition | Every store and evaluator is a consumer |
| Trace store | ClickHouse for metadata, S3 Parquet for content, Langfuse as the trace UI. Hands over queryable runs | Cheap columnar scans over 42M spans a day |
| Online evals | Rule checks on 100 percent, NLI groundedness on GPUs, a small-model judge on a sample. Hands over scores per run | Quality signal within minutes |
| Offline evals | Temporal workflows running golden sets from GitHub Actions. Hands over pass or block with reasons | A change cannot ship worse than it was |
| Human review | Argilla queues for disagreements and negative feedback. Hands over labels | Labels calibrate the judge and grow the golden sets |
| Alerts | Grafana dashboards and burn-rate alerts to PagerDuty. Hands over a page with the suspect version | Detection in 30 minutes, with the cause attached |

**The one idea to hold:** every score is tied to the exact versions that produced it, so a drop always points at a change.

## 3. Data Sources

Four streams feed the platform, all keyed by run id.

**How:**
1. **Spans** from the SDK: model calls with tokens and cost, tool calls with status, retrieval with chunk ids.
2. **Explicit feedback**: thumbs, free text and escalations from the product, about 28k thumbs-down a day.
3. **Outcomes** from systems of record: ticket reopened in 72 h, invoice disputed, posted to Kafka by each team.
4. **Change events**: every deploy of a prompt, model, tool or index, with its version, from CI.

**Decision.** Change events are first-class data, because "what changed at 14:05" is the first question in every regression.

**Trap.** Using thumbs as the quality metric. Under 1 percent of users click, and they skew angry.

## 4. Processing

The collector decides what to keep; stream jobs turn spans into scores and windows.

**How:**
1. Tail sampling keeps content for every run that errored, got negative feedback, failed its judge, cost over $0.20, or ran over 30 s, plus 5 percent of healthy runs: about 10 percent of runs, 25 GB a day.
2. Tenants that opted out get content stripped inside the SDK; their runs are scored in-process and only scores leave.
3. A Flink job computes per agent, per 15 minute window: escalation rate, tool error rate, re-ask within 10 minutes, cost per run, and judge pass rate. The support agent's 1M runs a day give about 2,000 judged runs per 30 minutes, so a 9-point drop from 85 percent is about 11 standard errors, and even a 3-point drop shows in one window.
4. Per-tenant span quotas at the collector (default 2M spans a day) drop healthy content first when a runaway agent floods.

**Decision.** Metadata is never sampled and content is sampled by interest, because cost and latency need every run but a reviewer only reads the interesting ones.

**Trap.** Head sampling at 10 percent. It discards 90 percent of the failures before anyone knows they failed.

## 5. Agents

The platform's model-driven parts are judges and a failure clusterer, each with a measured agreement rate. Judging cost falls by applying three levers in order.

| Lever, in order | Judging and gates a month | Saving a month |
|---|---|---|
| Start: Sonnet 5.5 judges all 105M runs at $0.0075 | $788k | |
| Model mix: Haiku 5.5 judges ($0.000375), Sonnet 5.5 calibrates 5k a day | $40.5k | $747k |
| Sampling: 10 percent plus all negative feedback, 380k a day | $5.4k | $35.1k |
| Gates: 3,600 Sonnet 5.5 cases a change, 173 changes | $12.9k | |
| Gates: prompt caching of agent prefixes | $7.9k | $5.0k |
| Gates: reuse outputs of unchanged cases on reruns | $6.7k | $1.2k |

**How:**
1. **Rubric judge** on Haiku 5.5 at 3,000 input and 150 output tokens per run; disagreements with the calibration judge go to humans.
2. **Groundedness**: a DeBERTa-v3 NLI model checks each sentence against its cited passage on all 1.75M RAG runs: 8.75M pairs a day, 300 pairs/s peak, on 3 L4 GPUs (2 for load, 1 spare).
3. **Pairwise judge** for canaries runs in both orders; inconsistent pairs count as ties.
4. A weekly job clusters failed runs with HDBSCAN and names each cluster.

**Decision.** A judge ships only at Cohen's kappa of at least 0.6 against 400 human labels per agent, rechecked quarterly and on every judge-model change.

**Trap.** Using the agent's own model as its judge. It shares the same blind spots and rates its own style higher.

## 6. Memory

The platform remembers baselines, labels and the golden sets.

**How:**
1. **Reference windows**: 28 days of per-agent metric distributions and input embeddings in ClickHouse, the baseline for drift.
2. **Golden sets**: versioned in Git LFS with a manifest per agent, 300 to 1,000 cases, each tagged by slice and must-pass.
3. **Labels**: Argilla records with labeler, rubric version and source run id.
4. **Eval history**: every gate result with versions, per-case outcomes and cost, kept 13 months.

**Decision.** Every golden case keeps its source run id, so a GDPR erasure cascades into the test sets too.

**Trap.** Copying production conversations into golden sets without scrubbing. The test suite becomes the least-governed copy of customer data.

## 7. MCP Tool Servers

The platform exposes itself as an MCP server for engineers' coding agents and the on-call triage agent.

**How:**
1. Tools: `search_runs(agent, filter, window)`, `get_run(run_id)`, `compare_eval_runs(a, b)`, `open_label_task(run_ids)`.
2. Read-only, scoped by the caller's team and tenant grants through the same OAuth as the UI.
3. Results return metadata and redacted content, capped at 20k tokens with cursors.
4. Built on the MCP Python SDK; every call is itself traced.

**Decision.** No write tools beyond opening a label task, because an agent that can edit golden sets can grade itself.

**Trap.** Returning raw trace content to the triage agent. Customer text then reaches a model and a team that never had access.

## 8. Endpoints

Ingest is OTLP; everything else is a small REST surface for CI, product feedback and privacy requests.

| Endpoint | Purpose |
|---|---|
| OTLP gRPC `:4317` | Span ingest through the collector |
| `POST /v1/feedback` | Thumbs, text and escalations, by run id |
| `POST /v1/gates` | CI starts a gated eval; returns a gate id |
| `GET /v1/gates/{id}` | Pass or block, with failed cases and slices |
| `POST /v1/erasure` | Tenant and subject id; returns a ticket with a 30 day deadline |

| Stage, run to alert | p95 |
|---|---|
| SDK batch and export | 3 s |
| Collector tail-sampling wait | 30 s |
| Kafka to ClickHouse | 15 s |
| Judge queue and scoring | 8 min |
| 15 minute window close and alert rule | 16 min |
| **Run to page** | **about 25 min** |

**How:**
1. The SDK exports in batches of 512 spans or every 2 s, dropping rather than blocking when the buffer fills.
2. Gates run as Temporal workflows so a CI retry rejoins the same run instead of paying twice.
3. Eval traffic uses its own provider quota of 4M tokens a minute, so a gate storm cannot throttle production.

**Decision.** The agent's request path only pays for an in-memory append, because observability that adds latency gets turned off.

**Trap.** Exporting spans synchronously. A collector hiccup becomes a customer outage.

## 9. Caching

Caching here saves judge dollars and gate minutes.

**How:**
1. Cache judge results by hash of (rubric version, judge model, input, output), so re-running a gate on unchanged cases costs nothing.
2. Cache agent outputs in offline runs by (case, all versions, seed) for the unchanged half of a pull request's reruns.
3. Prompt-cache the judge rubric and few-shot block, about 2,000 of the 3,000 tokens.
4. Pre-aggregate dashboards in ClickHouse materialized views per agent and 15 minutes.

**Decision.** Any version change in the key invalidates, because a stale score attached to a new prompt is worse than no score.

**Trap.** Caching on the input alone. A new model then inherits the old model's grades.

## 10. Data Stores

Metadata and content live apart, so cost, erasure and opt-outs each touch one store.

| Store | Holds | Size |
|---|---|---|
| Kafka (MSK) | Spans, feedback, scores, 3 days | About 90 GB a day, including the judge sample's content |
| ClickHouse | Span metadata 30 days, rollups 13 months | 42 GB a day raw, about 5 GB compressed; 160 GB hot |
| S3 Parquet | Sampled content, 90 days, partitioned by tenant and day | 25 GB a day raw, 5 GB zstd; 450 GB |
| Postgres | Gates, judge versions, calibration results | Under 10 GB |
| Git LFS | Golden sets | Under 2 GB |

**How:**
1. Monthly cost: judges $5.4k and gates $6.7k (from the lever table), NLI GPUs $1.9k (3 L4 at an assumed $0.85 an hour), and assumed infra prices of ClickHouse $4k, MSK $2.5k, collectors $2k, Grafana Cloud $1.5k, Argilla $0.5k: about $24.5k against $50k, leaving room to double the judge sample.
2. Erasure: ClickHouse lightweight deletes on the hashed subject id; a weekly compaction rewrites affected Parquet partitions.

**Decision.** Content lives apart from metadata, so erasure and opt-outs touch one small store, not the whole history.

**Trap.** Storing content in the same rows as metrics. Every erasure then rewrites months of metrics.

## 11. Output

Four outputs, each tied to versions.

**How:**
1. **Gate result**: pass or block, the failed must-pass cases, slice deltas with confidence intervals, and cost of the run, posted on the pull request.
2. **Agent scorecard**: success metric, judge pass rate, groundedness, cost per successful run, per day and per version.
3. **Page**: the metric, the window, the change event nearest before the drop, and 5 example run links.
4. **Weekly failure clusters** with counts and links, turned into golden-set candidates.

**Decision.** Every alert carries the suspect change, because detection without a cause still costs a day of bisecting.

**Trap.** Reporting the judge score alone. Leadership needs the business outcome; the judge is a leading indicator.

## 12. Guardrails

Limits on cost, tenant data and gate integrity live in code, not in a prompt or a team's goodwill.

**How:**
1. Gate rule in code: block on any must-pass failure, a paired drop over 3 points with McNemar p under 0.05, or a drop over 8 points in any slice of 50 or more cases.
2. Why 3 points: at 600 cases and an 85 percent pass rate, an unpaired difference has a standard error of about 2.1 points; pairing with about 6 percent discordant cases cuts it to about 1 point.
3. Per-team monthly eval spend caps, enforced in the gate workflow; overrides need a second approver.
4. Judges run on scrubbed content; opt-out tenants are scored in-process only.

**Decision.** Overriding a block needs a named approver and is logged, because a gate that anyone can skip trains everyone to skip it.

**Trap.** A fixed 2-point threshold on 600 cases. It blocks on noise, teams learn to rerun until green, and the gate is dead.

## 13. Key Impact

Five numbers show whether regressions are now caught and whether the scores can be trusted.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Time to detect a regression | 8 days | Under 30 minutes | Change event to page, from replayed incidents |
| Changes gated | 0 percent | 100 percent | CI checks against deploy events |
| Judge agreement | Unknown | Kappa at least 0.6 | Quarterly 400-label audit per agent |
| Negative feedback reviewed | 0 percent | 100 percent triaged in 5 days | Argilla queue age |
| Regressions reaching production | 3 a quarter | Under 1 | Incident reviews |

**How:**
1. Replay last month's 9-point drop through the pipeline before launch and time the page.
2. Report cost per successful run next to quality, so a cheaper model that fails more shows as a loss.

**Decision.** Headline the detection time, because it is the number that failed and the one leadership asked about.

**Trap.** Counting judged runs. Volume of scoring says nothing about whether the scores are right.

## 14. Failure Modes

The eval system fails in its own ways, separate from the agents it watches.

**How:**
1. **Judge drift after a provider update**: a nightly run on 200 fixed calibrated cases alerts if agreement drops 5 points.
2. **Collector overload**: per-tenant quotas shed healthy content; metadata keeps flowing.
3. **Low-traffic agents**: 10 percent of 2,000 runs a day is 200, too few; sample at least 300 a day per agent.
4. **Eval storm before a release**: Temporal queues gates by priority within the 4M TPM eval quota.
5. **Golden set staleness**: cases older than 6 months with no failures are retired quarterly.

**Decision.** Observability fails open for the agent and closed for the gate: lost spans never block a customer, but a gate that cannot finish blocks the merge.

**Trap.** Trusting the judge after the provider silently updates it. The scores move and the agent did not change.

## 15. Build Order

Six phases over 26 weeks for 6 engineers, each ending with a number.

**How:**
1. **Weeks 1-4**: SDK, collector, Kafka, ClickHouse, Langfuse for all 30 agents. Measure: runs with full version tags, 100 percent.
2. **Weeks 5-8**: rule checks and Flink windows, burn-rate alerts. Measure: replayed incident detection time.
3. **Weeks 9-13**: golden sets and the CI gate for the 7 agents that have sets. Measure: gate time under 20 minutes.
4. **Weeks 14-18**: small-model judge, calibration, NLI on GPUs. Measure: kappa per agent.
5. **Weeks 19-22**: Argilla loop and erasure. Measure: feedback triage age.
6. **Weeks 23-26**: sets for the other 23 agents and failure clusters. Measure: changes gated, 100 percent.

**Decision.** Tracing and cheap signals before judges, because the 9-point drop would have shown in escalation rate alone.

**Trap.** Building the judge first. Without traces and labels there is nothing to judge and nothing to check it against.
