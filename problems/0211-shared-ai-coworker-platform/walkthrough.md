## 1. What the problem is really asking

The compute is small here. 30,000 tasks a day is about one task a second at peak. What's hard is everything *around* the model: **state that lasts days, memory that many coworkers share, and permissions that never widen**. The prompt gives you the failure that proves it: three teams built their own coworkers, each with its own memory store, and two of them now disagree about the travel policy because they learned it from different emails.

So this is a **platform** problem. The question is how to make the 4th through 80th coworker cheap to build (two weeks instead of ten) while making them *safer* than the three bespoke ones, not just faster to copy.

Three decisions carry the design:

- **A coworker is configuration on one runtime.** A manifest names its charter, channels, pinned skills, memory scopes, approval policy and budget. 80 bespoke builds would mean 80 memory stores and 80 permission models.
- **Memory has scopes with write rules.** Firm facts come from owned documents and coworkers can only cite them. A model can *propose* a memory, but rules decide what's stored. That's how one bad email can't rewrite what every coworker believes.
- **Every action runs as the requester, through a durable workflow.** Permissions are the intersection of the requester's, the coworker's and the skill's. Approvals are workflow signals, so a Slack click resumes a task that started in email four days earlier.

The model answer's one idea: the model writes and plans; the workflow, the memory scopes and the policy engine decide what is remembered, who is acted for, and what needs a human.

## 2. The numbers that drive the design

**Task rate.** 30,000 tasks / 86,400 s = **0.35 tasks/s average**. Monday-morning peak is 3 times that, about **1.05/s**. That's tiny. Say so out loud: you're not designing for throughput, you're designing for state and permissions.

**Model calls.** About 4 model calls per task: 30,000 × 4 × 30 days = **3.6M calls a month**. Tasks a month: 30,000 × 30 = **900,000**.

**The naive bill.** If every call runs on Sonnet 5.5 with 8k input and 600 output tokens and no caching:

- Per call: 8,000 × $2/M + 600 × $10/M = $0.016 + $0.006 = **$0.022**.
- Per month: 3.6M × $0.022 = **$79.2k**. That's essentially the whole $80k budget on models alone, before any infrastructure.

**Applying the levers in order** (reveal the model answer for its table):

| Lever | How the number comes out | Monthly cost |
|---|---|---|
| Model mix: 60 percent of calls on Haiku 5.5 | Haiku call = 8,000 × $0.10/M + 600 × $0.50/M = $0.0011. 1.44M Sonnet calls × $0.022 + 2.16M Haiku calls × $0.0011 | **$34.1k** (saves $45.1k) |
| Prompt caching of the 5k stable prefix | Sonnet saves 5k × ($2 − $0.20)/M per call; Haiku saves 5k × ($0.10 − $0.01)/M, with Haiku's $0.01 cache read **assumed** | **$20.1k** (saves $14.0k) |
| Retrieval trimming: 5 chunks instead of 8 on Sonnet calls | 3 fewer chunks × about 400 tokens × $2/M × 1.44M calls | **$16.6k** (saves $3.5k) |

That's about **$0.018 of model cost per task** ($16.6k / 900,000).

**Latency for a simple Slack answer.** The p95 budget: ack 1 s + route 0.8 s + retrieval 1.5 s + plan 5 s + one tool call 4 s + streamed reply 6 s ≈ **18 s**, under the 20 s target. The p50 is about 7 s. The Slack ack is a separate deadline: 3 s, met in under 1 s by the adapter.

**Storage.** 400,000 documents chunked at about 400 tokens give about **2M chunks**, about 16 GB of vectors with the HNSW index. Temporal handles 900,000 workflows a month, about 15,000 open at once because 20 percent of tasks wait over an hour.

