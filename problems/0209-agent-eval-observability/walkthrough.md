## 1. What the problem is really asking

Strip the story and this is a **measurement system with a cost ceiling**. Thirty agents produce 3.5 million runs a day. You have to notice within 30 minutes when one of them gets worse, block changes that would make one worse, and do all of it for $50,000 a month. The last regression took eight days to notice because the only signal was a weekly CSAT export.

The core tension is **coverage against cost**. You'd like to trace every span, store every prompt and judge every run with a strong model. The numbers in section 2 show you can't: judging everything on Sonnet 5.5 costs more than fifteen times the whole budget. So the design is a set of decisions about what you keep for *every* run, what you keep for *some* runs, and how you prove that the sampled signal still catches a regression in time.

Three decisions carry the design:

- **Metadata for all, content for a slice.** Tokens, cost, latency, tool status and version tags are kept for 100 percent of runs. Prompt and completion text is kept by tail sampling, which keeps every interesting run and a few percent of healthy ones.
- **A cheap judge you have calibrated.** Haiku 5.5 does the judging, Sonnet 5.5 checks a small sample, and humans label enough runs to compute an agreement statistic. A judge you haven't measured against humans is just another opinion.
- **A gate whose threshold is set by statistics, not taste.** The threshold that blocks a merge comes from the standard error at the golden-set size. If it's tighter than the noise, teams rerun until green and the gate dies.

Underneath all three is one idea from the model answer: every score is tied to the exact prompt, model and tool versions that produced it, so a drop always points at a change.

## 2. The numbers that drive the design

Do this arithmetic out loud in the first few minutes. Every later section leans on it.

**Span rate.** The prompt gives 42 million spans a day.

- 42,000,000 / 86,400 s = **486 spans/s average**. The prompt gives the peak: **1,500/s**.
- That rate rules out synchronous writes from the agent. Export has to be batched and async.

**Raw content volume.** 42M spans × 6 KB = **252 GB a day** if you kept every prompt and completion. That's the number that pushes you to keep content for a slice only.

**Cost of judging everything.** Assume the judge reads 3,000 input tokens and writes 150 output tokens per run, the figures the model answer uses.

| Judge | Input cost | Output cost | Per run | × 105M runs a month |
|---|---|---|---|---|
| Sonnet 5.5 ($2 / $10) | 3,000 × $2/M = $0.006 | 150 × $10/M = $0.0015 | **$0.0075** | **$788k** |
| Haiku 5.5 ($0.10 / $0.50) | 3,000 × $0.10/M = $0.0003 | 150 × $0.50/M = $0.000075 | **$0.000375** | **$39k** |

105M runs a month is 3.5M a day × 30. Sonnet on everything is about sixteen times the $50k budget. Haiku on everything nearly fits, but it would eat most of the budget and leave nothing for storage, GPUs or gates. This is the arithmetic rubric criterion 1.3 asks for.

**Applying the levers in order.** The model answer's lever table goes:

1. **Model mix:** Haiku judges all 105M runs ($39.4k) and Sonnet calibrates 5,000 a day (150k a month × $0.0075 = $1.1k). Total **$40.5k**, saving $747k.
2. **Sampling:** judge 10 percent of runs (350k a day) plus all negative feedback (about 28k thumbs-down a day, which is 0.8 percent of 3.5M). That's about 380k a day, or 11.4M a month × $0.000375 = $4.3k, plus the same $1.1k calibration: **$5.4k**.
3. **Gates:** 40 changes a week is about 173 a month (40 × 52 / 12). The model answer budgets 3,600 Sonnet 5.5 cases a change for **$12.9k**, then prompt caching of agent prefixes takes it to $7.9k and reusing unchanged outputs on reruns takes it to **$6.7k**.

