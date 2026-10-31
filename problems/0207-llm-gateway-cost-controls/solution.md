# LLM Gateway with Cost Controls: model answer

## 1. Scenario
Forty teams call models directly, so nobody can cap spend, survive an outage, or stop data reaching the wrong provider. The gateway is one paved road: every call goes through it, and it adds limits, routing, failover, redaction and attribution without hiding provider features.

| What | Number | What it drives |
|---|---|---|
| Requests | 45M a month: 17 per second average, 70 at the 4x peak; plan for 150 | 8 gateway pods across 3 zones |
| Tokens | 155B in, 19B out: 3.6M input tokens a minute average, 14M at peak | TPM buckets per team, under the provider org limits |
| Spend | $501,000 a month at list price, growing 12% a month | Routing, caching and batch are worth real money |
| Overhead | At most 25 ms added at p99 | No model call inside the gateway's hot path |
| Availability | 99.95% for 12 customer-facing teams | Fallback across providers, circuit breakers |

**How:**
1. Pull 30 days of provider usage exports and tag each key to a team: this is the baseline spend map.
2. List every team's routes with their data class (public, internal, confidential, restricted) and priority (P0 customer-facing, P1 internal, P2 offline).
3. Agree the headline with finance: spend per month at equal eval scores, and 100% of spend attributed to a team.
4. Out of scope: prompt content safety for each product, fine-tuning, and self-hosted models.

**Decision.** Adoption is the first requirement. A gateway that 30 of 40 teams use leaves the other 10 able to run the $38,000 weekend again.

**Trap.** Promising savings before measuring the mix. Most of the money is in two models; the levers only matter where the tokens are.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Team SDKs | Stock OpenAI and Anthropic SDKs with `base_url` and a virtual key. Hands over a request plus `x-team-feature`, `x-run-id`, `traceparent` | Teams change two lines, not their code |
| Envoy AI Gateway (edge) | TLS, mTLS from services, request size cap, global RPM limit. Hands over an authenticated request | Fast, battle-tested edge; rate limits shared across pods |
| Policy core (LiteLLM proxy) | Virtual key lookup, TPM and budget admission, model allowlist, routing. Hands over a chosen provider and model | One place where team rules live in code |
| Redaction (Presidio) | Tokenizes PII on routes to providers not cleared for the data class. Hands over a clean request and a vault map | Data class decides the provider, not the developer |
| Provider adapters | Anthropic API, Claude on Amazon Bedrock, the second provider; per-provider circuit breakers and hedging. Hands over a stream | Outages become a failover, not an incident |
| Batch workflows (Temporal) | Submits offline jobs to provider batch APIs, polls, stores results in S3. Hands over results and usage | Half price for 20% of traffic, and durable across restarts |
| Usage log (Kafka to ClickHouse) | One event per call with tokens, cost, latency, team, trace id. Hands over chargeback and alerts | Attribution and reconciliation from one record |
| Observability (OpenTelemetry, Grafana) | Spans with GenAI semantic conventions, per-team dashboards | Teams debug their own calls |

**The one idea to hold:** the gateway decides who may call what, how much, and where it goes; it never edits what a team asked the model to do.

## 3. Data Sources
The gateway's inputs are traffic, prices, provider health and the team registry. Each one has an owner and a refresh rule.

| Input | Source | Refresh |
|---|---|---|
| Team registry: owner, budget, priority, data class, allowed models | Backstage catalog plus a Postgres table finance can edit | On change, pushed in 10 s |
| Price table by model and date | Provider pricing pages, entered by the platform team, versioned with an effective date | On provider change |
| Provider limits and health | `ratelimit` response headers, error rates, status pages | Per request; status every 60 s |
| Routing eligibility | Each opted-in team's eval results per route | On every eval run |

**How:**
1. Sync teams from Backstage nightly; budgets and data class live in Postgres with an audit trail.
2. Store prices as rows `(model, token_type, usd_per_mtok, effective_from)`; cost is computed with the price valid at request time.
3. Parse rate-limit headers on every response to track remaining provider capacity per org.

**Decision.** Prices are versioned data, not constants. A price change mid-month otherwise rewrites history in the chargeback.

**Trap.** Trusting the gateway's cost numbers without reconciling. Compare against the provider invoice monthly; a gap over 1% is a bug.

## 4. Processing
Every request runs the same pipeline, and each stage has a latency budget.

