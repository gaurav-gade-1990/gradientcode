# Multi-Tenant Support Platform: model answer

## 1. Scenario
Two hundred businesses want the same support agent shaped to their brand, knowledge and systems. The platform runs one runtime, makes onboarding a configuration task, and keeps every tenant's traffic, data and spend separate.

| What | Number | What it drives |
|---|---|---|
| Traffic | 3M conversations, 15M turns a month; 5.8 turns/s average, 23/s at the 4x peak; plan for 40/s | Shared runtime, provider capacity across two endpoints |
| Noisy neighbor | Largest tenant normally 1.9 turns/s at peak, 19/s in a flash sale | Per-tenant admission control |
| Tiers | Enterprise 50%, Growth 35%, Starter 15% of turns | Priority classes and per-tier latency SLOs |
| Knowledge | 10M chunks, 200 to 400,000 articles per tenant | Per-tenant vector partitions |
| Money | $0.80 per resolution; model spend under $120,000 a month | Routing and per-tenant cached prefixes |

**How:**
1. Pick five design-partner tenants across tiers; pull 500 real conversations from each as the first golden sets.
2. Set per-tenant baselines from their help desks: resolution rate, first response time, CSAT.
3. Agree platform SLOs per tier: time to first token, availability 99.9%, zero cross-tenant reads.
4. Out of scope: voice, per-tenant fine-tuned models, and data residency outside the US and EU regions already offered.

**Decision.** Make the tenant config the product. Everything that differs between tenants lives in versioned data; nothing differs in code.

**Trap.** Building for the average tenant. The design is shaped by the largest tenant's flash sale and the smallest tenant's cold cache.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Widget and API edge | Tenant API key plus end-user JWT signed by the tenant. Hands over a turn tagged `tenant_id`, `user_id`, tier | Tenant identity is fixed here, once |
| Admission control | Redis token buckets per tenant (RPM, TPM) and per tier. Hands over admit, queue or shed | One tenant's surge cannot use another's capacity |
| Config service | Immutable, versioned tenant configs: prompt, policies, tools, limits, model tier. Hands over the pinned version | Onboarding and changes without deploys |
| Orchestrator (LangGraph) | Route, retrieve, answer or act; 8 steps max. Hands over tool calls and answers | Code owns the flow for every tenant alike |
| Retrieval | pgvector, one partition per tenant, hybrid search. Hands over 5 cited chunks | Search physically scoped to one tenant |
| Tool gateway (MCP) | Per-tenant connectors and credentials, limits in code. Hands over typed results | Money and permissions enforced outside the model |
| Workflow engine (Temporal) | Refunds, returns, approvals that run for minutes or days. Hands over status events | Actions survive deploys and outlive the chat |
| Model gateway (LiteLLM) | Haiku 5.5 and Sonnet 5.5 on the Anthropic API and Bedrock. Hands over tokens and usage | Failover and per-tenant spend tags |
| Event log (Kafka to ClickHouse) | Every turn, tool call, token count and outcome keyed by tenant. Hands over metering and eval samples | Cost attribution, billing, drift |
| Evals | Platform suite plus per-tenant suite gate every config change | A tenant edit cannot ship a regression |

**The one idea to hold:** `tenant_id` is set once at the edge and enforced by every layer below it in code, never carried by the prompt.

## 3. Data Sources
Each tenant brings three kinds of data, each with its own freshness and its own credentials.

| Source | Example | Reaches the model by |
|---|---|---|
| Knowledge | Zendesk Guide, Confluence, Notion, a website crawl | Indexed per tenant; synced hourly or on webhook |
| Live systems | Shopify, Salesforce, a tenant's own REST API | Tool calls through the gateway |
| History | Past tickets with outcomes | Never retrieved for answers; mined for evals |

**How:**
1. Offer connectors as config: each tenant picks sources and authorizes with OAuth; tokens go to HashiCorp Vault under `tenants/{id}/`.
2. Run sync jobs on a per-tenant queue with weighted fair scheduling, so a 400,000-article import does not stall a 200-article tenant.
3. Sample 1,000 resolved tickets per tenant into a candidate eval set, reviewed by the tenant's admin.

**Decision.** Tenant ticket history feeds evals, not answers. Old tickets contain one-off promises agents made, and retrieving them turns exceptions into policy.

**Trap.** A single global sync queue. The first big tenant's backfill delays every other tenant's article edits by hours.

## 4. Processing
The same pipeline runs for every tenant; only the inputs and limits differ.

