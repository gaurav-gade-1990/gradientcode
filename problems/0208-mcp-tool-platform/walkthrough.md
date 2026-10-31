## 1. What the problem is really asking

Problem 207 (llm-gateway-cost-controls) put one gateway in front of every **model** call. This problem puts one in front of every **tool** call, and the stakes are different. A model call costs money; a tool call reads a Salesforce account, deletes a repository or emails a customer. Today 140 agents do that through 48 servers, mostly with shared service accounts, so "who did this?" has no answer, and a community server already shipped a poisoned description that nobody could trace.

The core tension: 70 teams want tools in days, and the CISO wants every call attributable to a user, authorised in code, sandboxed when untrusted, and audited for 400 days, all within 40 ms of overhead. A platform that's slow or restrictive will be routed around; a platform that's easy but leaky is the current state with extra steps.

Three decisions carry the design:

- **A gateway every call must cross, not a library.** A library can be skipped; a network path can't. One virtual MCP server per agent exposes exactly its grant.
- **The user's own downstream token, and authorisation in OPA.** Per-user OAuth tokens held in Vault mean Salesforce and GitHub enforce their own ACLs. On top, OPA computes user scopes ∩ agent grant ∩ tool's required scopes, default deny. Nothing lives in a prompt or tool description.
- **Approval attaches to a version and a hash.** A canonical SHA-256 of `tools/list` is what gets approved. Any description change is a new version, a new poisoning test and a new approval, and the gateway serves descriptions from the registry, not from the live server.

## 2. The numbers that drive the design

**Call rate.**

| Step | Arithmetic | Result |
|---|---|---|
| Average | 2.4M calls ÷ 86,400 s | about 28 calls/s |
| Peak | given | 90 calls/s |
| Per-gateway-pod capacity | from the model answer | about 500 calls/s |

Six pods across 3 zones gives far more capacity than 90 calls/s needs. The fleet is **sized for failure, not load**. What does matter is that every millisecond of overhead is paid 2.4M times a day.

**Overhead budget.** p95 under 40 ms, excluding the downstream system:

| Stage | p50 | p95 |
|---|---|---|
| Envoy TLS and route | 2 ms | 4 ms |
| JWT verify, cached JWKS | 1 ms | 1 ms |
| OPA decision, local bundle | 2 ms | 4 ms |
| Rate limit and token lookup, Redis | 3 ms | 8 ms |
| Argument schema validation | 1 ms | 2 ms |
| Proxy hop and result scan | 8 ms | 15 ms |
| Audit produce, async | 1 ms | 3 ms |
| Total | 18 ms | 37 ms |

4 + 1 + 4 + 8 + 2 + 15 + 3 = 37 ms at p95. That only works if policy and token lookups are local or cached: an OPA bundle in memory, JWKS cached, tokens in Redis.

**Tool-definition tokens.** This is the number most candidates never compute, and the prompt asks for it.

| Step | Arithmetic | Result |
|---|---|---|
| Tool text per turn | 60 tools × 180 tokens | 10,800 tokens |
| Turns a month | 1.2M a day × 30 | 36M |
| No caching | 36M × 10,800 × $2 / 1M | about $778,000 a month |
| 90% cache reads | 36M × 10,800 × (0.9 × $0.20 + 0.1 × $2) / 1M | about $148,000 a month |
| Tool search, 12 tools | 12 × 180 = 2,160 tokens, same cache rate | about $30,000 a month |

So prompt caching saves about $630,000 and tool search another $118,000. Tool search only keeps its saving if the tool set is **stable for the session**; re-searching each turn changes the prefix and the cache misses.

**Shared quotas.** Salesforce allows 1M calls per 24 hours for the whole company. The rest of the company uses about 600,000, so agents get 300,000, split by team, leaving headroom. GitHub allows 5,000 requests an hour per user token, another reason per-user tokens beat one shared account.

**Sandbox capacity.** Code execution is 12% of peak traffic: 0.12 × 90 ≈ 11 calls/s at 2 s each, about 22 running at once, so a warm pool of 40 Firecracker microVMs (about 125 ms boot) has room.

