## 1. What the problem is really asking

There's no agent, no retrieval and no end user in this problem. It's **infrastructure**: a reverse proxy in front of every model call in a 9,000-person company. The three incidents in the context tell you exactly what the proxy is for. A provider outage took down four features (so: failover). A runaway agent burned $38,000 over a weekend (so: limits that act within minutes, per run). A support tool sent account numbers to a provider without zero retention (so: routing by data class, with redaction).

The core tension: the gateway has to **control** traffic (limits, budgets, routing, redaction) while staying **invisible** to it (at most 25 ms added at p99, streaming token by token, provider features like `cache_control` and tools untouched). And it only works if every team actually uses it.

Three decisions carry the design:

- **Reserve then reconcile.** Output length is unknown at admission, so reserve `max_tokens` against the team's token bucket and budget, then refund the unused part when the response finishes.
- **Provider-native pass-through, not a unified schema.** The gateway decides who may call what, how much and where it goes; it never edits what a team asked the model to do.
- **Priority classes decide everything under pressure.** P0 customer-facing, P1 internal, P2 offline. P2 is shed first and fails closed; P0 is never shed by the gateway, fails open, and at 100% budget gets a bounded overdraft with an approver instead of a hard stop.

## 2. The numbers that drive the design

**Rates.**

| Step | Arithmetic | Result |
|---|---|---|
| Average requests | 45M ÷ (30 × 86,400 s) | about 17/s |
| Peak | × 4 | about 70/s |
| Plan for | headroom | 150/s |
| Average input tokens a minute | 155B ÷ (30 × 1,440 min) | about 3.6M |
| Peak input tokens a minute | × 4 | about 14M |

150 requests a second is small for a proxy, so the fleet is 8 LiteLLM pods across 3 zones, each sized for about 30 rps of mostly idle streams. The token rate matters more: per-team TPM buckets must sum to at most 80% of each provider org limit.

**Overhead budget.** The model answer spends the 25 ms like this:

| Stage | p99 |
|---|---|
| Envoy TLS, mTLS, size cap, global RPM | 3 ms |
| Virtual key and team policy, in memory | 1 ms |
| TPM and budget admission, Redis Lua | 3 ms |
| Routing decision | 2 ms |
| Presidio redaction, only where needed | 10 ms |
| Warm provider connection | 2 ms |
| Usage event to Kafka, async | 0 ms |
| Total | 21 ms |

3 + 1 + 3 + 2 + 10 + 2 + 0 = 21 ms. Notice what isn't in the table: any model call. A routing or moderation model in the hot path would cost about 300 ms by itself.

**Spend.** The model answer puts the current mix at **$501,000 a month at list price**, growing 12% a month. Then it applies the levers in order:

| Lever | Monthly spend | Saved |
|---|---|---|
| Baseline | $501,000 | |
| Routing: 40% of Opus to Sonnet, 30% of Sonnet to Haiku, where evals pass | $396,000 | $105,000 |
| Prompt caching: 50% of input read from cache | $297,000 | $99,000 |
| Batch API for the 20% offline traffic, 50% off | $267,000 | $30,000 |
| Semantic cache on 3 FAQ bots | $264,000 | $3,000 |
| Gateway infrastructure | +$9,000 | |

Check the arithmetic as you go: 501 − 105 = 396; 396 − 99 = 297; batch is 50% off on 20% of $297,000, about $30,000, giving 267; 267 − 3 = 264; plus $9,000 of infrastructure is $273,000. That's about a 45% cut, beating the 35% target (under $325,000). The second provider is assumed at $2.50 / $10 per MTok with cached input at half price.

The table also answers "which levers are not worth it": the semantic cache saves $3,000, about 1%, and carries a data-leak risk.

**Usage log.** One event per call is 45M events a month, about 1.5M rows a day, roughly 45 GB a month; 13 months of retention is about 600 GB raw, 60 GB compressed in ClickHouse.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–4 | Restate the three incidents as requirements; write rps, TPM, spend and the 25 ms budget |
| 4–10 | **Pillar A:** adoption as requirement one; the Single View with a separate batch path |
| 10–19 | **Pillar B:** team registry and versioned prices, the 21 ms pipeline with reserve-then-reconcile, per-run caps, affinity, the usage MCP server |
| 19–26 | **Pillar C:** native routes and egress blocking, the lever table, ClickHouse, response headers |
| 26–32 | **Pillar D:** the budget ladder and P0 overdraft, savings at equal evals, breakers and fail-open/closed, visibility-first build |
| 32–60 | Follow-ups |

