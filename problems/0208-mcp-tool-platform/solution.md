# Shared MCP Tool Platform: model answer

## 1. Scenario

The user is an agent builder on one of 70 teams who needs a governed tool in days, and the security team who must answer "what did agent X do, for whom" in minutes. The platform is one MCP gateway, one registry and one audit trail that every agent's tool call passes through.

| What | Number | What it forces |
|---|---|---|
| Tool calls | 2.4M a day, 28/s average, 90/s peak | Small fleet, but every millisecond of overhead is paid 2.4M times |
| Overhead budget | p95 40 ms per call | Policy and token lookup must be local and cached |
| Tool definitions | 60 tools x 180 tokens = 10,800 tokens per turn | About $148k a month on Sonnet 5.5 even with caching, before any work is done |
| Shared quota | Salesforce 1M calls a day for the whole company | Admission control per team, not per pod |
| Audit horizon | 400 days, immutable | An append-only event log, not application logs |

**How:**
1. Inventory the 48 servers: owner, version, credential type, whether a shared account is used, and which agents load them.
2. Set baselines: 6 weeks to onboard a tool, 31 servers on shared accounts, 0 percent of calls attributable to a user.
3. Agree targets with the CISO: 100 percent of calls through the gateway, 0 shared accounts, onboarding in 3 business days.
4. Out of scope: building agents, hosting models, and replacing the downstream systems' own permission models.

**Decision.** The platform is a gateway that every call must cross, not a library teams import, because a library can be skipped and a network path cannot.

**Trap.** Starting with the registry UI. A catalog without enforcement on the call path is documentation, and the shadow servers keep running.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Agents (clients) | 140 agents on LangGraph, the Claude Agent SDK and others. Hand over an MCP request with a platform access token for one user | Agents stay thin; none of them holds a downstream secret |
| Gateway | Envoy plus a stateless MCP proxy on the official MCP SDK, one virtual server per agent. Hands over an authenticated, rate-checked call | One path that every call must cross |
| Identity | Okta as IdP, the gateway as OAuth 2.1 resource server, Vault holding per-user downstream tokens. Hands over a short-lived downstream token for this user | The user's own permissions apply downstream |
| Policy | OPA with versioned Rego bundles. Hands over allow, deny, or needs-approval plus the bundle hash | Scope rules live in code the model cannot talk past |
| Registry | Postgres rows per server version: owner, schema hash, scopes, risk tier, data class. Hands over the only tools an agent may see | Approval attaches to a version and a hash, not a vendor |
| Workflow | Temporal for approvals, server onboarding and long-running tool jobs. Hands over a decision or a job result | Waits of minutes to days survive deploys |
| Tool runtime | First-party pods, vendor remotes behind an egress proxy, gVisor for third-party code, Firecracker for code execution. Hands over a typed result | Untrusted code never shares a kernel or a credential |
| Event log | Kafka topic per call event, into ClickHouse and S3 Object Lock, plus per-tool health stats in Redis. Hands over audit rows and live health | Audit and circuit breaking come from one stream |

**The one idea to hold:** the model only chooses which tool to call; identity, scope, quota and audit are decided by the gateway on every call, in code.

## 3. Data Sources

The platform reads five sources, each with its own freshness need.

**How:**
1. **Server manifests**: `tools/list` output plus an owner file from each repo, pulled on every release; 410 tools today.
2. **Identity**: Okta groups by SCIM push, under 60 s; offboarding revokes the user's Vault tokens in the same event.
3. **Downstream permissions**: never copied. The user's own OAuth token makes Salesforce and GitHub enforce their own ACLs.
4. **Quotas**: Salesforce `/limits` and GitHub `X-RateLimit-Remaining`, read every 60 s.
5. **Call events**: the gateway's own stream, 2.4M a day.

**Decision.** Downstream ACLs stay downstream, because a synced copy of 30 permission models is always stale and the user token already carries the truth.

**Trap.** Mirroring Salesforce sharing rules into OPA. The copy drifts within days and the gateway allows what Salesforce would deny.

## 4. Processing

Two pipelines: onboarding a server version, and rolling the call stream into health stats.

