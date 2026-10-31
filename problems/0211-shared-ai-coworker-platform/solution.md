# Shared AI Coworker Platform: model answer

## 1. Scenario

The users are 25 team leads who want a coworker in two weeks, and 6,000 employees who ask those coworkers for help in Slack, email and tickets. The platform supplies the runtime, memory, skills, identity and approvals once, so a coworker is a configuration plus a few team-specific skills.

| What | Number | What it forces |
|---|---|---|
| Tasks | 30,000 a day, 0.35/s average, about 1.05/s peak | Small compute; the hard part is state and permissions |
| Model calls | 3.6M a month at 4 per task | $79k a month on Sonnet 5.5 alone; $17k with a Haiku share, caching and trimming |
| Long waits | 20 percent wait over an hour, up to 5 days | A durable workflow per task, not a chat loop |
| Coworkers | 25 now, 80 in a year | Building one must cost days, not 10 weeks |
| Budget | $80k a month | Per-team budgets enforced at admission |

**How:**
1. Inventory the 3 existing coworkers: memory stores, identities, tools, and where their facts disagree.
2. Pick one success metric per coworker with its team, such as invoices processed without rework for AP.
3. Baselines: 10 weeks to build, 0 shared skills, 3 conflicting copies of the travel policy.
4. Out of scope: replacing ServiceNow or the HR system, and fully autonomous payments.

**Decision.** A coworker is a manifest (charter, channels, skills, memory scopes, approval policy, budget) on one runtime, because 80 bespoke builds would mean 80 memory stores and 80 permission models.

**Trap.** Starting with the marketplace UI. Skills without a shared identity and memory model just copy the 3 inconsistent coworkers faster.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Channel adapters | Slack Events API, Microsoft Graph mail webhooks, ServiceNow and Jira webhooks. Hand over a normalized message with a verified sender and a task id | One task can cross three channels |
| Intake and admission | Router to the right coworker, per-team token budgets and concurrency. Hands over an admitted task | One team cannot spend everyone's budget |
| Task workflow | Temporal workflow per task, holding state through days of waiting. Hands over steps and approval requests | Survives deploys and 5-day waits |
| Coworker runtime | LangGraph agent loading the manifest and pinned skills, models via LiteLLM. Hands over tool calls and replies | Same loop for every coworker |
| Skills registry | Versioned skill bundles with tests, scopes and owners. Hands over the exact skill versions a coworker may load | Reuse with accountability |
| Memory service | Scoped facts and preferences in Postgres and pgvector, plus ACL-aware document retrieval. Hands over facts with provenance | Shared knowledge without shared secrets |
| Policy and identity | OPA plus on-behalf-of OAuth tokens. Hands over allow, deny or needs-approval | Permissions in code |
| Event log | Kafka of every task event into ClickHouse and Langfuse. Hands over metrics, cost and audit | Proving value and debugging |

**The one idea to hold:** the model writes and plans; the workflow, the memory scopes and the policy engine decide what is remembered, who is acted for, and what needs a human.

## 3. Data Sources

Four sources feed the coworkers; each has an owner and its own freshness.

**How:**
1. **Documents**: 400,000 in SharePoint and Confluence with ACLs synced every 15 minutes; about 2M chunks.
2. **Systems of record**: ServiceNow, Workday, NetSuite, Salesforce, read live through skills, never indexed.
3. **Conversations**: Slack threads, mail threads and ticket comments tied to a task id.
4. **Identity**: Entra ID groups by SCIM, including department, manager and EU residency.

**Decision.** Policies come from the owning document, not from conversations, because the travel policy conflict came from coworkers learning policy out of emails.

**Trap.** Indexing all Slack history as knowledge. It mixes opinions, outdated answers and private channels into the firm's "facts".

## 4. Processing

Processing turns documents into searchable chunks and conversations into tasks and candidate memories.

**How:**
1. Parse documents with Unstructured, chunk by heading at about 400 tokens, embed into pgvector with the source ACL on each chunk.
2. Normalize each inbound message to (sender, channel, thread, task id, attachments); attachments are scanned and stored in S3.
3. Route to a coworker by explicit mention or channel binding first, then a small-model classifier for the rest.
4. Extract candidate memories after each task: Haiku 5.5 proposes facts with a source and scope; the memory service validates them.

**Decision.** Candidate memories are proposals checked by rules, because a model deciding on its own what the firm believes is how a phishing email becomes policy.

**Trap.** Embedding every chat turn into one vector store "as memory". Retrieval then returns stale guesses with the same weight as the handbook.

## 5. Agents

Each coworker is a LangGraph loop over its manifest; the platform owns routing and model choice, and three levers set the bill.

| Lever, in order | Model cost a month | Saving a month |
|---|---|---|
| Start: Sonnet 5.5 on all 3.6M calls, 8k in, 600 out, no caching | $79.2k | |
| Model mix: 60 percent of calls on Haiku 5.5 | $34.1k | $45.1k |
| Prompt caching of the 5k-token stable prefix (Haiku cache reads assumed at $0.01) | $20.1k | $14.0k |
| Retrieval trimming: 5 chunks instead of 8 on Sonnet calls | $16.6k | $3.5k |

