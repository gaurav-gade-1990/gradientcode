## 1. What the problem is really asking

Problem 201 (returns-refunds-agent) designed one support agent for one retailer. This problem asks you to turn that agent into **a platform that 200 businesses share**. The agent itself barely changes. What's new is everything around it: who gets capacity when one tenant surges, how one tenant's data is made unreachable from another's, how a tenant changes its own prompt without breaking anyone, where multi-day actions run, and who pays for which tokens.

The core tension: sharing is what makes the economics work (one runtime, one cached tool prefix, one team of eight), and sharing is exactly what lets a noisy or careless tenant hurt the other 199. Every section is an answer to "how do we share this without leaking or starving?"

Three decisions carry the design:

- **`tenant_id` is set once at the edge and enforced by every layer below in code.** Row-level security in Postgres, a vector partition per tenant, per-tenant Vault paths and KMS keys, every cache keyed by tenant. Never carried by the prompt.
- **Admission control per tenant and per tier.** Redis token buckets cap each tenant at 3 times its contracted peak, and under platform load you degrade to Haiku, then queue Starter, then shed Starter, in that order.
- **Configuration is versioned data, gated by evals and pinned per conversation.** A tenant's prompt change is a new immutable version that must pass that tenant's eval suite, ships to a 10% canary, and only affects new conversations.

## 2. The numbers that drive the design

**Traffic.**

| Step | Arithmetic | Result |
|---|---|---|
| Turns a month | 3M conversations × 5 turns | 15M turns |
| Average rate | 15M ÷ (30 × 86,400 s) | about 5.8 turns/s |
| Business-hours peak | × 4 | about 23 turns/s |
| Plan for | headroom | 40 turns/s |
| Largest tenant at peak | 8% of 23 | about 1.9 turns/s |
| Its flash sale | × 10 | about 19 turns/s |

The flash-sale number is the one that shapes admission control: a single tenant can briefly want almost as much as the whole platform's normal peak. The model answer caps it at 6 turns/s, which is about 3 times its contracted 1.9.

**Knowledge.** 10M chunks × 1,536 dimensions × 2 bytes (`halfvec`) is about 30 GB. At about 400 tokens a chunk that's 4B tokens, $80 for a full re-embed with `text-embedding-3-small`. Re-embedding is cheap; the hard part is isolation.

**Latency (Enterprise, p95).**

| Stage | Time |
|---|---|
| Edge, auth, tenant and config load | 40 ms |
| Admission check (Redis Lua token bucket) | 5 ms |
| Input guard | 60 ms |
| Router in parallel with retrieval and user context | 250 ms |
| Sonnet 5.5 first token, cached prefix | 650 ms |
| First-sentence citation check | 100 ms |
| Total | 1,105 ms |

40 + 5 + 60 + 250 + 650 + 100 = 1,105 ms against a 1.5 s SLO. Starter's 2.5 s SLO leaves room for up to 1 s waiting in the admission queue.

**Cost.** A Sonnet 5.5 turn is a 6,000-token prefix, 3,000 uncached tokens and 250 output tokens.

| Piece | Arithmetic | Cost |
|---|---|---|
| Prefix, cache hit | 6,000 × $0.20 / 1M | $0.0012 |
| Prefix, cache write at 1.25× | 6,000 × $2.50 / 1M | $0.015 |
| Uncached input | 3,000 × $2 / 1M | $0.006 |
| Output | 250 × $10 / 1M | $0.0025 |
| No cache at all | 9,000 × $2 / 1M + $0.0025 | $0.0205 |

Now apply the levers in order:

| Monthly, 15M turns | Total |
|---|---|
| Sonnet on every turn, no cache: $0.0205 × 15M | $307,500 |
| Sonnet on every turn, per-tenant cached prefix | $177,000 |
| Router plus 55% Haiku, cached prefix | $85,000 |

$307,500 is far over the $120,000 ceiling. Caching alone still misses it. **Routing 55% of turns to Haiku is the lever that moves cost most**, bringing the platform to $85,000. That's the "one lever" the prompt asks for.

Per tier, from the model answer:

| Tier | Turns | Prefix hit rate | Monthly | Per conversation |
|---|---|---|---|---|
| Enterprise | 7.5M | 95% | $38,400 | $0.026 |
| Growth | 5.25M | 85% | $30,200 | $0.029 |
| Starter | 2.25M | 60% | $16,400 | $0.036 |

Starter costs the most per conversation because small tenants have cold caches: fewer conversations means their tenant-specific prefix expires between visits.