**Total cost.** Models $16.6k plus assumed infra (Temporal $3k, EKS $5k, Postgres $3k, Kafka $2.5k, ClickHouse and Langfuse $3k, Datadog $4k, Redis and S3 $1k) ≈ **$38k** against $80k, which leaves room to grow from 25 to 80 coworkers. All in, that's under $0.05 per completed task.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–5 | Read the prompt. Write 1.05/s peak, 3.6M calls, $79.2k naive. Note the travel-policy conflict as your memory requirement. |
| 5–12 | **Pillar A.** Two users, coworker-as-manifest, the eight layers. |
| 12–32 | **Pillar B.** Sources and where policy comes from, memory proposals, the cost levers, the four memory scopes, the skill manifest. Memory and skills are the heart of this problem. |
| 32–44 | **Pillar C.** One task id across channels, the latency table, ACL-keyed caches, stores and the $38k total. |
| 44–56 | **Pillar D.** On-behalf-of identity, approval thresholds in code, hours-saved measurement, failure modes, the migration-first plan. |
| 56–60 | Check every money or permission limit you named lives in OPA or the workflow. |

## 4. Pillar A: Frame

### Scenario

**The question:** who uses the platform, what must it make cheap, and which numbers shape it?

Two users, and the rubric wants both: **25 team leads** who build coworkers, and **6,000 employees** who use them in Slack, email and tickets. The platform supplies runtime, memory, skills, identity and approvals once, so a coworker is a manifest plus a few team-specific skills.

How to reason to that: the prompt's numbers say compute is small (1.05/s). What it does say is "10 weeks each," "three memory stores," "80 within a year." The thing to make cheap is *building a coworker*, so set a measurable target: 10 weeks down to 2.

Baselines: 10 weeks to build, 0 shared skills, 3 conflicting copies of the travel policy. Out of scope: replacing ServiceNow or the HR system, and fully autonomous payments.

**The trap:** starting with the marketplace UI. Skills without a shared identity and memory model just copy the three inconsistent coworkers faster.

**Rubric:** both users (1.1), peak tasks and model calls per second (1.2), coworker as configuration (1.3), and a build-time target (1.4).

### Single View

**The question:** what are the layers from a message to an action in a system of record?

Eight layers: Channel adapters → Intake and admission → Task workflow (Temporal) → Coworker runtime (LangGraph via LiteLLM) → Skills registry → Memory service (Postgres + pgvector) → Policy and identity (OPA + on-behalf-of OAuth) → Event log.

The reasoning for each boundary:

- **Adapters normalize three channels into one task with one id**, because a task can move from email to Slack to a ticket.
- **A durable workflow per task**, because a chat loop dies on a deploy and tasks wait up to 5 days.
- **Skills and memory as separate layers**, so they can be shared with their own rules instead of baked into each coworker.
- **Policy and identity on the action path**, so every tool call is checked, not just the first.

**The trap:** drawing a chatbot with tools. It has nowhere to keep a 4-day wait and nowhere to enforce scopes.

**Rubric:** one task id across channels (2.1), a durable workflow (2.2), skills and memory as separate layers (2.3), and policy and identity on the action path (2.4).

## 5. Pillar B: Build the core

### Data Sources

**The question:** where does firm knowledge come from, and what's read live instead?

Four sources: 400,000 documents in SharePoint and Confluence with **ACLs synced every 15 minutes** onto each chunk; systems of record (ServiceNow, Workday, NetSuite, Salesforce) **read live through skills, never indexed**; conversations tied to a task id; and identity from Entra ID by SCIM, including department, manager and EU residency.

The decision that earns the marks: **policies come from the owning document, not from conversations.** That's the direct fix for the travel-policy conflict. The alternative of indexing everything, including Slack, mixes opinions, outdated answers and private channels into the firm's "facts."

Why read systems of record live: an indexed invoice status is stale the moment it's written, and indexing Workday copies HR data into a store with different access rules.

**The trap:** indexing all Slack history as knowledge.

**Rubric:** ACLs on every chunk (3.1), live reads of systems of record (3.2), and policy from owned documents (3.3).

### Processing

**The question:** how are documents, messages and new memories processed?

- Parse documents with Unstructured, **chunk by heading at about 400 tokens**, and embed into pgvector with the source ACL on each chunk.
- Normalize each inbound message to (sender, channel, thread, task id, attachments).
- **Route by explicit mention or channel binding first**, then a small-model classifier for the rest. A bound channel is deterministic and free; a classifier is only for the ambiguous remainder.
- After each task, Haiku 5.5 proposes candidate memories with a source and scope, and the memory service **validates them by rules**.