The prompt's six "strong answer" bullets are almost a checklist. Tick each one aloud as you cover it.

## 4. Pillar A: Frame

### Scenario

**The question:** who uses the gateway, what job does it do, and which numbers shape it?

**How to reason.** The users are 40 internal teams and finance. The job: one paved road for every model call, adding limits, routing, failover, redaction and attribution without hiding provider features. Derive rates and tokens per minute (section 2) and state the $501,000 baseline. Build the baseline spend map from 30 days of provider usage exports, tagging each key to a team, and list each team's routes with data class (public, internal, confidential, restricted) and priority (P0, P1, P2).

The headline agreed with finance: **monthly spend at equal eval scores**, and 100% of spend attributed. Out of scope: per-product content safety, fine-tuning, self-hosted models.

The decision the rubric rewards is treating **adoption as the first requirement**. A gateway that 30 of 40 teams use leaves 10 able to rerun the $38,000 weekend.

**The trap.** Promising savings before measuring the mix. Most of the money sits in two models.

**Rubric criteria earned:** rps and TPM from monthly volume; baseline spend from the mix; savings at equal eval quality; full adoption as a requirement.

### Single View

**The question:** draw the gateway as layers.

**How to reason.** Teams use stock OpenAI and Anthropic SDKs with a new `base_url`, a virtual key and three headers (`x-team-feature`, `x-run-id`, `traceparent`). Envoy AI Gateway handles TLS, mTLS, size caps and a global RPM limit. LiteLLM is the policy core: key lookup, TPM and budget admission, allowlists, routing. Presidio redacts on routes to providers not cleared for the data class. Provider adapters cover the Anthropic API, Claude on Amazon Bedrock and the second provider, each with circuit breakers and hedging. **Batch traffic takes a separate durable path** through Temporal to provider batch APIs. Kafka to ClickHouse is the usage log; OpenTelemetry and Grafana give per-team dashboards.

The one idea: the gateway decides who may call what, how much, and where it goes; it never edits what a team asked the model to do.

**The trap.** Making batch just another synchronous route. It runs for hours and must survive restarts.

**Rubric criteria earned:** edge, policy, redaction, adapters and usage log as layers; a durable batch path; the controls-versus-leaves-alone idea.

## 5. Pillar B: Build the core

### Data Sources

**The question:** what does the gateway need to know about teams, prices and providers?

**How to reason.** Four inputs, each with an owner. The team registry (owner, budget, priority, data class, allowed models) comes from Backstage plus a Postgres table finance can edit, pushed to pods within 10 s. Prices are rows `(model, token_type, usd_per_mtok, effective_from)`, and cost uses the price valid **at request time**, so a mid-month price change doesn't rewrite history. Provider limits come from `ratelimit` response headers on every call, plus status pages every 60 s. Routing eligibility comes from each opted-in team's eval results per route.

**The trap.** Trusting your own cost numbers. Reconcile against the provider invoice monthly; a gap over 1% is a bug.

**Rubric criteria earned:** team registry; versioned prices; per-request provider signals; invoice reconciliation.

### Processing

**The question:** what does every request pass through, and how much time does each stage add?

**How to reason.** Show the 21 ms table. Then answer the prompt's first bullet: **how do you enforce tokens per minute when output length is unknown?** You have two choices. Wait for the real output count, which admits a burst that blows the provider limit before you notice. Or reserve: count input with the provider tokenizer, reserve `max_tokens` for output (capped per key), admit only if the bucket and the budget cover it, and refund the unused reservation on completion. The model answer reserves then reconciles (problem token-bucket-rate-limiter).

Streaming passes through unbuffered. Where redaction applies, the gateway re-identifies tokens in the stream with a small lookahead buffer.

**The trap.** A model call in the hot path. That alone costs 300 ms.