**How:**
1. Onboarding runs as a Temporal workflow: canonicalize `tools/list` (sorted keys, normalized whitespace), compute a SHA-256 schema hash, run Semgrep and Trivy on the code.
2. Run the poisoning suite: a canary agent in a sandbox with honeytoken credentials runs 200 tasks against the new descriptions; a judge flags any call that touches a honeytoken or an unlisted host. At 30 versions a week and 8k tokens a run on Sonnet 5.5, that is about $500 a month.
3. Embed each description with a hosted embedding model into pgvector; 410 tools cost under $1.
4. A Flink job rolls the Kafka stream into per-tool error rate, p95 and quota burn every 60 s, written to Redis.

**Decision.** A new version gets a new hash and a new approval, because a description is prompt text and a one-word change can redirect every agent that loads it.

**Trap.** Approving a server by name. The poisoning incident was a minor release of an approved server.

## 5. Agents

Not an agent: the gateway is deterministic code, and we would add one only if tool choice needed reasoning that search cannot do. It does shape what consumer agents see: 10,800 tokens of tool text per turn become 2,160, over 36M turns a month on Sonnet 5.5.

| Lever, in order | Tool-text cost a month | Saving a month |
|---|---|---|
| Start: 60 tools, no caching, $2 per MTok | $778k | |
| Prompt caching, 90 percent reads at $0.20 | $148k | $630k |
| Tool search, 12 tools per session | $30k | $118k |

**How:**
1. Tool search: on session start the gateway embeds the task and returns the top 12 of the agent's allowed tools, plus a `find_tools` meta-tool to load more.
2. Pin the chosen set for the session, so the prompt prefix stays byte-stable and the 90 percent cache rate holds.
3. A review agent drafts the security summary in onboarding; two humans approve any write tool.

**Decision.** Search inside the allowed set, never over all 410 tools, because ranking must not become a way to discover tools the agent was not granted.

**Trap.** Re-running tool search every turn. The tool block changes, the prefix cache misses, and the saving disappears.

## 6. Memory

The platform keeps four kinds of state, each in the store its guarantee needs.

**How:**
1. **Session**: `Mcp-Session-Id` mapped to user, agent, pinned tool versions and tool set, in Redis for 24 h.
2. **Consent and tokens**: refresh tokens per (user, provider) in Vault transit encryption; access tokens cached in Redis until 60 s before expiry.
3. **Idempotency**: write-tool keys `(agent, user, tool, key)` in Postgres for 24 h; a retry returns the stored result.
4. **Approvals**: Temporal workflow state, 30 minute TTL, then the call is denied.

**Decision.** No tool results are stored beyond a 60 s read cache, because the platform is a path for data, not a second copy of 30 systems.

**Trap.** Keying the token cache by agent. Two users of one agent then share a Salesforce identity, which is the shared account again.

## 7. MCP Tool Servers

Servers fall into four hosting tiers by trust.

**How:**
1. **First-party** (22 servers): pods on EKS behind the gateway, Streamable HTTP, a SPIFFE identity each, no internet egress.
2. **Vendor remote** (9): reached through an Envoy egress proxy pinned to the vendor's hosts; the gateway sends the user's downstream token, never the platform token.
3. **Third-party packages** (17): run in gVisor on a dedicated node pool, no cloud metadata endpoint, one egress allowlist each.
4. **Code execution**: Firecracker microVMs, about 125 ms boot, a warm pool of 40 for the 11 sandboxed calls a second at peak (12 percent of traffic) at 2 s each.
5. Agents pin `server@^1.4`; a new minor version serves 5 percent of sessions for 48 h and promotes only if its error rate and p95 match the old one.
6. The 6 mTLS-only legacy services get a gateway-signed 60 s JWT naming the user.

**Decision.** Sandbox by provenance, because a third-party package is unreviewed code with network access until proven otherwise.

**Trap.** Forwarding the agent's platform token to the server. The MCP spec forbids token passthrough, and a malicious server can replay it.

## 8. Endpoints

The gateway exposes MCP for agents and REST for people and pipelines.