**Audit storage.** 2.4M events a day × 1.2 KB ≈ 2.9 GB a day; over 400 days that's about 1.2 TB in S3 Object Lock, about 120 GB compressed in ClickHouse. Monthly infrastructure is about $23,000 at assumed list prices, against the $45,000 budget.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–4 | Restate the incidents as requirements; write calls/s, 40 ms, the tool-token cost and the Salesforce quota |
| 4–10 | **Pillar A:** two users and the attribution target; the Single View with identity separate from policy |
| 10–19 | **Pillar B:** manifests and no ACL copies, hash-based approval with a poisoning suite, tool search within the grant, user-keyed tokens, sandbox tiers |
| 19–26 | **Pillar C:** the 37 ms budget and kill switch, user-keyed caches, Kafka as record, typed denials |
| 26–32 | **Pillar D:** the scope intersection, approvals and quotas, shadow-path reconciliation, fail closed on writes, gateway-first build |
| 32–60 | Follow-ups |

Interviewers on this problem dig into identity: be ready to walk a single call from Okta to Salesforce without any long-lived secret in the agent.

## 4. Pillar A: Frame

### Scenario

**The question:** who uses the platform, what must it guarantee, and which numbers shape it?

**How to reason.** There are two users with opposite needs. **Agent builders** on 70 teams want a governed tool in days. **Security** needs to answer "what did agent X do, for whom" in minutes. Name both. Convert 2.4M calls a day into about 28/s average and 90/s peak, and compute the tool-definition cost (about $148,000 a month even with caching).

Inventory first: the 48 servers with owner, version, credential type, shared-account use and which agents load them. Baselines: 6 weeks to onboard a tool, 31 servers on shared accounts, 0% of calls attributable to a user. Targets: **100% of calls through the gateway, 0 shared accounts, onboarding in 3 business days.** Out of scope: building agents, hosting models, replacing downstream permission models.

**The trap.** Starting with the registry UI. A catalog without enforcement on the call path is documentation, and shadow servers keep running.

**Rubric criteria earned:** both users; calls per second; tool-definition token cost; an attribution target.

### Single View

**The question:** draw the layers from agent to downstream system.

**How to reason.** Agents (LangGraph, the Claude Agent SDK and others) send MCP requests carrying a platform access token for one user and hold no downstream secrets. The **gateway** (Envoy plus a stateless MCP proxy on the official SDK) is the one path. **Identity** and **policy** are separate layers, and the rubric checks that: identity is Okta as IdP, the gateway as an OAuth 2.1 resource server, and Vault holding per-user downstream tokens; policy is OPA with versioned Rego bundles returning allow, deny or needs-approval plus the bundle hash. The registry (Postgres rows per server version) decides the only tools an agent may see. **Temporal** handles approvals, onboarding and long jobs. The tool runtime has hosting tiers by trust. A **Kafka event log** feeds both ClickHouse/S3 audit and Redis health stats.

The one idea: the model only chooses which tool to call; identity, scope, quota and audit are decided by the gateway on every call, in code.

**The trap.** Merging identity and policy into one "auth" box. Identity answers "who is this?"; policy answers "may they do this?".

**Rubric criteria earned:** a gateway on every call; identity separate from policy; a workflow engine; an event log feeding audit and health.

## 5. Pillar B: Build the core

### Data Sources

**The question:** what does the platform read, and how fresh must each source be?

**How to reason.** Five sources. Server manifests: `tools/list` output plus an owner file from each repo, pulled on every release (410 tools today). Identity: Okta groups by SCIM push in under 60 s; offboarding revokes the user's Vault tokens in the same event. Quotas: Salesforce `/limits` and GitHub `X-RateLimit-Remaining` every 60 s. Call events: the gateway's own stream.

The interesting source is the one you **don't** read: downstream permissions. You could mirror 30 permission models into OPA, but the copy drifts within days and the gateway would allow what Salesforce would deny. The user's own OAuth token already carries the truth, so Salesforce and GitHub enforce their own ACLs.

**The trap.** Mirroring Salesforce sharing rules into OPA.

**Rubric criteria earned:** manifests pulled each release; identity sync with revocation on offboarding; downstream ACLs left downstream.

### Processing

**The question:** how does a new server version get approved, and how does the call stream become live health?

**How to reason.** Onboarding is a Temporal workflow. Canonicalise `tools/list` (sorted keys, normalised whitespace) and compute a **SHA-256 schema hash**, so any description change is a new version (problem tool-registry-versioning). Run Semgrep and Trivy on the code. Then the **poisoning suite**: a canary agent in a sandbox with honeytoken credentials runs 200 tasks against the new descriptions, and a judge flags any call touching a honeytoken or an unlisted host. The model answer prices this at about $500 a month at 30 versions a week. Embed each description into pgvector for tool search (under $1 for 410 tools).