**How:**
1. A coworker loads only its pinned skills, so the prompt holds about 8k tokens, 5k of them a stable cached prefix.
2. Classification, extraction and summaries (60 percent of calls) go to Haiku 5.5; planning and drafting go to Sonnet 5.5.
3. That is about $0.018 of model cost per task.
4. A step limit of 15 tool calls per task; past it, the task goes to the team's human queue.
5. Handoffs between coworkers go through the workflow with a summary, never by sharing scratchpads.

**Decision.** Model tier is chosen by the step type in code, because leaving it to each team means every team picks the biggest model.

**Trap.** One giant super-coworker that does everything. Its prompt grows past every cache and its permissions become the union of all teams.

## 6. Memory

Four scopes, each with a write rule.

| Scope | Holds | Who may write |
|---|---|---|
| Firm | Facts from owned documents (policies, office addresses) | Document owners; coworkers only cite |
| Team | Team runbooks and decisions | Coworkers propose, a team curator approves |
| User | Preferences ("send summaries Mondays") | The user, directly or by confirming |
| Coworker episodic | Past tasks, compacted | The workflow, 180 days |

**How:**
1. Every fact row has scope, owner, source link, created by, expiry and a version; reads filter by the caller's tenant, team and user in the SQL query.
2. Conflicting facts at the same scope keep both and flag the curator.
3. GDPR erasure deletes a user's preferences and episodic rows and redacts their name from team facts.

**Decision.** Scope and tenant are in the primary key and the query, never in the prompt, because a prompt edit must not be able to widen a read.

**Trap.** Letting any coworker write firm-wide memory. One wrong email answer then reaches all 80 coworkers.

## 7. MCP Tool Servers

Skills reach systems through MCP servers run by the owning teams.

**How:**
1. A skill bundle is a manifest: name, semver, instructions, MCP tools with required scopes, data class, an eval suite of at least 30 cases, and an owner.
2. Publishing runs the eval suite and a security review in a Temporal workflow; write skills need two reviewers.
3. Coworkers pin `ap-invoice-match@^2.1`; dependencies are resolved at publish time and locked.
4. MCP servers for Workday and NetSuite are owned by HR and finance, who decide which scopes exist.

**Decision.** Usage and failures are metered per skill version, so the owner sees adoption and is paged for their own breakage.

**Trap.** Copying a skill into your coworker to tweak it. Forks never get the upstream fix, and 80 coworkers drift.

## 8. Endpoints

Three channel adapters and a small builder API, all resolving to one task id.

| Stage, simple Slack answer | p50 | p95 |
|---|---|---|
| Event to ack | 0.3 s | 1 s |
| Route and admit | 0.3 s | 0.8 s |
| Memory and retrieval | 0.6 s | 1.5 s |
| Model plan, Haiku or Sonnet 5.5 | 2 s | 5 s |
| One tool call | 1 s | 4 s |
| Model reply, streamed | 3 s | 6 s |
| **Total** | **about 7 s** | **about 18 s** |

**How:**
1. Slack: ack the event within 3 s from the adapter, then reply in thread; approvals use Block Kit buttons signed with the task id.
2. Email: Microsoft Graph change notifications; replies thread by `In-Reply-To`; approvals by signed one-time links bound to the approver.
3. Tickets: webhooks on comment and state change; an approval is a state transition by an authorized user.
4. `POST /v1/coworkers`, `POST /v1/skills/{name}/versions`, `GET /v1/tasks/{id}` for builders.
5. Admission: per-team monthly budgets and 50 concurrent tasks each; Slack interactive tasks run ahead of email and batch.

**Decision.** Every channel resolves to the same task id and workflow, so an approval clicked in Slack resumes a task begun by email.

**Trap.** Treating each channel message as a new conversation. The task forks and two coworkers answer the same invoice.

## 9. Caching

Caching keeps prompts cheap and the 20 second answer fast, without crossing a permission boundary.

**How:**
1. Prompt-cache the charter, skill instructions and tool schemas, about 5k of 8k tokens, for 90 percent of calls.
2. Cache retrieval results per (query hash, user ACL hash) for 10 minutes.
3. Cache on-behalf-of tokens per (user, provider) until 60 s before expiry.
4. Cache firm-scope fact lookups for 5 minutes, invalidated on document change.

**Decision.** Any cache that holds user-visible content keys on the user's ACL, because two users may see different documents for the same question.

**Trap.** A semantic answer cache shared across teams. An HR answer is then served to sales.

## 10. Data Stores

Postgres holds facts and vectors together; Temporal holds every open task.

| Store | Holds | Size |
|---|---|---|
| Postgres with pgvector | Memory facts, skills registry, coworker manifests, 2M chunk vectors | About 16 GB of vectors with the HNSW index, 50 GB total |
| Temporal Cloud | Task workflow state, about 15,000 open at any time | 900,000 workflows a month |
| Redis | Sessions, tokens, rate buckets | 4 GB |
| Kafka, ClickHouse, Langfuse | Task events, traces, cost | About 10 GB a day of traces |
| S3 | Attachments, 1 year | About 2 TB |