**Can a sample still catch the regression?** The support agent runs 1M times a day. In 30 minutes that's 1M / 48 ≈ 20,800 runs, and 10 percent of those is about 2,000 judged runs. At an 85 percent pass rate the standard error is √(0.85 × 0.15 / 2,000) ≈ 0.8 points. The 9-point drop from last month is about 11 standard errors, so sampling doesn't cost you detection on the big agents. The small ones are a different story (see Failure Modes).

**Storage after sampling.** Tail sampling keeps content for about 10 percent of runs: 10 percent of 252 GB ≈ **25 GB a day**. Metadata is about 42 GB a day raw, roughly 5 GB compressed in ClickHouse. Keeping 30 days of that is about 150 GB, and with 13 months of rollups you get the model answer's 160 GB hot. Content at 5 GB a day zstd × 90 days = **450 GB** in S3.

**The whole budget.** Judges $5.4k + gates $6.7k + NLI GPUs $1.9k (3 L4 × $0.85/h × 730 h) + assumed infra (ClickHouse $4k, MSK $2.5k, collectors $2k, Grafana Cloud $1.5k, Argilla $0.5k) = **about $24.5k**, against $50k.

**The latency budget.** 3 s export + 30 s tail-sampling wait + 15 s into ClickHouse + 8 min judge queue + 16 min window close and alert ≈ **25 minutes**, inside the 30-minute target.

## 3. How to spend your time

The problem allows 60 minutes. A workable plan:

| Minutes | What you do |
|---|---|
| 0–5 | Read the prompt. Write down 486/s, 252 GB a day, $788k vs $39k. |
| 5–12 | **Pillar A.** Scenario with the numbers table, then the Single View. Get the event log and the version tags on the diagram. |
| 12–30 | **Pillar B.** Sampling and stream windows, then the judge lever table and calibration. This is where most of the marks are. |
| 30–42 | **Pillar C.** Endpoints with the run-to-page budget, caching keys, stores with sizes and the cost total. |
| 42–55 | **Pillar D.** The gate threshold with its standard error, impact table, failure modes, the 26-week plan. |
| 55–60 | Check each section has a decision and a trap, and that the cost total is under $50k. |

If you're short of time, don't skimp on Processing, Agents and Guardrails. Those three sections hold the statistics and the money, and they're what separates this problem from a generic logging design.

## 4. Pillar A: Frame

### Scenario

**The question:** who uses this, what must it detect, and which numbers shape it?

The users are the 12 agent teams and leadership. The job is "know within minutes that a change made an agent worse, and stop bad changes before they ship." The headline requirement is the **30-minute page**, because that's the number that failed (eight days) and the one leadership asked about.

How to reason to it: put the scale numbers in a table where each row says *what it forces*. 486/s forces async export. 252 GB a day forces content sampling. $788k forces a cheap judge. 40 changes a week with a 20-minute gate forces small, parallel golden sets. Then define one **business** success metric per agent with an owner, such as "resolved without escalation" for support. A judge score alone isn't enough, because leadership cares about outcomes and the judge is only a leading indicator.

Set baselines: 8 days to detect, 0 percent of thumbs-down reviewed, 0 changes gated, and 7 of the 30 agents with a golden set today. Put building the agents and model training out of scope.

**The trap:** starting with a dashboard. Without versioned traces and a calibrated judge, the dashboard charts noise.

**Rubric:** converting 42M spans to per-second and bytes (1.1), one business metric per agent (1.2), the unaffordable-judging arithmetic (1.3), and 30 minutes as the headline (1.4).

### Single View

**The question:** what's the path from an agent run to a page, and to a CI block?

The model answer has eight layers: Agent SDK → Collector → Event log → Trace store → Online evals → Offline evals → Human review → Alerts. The reasoning for each boundary:

- **Agent SDK on OpenTelemetry** with the GenAI semantic conventions, because 12 teams won't adopt a custom format, and async batched export keeps the cost under 1 ms per span.
- **A collector tier that does tail sampling.** The sampling decision needs the whole trace (did it error? did it get a thumbs-down?), so it can't happen in the SDK.
- **Kafka between collection and everything else.** Every store and evaluator becomes a consumer, so adding a new evaluator doesn't touch ingest.
- **Online evals, offline gates and human review as separate layers.** They run on different clocks (minutes, per pull request, days) and fail differently.