For health, a Flink job rolls the Kafka stream into per-tool error rate, p95 and quota burn every 60 s, written to Redis.

**The trap.** Approving a server by name. The poisoning incident was a minor release of an approved server.

**Rubric criteria earned:** canonical hash per version; a poisoning test before approval; per-tool health on a short interval.

### Agents

**The question:** what model-driven pieces does the platform own, and how does it cut tool-definition tokens?

**How to reason.** The gateway itself is deterministic code, not an agent; you'd add one only if tool choice needed reasoning search can't do. But the platform shapes what consumer agents see. Show the lever table: $778,000 with no caching, $148,000 with 90% cache reads, $30,000 with **tool search** returning the top 12 of the agent's allowed tools at session start, plus a `find_tools` meta-tool to load more.

Two rules make it safe and keep the saving. Search **only within the allowed set**, never over all 410 tools, so ranking can't become a way to discover tools the agent wasn't granted. And **pin the chosen set for the session**, so the prefix stays byte-stable and the 90% cache rate holds.

One model-driven step lives in onboarding: a review agent drafts the security summary, and two humans approve any write tool.

**The trap.** Re-running tool search every turn.

**Rubric criteria earned:** tool search with a dollar estimate; search within the grant; a stable set per session; humans approve write tools.

### Memory

**The question:** what state does the platform keep, where, and for how long?

**How to reason.** Four kinds, each in the store its guarantee needs. Session: `Mcp-Session-Id` to user, agent and pinned tool versions in Redis for 24 h. Tokens: refresh tokens **per (user, provider)** under Vault transit encryption; access tokens cached in Redis until 60 s before expiry. Idempotency: write-tool keys `(agent, user, tool, key)` in Postgres for 24 h, so a retry returns the stored result. Approvals: Temporal state with a 30-minute TTL, then the call is denied.

The decision: no tool results beyond a 60 s read cache. The platform is a path for data, not a second copy of 30 systems.

**The trap.** Keying the token cache by agent. Two users of one agent then share a Salesforce identity, which is the shared account again.

**Rubric criteria earned:** tokens keyed by user and provider; refresh tokens in Vault; idempotency keys; no long-lived result storage.

### MCP Tool Servers

**The question:** how are servers of different provenance hosted, isolated and versioned?

**How to reason.** Sandbox by provenance. First-party (22 servers): EKS pods, Streamable HTTP, a SPIFFE identity each, no internet egress. Vendor remote (9): through an Envoy egress proxy pinned to the vendor's hosts, receiving the user's downstream token. Third-party packages (17): **gVisor** on a dedicated node pool, no cloud metadata endpoint, an egress allowlist each. Code execution: **Firecracker** microVMs with a warm pool of 40.

Never forward the agent's platform token to a server. The MCP spec forbids token passthrough, and a malicious server could replay it.

Versioning: agents pin `server@^1.4`; a new minor version serves 5% of sessions for 48 h and promotes only if its error rate and p95 match the old one. The 6 mTLS-only legacy services get a gateway-signed 60 s JWT naming the user.

**The trap.** Token passthrough.

**Rubric criteria earned:** named sandbox technologies with egress allowlists; no passthrough; staged rollout with a rollback condition; legacy services handled.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what endpoints exist, and where do the 40 ms go?

**How to reason.** For agents: `POST /mcp/{agent}` over Streamable HTTP aggregates the agent's allowed servers into **one virtual server** with namespaced names like `jira.create_issue` (problem mcp-jsonrpc-dispatch). For OAuth: `/.well-known/oauth-protected-resource`, tokens bound to the gateway's audience with resource indicators (RFC 8707), and `/connect/{provider}` for one-time consent. For people: `/registry/v1/servers`, `/audit/v1/query`, and `POST /admin/kill/{server}`, which revokes a version everywhere in under 60 s. Long jobs return a Temporal job id and stream progress. Show the 37 ms table, then the fleet: 6 pods across 3 zones, about 500 calls/s each, sized for availability.

One virtual server per agent is the decision: the agent sees exactly its grant and nothing it would need to be told to ignore.

**The trap.** Direct per-server URLs "for latency". Each is a path with no policy and no audit.