**Margin.** If half of 3M conversations resolve, $0.80 × 1.5M = $1.2M of revenue against $85,000 of model spend, a gross margin on model spend above 90%.

**Events.** About 90M events a month into Kafka, about 150/s at peak. 15% of conversations act, so Temporal runs 450,000 workflows a month.

## 3. How to spend your time

The session is 60 minutes; aim to say the answer in about 30.

| Minutes | What you do |
|---|---|
| 0–4 | Restate the platform job; write turns/s, the flash-sale load and the $120,000 ceiling |
| 4–10 | **Pillar A:** per-tier SLOs and margin; a Single View with admission control, config service, Temporal and Kafka |
| 10–19 | **Pillar B:** fair per-tenant sync, partitions not filters, one graph with pinned config, RLS and KMS, the tool gateway |
| 19–26 | **Pillar C:** runtime and admin APIs, the three-row cost table and per-tier table, partitioned stores, usage events |
| 26–32 | **Pillar D:** canaries and degrade-queue-shed, per-tenant margin, blast-radius failure modes, isolation-first build order |
| 32–60 | Follow-ups and deep dives |

Medium problems are graded on the platform pieces: admission control, the durable workflow and the event log. If you're running out of time, cut detail from Processing, not from those.

## 4. Pillar A: Frame

### Scenario

**The question:** who are the users, what's the job, and which numbers shape the design?

**How to reason.** There are two users: the tenant (who configures the agent) and the tenant's customers (who chat with it). The job is "one runtime, shaped per tenant, where onboarding is configuration". Derive average and peak turns per second and the flash-sale load (section 2). Then commit to targets: per-tier time to first token (1.5 s Enterprise, 2.5 s Starter), 99.9% availability, zero cross-tenant reads, and model spend under the ceiling.

Start with five design-partner tenants across tiers and pull 500 real conversations from each as the first golden sets. Out of scope: voice, per-tenant fine-tuned models, data residency outside the US and EU regions already offered.

**The trap.** Building for the average tenant. The design is shaped by the largest tenant's flash sale and the smallest tenant's cold cache.

**Rubric criteria earned:** average and peak turns per second; the flash-sale load; per-tier SLOs and a cost target; out of scope.

### Single View

**The question:** what are the layers, and where is tenant identity set?

**How to reason.** Compared with a single-tenant design, four layers are new and the rubric names all of them: **admission control** (Redis token buckets per tenant and tier), a **config service** (immutable, versioned tenant configs), a **workflow engine** (Temporal, for actions that run minutes or days), and an **event log** (Kafka to ClickHouse, for metering and eval samples). Around them sit the familiar ones: the widget and API edge (tenant API key plus an end-user JWT signed by the tenant), the LangGraph orchestrator, per-tenant retrieval, an MCP tool gateway, LiteLLM over the Anthropic API and Bedrock, and evals that gate every config change.

Draw the arrow from the edge carrying `tenant_id`, `user_id` and tier, and say every layer below enforces it. The one idea: tenant identity is set once at the edge and enforced in code below, never carried by the prompt.

**The trap.** Leaving out the event log. Without it, finance's "what does each tenant cost?" has no answer.

**Rubric criteria earned:** admission control, config service, workflow engine and event log as layers; identity set at the edge and enforced below; the isolation idea.

## 5. Pillar B: Build the core

### Data Sources

**The question:** what data does each tenant bring, how does it reach the model, and how do syncs stay fair?