The alternative is to send spans straight from the SDK into a vendor tracing tool and call it done. That gives you traces, but no place for tail sampling, no replayable stream for evaluators, and no gate.

**The trap:** forgetting the version tags. If spans don't carry prompt, model and tool versions, a drop can't point at a change. That's why the model answer's one idea is about versions.

**Rubric:** OpenTelemetry with async export (2.1), an event log in the middle (2.2), the three eval layers kept apart (2.3), and version tags on every span (2.4).

## 5. Pillar B: Build the core

### Data Sources

**The question:** which signals feed quality, and which ones mislead?

Four streams, all keyed by run id: spans from the SDK, explicit feedback (thumbs, text, escalations), outcomes from systems of record (ticket reopened within 72 hours, invoice disputed), and change events from CI.

The reasoning: thumbs look like the obvious quality signal, but under 1 percent of users click and they skew angry. Outcomes from systems of record are slower but honest. And **change events are data**, because "what changed at 14:05" is the first question in every regression. Without them, a page tells you something broke but not what.

**The trap:** using thumbs as the quality metric.

**Rubric:** outcomes from systems of record (3.1), change events recorded as data (3.2), and noting feedback is sparse and biased (3.3).

### Processing

**The question:** what's sampled, what's computed in stream, and how do you stop one tenant flooding the pipeline?

The alternatives for sampling are head sampling (decide at the start of a trace, keep 10 percent) and tail sampling (decide when the trace is complete). Head sampling is cheaper to run but discards 90 percent of failures before anyone knows they failed. Tail sampling keeps content for every run that errored, got negative feedback, failed its judge, cost over $0.20 or ran over 30 s, plus 5 percent of healthy runs. That comes to about 10 percent of runs and 25 GB a day. **Metadata is never sampled.**

Opt-out tenants have content stripped inside the SDK and are scored in-process, so only scores leave.

For detection, a Flink job computes per agent per 15-minute window: escalation rate, tool error rate, re-ask within 10 minutes, cost per run and judge pass rate. Show the statistics from section 2 here: about 2,000 judged runs per 30 minutes on support, so a 9-point drop is about 11 standard errors.

For isolation, a per-tenant span quota at the collector (default 2M spans a day) drops healthy content first when a runaway agent floods.

**The trap:** head sampling at 10 percent.

**Rubric:** tail sampling that keeps errors and negative feedback (4.1), 100 percent metadata (4.2), windows short enough for 30 minutes (4.3), and the per-tenant quota (4.4).

### Agents

**The question:** which judges score runs, what do they cost, and how do you trust them?

This is the section with the lever table, and the reasoning is the order you apply levers: model mix first (biggest saving, $747k), then sampling ($35.1k), then the gate levers. Reveal the model answer for the full table.

There are three model-driven scorers, plus a clustering job:

- **Rubric judge** on Haiku 5.5 at 3,000 in and 150 out. Disagreements with the Sonnet calibration judge go to humans.
- **Groundedness** with a DeBERTa-v3 NLI model on all 1.75M RAG runs: 8.75M sentence-passage pairs a day, 300 pairs/s at peak, on 3 L4 GPUs (2 for load, 1 spare). This is the "size it in GPUs from a throughput number" the rubric wants.
- **Pairwise judge** for canaries runs in both orders, and inconsistent pairs count as ties. That cancels position bias (problem llm-judge-position-swap builds this).
- A weekly HDBSCAN job clusters failed runs.

**How you trust the judge:** it ships only at Cohen's kappa of at least 0.6 against 400 human labels per agent, rechecked quarterly and on every judge-model change. Kappa rather than raw agreement, because at an 85 percent pass rate a judge that always says "pass" agrees 85 percent of the time.