The reasoning for proposals rather than direct writes: a model deciding on its own what the firm believes is how a phishing email becomes policy.

**The trap:** embedding every chat turn into one vector store "as memory." Retrieval then returns stale guesses with the same weight as the handbook.

**Rubric:** explicit binding before a classifier (4.1), memories as validated proposals (4.2), and chunk size plus embedding store (4.3).

### Agents

**The question:** how does a coworker run, which models, and what does it cost?

Each coworker is a LangGraph loop over its manifest, loading only its pinned skills, so its prompt is about 8k tokens with a 5k cached prefix. Classification, extraction and summaries (60 percent of calls) go to Haiku 5.5; planning and drafting go to Sonnet 5.5. That gives the lever table in section 2, ending at $16.6k a month.

Two bounds matter. A **step limit of 15 tool calls per task**; past it, the task goes to the team's human queue. And **handoffs between coworkers go through the workflow with a summary**, never by sharing scratchpads (problem tenant-isolated-memory is related).

The decision: model tier is chosen **by step type in code**, not per team. If teams pick, every team picks the biggest model.

**The trap:** one giant super-coworker. Its prompt grows past every cache, and its permissions become the union of all teams.

**Rubric:** levers in order with dollar savings (5.1), model tier by step type in code (5.2), a tool-call cap with human handoff (5.3), and handoff through the workflow with a summary (5.4).

### Memory

**The question:** what are the scopes, and who may write each one?

| Scope | Who may write |
|---|---|
| Firm | Document owners only; coworkers cite |
| Team | Coworkers propose, a team curator approves |
| User | The user, directly or by confirming |
| Coworker episodic | The workflow, kept 180 days |

Every fact row carries scope, owner, source link, created-by, expiry and version. Conflicting facts at the same scope are both kept and the curator is flagged. GDPR erasure deletes a user's preferences and episodic rows and redacts their name from team facts.

The decision: **scope and tenant are in the primary key and the SQL query, never in the prompt**, so no prompt edit can widen a read.

**The trap:** letting any coworker write firm-wide memory. One wrong email answer then reaches all 80 coworkers.

**Rubric:** four scopes (6.1), a write rule per scope with no direct firm writes (6.2), provenance on each fact (6.3), and scope filtered in the query (6.4).

### MCP Tool Servers

**The question:** what's a skill, and how is it published, pinned and owned?

A skill is a **manifest**: name, semver, instructions, MCP tools with required scopes, data class, an eval suite of at least 30 cases, and an owner. Publishing runs the eval suite and a security review in a Temporal workflow; skills that write need two reviewers. Coworkers pin versions like `ap-invoice-match@^2.1`, with dependencies resolved and locked at publish time (problem skill-dependency-resolver). MCP servers for Workday and NetSuite are owned by HR and finance, who decide which scopes exist.

This answers "who is paid or blamed when it breaks": usage and failures are **metered per skill version**, so the owner sees adoption and gets paged for their own breakage.

**The trap:** copying a skill to tweak it. Forks never get the upstream fix, and 80 coworkers drift.

**Rubric:** a manifest with version, tools, scopes, tests and owner (7.1), a passing eval and review before publishing (7.2), and pinned versions with per-version metering (7.3).

## 6. Pillar C: Serve and store

### Endpoints

**The question:** how does each channel connect, and how fast is a simple answer?

- **Slack:** ack within 3 s from the adapter, reply in thread. Approvals are Block Kit buttons signed with the task id.
- **Email:** Microsoft Graph change notifications, replies threaded by `In-Reply-To`, approvals by signed one-time links bound to the approver.
- **Tickets:** webhooks on comment and state change; an approval is a state transition by an authorized user.
- **Builders:** create coworkers, publish skill versions, read task state.
- **Admission:** per-team monthly budgets and 50 concurrent tasks each, with Slack interactive tasks ahead of email and batch.

Then the latency table: about 7 s p50 and 18 s p95 (section 2).