**How:**
1. Parse with Unstructured, split on headings to about 400 tokens with 50 overlap, and tag `tenant_id`, `source`, `audience`, `locale`, `updated_at`.
2. Embed with `text-embedding-3-small` stored as `halfvec`: 10M chunks is about 30 GB, and a full re-embed of 4B tokens costs $80.
3. Hash chunk text and upsert only changes; a typical tenant edit is searchable within 3 minutes.
4. Cap ingest per tier (Starter 20,000 articles, Growth 100,000) in code at the connector.

**Decision.** One shared embedding model for all tenants. Per-tenant models would multiply index rebuilds and make evals incomparable.

**Trap.** Writing `tenant_id` only as metadata on a shared index. A missing filter on one query is then a cross-tenant leak; partition instead.

## 5. Agents
One agent graph for every tenant, parameterized by the pinned config version.

| Step | Model | Notes |
|---|---|---|
| Route | Haiku 5.5 | 1,500 in, 20 out; picks path and answer model |
| Answer | Haiku 5.5 (55% of turns) or Sonnet 5.5 (45%) | FAQ-style turns go small; actions and multi-part turns go mid |
| Act | Sonnet 5.5 plus a Temporal workflow | Proposes; the workflow executes |

**How:**
1. Load the config version at session start and pin it for the whole conversation, so a mid-chat promotion never changes behavior.
2. Let the tier set the ceiling: Starter cannot route to Opus; Enterprise can enable Opus 5.5 for named intents.
3. Start a Temporal workflow for any action; the chat turn returns "started" and later events stream the result.
4. Stop at 8 steps or 25 s, then hand off into the tenant's own help-desk queue.

**Decision.** Route per turn rather than per tenant. A Starter tenant's "where is my order" and an Enterprise tenant's billing dispute need different models regardless of plan.

**Trap.** Letting a tenant's prompt raise the step limit or change the model. Those are config fields the platform validates, not prompt text.

## 6. Memory
Memory is keyed by tenant, end user and agent, and never crosses a tenant.

| Tier | Holds | Lives in | Expires |
|---|---|---|---|
| Thread | Last 6 turns plus typed fields | Postgres checkpointer, RLS by tenant | Tenant setting, 30 to 365 days |
| End user | Preferences, open cases | Postgres, RLS | On tenant or user deletion request |
| Tenant | Policies, tone, glossary | Config version, in the cached prefix | New version |

**How:**
1. Set `app.tenant_id` on every Postgres connection checkout; row-level security policies filter every table on it.
2. Encrypt transcripts with a per-tenant data key under a per-tenant AWS KMS key; Enterprise tenants can bring their own key.
3. Run deletion requests as a Temporal workflow that removes rows, vectors and S3 objects, and reports completion.

**Decision.** Per-tenant KMS keys for every tier, at about $200 a month. Offboarding a tenant becomes crypto-shredding: revoke the key and backups are unreadable.

**Trap.** Learning shared "insights" across tenants in memory. One tenant's refund exceptions surfacing in another's answers ends the contract.

## 7. MCP Tool Servers
A tool gateway hosts per-tenant connectors behind one interface, and enforces each tenant's limits.

| Tool family | Example tools | Limit in code |
|---|---|---|
| Commerce | `get_order`, `start_refund`, `create_return` | Tenant refund cap, platform ceiling $1,000 |
| CRM | `get_account`, `update_case` | Field allowlist per tenant |
| Custom | The tenant's own MCP server over HTTPS | Allowed tool names, 10 s timeout, response size cap |

**How:**
1. Resolve credentials from Vault by `tenant_id` inside the gateway; the orchestrator never holds a tenant secret.
2. Compute the effective permission as the intersection of tenant-enabled tools, the end user's scopes from the JWT, and the agent's allowed tools.
3. Pass every write to Temporal as an activity with an idempotency key of `tenant_id:workflow_id:step`.

**Decision.** Tenant limits come from config, but the platform ceiling is a constant in the gateway. No config value above $1,000 is accepted.

**Trap.** Loading every tenant's tools into one tool list. The model then sees other tenants' tool names, and the prompt cache breaks for everyone.

## 8. Endpoints
A runtime API for conversations and an admin API for configuration, both tenant-scoped.

| Stage (Enterprise, p95) | Time |
|---|---|
| Edge, auth, tenant and config load (Redis) | 40 ms |
| Admission check (Redis Lua token bucket) | 5 ms |
| Input guard | 60 ms |
| Router in parallel with retrieval and user context | 250 ms |
| Model time to first token, cached prefix (Sonnet 5.5) | 650 ms |
| First-sentence citation check | 100 ms |
| **Total** | **1,105 ms (SLO 1.5 s)** |