**The trap:** using the agent's own model as its judge. It shares the agent's blind spots and rates its own style higher.

**Rubric:** judge priced per run and per month (5.1), kappa with a threshold (5.2), both orders for pairwise (5.3), and GPU sizing from throughput (5.4).

### Memory

**The question:** what does the platform keep over time to compare against?

Four things: 28-day reference windows of per-agent metric distributions and input embeddings (the drift baseline), versioned golden sets in Git LFS with 300 to 1,000 cases each tagged by slice and must-pass, Argilla labels with labeler and rubric version, and 13 months of gate history.

The decision that earns the marks: **every golden case keeps its source run id**, so a GDPR erasure cascades into the test sets. That connects Memory to the 30-day erasure requirement.

**The trap:** copying production conversations into golden sets without scrubbing. The test suite becomes the least-governed copy of customer data.

**Rubric:** reference window for drift (6.1), versioned sets with slices and must-pass (6.2), and source run links so erasure cascades (6.3).

### MCP Tool Servers

**The question:** what does the platform expose to agents, and with what limits?

Here the platform *is* the MCP server, for engineers' coding agents and an on-call triage agent. Tools: `search_runs`, `get_run`, `compare_eval_runs`, and `open_label_task`. They're read-only and scoped by the caller's team and tenant grants through the same OAuth as the UI. Results return metadata and redacted content, capped at 20k tokens with cursors.

The reasoning for no write tools: an agent that can edit golden sets or scores can grade itself. Opening a label task is allowed because a human still does the labeling.

**The trap:** returning raw trace content to the triage agent. Customer text then reaches a model and a team that never had access.

**Rubric:** read-only search and lookup (7.1), scoping by team and tenant grants (7.2), and no write access to golden sets or scores (7.3).

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what endpoints exist, and how long from a bad run to a page?

Ingest is OTLP gRPC; the rest is a small REST surface: feedback, start a gate, get a gate result, and an erasure request that returns a ticket with a 30-day deadline.

The part that earns most marks is the **stage-by-stage latency budget**, which sums to about 25 minutes (section 2). Lay it out as a table so the examiner can see the 30-minute target is met with room to spare. Note that the biggest stage is the 15-minute window itself, which is why the window can't be an hour.

Three rules in How:

- The SDK exports in batches of 512 spans or every 2 s, and **drops rather than blocks** when its buffer fills.
- Gates run as Temporal workflows, so a CI retry rejoins the same run instead of paying twice.
- Eval traffic has its own provider quota of 4M tokens a minute, so a gate storm can't throttle production agents.

**The trap:** exporting spans synchronously. A collector hiccup becomes a customer outage.

**Rubric:** export off the critical path (8.1), the latency budget under 30 minutes (8.2), a separate eval quota (8.3), and durable gate runs (8.4).

### Caching

**The question:** what's cached to save judge cost and gate time, and what invalidates it?

Cache judge results by a hash of (rubric version, judge model, input, output). Cache offline agent outputs by (case, all versions, seed) so the unchanged cases in a pull request's rerun cost nothing. Prompt-cache the judge rubric and few-shot block, about 2,000 of the 3,000 tokens. Pre-aggregate dashboards with ClickHouse materialized views.

The reasoning is all in the cache key. If you key on the input alone, a new judge model inherits the old model's grades and a new rubric inherits the old rubric's. Any version change in the key must invalidate, because a stale score attached to a new prompt is worse than no score.

**The trap:** caching on the input alone.

**Rubric:** keys include rubric version and judge model (9.1), reuse of unchanged offline outputs (9.2), and prompt-caching the rubric prefix (9.3).

### Data Stores

**The question:** where do metadata and content live, how big are they, and what does it cost?

Five stores: Kafka (3 days), ClickHouse for metadata (30 days, plus 13 months of rollups), S3 Parquet for sampled content (90 days, partitioned by tenant and day), Postgres for gates and calibration, Git LFS for golden sets. Sizes come straight from section 2: 160 GB hot in ClickHouse, 450 GB in S3.