**Rubric criteria earned:** MCP per agent over Streamable HTTP; a kill switch with propagation time; a stage budget within 40 ms; fleet sized with its driver.

### Caching

**The question:** what's cached, with what key and TTL, and what must never be cached?

**How to reason.** Downstream access tokens per (user, provider) in Redis, refreshed **single-flight** when 20 calls hit a 401 at once (problem oauth-single-flight-refresh). OPA bundles in memory, refreshed every 30 s; JWKS for 10 minutes. The tool list per (agent, registry version), invalidated by the kill switch. Read-only, idempotent tool results for 60 s keyed by **(user, tool, version, args hash)**, which cut Salesforce calls 28% in the pilot, directly protecting the shared quota.

**The trap.** Caching results by (tool, args) alone. The first caller's permissions then serve everyone.

**Rubric criteria earned:** tokens cached with refresh and single-flight; the user in every result key; read-only results only, with a TTL.

### Data Stores

**The question:** which stores, how big, and what does it cost?

**How to reason.** Make **Kafka the system of record** for calls and every other store a projection, so a new audit question is a new consumer, not a migration. Postgres (under 20 GB) for registry, idempotency and grants; Redis (8 GB) for sessions, tokens, buckets and health; Vault for 5,000 users × 6 providers; Kafka at 2.9 GB a day with 7-day retention; ClickHouse with 400 days of audit (about 120 GB compressed); S3 Object Lock in compliance mode for the raw copy (1.2 TB, about $30 a month, assumed).

Each audit event records user, agent, tool, version, schema hash, policy bundle hash, decision, latency and an args hash; PII in arguments goes through the redaction vault. Chain each hour's batch with a SHA-256 over the previous hash before it lands in Object Lock (problem hash-chained-audit-log). No GPUs: embeddings and the judge are API calls. Total infrastructure is about $23,000 a month against $45,000.

**The trap.** Writing audit rows from each tool server. Fifty implementations give fifty schemas and gaps.

**Rubric criteria earned:** audit sized from events, bytes and 400 days; immutable storage and a hash chain; version, schema and policy hashes per event; monthly cost against budget.

### Output

**The question:** what does a tool call return, including when it's denied?

**How to reason.** Results are capped at 25,000 tokens, with larger lists paginated by cursor, and content from external systems is wrapped as untrusted data. Errors are MCP `isError` content with machine codes: `missing_scope`, `needs_approval` (with an approval id), `rate_limited` (with `retry_after`), `version_killed`. Calls over 30 s return job handles. Each team gets a weekly access report: tools used, scopes granted but unused for 30 days, denials.

Typed denials are a design decision: "you need Jira write access" is something an agent can explain to the user; "-32603" isn't.

**The trap.** Returning denials as prose. Agents retry them as transient failures and burn quota.

**Rubric criteria earned:** capped, paginated results; typed denials with retry hints; external content marked untrusted.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** which controls stop a misbehaving agent, and where do they live?

**How to reason.** Answer the prompt's "where is the authorisation decision made?" directly: **in OPA, in the gateway**, as user scopes ∩ agent grant ∩ tool's required scopes, default deny (problem tool-permission-scopes). For the 6 legacy services that trust the gateway's JWT, OPA also checks resource ownership (project id against the user's groups), since there's no downstream ACL to lean on. Risk tier 3 tools (repo delete, external email, opportunity stage change) pause in a Temporal approval sent to Slack with a 30-minute TTL. Per-team token buckets split the agents' 300,000 Salesforce calls, with interactive ahead of batch. Validate arguments against the registered JSON Schema and flag calls whose arguments copy spans from untrusted results (problem prompt-injection-quarantine).

The backstop: the downstream token is the user's, so even a policy bug can't exceed what the user could do by hand.

**The trap.** "Never delete repositories" in a tool description. A prompt is a suggestion; a deny rule is a control.

**Rubric criteria earned:** the scope intersection in code, default deny; high-risk writes behind approval with a timeout; per-team quota split with interactive priority; no limits in prompts or descriptions.

### Key Impact

**The question:** which numbers prove the platform worked?

**How to reason.** Five metrics with baselines: calls through the gateway (unknown to 100%), shared-account calls (31 servers to 0), onboarding (6 weeks to 3 business days), tool-text spend ($148,000 to $30,000 a month), time to kill a bad version (unknown to under 5 minutes, drilled monthly). The headline is **the share of calls attributable to a user**, because it's the CISO's question and every other control depends on it.