**How:**
1. Runtime: `POST /v1/conversations`, `POST /v1/conversations/{id}/messages` (SSE), `GET /v1/actions/{workflow_id}`.
2. Admin: `PUT /v1/config` creates a draft version, `POST /v1/config/{version}/evaluate`, `POST /v1/config/{version}/promote`, `GET /v1/usage`.
3. Outbound webhooks to tenants signed with HMAC-SHA256 over timestamp and body; retries with backoff.
4. Run on EKS with separate node pools for Enterprise and shared tiers; scale on concurrent streams.

**Decision.** Starter gets 2.5 s, not 1.5 s. When the platform is busy, Starter waits up to 1 s in the admission queue before shedding, which buys headroom for Enterprise.

**Trap.** One global rate limit. It either throttles everyone during one tenant's surge or lets that tenant consume the platform.

## 9. Caching
The cached prefix is the biggest cost lever after routing, and it behaves differently by tier.

| Monthly cost, 15M turns | Total |
|---|---|
| Sonnet 5.5 on every turn, no prompt cache | $307,500 |
| Sonnet 5.5 on every turn, per-tenant cached prefix | $177,000 |
| Router plus 55% Haiku 5.5, cached prefix (sum of tiers below) | $85,000 |

| Tier | Turns | Prefix hit rate | Monthly | Per conversation |
|---|---|---|---|---|
| Enterprise | 7.5M | 95% | $38,400 | $0.026 |
| Growth | 5.25M | 85% | $30,200 | $0.029 |
| Starter | 2.25M | 60% | $16,400 | $0.036 |

A Sonnet turn is a 6,000-token prefix ($0.0012 read, $0.015 written at 1.25x), 3,000 uncached tokens ($0.006) and 250 output ($0.0025).

**How:**
1. Order the prefix: platform tools (2,000 tokens, identical for all tenants), tenant tools, platform rules, tenant policies, then the breakpoint.
2. Put a breakpoint after the shared platform tools too; a Starter miss then writes 4,000 tokens, not 6,000, which brings Starter to about $0.028 a conversation.
3. Cache tenant configs and retrieval results per tenant in Redis with the config version in the key.

**Decision.** Never share answer caches across tenants; key every cache by `tenant_id` and config version.

**Trap.** Sorting tenant tools before platform tools. Tools render first, so a tenant-specific tool at the top destroys the shared prefix for every tenant.

## 10. Data Stores
Isolation is built into the storage layout, not added by query discipline.

| Store | Holds | Size |
|---|---|---|
| Aurora Postgres + pgvector | Configs, threads, users, chunks partitioned by tenant | About 30 GB vectors, 400 GB transcripts a year |
| Redis (ElastiCache) | Token buckets, config cache, stream resume | About 20 GB |
| Kafka (MSK, 3 brokers) | Turn, tool and usage events, keyed by tenant | 90M events a month, 150/s at peak |
| ClickHouse | Usage, cost and quality facts | About 200 GB a year compressed |
| Temporal Cloud | Action workflows | 450,000 a month (15% of conversations act) |
| S3 (per-tenant KMS) | Raw documents, exports | About 2 TB |

**How:**
1. List-partition `chunks` by `tenant_id` with an HNSW index per partition; queries name the partition, so another tenant's vectors are not reachable.
2. Give the 5 largest tenants their own partitions and read replicas; the rest share hash partitions with RLS.
3. Consume Kafka into ClickHouse with exactly-once dedupe on event id.

**Decision.** pgvector partitions over a separate vector database. Per-partition recall@5 is 0.90 and p95 is 30 ms at 400,000 articles, and one database keeps RLS consistent.

**Trap.** Testing isolation by reading the code. Prove it with tests (section 12).

## 11. Output
Every tenant gets the same typed events, rendered in its own brand.

| Event | Contains | Source |
|---|---|---|
| `token`, `citation` | Answer text and tenant article links | Model, retrieval |
| `action_proposal` | Action, amount, `action_id` | Tool gateway |
| `action_status` | Workflow state and receipt | Temporal |
| `handoff` | Ticket id in the tenant's help desk | Tool gateway |

**How:**
1. Validate each event against a Pydantic schema; the widget themes it from the tenant's brand config.
2. Emit a usage event to Kafka for every turn: tokens in, cached, out, model, tools, outcome.
3. Write handoffs into the tenant's queue with a summary and the transcript.

**Decision.** Receipts come from workflow results, never from model text.

**Trap.** Letting tenants inject raw HTML into answers through their brand config; sanitize it as untrusted input.

## 12. Guardrails
Isolation, money and admission rules hold even when a prompt, a tenant admin or an end user pushes on them.