Then the cost total, about $24.5k against $50k, leaving room to double the judge sample. Label every non-model price as assumed, as the model answer does.

The design choice is **content apart from metadata**. Erasure and opt-outs then touch one small store. Erasure itself is ClickHouse lightweight deletes on the hashed subject id plus a weekly compaction that rewrites the affected Parquet partitions, which is how you delete from storage built to be append-only and still meet 30 days.

**The trap:** storing content in the same rows as metrics. Every erasure then rewrites months of metrics.

**Rubric:** sizing from spans, bytes and retention (10.1), content separate from metrics (10.2), the cost breakdown under $50k (10.3), and erasure in append-only storage (10.4).

### Output

**The question:** what does a team or on-call engineer actually receive?

Four outputs: a gate result on the pull request (pass or block, failed must-pass cases, slice deltas with confidence intervals, cost), an agent scorecard (success metric, judge pass rate, groundedness, cost per successful run), a page (the metric, the window, the **nearest change event before the drop**, and 5 example runs), and weekly failure clusters.

The reasoning: detection without a cause still costs a day of bisecting. Putting the change event in the page is what turns "support is worse" into "support got worse after prompt v42 at 14:05."

**The trap:** reporting the judge score alone. Leadership needs the business outcome.

**Rubric:** failed cases and slice deltas with uncertainty (11.1), the change event in the page (11.2), and cost per successful run next to quality (11.3).

## 7. Pillar D: Run it safely

### Guardrails

**The question:** what makes the gate honest, and what limits cost and data exposure?

The gate rule, in code: block on any must-pass failure, on a paired drop over 3 points with McNemar p under 0.05, or on a drop over 8 points in any slice of 50 or more cases.

The reasoning for 3 points is the arithmetic you should show:

- At 600 cases and 85 percent pass, the **unpaired** standard error of a difference is √(2 × 0.85 × 0.15 / 600) ≈ **2.1 points**. A 2-point threshold would fire on noise about as often as on real drops.
- **Pairing** (same cases, old and new version) leaves only the discordant cases as noise. With about 6 percent discordant, the standard error is about √(0.06 / 600) = **1 point**, so a 3-point threshold is about three standard errors.

Problem prompt-regression-gate builds this test. The other guardrails: per-team monthly eval spend caps enforced in the gate workflow, a named second approver for any override (logged), and judges running only on scrubbed content.

**The trap:** a fixed 2-point threshold on 600 cases. It blocks on noise, teams learn to rerun until green, and the gate is dead.

**Rubric:** threshold justified by standard error (12.1), a paired test (12.2), a named approver for overrides (12.3), and spend caps in code (12.4).

### Key Impact

**The question:** which numbers prove the platform works, and how are they measured?

Five rows with baseline, target and method: detection time (8 days → under 30 minutes, measured by replaying incidents), changes gated (0 → 100 percent), judge agreement (unknown → kappa at least 0.6, quarterly 400-label audit), negative feedback reviewed (0 → 100 percent triaged in 5 days), regressions reaching production (3 a quarter → under 1).

The strongest move here: replay last month's 9-point drop through the pipeline before launch and time the page. That proves the headline number on a real incident rather than a synthetic one.

**The trap:** counting judged runs. Volume of scoring says nothing about whether the scores are right.

**Rubric:** baseline and target for detection time (13.1), share of changes gated (13.2), and recurring judge agreement audits (13.3).

### Failure Modes

**The question:** what breaks in the eval system itself?

Five failures. The two the rubric names explicitly:

- **The judge model changes underneath you.** A nightly run on 200 fixed calibrated cases alerts if agreement drops 5 points.
- **Low-traffic agents.** 10 percent of 2,000 runs a day is 200 judged runs, too few for a stable rate. Sample at least 300 a day per agent instead of a flat percentage.