| Stage (added by the gateway) | p99 |
|---|---|
| Envoy TLS, mTLS, size cap, global RPM | 3 ms |
| Virtual key and team policy (in-memory, refreshed from Redis) | 1 ms |
| TPM and budget admission (Redis Lua) | 3 ms |
| Routing decision | 2 ms |
| Presidio redaction (only on routes needing it) | 10 ms |
| Provider connection from a warm pool | 2 ms |
| Usage event to Kafka (async) | 0 ms |
| **Total** | **21 ms, under 25 ms** |

**How:**
1. Estimate tokens at admission: count input with the provider tokenizer and reserve `max_tokens` for output, capped per key.
2. On completion, refund the unused reservation from the bucket and the budget counter.
3. Stream chunks through unbuffered; redaction re-identifies tokens in the stream with a small lookahead buffer.

**Decision.** Reserve then reconcile. Waiting for the real output count admits a burst that blows the provider limit.

**Trap.** Running a model call (for routing or moderation) in the hot path. That alone costs 300 ms.

## 5. Agents
The gateway runs no agent, but a third of the traffic comes from agents, and agents fail in loops.

| Agent-aware feature | Rule |
|---|---|
| Per-run budget | `x-run-id` header; default cap $5 and 200 calls per run, set per key |
| Loop detection | Same request hash 6 times in one run within 60 s returns 429 `loop_detected` |
| Trace propagation | W3C `traceparent` carried to provider spans and the usage event |
| Router | Rules plus a small ONNX classifier on prompt features, for `model: auto` only |

**How:**
1. Count spend and calls per run in Redis with a 24 h expiry; reject with a typed error the agent framework can handle.
2. Route `auto` requests: the classifier labels short extraction or classification calls, and the route drops a tier only if that team's eval for it passes.
3. Never change the model of a request that names one explicitly.

**Decision.** Routing is opt-in per route, backed by the team's own eval. Silent downgrades break trust faster than they save money.

**Trap.** Per-key budgets only. The $38,000 weekend was one run looping; a monthly cap noticed it on Monday.

## 6. Memory
The gateway keeps counters and caches, plus enough session affinity to keep provider prompt caches warm.

| Tier | Holds | Lives in | Expires |
|---|---|---|---|
| Admission | Token buckets, budget counters, run counters | Redis cluster | Bucket windows; budgets monthly |
| Session affinity | `x-session-id` to provider and region | Redis | 10 minutes idle |
| Response cache | Exact-match results for temperature 0 eval calls | Redis | 24 h |
| Policy | Keys, teams, allowlists | Postgres, cached in each pod | Refreshed every 10 s |

**How:**
1. Pin a session to one provider and region while healthy; provider prompt caches are per provider, so a switch costs a full prefix write.
2. Mirror budget counters to Postgres every 30 s, so a Redis failover loses at most 30 s of spend.
3. Key the exact-match cache on a hash of model, messages, tools and parameters, scoped to the team.

**Decision.** No conversation memory in the gateway. History belongs to the calling app; storing it here doubles the data to protect.

**Trap.** Round-robin load balancing across providers. It halves prompt cache hit rates for every multi-turn app.

## 7. MCP Tool Servers
The gateway calls no tools, but it exposes two of its own: an MCP server for usage and budget questions, and a pass-through for teams' MCP tool calls inside provider requests.

| Tool | Does | Guard in code |
|---|---|---|
| `get_usage(team, period, group_by)` | Spend by feature and model from ClickHouse | Caller sees only teams they belong to |
| `get_budget_status(team)` | Spend, forecast, thresholds hit | Read only |
| `request_budget_increase(team, amount, reason)` | Opens a finance approval | Cannot approve itself |

**How:**
1. Build the server with the Python MCP SDK and the same SSO as the admin console.
2. Leave `mcp_servers` and tool definitions in provider requests untouched; the gateway only meters them.
3. Log every budget tool call to the audit table.

**Decision.** The usage MCP server lets engineers ask their coding agent "why did our spend jump?" without a new dashboard.

**Trap.** Letting a budget tool raise a budget. Increases need a finance approver in code.

## 8. Endpoints
Native provider APIs, not one translated schema, so teams keep `cache_control`, thinking, tools and batch.

| Route | Purpose |
|---|---|
| `POST /anthropic/v1/messages` | Anthropic-native pass-through, streaming |
| `POST /openai/v1/chat/completions`, `/v1/embeddings` | OpenAI-compatible routes |
| `POST /v1/batches`, `GET /v1/batches/{id}` | Durable offline jobs |
| `GET /v1/usage` | Team spend and limits |
| `/admin/keys`, `/admin/budgets` | Key issue and rotation, budget edits (finance role) |