The decision that answers the prompt's hardest question: **every channel resolves to the same task id and workflow**, so an approval clicked in Slack is a signal to the same Temporal workflow that started from email.

**The trap:** treating each channel message as a new conversation. The task forks, and two coworkers answer the same invoice.

**Rubric:** Slack ack in 3 s with async reply (8.1), cross-channel approval (8.2), a stage budget under 20 s (8.3), and per-team budgets and concurrency at admission (8.4).

### Caching

**The question:** what's cached, and what keeps caches from leaking across permissions?

Prompt-cache the charter, skill instructions and tool schemas (about 5k of 8k tokens). Cache retrieval results per (query hash, **user ACL hash**) for 10 minutes. Cache on-behalf-of tokens per (user, provider) until 60 s before expiry. Cache firm-scope fact lookups for 5 minutes, invalidated on document change.

The reasoning: two users can see different documents for the same question. Any cache holding user-visible content must key on the ACL, or it becomes a permission bypass.

**The trap:** a semantic answer cache shared across teams. An HR answer is then served to sales.

**Rubric:** caching the stable prefix (9.1), ACL in the content cache key (9.2), and OBO tokens refreshed before expiry (9.3).

### Data Stores

**The question:** where do facts, vectors and tasks live, and what does it cost?

Postgres with pgvector holds memory facts, the skills registry, manifests and the 2M chunk vectors (about 16 GB with HNSW, 50 GB total). Temporal Cloud holds about 15,000 open workflows. Redis holds sessions, tokens and rate buckets. Kafka, ClickHouse and Langfuse hold about 10 GB a day of traces. S3 holds attachments for a year.

Three points earn marks:

- **One Postgres for facts and vectors**, so a fact and its embedding change in one transaction. With a separate vector database, a deleted fact's vector can still be retrieved.
- **EU employees' episodic memory and attachments stay in the EU region**; firm facts are global.
- **The cost total** of about $38k, with every non-model price labeled assumed. No GPUs, since models and embeddings are API calls.

**The trap:** a separate vector database for memory.

**Rubric:** vector sizing from chunks (10.1), fact and embedding consistent in one transaction (10.2), EU personal memory in the EU (10.3), and a total under $80k with assumed labels (10.4).

### Output

**The question:** what does a user or approver receive?

Replies cite a document link or fact id. Actions return **receipts from the system of record**, such as a ServiceNow number or NetSuite bill id, never model prose. Approval requests state the action, amount, recipient and reason, with approve, reject and edit. Each team gets a weekly report of tasks, hours saved, overrides and cost.

The reasoning: "I paid the invoice" from the model is a claim, not a record.

**The trap:** approval requests that say "approve this action?" People approve what they can't read.

**Rubric:** citations (11.1), receipts from the system of record (11.2), and approval requests with action, amount, recipient and reason (11.3).

## 7. Pillar D: Run it safely

### Guardrails

**The question:** whose identity does a coworker use, and what needs a human?

**Effective permission = requester scopes ∩ coworker grant ∩ skill scopes.** The coworker acts on behalf of the requester, and uses its own principal only for scheduled duties with a narrower grant. So the worst case of a bad plan is what that person could have done by hand.

Approval policy lives in code: payments over $1,000 go to the budget owner, over $10,000 need two approvers, external email needs the requester, HR changes need HR. Approvals **expire in 48 h and escalate** to the approver's manager. Inbound external email is untrusted: it can't write memory or trigger a write tool without a human.

The alternative is a broad service account "to keep it simple." Then every employee has finance access through the chat box.

**The trap:** the broad service account.

**Rubric:** on-behalf-of, never exceeding the requester (12.1), thresholds in code (12.2), expiry and escalation (12.3), and untrusted email blocked from memory and writes (12.4).

### Key Impact

**The question:** how do you prove coworkers save time?