Plus collector overload (quotas shed healthy content, metadata keeps flowing), an eval storm before a release (Temporal queues gates by priority inside the 4M TPM quota), and stale golden sets (cases older than 6 months with no failures retired quarterly).

The decision to state in one line: **fail open for the agent, closed for the gate.** Lost spans never block a customer, but a gate that can't finish blocks the merge.

**The trap:** trusting the judge after a silent provider update.

**Rubric:** judge model drift (14.1), low-traffic agents (14.2), and open-for-agent, closed-for-gate (14.3).

### Build Order

**The question:** in what order, and what number ends each phase?

Six phases over 26 weeks: tracing for all 30 agents (weeks 1–4), rule checks and windows with burn-rate alerts (5–8), golden sets and the CI gate for the 7 agents that have sets (9–13), the small-model judge with calibration and NLI (14–18), the Argilla loop and erasure (19–22), and sets for the other 23 agents (23–26). Each ends with a measured number, such as "runs with full version tags, 100 percent" or "gate time under 20 minutes."

The reasoning for the order: the 9-point drop would have shown in escalation rate alone, so tracing and cheap signals deliver most of the value before any judge exists. A judge built first has nothing to judge and nothing to be calibrated against.

**The trap:** building the judge first.

**Rubric:** tracing and cheap signals before judges (15.1), a measured number per phase (15.2), and 26 weeks for 6 engineers (15.3).

## 8. The decisions that separate strong answers

**Tail sampling vs head sampling.** Head sampling is simpler and cheaper to run, and it's what most tracing tools do by default. But the runs you most want to read are the ones that failed, and head sampling throws away 90 percent of them before they fail. Tail sampling costs a 30-second buffer in the collector and a stage in the latency budget, and in return it keeps every error, every thumbs-down and every judge failure. Strong answers also say that metadata is exempt from sampling entirely.

**Haiku judge on a sample vs Sonnet judge on everything.** The weak answer picks the strongest judge "for quality." The strong answer shows the $788k, picks Haiku, and then earns trust back with calibration: Sonnet checks 5,000 a day, humans label 400 per agent, and the judge ships only at kappa 0.6. Cost and trust are solved by different mechanisms.

**A statistical gate vs a fixed threshold.** A gate is only useful if teams believe it. Showing the 2.1-point unpaired standard error, then pairing to get it to about 1 point, is what justifies 3 points. Without that arithmetic, any threshold you name is a guess.

## 9. Common mistakes

- Designing a logging pipeline and forgetting the gate, or a gate and forgetting online detection. The prompt asks for both.
- Never doing the judging arithmetic, so the design quietly assumes a judge on every run.
- Sampling metadata along with content, which breaks cost and latency dashboards.
- No change events, so pages say what broke but not why.
- Treating GDPR erasure as a footnote. Append-only stores need a plan: separate content, deletes keyed on a hashed subject id, compaction, and golden cases linked to source runs.
- No per-tenant quota, so one runaway agent floods the collector for all 1,800 tenants.
- Letting the triage agent read raw customer content because "it's internal."

## 10. Follow-ups an interviewer might ask

- *The judge provider ships a new version and scores jump 4 points overnight. What happens?* The nightly 200-case calibration run alerts on the agreement drop, the cache invalidates because the judge model is in the key, and scores before and after are tagged with different judge versions so nobody compares them directly.
- *A team wants to skip the gate for a hotfix.* They need a named second approver, and the override is logged. Count overrides in Key Impact so a rising number is visible.
- *How would you detect input drift before quality drops?* Compare the current window's input embeddings and tool-use mix against the 28-day reference window (problem embedding-drift builds the statistic).
- *How do you avoid paging on noise for small agents?* Use a minimum sample per agent (at least 300 a day) and burn-rate alerts over two windows instead of one threshold (problem slo-burn-rate-alerts).
- *How would you roll out a model upgrade safely?* Canary it, run the pairwise judge in both orders on canary vs control traffic, and promote only if the business metric holds (problem canary-analysis).