| Stage | p50 | p95 |
|---|---|---|
| Envoy TLS and route | 2 ms | 4 ms |
| JWT verify, cached JWKS | 1 ms | 1 ms |
| OPA decision, local bundle | 2 ms | 4 ms |
| Rate limit and token lookup, Redis | 3 ms | 8 ms |
| Argument schema validation | 1 ms | 2 ms |
| Proxy hop and result scan | 8 ms | 15 ms |
| Audit produce, async | 1 ms | 3 ms |
| **Platform overhead** | **18 ms** | **37 ms** |

**How:**
1. `POST /mcp/{agent}` (Streamable HTTP) aggregates the agent's allowed servers into one virtual server with namespaced names such as `jira.create_issue`.
2. `/.well-known/oauth-protected-resource` and resource-indicator tokens (RFC 8707) bound to the gateway's audience; `/connect/{provider}` runs the one-time consent.
3. `/registry/v1/servers`, `/audit/v1/query` and `POST /admin/kill/{server}`, which revokes a version everywhere in under 60 s.
4. Long jobs return a job id from Temporal and stream progress.
5. Run 6 gateway pods across 3 zones; each handles about 500 calls a second, so the fleet is sized for failure, not load.

**Decision.** One virtual server per agent, because the agent then sees exactly its grant and nothing it would need to be told to ignore.

**Trap.** Handing agents a direct URL per server "for latency". Every direct URL is a path with no policy and no audit.

## 9. Caching

Caching keeps the 40 ms budget and the shared quotas intact.

**How:**
1. Downstream access tokens in Redis per (user, provider), refreshed single-flight when 20 calls hit a 401 at once.
2. OPA bundles in memory, refreshed every 30 s; JWKS for 10 minutes.
3. The tool list per (agent, registry version), invalidated by the kill switch.
4. Read-only, idempotent tool results for 60 s keyed by (user, tool, version, args hash); this cut Salesforce calls 28 percent in the pilot.

**Decision.** The user is part of every result cache key, because two users can see different rows for the same query.

**Trap.** Caching results by (tool, args) alone. The first caller's permissions then serve everyone.

## 10. Data Stores

Kafka holds every call event; every other store is a projection sized from 2.4M events a day.

| Store | Holds | Size |
|---|---|---|
| Postgres (RDS) | Registry, idempotency keys, grants | Under 20 GB |
| Redis (ElastiCache) | Sessions, token cache, rate buckets, health stats | 8 GB |
| Vault | Refresh tokens, transit keys | 5,000 users x 6 providers |
| Kafka (MSK) | Call events, 7-day retention | 2.9 GB a day at 1.2 KB an event |
| ClickHouse | Queryable audit, 400 days | About 120 GB compressed |
| S3 Object Lock | Raw audit copy, compliance mode | 1.2 TB, about $30 a month (assumed) |

**How:**
1. Write each audit event with user, agent, tool, version, schema hash, policy bundle hash, decision, latency and an args hash; argument values with PII go through the redaction vault.
2. Chain each hour's batch with a SHA-256 over the previous hash and land it in Object Lock.
3. No GPUs: embeddings and the judge are API calls.
4. Monthly infra cost (assumed list prices): about $23k, from $7k metal sandbox nodes, $4k Datadog, $3k ClickHouse Cloud, $2.5k MSK, $1.5k each for Temporal Cloud and Vault, and $3.5k for EKS, RDS and Redis, against the $45k budget.

**Decision.** Kafka is the system of record for calls and every store is a projection, so a new audit question is a new consumer, not a migration.

**Trap.** Writing audit rows from each tool server. Fifty implementations give fifty schemas and gaps.

## 11. Output

The platform returns three shapes to agents and one to people.

**How:**
1. **Results**: capped at 25k tokens, larger lists paginated with a cursor; content from external systems wrapped as untrusted data.
2. **Errors** as MCP `isError` content with a machine code: `missing_scope`, `needs_approval` (with an approval id), `rate_limited` (with `retry_after`), `version_killed`.
3. **Job handles** for calls over 30 s.
4. **Weekly access report** per team: tools used, scopes granted but unused for 30 days, denials.