**How:**
1. Run 8 LiteLLM pods behind Envoy across 3 zones, each handling about 30 rps of mostly idle streams; scale on open connections.
2. Return limit headers on every response: `x-ratelimit-remaining-tokens`, `x-gateway-cost-usd`, `x-gateway-model`.
3. Submit batch jobs through a Temporal workflow to the Anthropic Message Batches API or the second provider's batch API; results in S3 within 24 h.
4. Block direct egress to provider domains with network policy, so the gateway is the only route.

**Decision.** Pass-through per provider over a unified schema. Translation layers lag new features by months and quietly drop cache breakpoints.

**Trap.** Calling adoption done when keys are issued. Egress blocking and rotating the old provider keys are what make it complete.

## 9. Caching
Caching levers sit beside routing and batch; together they cut the bill by about 45% after paying for the gateway.

| Lever, applied in order | Monthly spend | Saved |
|---|---|---|
| Baseline at list price, no levers | $501,000 | |
| Routing: 40% of Opus to Sonnet, 30% of Sonnet to Haiku, where evals pass | $396,000 | $105,000 |
| Prompt caching: 50% of input tokens read from cache (writes add about 3%) | $297,000 | $99,000 |
| Batch API for the 20% offline traffic, 50% off | $267,000 | $30,000 |
| Semantic cache on 3 FAQ bots, 30% hit rate on 0.9M requests | $264,000 | $3,000 |
| Gateway infrastructure (pods, Redis, MSK, ClickHouse) | +$9,000 | |

The second provider is assumed at $2.50 / $10 per MTok with cached input at half price.

**How:**
1. Report each team's cache hit rate from `cache_read_input_tokens`; most misses are timestamps or unsorted tool lists in the prefix.
2. Add top-level automatic caching on Anthropic routes for teams that opt in; never reorder their prompts.
3. Enable exact-match caching for temperature 0 eval runs, which repeat the same 4,000 cases nightly.

**Decision.** Prompt caching is fixed by teams, coached by the gateway's per-team hit-rate report. Semantic caching stays opt-in and narrow: it saves 1% and can return another user's answer.

**Trap.** Turning on a global semantic cache. The savings are small and a cross-team hit is a data leak.

## 10. Data Stores
Hot counters in Redis, policy in Postgres, the usage log in ClickHouse.

| Store | Holds | Size |
|---|---|---|
| Redis (ElastiCache, cluster mode) | Buckets, budgets, run counters, affinity, exact cache | About 20 GB |
| Postgres (RDS) | Teams, keys (hashed), budgets, prices, batch jobs, audit | Under 50 GB |
| Kafka (MSK) | Usage events, 7-day retention | 45M events a month, about 45 GB |
| ClickHouse | Usage events for 13 months, rollups by team and day | About 600 GB raw, 60 GB compressed |
| S3 | Batch results; 1% sampled, redacted payloads for 30 days | About 2 TB |

**How:**
1. Write usage events with the trace id and an idempotency key so a replayed Kafka partition does not double-count.
2. Build ClickHouse materialized views for spend by team, feature, model and day.
3. Store provider keys in AWS Secrets Manager, rotated every 30 days; virtual keys are stored as hashes.

**Decision.** ClickHouse over Postgres for usage. 1.5M rows a day with group-by over 13 months is an analytics workload.

**Trap.** Logging full prompts by default. Sample 1%, redact, and expire in 30 days.

## 11. Output
The gateway returns the provider's response unchanged, plus metadata, and produces three reports.

| Output | Contains | Audience |
|---|---|---|
| Response headers | Model used, provider, cost, cache tokens, remaining limits | The calling service |
| Team dashboard (Grafana) | Spend vs budget, p99 latency, errors, cache hit rate | Team leads |
| Monthly chargeback | Spend by team and feature, reconciled to invoices | Finance |
| Alerts | 50%, 80%, 100% budget; error and latency SLOs | Team and platform on-call |

**How:**
1. Never alter the response body; metadata goes in headers and the usage event.
2. Generate chargeback from ClickHouse on day 2 of the month, after invoice reconciliation.
3. Post budget alerts to the team's Slack channel with the top 3 features by spend.

**Decision.** The body stays the provider's. Teams debug against provider docs, not against gateway quirks.

**Trap.** Showing cost only in a monthly report. Teams change behavior when the cost is in the response header they log.

## 12. Guardrails
Each rule protects money, data or availability, and each is enforced in code at admission.