**Rubric criteria earned:** stage budget under 25 ms; reserve and reconcile; unbuffered streaming; no model calls in the hot path.

### Agents

**The question:** the gateway runs no agent, so what does it do for the agents that call it?

**How to reason.** Start from the $38,000 weekend: one run looping, noticed on Monday by a monthly cap. So the gateway needs per-run controls keyed by `x-run-id`: a default cap of $5 and 200 calls per run, configurable per key, counted in Redis with a 24 h expiry. Add loop detection: the same request hash 6 times in one run within 60 s returns 429 `loop_detected` (problem 102, agent-loop-detection, builds the run-side version). Propagate W3C `traceparent` to provider spans and the usage event.

The router applies only to `model: auto`: rules plus a small ONNX classifier on prompt features label short extraction or classification calls, and a route drops a tier **only if that team's eval for it passes** (problem model-router). An explicitly named model is never changed.

**The trap.** Per-key monthly budgets only.

**Rubric criteria earned:** per-run cap by run id; repeated-request detection; trace propagation; opt-in, eval-backed routing.

### Memory

**The question:** what state does the gateway keep, where, and for how long?

**How to reason.** Admission state (buckets, budget counters, run counters) lives in a Redis cluster, mirrored to Postgres every 30 s so a Redis failover loses at most 30 s of spend. Session affinity maps `x-session-id` to a provider and region for 10 idle minutes, because **provider prompt caches are per provider**; switching costs a full prefix write. An exact-match response cache serves temperature-0 eval calls for 24 h, keyed on model, messages, tools and parameters, scoped to the team. Policy lives in Postgres, cached in each pod and refreshed every 10 s.

The decision: **no conversation memory in the gateway.** History belongs to the calling app; storing it here doubles the data to protect.

**The trap.** Round-robin load balancing across providers, which halves prompt cache hit rates for every multi-turn app.

**Rubric criteria earned:** counters in a shared store with a durability plan; session affinity for warm caches; no conversation history, with a reason.

### MCP Tool Servers

**The question:** does the gateway expose or touch tools?

**How to reason.** Two roles. First, **pass-through**: `mcp_servers` and tool definitions inside provider requests are left untouched and only metered. Second, the gateway exposes its own small MCP server (Python MCP SDK, same SSO as the admin console): `get_usage(team, period, group_by)` scoped to the caller's teams, read-only `get_budget_status(team)`, and `request_budget_increase(team, amount, reason)`, which opens a finance approval and cannot approve itself. Every budget tool call is written to the audit table. The payoff: an engineer can ask their coding agent "why did our spend jump?" without a new dashboard.

**The trap.** Letting a budget tool raise a budget. Increases need a finance approver in code.

**Rubric criteria earned:** tool definitions passed through; usage tools scoped to the caller; budget increases behind an approver.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what's the API surface, and how do you make sure every team uses it?

**How to reason.** Provider-native routes: `POST /anthropic/v1/messages` (streaming pass-through), OpenAI-compatible `/openai/v1/chat/completions` and `/v1/embeddings`, `POST /v1/batches` and `GET /v1/batches/{id}` backed by a Temporal workflow to the Anthropic Message Batches API or the second provider's batch API (results in S3 within 24 h), `GET /v1/usage`, and finance-role admin routes. Every response gets `x-ratelimit-remaining-tokens`, `x-gateway-cost-usd` and `x-gateway-model` headers.

Native over unified is the decision to defend: translation layers lag new features by months and quietly drop cache breakpoints. Size the fleet: 8 pods across 3 zones, scaled on open connections.

Then adoption. Issuing keys isn't adoption. **Block direct egress to provider domains with network policy**, and rotate the old provider keys, so the gateway is the only route.

**The trap.** Calling adoption done when keys are issued.

**Rubric criteria earned:** native pass-through; fleet sized from peak; a durable batch endpoint; egress blocking and key rotation.

### Caching

**The question:** which cost levers save the most, and which aren't worth it?

**How to reason.** Walk the lever table in order (section 2), routing and prompt caching quantified separately ($105,000 and $99,000), batch for the offline 20% ($30,000), and the semantic cache last ($3,000).