Five metrics: time to build (10 weeks → 2), hours saved (0 → 9,000 a month), override rate (under 10 percent), skill reuse (60 percent of a coworker's skills from the marketplace), and cost per completed task (under $0.05, from $38k over 900,000 tasks).

The method is what earns marks. **Hours saved = completed tasks × per-task-type time-study minutes**, with a time study of 50 tasks per type before launch. Count only tasks completed without rework.

**The trap:** reporting messages handled. Volume says nothing about time saved.

**Rubric:** completed tasks × time-study minutes (13.1), excluding redone tasks (13.2), and build time plus cost per task (13.3).

### Failure Modes

**The question:** what breaks, and what does the platform do?

- **Memory poisoning:** provenance lets a curator find and revoke every fact from one source in one query.
- **Skill regression:** a new version runs in canary on 5 percent of tasks and rolls back automatically on a failed eval.
- **Approver unavailable:** the 48 h TTL escalates; the task **never auto-approves**.
- **Budget exhaustion:** a team at 100 percent drops to small-model-only and queues non-urgent tasks.
- **Channel outage:** tasks wait in Temporal and resume.

The principle: waiting is always safe and acting isn't, so degraded paths pause.

**The trap:** auto-approving on timeout. Every slow approver becomes a hole in the payment controls.

**Rubric:** poisoning with revoke-by-source (14.1), canary and rollback (14.2), and no auto-approve on timeout (14.3).

### Build Order

**The question:** in what order do you build it in six months?

Five phases over 26 weeks: the Temporal task workflow, Slack adapter, OPA and on-behalf-of identity first (weeks 1–4, measured by the AP coworker migrated and tasks surviving a deploy); scoped memory with provenance (5–8, travel-policy conflicts at 0); the skills registry with the three existing coworkers rebuilt on it (9–13); email and ticket adapters with cross-channel approvals (14–18); then the self-serve builder and 10 new coworkers (19–26, build time per coworker).

The reasoning: migrating the three existing coworkers first proves the platform on real traffic and removes three memory stores.

**The trap:** launching 25 coworkers at once. Each one's problems look like platform problems.

**Rubric:** workflow and identity first (15.1), migration before new coworkers (15.2), and a number per phase (15.3).

## 8. The decisions that separate strong answers

**Scoped memory with write rules vs one shared vector store.** The weak answer gives every coworker a shared embedding store "so they learn from each other." That's exactly how the travel-policy conflict happened, just centralized. The strong answer has four scopes, puts the scope in the SQL query, makes firm facts read-only to coworkers, and stores provenance so a poisoned source can be revoked in one query.

**On-behalf-of vs a service account.** The service account is easier to build and makes every permission check trivially pass, which is the problem. On-behalf-of with an intersection of scopes means the coworker can never exceed the requester. The cost is token caching and a narrower principal for scheduled duties.

**One task id in a durable workflow vs per-channel conversations.** Per-channel chat is what most bots do. It can't resume a task on a Slack click four days after an email, and it forks tasks. A Temporal workflow per task, with approvals as signals from any channel, makes cross-channel resume a design property rather than glue code.

## 9. Common mistakes

- Designing for throughput when the peak is about one task a second.
- Letting the model write memory directly, at any scope.
- Indexing systems of record instead of reading them live.
- Sharing a semantic cache across teams or users without an ACL key.
- Approval thresholds written in the system prompt.
- Auto-approving on timeout.
- No per-team budget at admission, so one runaway coworker spends everyone's money.
- Measuring "tasks attempted" or messages handled instead of hours saved on completed tasks.

## 10. Follow-ups an interviewer might ask

- *A coworker learned a wrong fact from a phishing email. How bad is it?* Inbound external email can't write memory without a human. If a wrong team fact got through a curator, provenance lets you revoke every fact from that source in one query.
- *Team A wants to fork Team B's skill to change one line.* Publish a new version upstream or a new skill with its own owner and evals. Forks never get upstream fixes.
- *An EU employee asks to be forgotten.* Delete their preferences and episodic rows, redact their name from team facts, and their EU-region attachments go with them.
- *How does the approval in Slack resume the email task?* The button is signed with the task id and sends a signal to that task's Temporal workflow (problems durable-workflow-replay and human-approval-gates).
- *How do you enforce tool scopes per skill?* Intersect requester, coworker and skill scopes before each call in OPA (problem tool-permission-scopes).