| Rule | Enforced by |
|---|---|
| Budgets | 50% email, 80% Slack and optional `auto` routing, 100% hard stop for P1 and P2; P0 continues to 110% with a VP approval, then stops |
| Rate limits | Per-team RPM and TPM buckets summing to at most 80% of each provider org limit; P2 borrows unused capacity |
| Data class | Restricted data goes only to providers under zero retention in US regions (Anthropic API with ZDR, Claude on Bedrock); others are blocked |
| PII | Presidio tokenizes account numbers, SSNs, emails before non-cleared providers; originals in a vault |
| Models | Per-key allowlist and `max_tokens` cap |

**How:**
1. Evaluate the policy with OPA bundles loaded into each pod; deny returns a typed reason.
2. Shed load by priority when provider 429s exceed 5%: P2 first, then P1; P0 is never shed by the gateway.
3. Write every key, budget and policy change to an append-only audit table.

**Decision.** Limits that protect money and privacy live in gateway code. A team's prompt or SDK setting cannot override them.

**Trap.** A hard stop for customer-facing features at exactly 100%. Give P0 a bounded overdraft with an approver, or the gateway causes the outage.

## 13. Key Impact
The headline is spend at equal quality, with adoption and availability beside it.

| Metric | Baseline | Target | Measured by |
|---|---|---|---|
| Monthly spend at current volume | $501,000 | Under $325,000 (35% cut) | ClickHouse, reconciled to invoices |
| Spend attributed to a team and feature | About 40% | 100% | Unattributed rows in ClickHouse |
| Traffic through the gateway | 0% | 100% | Egress logs to provider domains |
| P0 LLM availability | 99.5% observed | 99.95% | Synthetic probes and error rate |
| Added latency, p99 | n/a | Under 25 ms | Gateway spans |

**How:**
1. Gate each routing change on the team's eval score staying within 1 point of the baseline model.
2. Report savings per lever monthly, so a lever that stops paying is visible.
3. Count incidents: provider outages absorbed without a customer-facing error.

**Decision.** Savings count only at equal eval scores. A cheaper model that fails a team's eval is a cost moved to support.

**Trap.** Reporting the forecast savings. Report the reconciled invoice.

## 14. Failure Modes
The gateway is now on every request path, so its own failures matter as much as the providers'. Each one needs a tested fallback.

- **Provider returns 500s or slows down.** A breaker per provider and model opens at 50% errors over 20 calls in 30 s; traffic moves to Claude on Bedrock or the second provider; half-open after 30 s with 5 probes.
- **Slow responses on short P0 calls.** Hedge non-streaming calls under 2,000 tokens after their p95 (about 1.2 s); the loser is cancelled, adding about 3% cost on those routes.
- **Redis is down.** P0 falls back to per-pod local buckets and budgets for up to 10 minutes; P2 fails closed.
- **Kafka is down.** Pods buffer usage events to local disk for 6 hours and replay with idempotency keys.
- **Runaway agent.** The per-run cap stops it at $5; the team gets a Slack alert with the run id.

**How:**
1. Run game days monthly: kill a provider with Toxiproxy, drop Redis, pause Kafka.
2. Page on gateway p99 over 25 ms, 5xx above 0.5%, and breaker state changes.
3. Keep the gateway stateless, at least 2 pods per zone, with a 15-minute rollback.

**Decision.** Fail open for P0 and fail closed for P2. Losing a few minutes of budget accuracy is cheaper than a customer outage.

**Trap.** Hedging streaming or long calls. It doubles cost on the expensive tail for no visible gain.

## 15. Build Order
1. **Weeks 1 to 2:** pass-through gateway with virtual keys and usage events for 3 pilot teams. Number: added p99 under 25 ms.
2. **Week 3:** ClickHouse attribution and reconciliation. Number: within 1% of the invoice.
3. **Week 4:** TPM and RPM buckets, budgets with alerts. Number: zero provider 429s caused by one team.
4. **Week 5:** breakers and fallback to Bedrock. Number: a provider kill in staging with zero P0 errors.
5. **Week 6:** Presidio and data-class routing. Number: zero restricted payloads to non-cleared providers in 10,000 test requests.
6. **Weeks 7 to 8:** all 40 teams, egress blocked, old keys rotated. Number: 100% of traffic through the gateway.
7. **Weeks 9 to 12:** routing, cache coaching, batch. Number: spend under $325,000.

**How:**
1. Migrate teams by priority, P2 first, so the risky cut-over happens on traffic that can wait.
2. Hold each team's old key for 2 weeks as a rollback path, then revoke it.
3. Publish a one-page migration guide: change `base_url`, add the virtual key, add three headers.

**Decision.** Visibility before control, control before savings. Teams accept limits once they can see their own spend.

**Trap.** Starting with routing because it saves the most. Without attribution nobody can prove the saving.