**How:**
1. EU employees' episodic memory and attachments live in the EU region; firm facts are global.
2. Monthly cost: models $16.6k from the lever table, plus assumed infra prices of Temporal $3k, EKS $5k, Postgres $3k, Kafka $2.5k, ClickHouse and Langfuse $3k, Datadog $4k, Redis and S3 $1k: about $38k against $80k, so the 80-coworker year fits.
3. No GPUs: models and embeddings are API calls.

**Decision.** One Postgres for facts and vectors, because a fact and its embedding must change in one transaction.

**Trap.** A separate vector database for memory. The fact is deleted and its vector is still retrieved.

## 11. Output

Every output is either a cited reply, a receipt from a system of record, or a readable approval request.

**How:**
1. **Replies** cite sources (document link or fact id), in the channel the user used.
2. **Actions** return receipts from the system of record (ServiceNow number, NetSuite bill id), never model prose.
3. **Approval requests** state the action, amount, recipient and why, with approve, reject and edit.
4. **Weekly coworker report** for each team: tasks, hours saved, overrides, cost.

**Decision.** A receipt is built from the tool result, because "I paid the invoice" from the model is a claim, not a record.

**Trap.** Approval requests that say "approve this action?". People approve what they cannot read.

## 12. Guardrails

Limits that protect money, permissions and privacy live in OPA and the workflow, never in a prompt.

**How:**
1. Effective permission is requester scopes intersected with coworker grant intersected with skill scopes; coworkers act on behalf of the requester, and use their own principal only for scheduled duties with a narrower grant.
2. Approval policy in code: payments over $1,000 go to the budget owner, over $10,000 need two approvers, external email needs the requester, HR changes need HR.
3. Approvals expire in 48 h and escalate to the approver's manager.
4. Inbound external email is untrusted data: it cannot write memory or trigger a write tool without a human.

**Decision.** The coworker can never exceed the person who asked, so the worst case of a bad plan is what that person could have done by hand.

**Trap.** A coworker service account with broad finance access "to keep it simple". Every employee then has finance access through the chat box.

## 13. Key Impact

Five numbers show whether coworkers save time, and whether the platform makes them cheap to build.

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Time to build a coworker | 10 weeks | 2 weeks | Manifest created to first production task |
| Hours saved | 0 | 9,000 a month | Completed tasks times the per-task-type time study minutes |
| Human override rate | Unknown | Under 10 percent | Edits and rejections of coworker actions |
| Skill reuse | 0 | 60 percent of skills per coworker from the marketplace | Registry |
| Cost per completed task | Unknown | Under $0.05 all in, from $38k over 900,000 tasks | Ledger joined to outcomes |

**How:**
1. Run a time study of 50 tasks per task type before launch; that sets the minutes saved per task.
2. Count only tasks completed without rework.

**Decision.** Headline hours saved on completed tasks, because tasks attempted include the ones a human had to redo.

**Trap.** Reporting messages handled. Volume says nothing about time saved.

## 14. Failure Modes

Every failure below degrades to waiting, never to acting.

**How:**
1. **Memory poisoning**: a wrong fact spreads; provenance lets a curator find and revoke every fact from one source in one query.
2. **Skill regression**: a new version fails its eval in canary on 5 percent of tasks and rolls back automatically.
3. **Approver unavailable**: the 48 h TTL escalates; the task never auto-approves.
4. **Budget exhaustion**: a team at 100 percent drops to small-model-only and queues non-urgent tasks.
5. **Channel outage**: tasks wait in Temporal and resume when Slack or Graph recovers.

**Decision.** Waiting is always safe and acting is not, so every degraded path pauses instead of guessing.

**Trap.** Auto-approving on timeout to keep tasks moving. That turns every slow approver into a hole in the payment controls.

## 15. Build Order

Five phases over 26 weeks for 10 engineers, migrating the existing coworkers first.

**How:**
1. **Weeks 1-4**: Temporal task workflow, Slack adapter, OPA, on-behalf-of identity. Measure: AP coworker migrated, tasks surviving a deploy.
2. **Weeks 5-8**: memory service with scopes and provenance. Measure: travel policy conflicts, 0.
3. **Weeks 9-13**: skills registry with tests and pinning; the 3 existing coworkers rebuilt on it. Measure: share of their skills shared.
4. **Weeks 14-18**: email and ticket adapters, cross-channel approvals. Measure: approval median time.
5. **Weeks 19-26**: self-serve coworker builder and team budgets; 10 new coworkers. Measure: build time per coworker.

**Decision.** Migrate the 3 existing coworkers before building new ones, because they prove the platform on real traffic and remove 3 memory stores.

**Trap.** Launching 25 coworkers at once. Each one's problems look like platform problems and nobody can tell which is which.