| Rule | Enforced by |
|---|---|
| Tenant isolation | Edge-set `tenant_id`, RLS, vector partitions, per-tenant Vault paths and KMS keys |
| Overload | Token buckets: tenant cap at 3x contracted peak; tier priority; degrade, queue, then shed |
| Money | Tenant refund cap plus $1,000 platform ceiling in the gateway |
| Config safety | Schema validation: no step limit above 12, no model outside the tier |
| Injection | Retrieved and tool content wrapped as data; Lakera Guard on input |

**How:**
1. Plant a unique canary document in every tenant; a nightly job queries every tenant for every other tenant's canary and pages on any hit.
2. Under load: above 85% of provider capacity, route borderline turns to Haiku; above 90%, queue Starter up to 1 s; above 95%, shed Starter to "we will email you" and queue Growth.
3. Cap the flash-sale tenant at 6 turns/s; overflow gets a handoff message, and the other 199 see no change.

**Decision.** Limits that protect money, permissions or privacy live in code, never in a tenant's prompt.

**Trap.** Shedding before degrading. Moving a turn to Haiku costs a little quality; shedding costs a customer.

## 13. Key Impact
The platform's success is tenants' resolution at a healthy margin.

| Metric | Target | Measured by |
|---|---|---|
| Resolution rate, median tenant | 50% | ClickHouse outcomes, 7-day reopen window |
| Gross margin on model spend | Above 90% ($1.2M revenue, $85,000 spend) | Usage events times price table |
| p95 time to first token | 1.5 s Enterprise, 2.5 s Starter | Traces per tier |
| Config changes blocked by evals | Tracked; target zero regressions shipped | Eval gate logs |
| Cross-tenant reads | Zero | Canary job |
| Tenant onboarding time | Under 2 days, from 3 weeks | Admin console |

**How:**
1. Attribute cost per tenant, feature and model from usage events, with cached tokens at their discounted price and shared costs pro rata by turns.
2. Alert tenants and account managers at 50%, 80% and 100% of their monthly quota, once each.
3. Run a 4-week holdout for each new tenant to measure its resolution lift against its human team.

**Decision.** Report margin per tenant, not only in aggregate. A few Starter tenants with huge knowledge bases can lose money unnoticed.

**Trap.** Reporting the platform average resolution rate. It hides the ten tenants whose config is failing.

## 14. Failure Modes
Shared platforms fail in shared ways, so each failure needs a blast-radius limit as well as a fix.

- **Flash-sale surge.** The tenant bucket caps it at 6 turns/s; overflow goes to handoff; other tenants keep their SLO.
- **Provider 429s or outage.** LiteLLM fails over from the Anthropic API to Bedrock; if both are saturated, degrade and shed by tier.
- **A tenant ships a bad prompt.** Its eval suite blocks promotion; if a regression slips through, the 10% canary for 24 h catches it and rollback is a version pointer flip.
- **Temporal worker backlog.** Actions queue but never run twice; chat tells the customer the action is pending.
- **Kafka consumer lag.** Billing is delayed, not lost; alert when lag exceeds 10 minutes.

**How:**
1. Load-test monthly with k6 replaying 40 turns/s plus a synthetic 20 turns/s surge from one tenant.
2. Run chaos drills: kill a Temporal worker mid-refund and check exactly one refund lands.
3. Alert on per-tenant error rate, shed count and canary hits in Datadog.

**Decision.** Every failure is contained to one tenant or one tier wherever possible.

**Trap.** A config rollback that reloads live conversations. Pinned versions finish on the old config.

## 15. Build Order
1. **Weeks 1 to 2:** tenant identity at the edge, RLS, partitions, canary job; golden sets for five design partners. Number: zero canary hits.
2. **Week 3:** versioned config and the eval gate. Number: a deliberately bad prompt is blocked 10 times out of 10.
3. **Week 4:** retrieval per tenant. Number: recall@5 above 0.88 on every partner.
4. **Week 5:** admission control and load test. Number: other tenants' p95 unchanged during a 10x surge.
5. **Week 6:** tool gateway and Temporal actions. Number: zero duplicate refunds across 1,000 chaos runs.
6. **Week 7:** Kafka metering and per-tenant cost. Number: attributed cost within 1% of the provider invoice.
7. **Weeks 8 to 10:** onboard 20, then all 200 tenants. Number: onboarding under 2 days.

**How:**
1. Gate each step on its number; isolation tests run on every merge forever.
2. Onboard tenants in cohorts of 20 behind flags.
3. Reconcile metering against provider invoices monthly.

**Decision.** Isolation and admission control before features. A clever agent on a leaky platform cannot be sold.

**Trap.** Onboarding the largest tenant first. Start with mid-size partners and add the airline once the surge test passes.