**How to reason.** Three kinds: knowledge (Zendesk Guide, Confluence, Notion, website crawls) indexed per tenant and synced hourly or on webhook; live systems (Shopify, Salesforce, a tenant's own REST API) reached through tool calls; and ticket history, which is **mined for evals, never retrieved for answers**, because old tickets contain one-off promises that would become policy.

Connectors are configuration: the tenant authorises with OAuth and tokens go to HashiCorp Vault under `tenants/{id}/`. Sync jobs run on a per-tenant queue with **weighted fair scheduling**, so a 400,000-article import doesn't stall a 200-article tenant's edit.

**The trap.** A single global sync queue. The first big backfill delays everyone's edits by hours.

**Rubric criteria earned:** indexed knowledge versus live tools; per-tenant credentials in a secrets manager; fair per-tenant ingestion.

### Processing

**The question:** how do 10M chunks get built and kept fresh?

**How to reason.** The same pipeline for every tenant: Unstructured, heading splits to about 400 tokens with 50 overlap, tags for `tenant_id`, `source`, `audience`, `locale` and `updated_at`, one shared embedding model (`text-embedding-3-small` as `halfvec`, about 30 GB, $80 for a full re-embed). Hash chunks and upsert only changes, so a typical edit is searchable in 3 minutes. Cap ingest per tier in code at the connector (Starter 20,000 articles, Growth 100,000).

One shared embedding model is deliberate: per-tenant models would multiply rebuilds and make evals incomparable across tenants.

**The trap.** Putting `tenant_id` only as metadata on one shared index. A single query that forgets the filter is a cross-tenant leak. Partition instead, so the wrong tenant's vectors aren't reachable at all.

**Rubric criteria earned:** chunking, tenant metadata and the embedding model; index size and re-embed cost; changed content only; isolation by partition, not filter.

### Agents

**The question:** how does one agent graph serve 200 configurations?

**How to reason.** Parameterise one graph by a config version. Haiku routes each turn (1,500 in, 20 out) and picks the answer model: Haiku for 55% of turns (FAQ-style), Sonnet for 45% (actions, multi-part questions). Routing is **per turn, not per tenant**, because a Starter tenant's "where is my order" and an Enterprise tenant's billing dispute need different models whatever the plan. The tier sets the ceiling: Starter can't route to Opus; Enterprise can enable Opus 5.5 for named intents.

Pin the config version at session start for the whole conversation, so a mid-chat promotion never changes behaviour. For any action, start a Temporal workflow; the turn returns "started" and later events stream the result (problem durable-workflow-replay). Stop at 8 steps or 25 s and hand off into the tenant's own help-desk queue.

**The trap.** Letting a tenant's prompt raise the step limit or change the model. Those are validated config fields, not prompt text.

**Rubric criteria earned:** pinned config; a stated small/mid split; actions in a durable workflow; limits as validated config.

### Memory

**The question:** what's remembered per thread, user and tenant, and how is it kept separate?

**How to reason.** Thread memory (last 6 turns plus typed fields) lives in a Postgres checkpointer with retention set per tenant, 30 to 365 days. End-user memory (preferences, open cases) lives in Postgres until a deletion request. Tenant memory (policies, tone, glossary) is the config version, in the cached prefix.

Enforce separation in the database: set `app.tenant_id` on every connection checkout, and RLS policies filter every table on it (problem tenant-isolated-memory). Encrypt transcripts with a per-tenant data key under a per-tenant KMS key, about $200 a month for all tiers, with bring-your-own-key for Enterprise. Offboarding becomes crypto-shredding: revoke the key and backups are unreadable. Deletion requests run as a Temporal workflow across rows, vectors and S3.

**The trap.** Learning shared "insights" across tenants. One tenant's refund exceptions showing up in another's answers ends the contract.

**Rubric criteria earned:** memory keyed by tenant and user with RLS; per-tenant keys and offboarding; no cross-tenant learning.

### MCP Tool Servers

**The question:** how are per-tenant tools, credentials and limits handled?

**How to reason.** A tool gateway hosts per-tenant connectors behind one interface: commerce (`get_order`, `start_refund`, `create_return`), CRM (`get_account`, `update_case` with a per-tenant field allowlist), and custom tenant MCP servers over HTTPS (allowed tool names, 10 s timeout, response size cap). Credentials resolve from Vault by `tenant_id` **inside the gateway**; the orchestrator never holds a tenant secret.

Effective permission is the **intersection** of tenant-enabled tools, the end user's scopes from the JWT and the agent's allowed tools (problem tool-permission-scopes). Money has two layers: the tenant's refund cap from config, and a $1,000 platform ceiling that's a constant in the gateway; no config value above it is accepted. Every write runs as a Temporal activity with idempotency key `tenant_id:workflow_id:step`.

**The trap.** Loading every tenant's tools into one tool list. The model sees other tenants' tool names, and the cache breaks for everyone.

**Rubric criteria earned:** credentials resolved in the gateway; intersected permissions; a platform money ceiling; idempotent writes.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what are the runtime and admin APIs, and how is latency spent?

**How to reason.** Runtime: create a conversation, post a message (SSE), and `GET /v1/actions/{workflow_id}`. Admin is where configuration becomes safe: `PUT /v1/config` makes a draft version, `POST /v1/config/{version}/evaluate` runs the tenant's suite, `POST /v1/config/{version}/promote` ships it, and `GET /v1/usage` reports metering. Outbound webhooks to tenants are signed with HMAC-SHA256 over timestamp and body. Run on EKS with separate node pools for Enterprise and shared tiers.

Show the 1,105 ms table, then explain tiers under load: Starter waits up to 1 s in the admission queue before shedding, which is why its SLO is 2.5 s and why Enterprise keeps its headroom.

**The trap.** One global rate limit. It either throttles everyone during one tenant's surge or lets that tenant consume the platform (problem token-bucket-rate-limiter).

**Rubric criteria earned:** stage budget within 1.5 s; create, evaluate and promote endpoints; signed webhooks; tier latency under load.

### Caching

**The question:** what does the platform cost per month and per tier, and which lever moves it most?

**How to reason.** Present the three-row table in the order you apply the levers ($307,500, $177,000, $85,000), then the per-tier table with hit rates. The prompt-ordering decision is what lets tenants share a prefix. Tools render first in the prompt, so order it: platform tools (2,000 tokens, identical for every tenant), tenant tools, platform rules, tenant policies, then the breakpoint. Add a second breakpoint after the shared platform tools, so a Starter cache miss writes 4,000 tokens instead of 6,000, which lowers Starter's per-conversation cost.

Tenant configs and retrieval results cache in Redis with the config version in the key. **Every cache is keyed by `tenant_id` and config version**, and no answer cache is ever shared across tenants.

**The trap.** Sorting tenant tools before platform tools, which destroys the shared prefix for every tenant.

**Rubric criteria earned:** monthly cost with and without routing and caching; per-tier cost with hit rates; shared prefix ordering; tenant-keyed caches.

### Data Stores

**The question:** which stores, how big, and how does the layout enforce isolation?

**How to reason.** Aurora Postgres with pgvector holds configs, threads, users and chunks (about 30 GB of vectors, 400 GB of transcripts a year). `chunks` is list-partitioned by `tenant_id` with an HNSW index per partition; queries name the partition. The 5 largest tenants get their own partitions and read replicas; the rest share hash partitions with RLS. Redis (about 20 GB) holds token buckets, config cache and stream resume. Kafka on MSK with 3 brokers carries 90M events a month, consumed into ClickHouse (about 200 GB a year compressed) with exactly-once dedupe on event id. Temporal Cloud runs 450,000 workflows a month. S3 with per-tenant KMS holds about 2 TB.

Why not a separate vector database? Per-partition recall@5 is 0.90 and p95 is 30 ms at 400,000 articles, and one database keeps RLS consistent.

**The trap.** Testing isolation by reading the code. Prove it with tests (see Guardrails).

**Rubric criteria earned:** each store sized; per-tenant vector partitions; event log into an analytics store; measured vector-store justification.

### Output

**The question:** what does the platform return, and what does every turn emit for metering?

**How to reason.** Typed events, the same for every tenant and themed from brand config: `token` and `citation`, `action_proposal` (from the gateway), `action_status` (from Temporal, with the receipt), and `handoff` (ticket id in the tenant's help desk). Validate each against a Pydantic schema. Then the metering half: every turn emits a usage event to Kafka with tokens in, cached and out, the model, tools and outcome (problem tenant-cost-attribution).

**The trap.** Letting tenants inject raw HTML through brand config. Sanitise it as untrusted input. And, as in problem 201, receipts come from workflow results, never model text.

**Rubric criteria earned:** typed events including workflow status; a per-turn usage event; receipts from workflow results.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** what enforces isolation, money limits and fair capacity when a prompt or tenant pushes on them?

**How to reason.** The rule table: isolation by edge-set `tenant_id`, RLS, partitions, Vault paths and KMS keys; overload by token buckets with tier priority; money by the tenant cap plus the $1,000 ceiling; config safety by schema validation (no step limit above 12, no model outside the tier); injection by wrapping retrieved and tool content as data plus Lakera Guard.

Then make two of them concrete. **Prove isolation continuously**: plant a unique canary document in every tenant, and a nightly job queries every tenant for every other tenant's canary and pages on any hit. **Define the degrade ladder** with numbers: above 85% of provider capacity, route borderline turns to Haiku; above 90%, queue Starter up to 1 s; above 95%, shed Starter to "we will email you" and queue Growth. Cap the flash-sale tenant at 6 turns/s; its overflow gets a handoff message, and the other 199 see no change.

**The trap.** Shedding before degrading. Haiku costs a little quality; shedding costs a customer.

**Rubric criteria earned:** canary documents; degrade, queue, shed thresholds by tier; a numeric cap and what overflow gets; money and permission limits in code.

### Key Impact

**The question:** how do you know the platform works for tenants and for the business?

**How to reason.** Two audiences, two kinds of number. For tenants: resolution rate per tenant (median 50%, 7-day reopen window), with a 4-week holdout per new tenant against its human team. For the business: gross margin on model spend above 90% ($1.2M revenue against $85,000), p95 first token per tier, zero cross-tenant reads, onboarding from 3 weeks to under 2 days, and regressions blocked by evals.

Attribute cost per tenant, feature and model from usage events, with cached tokens at their discounted price and shared costs pro rata by turns. Alert tenants and account managers at 50%, 80% and 100% of quota, once each.

**The trap.** Reporting the platform average resolution rate, which hides the ten tenants whose config is failing. Likewise, report margin per tenant: a few Starter tenants with huge knowledge bases can lose money unnoticed.

**Rubric criteria earned:** per-tenant resolution; cost attribution with cache discounts; margin against spend; quota alerts at thresholds.

### Failure Modes

**The question:** what breaks on a shared platform, and how is blast radius limited?

**How to reason.** For each failure, say who it's contained to. Flash sale: the bucket caps it at 6 turns/s, overflow to handoff, others keep their SLO. Provider 429s or outage: LiteLLM fails over from the Anthropic API to Bedrock; if both saturate, degrade and shed by tier. Bad tenant prompt: its eval suite blocks promotion (problem prompt-regression-gate); if one slips through, the 10% canary for 24 h catches it, and rollback is a version-pointer flip. Temporal backlog: actions queue but never run twice. Kafka lag: billing is delayed, not lost; alert at 10 minutes.

Test it: monthly k6 load tests replaying 40 turns/s plus a synthetic 20 turns/s surge from one tenant; chaos drills that kill a Temporal worker mid-refund and check exactly one refund lands.

**The trap.** A config rollback that reloads live conversations. Pinned versions finish on the old config.

**Rubric criteria earned:** noisy neighbour; provider failover; bad config with eval gate, canary and rollback; crash mid-action without duplicates.

### Build Order

**The question:** in what order, and what number unlocks each step?

**How to reason.** Isolation and admission before features: a clever agent on a leaky platform can't be sold. Weeks 1–2: edge identity, RLS, partitions, canaries, five partners' golden sets (zero canary hits). Week 3: versioned config and the eval gate (a bad prompt blocked 10 out of 10 times). Week 4: per-tenant retrieval (recall@5 above 0.88 for every partner). Week 5: admission control (others' p95 unchanged during a 10x surge). Week 6: gateway and Temporal (zero duplicate refunds in 1,000 chaos runs). Week 7: metering (attributed cost within 1% of the invoice). Weeks 8–10: onboard in cohorts of 20 (under 2 days each).

**The trap.** Onboarding the largest tenant first. Add the airline once the surge test passes.

**Rubric criteria earned:** isolation and tests first; a number per step; cohorts, not all at once.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| Isolation | A `tenant_id` filter in every query | Edge-set identity, RLS, per-tenant partitions and keys, proven nightly with canaries |
| Noisy neighbour | Autoscale | Per-tenant buckets at 3× contracted peak, then degrade, queue, shed by tier |
| The cost lever | Prompt caching | Per-turn routing to Haiku for 55% of turns, then a shared platform prefix |

## 9. Common mistakes

- Designing a single agent and saying "and we run 200 of them".
- Isolation by metadata filter on one shared vector index.
- Running refunds inside the chat turn, so a deploy kills them.
- Letting a tenant's prompt set the model or step limit.
- A cost estimate without routing, which can't meet $120,000.
- Tenant tools placed before shared platform tools, breaking the shared cache.
- Only platform-wide averages for resolution and margin.

## 10. Follow-ups an interviewer might ask

- *The airline's flash sale starts. Walk me through the first minute.* Its bucket admits up to 6 turns/s; overflow gets a handoff message. If total load passes 85% of provider capacity, borderline turns move to Haiku; at 90% Starter queues up to 1 s. Other tenants' SLOs hold.
- *A tenant edits its prompt and it's worse. How far does the damage go?* Its eval suite should block promotion. If it doesn't, only that tenant's new conversations in the 10% canary see it for up to 24 h; rollback flips a version pointer and live conversations stay pinned.
- *An Enterprise tenant leaves. How do you prove its data is gone?* A Temporal deletion workflow removes rows, vectors and S3 objects and reports completion; revoking its KMS key makes backups unreadable.
- *Finance says your cost attribution is off. How would you know?* Reconcile attributed cost from usage events against the provider invoice monthly; the build gate is within 1%.
- *Why not one vector database per tenant?* Partitions in one Postgres already give 0.90 recall@5 and 30 ms p95 at the largest tenant, and keep RLS in one place; 200 databases would be eight engineers' full-time job.
