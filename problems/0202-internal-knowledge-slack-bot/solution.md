# Internal Knowledge Slack Bot: model answer

## 1. Scenario
Employees ask a question in Slack and get a cited answer in seconds instead of waiting 47 minutes for a colleague. The bot answers only from documents the asker can open today, and says so when it cannot find one.

| What | Number | What it drives |
|---|---|---|
| Traffic | 25,000 questions a month, 1,190 a weekday; busiest hour 15% is 0.05 questions/s, plan for 1/s bursts | One small service; cost is in tokens, not servers |
| Corpus | 38,000 pages, 120,000 files, 150,000 issues, about 1.5M chunks | Fits in Postgres with pgvector |
| Freshness | 1% changes daily; revocations live within 15 minutes | Event-driven sync plus a live permission check |
| Latency | Ack under 3 s (Slack's rule), first text p95 under 4 s | Ack first, answer asynchronously |
| Budget | $1,500 a month for model, embedding and rerank | A mid model on 8 chunks, no big prefix |

**How:**
1. Export 3 months of the six help channels (3,100 questions a month) and label 400 questions with the document that answers them.
2. Set baselines from that export: median first human reply 47 minutes, 22% of questions never answered.
3. Agree the success metric with IT and People: help-channel questions resolved with no human reply in the thread within 24 h.
4. Write down what is out of scope: Slack Connect channels, actions (opening tickets, granting access), and HR, Legal and Finance compensation folders.

**Decision.** Target 45% of help-channel questions resolved by the bot, gated on zero permission leaks in a 500-probe red-team set.

**Trap.** Treating this as a search problem only. The hard requirement is permissions, and it shapes retrieval, the channel rules and the sync design.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Slack app (Bolt for Python) | Receives `app_mention`, `message.im` and `/ask`; acks in under 3 s. Hands over a question, Slack user id, channel type and thread | Slack retries any event not acked in 3 s |
| Identity resolver | Maps Slack user to email, then to Google, Confluence and Jira groups. Hands over a principal set | Permissions are per person, not per bot |
| Connectors and sync | Webhooks and change feeds from the three sources. Hands over changed docs and their ACLs | Content and permissions both go stale |
| Processing | Parse, chunk, embed, attach ACLs. Hands over chunks to the index | Chunks must carry who may see them |
| Retrieval | Hybrid search filtered by principals, then rerank, then a live permission check. Hands over 8 chunks | The model only ever sees allowed text |
| Model (via LiteLLM) | Haiku 5.5 rewrites follow-ups, Sonnet 5.5 answers. Hands over text with `[n]` citations | One mid-model call per question fits the budget |
| Citation check | Every sentence matched to its cited chunk. Hands over the answer or an abstention | A wrong answer with a real link is worse than none |
| Evals and traces (Langfuse) | 400 labelled questions in CI, every live answer traced with feedback | Retrieval changes ship on recall numbers |

**The one idea to hold:** permission filtering happens in code before ranking, and again live before the model sees a chunk; the prompt never decides who sees what.

## 3. Data Sources
Three systems, each with its own content model, permission model and change feed.

| Source | Indexed | Permission model | Change feed |
|---|---|---|---|
| Confluence Cloud | 38,000 pages, 210 spaces | Space permissions plus page restrictions (inherited from parents) | Webhooks: page created, updated, removed, restrictions changed |
| Google Drive | 120,000 files in shared drives | Users, groups, domain, "anyone with link" | Changes API with a push channel, polled every 2 minutes as backup |
| Jira Cloud | 150,000 issues from the last 2 years | Project permission scheme plus issue security levels | Webhooks: issue created, updated, deleted |

**How:**
1. Read with service accounts: a Google Workspace service account with domain-wide delegation (read-only Drive scope), and Confluence and Jira API tokens for a read-only bot user added to every space and project.
2. Store each document's ACL as a flat list of principals (`user:`, `group:`, `domain:`), expanding page-restriction inheritance at sync time.
3. Apply a folder and space denylist in the connector (HR cases, Legal, Finance compensation), so those files are never fetched.
4. Run a nightly full reconciliation that diffs every source's document list and ACLs against the index, catching missed webhooks.

**Decision.** Service accounts plus a mirrored ACL, not per-user OAuth search. Per-user OAuth would make every query call three live search APIs and break the 4 s budget.

**Trap.** Indexing "anyone with the link" files as public. Those links are often shared with one vendor; treat them as visible only to explicit principals.

## 4. Processing
Each source becomes chunks that carry their own title, location and ACL.

**How:**
1. Parse Confluence storage format to Markdown; parse Drive files with Unstructured (Docs, Slides, PDFs) and convert Sheets to per-tab Markdown tables capped at 200 rows; build each Jira issue as one document from summary, description, resolution and the last 10 comments.
2. Split on headings to about 400 tokens with 50 overlap; prefix each chunk with its breadcrumb ("Space > Parent > Page > Section") before embedding.
3. Embed with OpenAI `text-embedding-3-small`: 1.5M chunks is 600M tokens, $12 for a full build; the daily 1% churn is 6M tokens, about $0.12.
4. Hash each chunk; re-embed only changed hashes, keep chunk ids stable, and tombstone deleted ones in the same transaction.
5. Scan chunks with `detect-secrets` and drop any containing keys or passwords.

**Decision.** An ACL change re-writes ACL rows only, without re-embedding. Group and sharing changes happen daily, and re-embedding for them would waste money and delay the revocation.

**Trap.** Embedding the chunk text alone. "Step 3: restart the service" means nothing without the page title in front of it.

## 5. Agents
This is a retrieval pipeline with one bounded tool loop, not an open agent.

**How:**
1. If the message is in a thread, Haiku 5.5 rewrites it into a standalone query using the last 6 thread messages (800 tokens in, 40 out).
2. Run retrieval (section 10) and hand Sonnet 5.5 the top 8 allowed chunks.
3. Give Sonnet one tool, `search_knowledge`, so it can run at most one more search with a refined query; cap the whole run at 2 searches and 15 s.
4. If no chunk scores above the rerank threshold of 0.3, skip generation and reply with "I couldn't find this" plus the top 3 links.

**Decision.** A pipeline with one extra search allowed. Free agents spent 4 searches on easy questions in early tests and tripled the cost.

**Trap.** Answering when retrieval found nothing good. The model will write a plausible IT policy from its training data.

## 6. Memory
Slack is the conversation memory; the bot stores almost nothing about people.

| Tier | Holds | Lives in | Expires |
|---|---|---|---|
| Thread | Last 6 messages | Slack, read with `conversations.replies` | Never stored by the bot |
| Run | Query, chunk ids, answer, feedback | Postgres | 30 days |
| User | Principal set; preferred spaces to boost | Redis (principals, 10 min); Postgres (preferences) | Principals refresh every 10 min |

**How:**
1. Fetch the thread from Slack on each follow-up instead of keeping a copy.
2. Cache each user's principal set in Redis for 10 minutes; flush it on a Google Directory or Atlassian group-membership change event.
3. Never carry chunks from one user's run into another user's context.

**Decision.** No cross-user memory or learned facts. A fact learned from one person's restricted doc could resurface for someone without access.

**Trap.** Reusing the earlier answer's chunks for a follow-up asked by a different person in the same thread. Re-run retrieval with the new asker's permissions.

## 7. MCP Tool Servers
One knowledge MCP server (Python MCP SDK) wraps retrieval so the bot, and later the IDE assistant, share the same permission logic.

| Tool | Does | Guard in code |
|---|---|---|
| `search_knowledge(query, sources?, updated_after?)` | Hybrid search, rerank, live check | Principals come from the caller's identity, not an argument |
| `get_document(doc_id, section?)` | Full section text | Same ACL filter plus live check |
| `get_jira_issue(key)` | Live issue status and assignee | Jira permission check API for that user |

**How:**
1. Authenticate the caller with a signed token carrying the Slack user id; resolve principals server-side.
2. Define strict JSON schemas and return typed errors (`not_found`, `forbidden`) the model can explain.
3. Refresh source OAuth tokens with a single-flight lock so 20 concurrent calls after expiry trigger one refresh.

**Decision.** The principal set is never a tool argument. If the model could pass it, a prompt injection in a document could widen it.

**Trap.** Returning "forbidden" with the document title. A title like "Layoffs Q3 plan" is itself a leak; say "not found".

## 8. Endpoints
Slack's 3-second rule decides the shape: ack immediately, then work in the background.

| Route | Purpose |
|---|---|
| `POST /slack/events` | `app_mention`, `message.im`; ack, enqueue |
| `POST /slack/commands` | `/ask`; ack with "Searching..." |
| `POST /slack/interactions` | Feedback buttons |
| `POST /hooks/confluence`, `/hooks/jira`, `/hooks/drive` | Change notifications, signature verified |

| Stage (after ack) | p95 |
|---|---|
| Principal lookup (Redis) | 20 ms |
| Follow-up rewrite, Haiku 5.5 | 300 ms |
| Query embedding | 80 ms |
| Hybrid search with ACL filter | 120 ms |
| Rerank and live permission check, in parallel | 300 ms |
| Sonnet 5.5 time to first token | 900 ms |
| First `chat.update` with the first sentence | 400 ms |
| **First answer text** | **2,120 ms** |

**How:**
1. Run Bolt on two ECS Fargate tasks behind an ALB; ack in about 150 ms, then hand the work to an asyncio worker.
2. Dedupe on Slack's `event_id` in Redis for 24 h, since Slack retries with `X-Slack-Retry-Num`.
3. Post a placeholder in the thread, then edit it at most once a second with `chat.update` to stay under Slack's rate tier.

**Decision.** Events API over HTTP in production, Socket Mode only for local development. HTTP scales behind a load balancer and is what Slack Marketplace review expects.

**Trap.** Doing the work before acking. Slack retries after 3 s, and the user gets three identical answers.

## 9. Caching
Here the prompt cache helps less than usual, because most of each prompt is the retrieved chunks, which change per question.

| Per question (Sonnet 5.5, $2 / $10 per MTok, $0.20 cached) | Tokens | With cache | Without |
|---|---|---|---|
| Stable prefix: rules, citation format, tool schema | 2,000 | $0.0004 | $0.0040 |
| Chunks, thread, question | 3,800 | $0.0076 | $0.0076 |
| Output | 300 | $0.0030 | $0.0030 |
| Haiku rewrite, embedding | | $0.0001 | $0.0001 |
| **Per question** | | **$0.0111** | **$0.0147** |
| **Per month at 25,000** | | **$278** | **$368** |

Add Cohere Rerank at about $2 per 1,000 searches ($50 a month) and indexing (under $20): about $350 a month, well inside $1,500.

**How:**
1. Put the stable prefix first with a `cache_control` breakpoint; per-user data and chunks after it.
2. Cache principal sets for 10 minutes and live permission checks per (user, doc) for 5 minutes, both under the 15-minute revocation SLA.
3. Cache query embeddings by normalized text for 1 hour.

**Decision.** No shared answer cache. Two people asking the same question may be allowed different documents, so a cached answer can leak.

**Trap.** Spending a week on prompt caching here. The lever is fewer, better chunks: dropping from 12 to 8 chunks saved more than the cache does.

## 10. Data Stores
One Postgres for chunks, vectors and ACLs, so the permission filter and the vector search run in one query.

| Store | Holds | Size |
|---|---|---|
| RDS Postgres + pgvector | 1.5M chunks, `halfvec(1536)` with HNSW, ACL arrays with a GIN index, run log | About 4.6 GB of vectors, 6 GB of text; db.r6g.xlarge (32 GB RAM) |
| ElastiCache Redis | Event dedupe, principal and live-check caches | Under 1 GB |
| S3 | Raw exports for re-parsing | About 25 GB |
| Langfuse | Traces and feedback | About 1 GB a month |

**How:**
1. Filter in SQL: `WHERE acl && :principals AND NOT deny && :principals`, then vector top 40 and `tsvector` top 40, fused with reciprocal rank fusion (k = 60).
2. Enable `hnsw.iterative_scan` (pgvector 0.8) so a tight ACL filter still returns enough rows.
3. Rerank the top 30 with Cohere Rerank 3.5; in parallel, live-check the top 30 against the source permission APIs; keep the top 8 that pass both.

**Decision.** Pre-filter by ACL inside the vector query, not post-filter. Post-filtering a top 10 can leave a contractor with 1 result, or none.

**Trap.** Trusting the mirror alone. A revocation can lag by minutes; the live check on the final candidates is what meets the 15-minute SLA.

## 11. Output
Every answer is a Block Kit message in the thread, built from typed parts.

| Part | Contents |
|---|---|
| Answer | Up to 6 sentences with `[n]` markers |
| Sources | Up to 4 links: title, space or drive, last-updated date |
| Staleness note | Shown when a cited doc is over 12 months old |
| Feedback | Helpful and Not helpful buttons, plus "Ask in #ask-it" |

**How:**
1. Render the answer and sources from a Pydantic model, never raw model text.
2. In public channels, answer only from documents visible to the whole company (ACL holds the `domain:` principal, or the guest group's if the channel has guests); if better restricted docs exist, send the asker an ephemeral note to ask in a DM.
3. In DMs, use the asker's full permissions.

**Decision.** A channel answer is read by everyone in the channel, so it uses only org-wide documents. The asker's own access applies only in DMs.

**Trap.** Posting a DM-quality answer in #general because the asker had access. Every channel member just read a restricted doc.

## 12. Guardrails
Each rule names what enforces it when the model ignores its instructions.

| Rule | Enforced by |
|---|---|
| Only documents the asker can open | ACL pre-filter in SQL plus live check |
| Channel answers only from org-wide docs | Retrieval mode set from the Slack channel type, in code |
| HR, Legal, Finance compensation never searchable | Connector denylist; never fetched |
| No external users | Bot refuses when `is_stranger` or the user's team id differs |
| No secrets | `detect-secrets` at index time |

**How:**
1. Wrap retrieved text as quoted data and instruct the model to ignore instructions inside it; it cannot widen access anyway.
2. Check each sentence against its cited chunk (token overlap at least 0.5); drop unsupported sentences, and abstain if fewer than half survive.
3. Run 500 permission probes weekly: test users in contractor and new-hire groups asking for restricted pages; any hit fails CI.

**Decision.** Permissions live in code, never in the prompt. The prompt only explains to the user why a source was not used.

**Trap.** Revoking someone's access and forgetting the cache. Principal and live-check caches must expire inside the SLA.

## 13. Key Impact
One headline number, measured against channels where the bot is off.

| Metric | Baseline | Target | Measured by |
|---|---|---|---|
| Help-channel questions resolved with no human reply in 24 h | 0% | 45% | Slack thread replies |
| Median time to first answer | 47 min | Under 10 s | Event timestamps |
| Helpful rate | n/a | 75% or higher | Feedback buttons |
| Citation accuracy | n/a | 95% or higher | Weekly sample of 100 judged by a Sonnet grader, spot-checked by hand |
| Permission leaks | n/a | 0 | Probe set and incident log |

**How:**
1. Turn the bot off in 2 of the 6 help channels for 4 weeks and compare resolution and wait time.
2. Grade the 400 labelled questions in CI: recall@8 above 0.85 and abstention correct on the 40 unanswerable ones.
3. Estimate time saved: 25,000 questions at 6 minutes of searching saved is 2,500 hours a month, about $225,000 at $90 an hour.

**Decision.** Resolution in help channels is the headline; it counts only answers that stopped a human from replying.

**Trap.** Reporting thumbs-up rate alone. People click Helpful on confident wrong answers.

## 14. Failure Modes
The worst failure here is a leak, not a wrong answer. Each row has a named catch.

- **A revocation lags in the mirror.** The live check on the final 30 candidates drops the doc; the 5-minute cache keeps the worst case under 15 minutes.
- **A Confluence webhook is missed.** The nightly reconciliation diff finds the change; an alert fires if more than 0.5% of docs differ.
- **Slack returns 429 on `chat.update`.** Stop streaming edits and post the final answer once.
- **A source token expires.** Single-flight refresh; if it fails, that source is skipped and the answer says which source was unavailable.
- **Model provider outage.** LiteLLM fails over to Claude on Amazon Bedrock; if both fail, reply with the top 3 links only.

**How:**
1. Write each row as a test: a revoked user, a dropped webhook, a stubbed 429, an expired token.
2. Alert in Datadog on sync lag over 10 minutes, abstention rate over 25%, and any probe hit.
3. Keep a per-source kill switch that removes it from retrieval without a deploy.

**Decision.** When a permission check fails or times out, drop the document. A worse answer is acceptable; a leak is not.

**Trap.** Failing open on a slow permission API to keep latency down.

## 15. Build Order
1. **Week 1:** 400 labelled questions and the 500-probe permission set. Number: baseline 47-minute wait.
2. **Week 2:** Confluence connector, ACL mirror and DM-only bot for the IT team. Number: recall@8 above 0.85 on Confluence questions, zero probe hits.
3. **Week 3:** Drive and Jira connectors with incremental sync. Number: sync lag p95 under 5 minutes.
4. **Week 4:** live permission check and citation check. Number: citation accuracy 95%, revocation test under 15 minutes.
5. **Week 5:** channel mode with org-wide docs, in 4 help channels. Number: first text p95 under 4 s.
6. **Week 6:** company-wide launch with the 2-channel holdout. Number: 45% resolved.

**How:**
1. Gate each week in CI on its number.
2. Roll out by Slack user group, IT first, then engineering, then everyone.
3. Review the 50 worst-rated answers every Friday and turn them into test cases.

**Decision.** Permissions before breadth. One source with correct ACLs ships before three sources without.

**Trap.** Launching to the whole company in week 2 because the demo looked good on public pages.