How do you measure calls you can't see? Reconcile Salesforce and GitHub audit logs against gateway events weekly; any unmatched call is a shadow path. Onboarding time is the adoption metric that keeps builders on side.

**The trap.** Counting registered servers. A server can be registered and still called around the gateway.

**Rubric criteria earned:** three or more baselines and targets; shadow-path reconciliation; an adoption metric.

### Failure Modes

**The question:** what breaks, and what fails open or closed?

**How to reason.** The prompt asks about two outages explicitly. **Okta down**: platform tokens already issued (60-minute lifetime) verify against cached JWKS and keep working; new sessions fail closed. **Audit pipeline down**: the gateway buffers events to local disk for 15 minutes; past that, **write tools fail closed** and reads continue. Then the rest: a token refresh stampede is absorbed by single-flight; quota exhaustion returns `rate_limited` at 90% of a team's share with batch shed first; and a **changed description on a live server** is caught because the gateway serves descriptions from the registry and checks the live hash on connect, quarantining on mismatch.

The rule: writes fail closed and reads degrade. An unaudited write is the incident; a slow read is an inconvenience.

**The trap.** Failing open on audit loss to protect availability. That's the window an attacker would choose.

**Rubric criteria earned:** IdP and audit outages; fail closed versus degrade stated; post-approval description changes.

### Build Order

**The question:** in what order over 26 weeks with 8 engineers?

**How to reason.** Put every call on the path first and tighten it later; teams won't migrate to gain restrictions, they migrate for a faster path. Weeks 1–4: pass-through proxy for the 48 servers, registry with pinned hashes, kill switch (share of calls through the gateway). Weeks 5–9: per-user OAuth for Salesforce, GitHub, Jira, Google and ServiceNow with Vault (shared-account calls). Weeks 10–13: OPA scopes and the Kafka audit trail (100% of events with a policy hash). Weeks 14–17: sandbox tiers and egress allowlists (17 of 17 third-party servers sandboxed). Weeks 18–21: approvals and per-team quotas (Salesforce 429s). Weeks 22–26: tool search and self-serve onboarding (tool-text spend and onboarding days).

**The trap.** Building per-user OAuth before the gateway carries traffic.

**Rubric criteria earned:** traffic before restrictions; a number per phase; 26 weeks for 8 engineers.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| Where authorisation lives | Tool descriptions and system prompts say what's allowed | OPA computes user ∩ agent ∩ tool scopes, default deny, and the downstream token is the user's own |
| What gets approved | The server, by name | A version identified by a canonical schema hash; the registry serves descriptions and a live hash mismatch quarantines |
| Tool-definition tokens | Ignored | $778,000 to $148,000 with caching, to $30,000 with tool search inside the grant, pinned per session |

## 9. Common mistakes

- A shared SDK or library instead of a network path every call must cross.
- A shared service account "for now", or a token cache keyed by agent.
- Forwarding the platform token to downstream servers.
- Mirroring downstream ACLs into the policy engine.
- Re-running tool search every turn, losing the cache.
- Result caches keyed without the user.
- Failing open when the audit pipeline is down.

## 10. Follow-ups an interviewer might ask

- *Walk one call from an agent to Salesforce.* The agent sends an MCP request with a platform token for the user to `POST /mcp/{agent}`. The gateway verifies the JWT against cached JWKS, OPA intersects scopes, Redis checks the team's Salesforce bucket and returns the user's cached access token (refreshing single-flight from Vault if needed), the gateway calls Salesforce as that user, and an audit event goes to Kafka. The agent never holds a downstream secret.
- *A vendor server pushes a new description at 2 am.* The gateway serves descriptions from the registry, so agents don't see it. The live hash check on connect fails and quarantines the server until a new version passes the poisoning suite and is approved.
- *One team's backfill starts eating the Salesforce quota.* Its per-team bucket returns `rate_limited` with `retry_after` at 90% of its share, batch is shed first, and the 60 s user-keyed read cache cuts repeat reads.
- *How fast can you kill a bad server?* `POST /admin/kill/{server}` revokes the version everywhere in under 60 s and invalidates the cached tool lists; the target is under 5 minutes end to end, drilled monthly.
- *Why not let a review model approve new servers?* It drafts the security summary, but a model can be fooled by exactly the poisoned text it reviews. Two humans approve any write tool.