Who fixes prompt caching? Not the gateway, which never reorders prompts. The gateway **coaches**: it reports each team's hit rate from `cache_read_input_tokens`, and most misses turn out to be timestamps or unsorted tool lists in the prefix. Teams that opt in get top-level automatic caching on Anthropic routes. Exact-match caching covers temperature-0 eval runs, which repeat the same 4,000 cases nightly.

The semantic cache position: opt-in and narrow. It saves 1% and can return another user's answer.

**The trap.** A global semantic cache. The savings are small and a cross-team hit is a data leak.

**Rubric criteria earned:** levers in order with dollar savings; prompt caching and routing separate; batch for offline; a semantic cache position with savings and risk.

### Data Stores

**The question:** which stores hold counters, policy and usage, and how big are they?

**How to reason.** Redis cluster (about 20 GB) for buckets, budgets, run counters, affinity and the exact cache. RDS Postgres (under 50 GB) for teams, hashed virtual keys, budgets, prices, batch jobs and audit. MSK Kafka for usage events with 7-day retention (about 45 GB for 45M events a month). ClickHouse for 13 months of usage (about 600 GB raw, 60 GB compressed) with materialized views by team, feature, model and day. S3 (about 2 TB) for batch results and 1% sampled, redacted payloads kept 30 days. Provider keys live in AWS Secrets Manager, rotated every 30 days.

Why ClickHouse? 1.5M rows a day with group-by over 13 months is analytics, not OLTP. Write every event with the trace id and an idempotency key so a replayed Kafka partition doesn't double-count (problem tenant-cost-attribution).

**The trap.** Logging full prompts by default. Sample 1%, redact, expire in 30 days.

**Rubric criteria earned:** usage sized monthly and over retention; an analytics store; idempotent events; secrets manager and hashed keys.

### Output

**The question:** what does the gateway return to callers, and what does it report?

**How to reason.** The response body is the provider's, unchanged, so teams debug against provider docs. Metadata (model used, provider, cost, cache tokens, remaining limits) goes in headers and the usage event. Three reports: a per-team Grafana dashboard (spend against budget, p99, errors, cache hit rate), a monthly chargeback by team and feature generated from ClickHouse on day 2 after invoice reconciliation, and alerts at 50%, 80% and 100% of budget posted to the team's Slack channel with the top 3 features by spend.

**The trap.** Cost only in a monthly report. Teams change behaviour when the cost is in a response header they log.

**Rubric criteria earned:** body unchanged with header metadata; per-request cost and limits; a reconciled chargeback.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** what enforces budgets, limits and data rules if a team's code or prompt tries to bypass them?

**How to reason.** Everything is enforced at admission with OPA bundles loaded into each pod, returning typed deny reasons. Budgets: 50% email, 80% Slack and optional `auto` routing, 100% hard stop for P1 and P2. The prompt asks what happens at 100% for a customer-facing team: **P0 continues to 110% with a VP approval, then stops.** A hard stop at exactly 100% would make the gateway cause the outage it exists to prevent.

Rate limits: per-team RPM and TPM buckets summing to at most 80% of each provider org limit, with P2 borrowing unused capacity. Data class: restricted data goes only to providers under zero retention in US regions (the Anthropic API with ZDR, Claude on Bedrock), and other providers are blocked. PII: Presidio tokenizes account numbers, SSNs and emails before non-cleared providers, with originals in a vault (problem pii-redaction-vault). Models: per-key allowlist and a `max_tokens` cap. Under provider pressure (429s above 5%), shed P2 first, then P1; P0 is never shed by the gateway. Every key, budget and policy change goes to an append-only audit table.

**The trap.** A hard stop for P0 at exactly 100%.

**Rubric criteria earned:** 50/80/100 actions in code; P0 handled without an outage; data-class routing and redaction; shedding by priority.

### Key Impact

**The question:** what number proves the gateway worked?

**How to reason.** Headline: monthly spend from $501,000 to under $325,000 at current volume, measured in ClickHouse and reconciled to invoices. Beside it: attribution coverage from about 40% to 100% (unattributed rows), adoption from 0% to 100% (egress logs to provider domains), P0 availability from 99.5% observed to 99.95%, added p99 under 25 ms. Gate every routing change on the team's eval score staying within 1 point of the baseline model, and report savings per lever monthly so a lever that stops paying is visible. Count provider outages absorbed without a customer-facing error.