**Decision.** Denials are typed results the agent can explain to the user, not protocol errors, because "you need Jira write access" is useful and "-32603" is not.

**Trap.** Returning denials as prose. Agents then retry them as transient failures and burn quota.

## 12. Guardrails

Every limit that protects money, permissions or privacy is enforced in the gateway, never in a prompt or a tool description.

**How:**
1. Effective permission is user scopes intersected with agent grant intersected with the tool's required scopes, in OPA; default deny. The 6 legacy services trust the gateway's JWT, so OPA also checks resource ownership there (project id against the user's groups).
2. Risk tier 3 tools (repo delete, external email, opportunity stage) pause in a Temporal approval sent to Slack, 30 minute TTL.
3. Per-team token buckets on shared quotas: the rest of the company uses about 600k Salesforce calls a day, so agents get 300k, split by team, with interactive calls ahead of batch.
4. Validate arguments against the registered JSON Schema; flag tool calls whose arguments copy spans from untrusted results.

**Decision.** The downstream token is the user's, so even a policy bug cannot exceed what the user could do by hand.

**Trap.** Writing "never delete repositories" in the tool description. A prompt is a suggestion; a deny rule is a control.

## 13. Key Impact

Five numbers tell the CISO and the agent teams whether the platform is doing its job.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Calls through the gateway | Unknown | 100 percent | Downstream audit logs joined to gateway events |
| Calls on shared accounts | 31 servers | 0 | Credential type per call event |
| Tool onboarding time | 6 weeks | 3 business days | Temporal workflow start to approval |
| Tool-text token spend | $148k a month | $30k | Ledger of tool-block tokens per turn |
| Time to kill a bad version | Unknown | Under 5 minutes | Kill drill, run monthly |

**How:**
1. Reconcile Salesforce and GitHub audit logs against gateway events weekly; any unmatched call is a shadow path.
2. Publish per-team cost and denial dashboards in Datadog.

**Decision.** The headline is the share of calls that are attributable to a user, because it is the CISO's question and every other control depends on it.

**Trap.** Counting registered servers. A server can be registered and still be called around the gateway.

## 14. Failure Modes

Each failure below has a detector and a chosen direction: fail closed or degrade.

**How:**
1. **Okta outage**: issued platform tokens (60 minute lifetime) verify against cached JWKS and keep working; new sessions fail closed.
2. **Audit pipeline down**: the gateway buffers events to local disk for 15 minutes; past that, write tools fail closed and reads continue.
3. **Token refresh stampede**: single-flight per (user, provider) makes 20 waiting calls cost one refresh.
4. **Quota exhaustion**: buckets return `rate_limited` at 90 percent of the share; batch traffic sheds first.
5. **Changed description on a live server**: the gateway serves descriptions from the registry and checks the live hash on connect; a mismatch quarantines the server.

**Decision.** Writes fail closed and reads degrade, because an unaudited write is the incident and a slow read is an inconvenience.

**Trap.** Failing open on audit loss "to protect availability". That outage window is the one an attacker would choose.

## 15. Build Order

Six phases over 26 weeks for 8 engineers, each ending with a number.

**How:**
1. **Weeks 1-4**: gateway as a pass-through proxy for the 48 servers, registry with pinned hashes, kill switch. Measure: share of calls through the gateway.
2. **Weeks 5-9**: per-user OAuth for Salesforce, GitHub, Jira, Google and ServiceNow; Vault; shared accounts removed. Measure: shared-account calls.
3. **Weeks 10-13**: OPA scopes and the Kafka audit trail. Measure: events with a policy hash, 100 percent.
4. **Weeks 14-17**: sandbox tiers and egress allowlists. Measure: third-party servers sandboxed, 17 of 17.
5. **Weeks 18-21**: approvals and per-team quotas. Measure: Salesforce 429s.
6. **Weeks 22-26**: tool search and self-serve onboarding. Measure: tool-text spend and onboarding days.

**Decision.** Put every call on the path first and tighten it later, because enforcement on a path nobody uses protects nothing.

**Trap.** Building per-user OAuth before the gateway carries traffic. Teams will not migrate to gain restrictions; they migrate for a faster path.