**The trap.** Reporting forecast savings. Report the reconciled invoice.

**Rubric criteria earned:** baseline and target spend with source; attribution and adoption measured; savings gated on flat evals.

### Failure Modes

**The question:** what breaks, including the gateway itself?

**How to reason.** The gateway is now on every request path, so its failures count as much as the providers'. Provider 500s or slowdowns: a breaker per provider and model opens at 50% errors over 20 calls in 30 s, traffic moves to Claude on Bedrock or the second provider, and it goes half-open after 30 s with 5 probes (problem circuit-breaker). Slow short P0 calls: hedge non-streaming calls under 2,000 tokens after their p95 (about 1.2 s), cancelling the loser, at about 3% extra cost on those routes (problem gateway-failover-hedging). Redis down: P0 falls back to per-pod local buckets for up to 10 minutes; P2 fails closed. Kafka down: pods buffer usage events to local disk for 6 hours and replay with idempotency keys. Runaway agent: stopped at $5 with a Slack alert carrying the run id.

Run monthly game days (kill a provider with Toxiproxy, drop Redis, pause Kafka); page on p99 over 25 ms, 5xx above 0.5% and breaker state changes.

**The trap.** Hedging streaming or long calls, which doubles cost on the expensive tail.

**Rubric criteria earned:** breakers with thresholds and a fallback; hedging limited and costed; fail-open/closed by priority; usage log outage without losing events.

### Build Order

**The question:** in what order, and what number unlocks each step?

**How to reason.** Visibility before control, control before savings. Weeks 1–2: pass-through with virtual keys and usage events for 3 pilot teams (added p99 under 25 ms). Week 3: attribution and reconciliation (within 1%). Week 4: buckets and budgets (zero provider 429s caused by one team). Week 5: breakers and Bedrock fallback (a staged provider kill with zero P0 errors). Week 6: Presidio and data-class routing (zero restricted payloads to non-cleared providers in 10,000 test requests). Weeks 7–8: all 40 teams, egress blocked, old keys rotated (100% through the gateway). Weeks 9–12: routing, cache coaching, batch (under $325,000). Migrate **P2 first**, hold each team's old key for 2 weeks as a rollback, and publish a one-page guide.

**The trap.** Starting with routing because it saves the most. Without attribution nobody can prove the saving.

**Rubric criteria earned:** visibility first; a number per step; low-priority first with a rollback path.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| TPM with unknown output | Count tokens after the response | Reserve `max_tokens` at admission, refund the unused part |
| Budget at 100% | Hard stop for everyone | Hard stop for P1 and P2; P0 overdraft to 110% with a VP approval |
| API shape | One unified schema | Provider-native pass-through; the body is never edited |

## 9. Common mistakes

- A routing or moderation model in the hot path, blowing the 25 ms budget.
- A unified schema that drops `cache_control`, tools or thinking.
- Monthly budgets only, which can't catch a weekend loop.
- Round-robin across providers, killing prompt cache hit rates.
- A global semantic cache sold as a big saving.
- Declaring adoption done without blocking egress or rotating keys.
- Hedging everything.

## 10. Follow-ups an interviewer might ask

- *Anthropic's API starts returning 500s at 11:00. What does a P0 team see?* The breaker for that provider and model opens at 50% errors over 20 calls in 30 s, and traffic moves to Claude on Bedrock. After 30 s it goes half-open with 5 probes. Session affinity re-pins, so the first turn on the new provider pays a prefix write.
- *A team asks for 2× its TPM for a backfill.* Mark it P2 and run it through the batch endpoint at 50% off; P2 can borrow unused capacity but is shed first under pressure.
- *Finance wants a hard stop on a customer-facing team.* Explain the bounded overdraft: 110% with a VP approval, then stop. A stop at exactly 100% turns the budget into an outage.
- *How do you know a team isn't calling a provider directly?* Network policy blocks egress to provider domains, old keys are rotated, and egress logs give the adoption metric.
- *Why not route everything to Haiku?* Routing only applies to `auto` requests whose team eval for that route passes; savings count only within 1 point of the baseline eval.
