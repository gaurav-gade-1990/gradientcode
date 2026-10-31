## 1. What the problem is really asking

On the surface this is "RAG over Confluence, Drive and Jira, in Slack". Plenty of candidates stop there and spend the session on chunk sizes. The real problem is in one sentence of the context: **never show someone a document they could not open themselves.** That turns a search problem into a permissions problem, and permissions shape the sync design, the retrieval query, the channel rules and the failure policy.

The core tension: three source systems each have their own permission model and change at their own pace, but every answer has to respect what the asker can open *today*, within 15 minutes of a revocation, while Slack demands an acknowledgement in 3 seconds.

Three decisions carry the design:

- **Mirror the ACLs, then check live.** Service accounts index everything with each document's ACL attached. Retrieval pre-filters by the asker's principals inside the vector query, and a live permission check on the final candidates closes the gap a lagging mirror leaves.
- **Channel answers are different from DM answers.** Everyone in a channel reads the reply, so channel answers use only org-wide documents. The asker's full access applies only in a DM.
- **Ack first, answer later.** Acknowledge Slack in about 150 ms, then do the work in a background worker and edit a placeholder message as the answer streams.

## 2. The numbers that drive the design

**Traffic.**

| Step | Arithmetic | Result |
|---|---|---|
| Questions a weekday | 25,000 a month ÷ about 21 weekdays | about 1,190 |
| Busiest hour | 15% of a weekday: 1,190 × 0.15 ÷ 3,600 s | about 0.05 questions/s |
| Plan for | bursts | 1 question/s |

That is almost nothing. One small service; the cost is in tokens, not servers.

**Corpus.** 38,000 Confluence pages + 120,000 Drive files in shared drives + 150,000 Jira issues from the last two years comes to about 1.5 million chunks. At about 400 tokens each, that's 600 million tokens.

| Embedding step | Arithmetic | Cost |
|---|---|---|
| Full build | 600M tokens with `text-embedding-3-small` | $12 |
| Daily churn | 1% of 600M = 6M tokens | about $0.12 |

**Vector storage.** 1.5M chunks × 1,536 dimensions × 2 bytes (`halfvec`) is about 4.6 GB. That fits in RAM on a db.r6g.xlarge with 32 GB, so Postgres with pgvector is enough.

**Latency.** Slack's 3 s ack is a hard rule; first answer text p95 under 4 s is the SLO. The model answer's stage budget after the ack:

| Stage | p95 |
|---|---|
| Principal lookup (Redis) | 20 ms |
| Follow-up rewrite, Haiku 5.5 | 300 ms |
| Query embedding | 80 ms |
| Hybrid search with ACL filter | 120 ms |
| Rerank and live permission check, in parallel | 300 ms |
| Sonnet 5.5 first token | 900 ms |
| First `chat.update` | 400 ms |
| Total | 2,120 ms |

20 + 300 + 80 + 120 + 300 + 900 + 400 = 2,120 ms, well under 4 s.

**Cost per question.** Sonnet 5.5 at $2 / $10 per MTok, $0.20 cached.

| Piece | With cache | Without |
|---|---|---|
| Stable prefix, 2,000 tokens | 2,000 × $0.20 / 1M = $0.0004 | 2,000 × $2 / 1M = $0.0040 |
| Chunks, thread, question, 3,800 tokens | $0.0076 | $0.0076 |
| Output, 300 tokens | $0.0030 | $0.0030 |
| Haiku rewrite, embedding | $0.0001 | $0.0001 |
| Per question | $0.0111 | $0.0147 |
| Per month (× 25,000) | about $278 | about $368 |

Add Cohere Rerank at about $2 per 1,000 searches ($50 a month) and indexing under $20, and the total is about $350 a month against a $1,500 budget. Notice what this table tells you: the cache saves only about $90 a month, because most of each prompt is retrieved chunks that change per question. Here **the lever is fewer, better chunks**, not caching.

**Impact.** 25,000 questions × 6 minutes of searching saved is 2,500 hours a month, about $225,000 at $90 an hour.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–3 | Restate the job and the permission rule; write traffic, corpus size and the revocation SLA on the board |
| 3–8 | **Pillar A:** Scenario with the 45% target gated on zero leaks; the Single View with an identity resolver |
| 8–16 | **Pillar B:** the three permission models, chunking with breadcrumbs, the bounded pipeline, Slack as memory, the knowledge server |
| 16–22 | **Pillar C:** ack-then-work, the cost table, the pre-filtered SQL query, channel versus DM output |
| 22–27 | **Pillar D:** guardrails, holdout channels, fail-closed failure modes, build order |
| 27–45 | Follow-ups |

Spend the extra minute on Data Sources and Data Stores. Those are where the permission design is decided, and that's what the interviewer is listening for.

## 4. Pillar A: Frame

### Scenario

**The question:** who asks, what job does the bot do, and which numbers shape the design?

**How to reason.** The user is any of the 1,800 employees or 150 contractors asking in one of six help channels, a DM or `/ask`; the job is "get a cited answer in seconds instead of 47 minutes." Ground the baseline in data: export 3 months of the help channels and label 400 questions with the document that answers them. That export also gives the second baseline, 22% of questions never answered.

For the metric, "helpful rate" is tempting but easy to game. The model answer picks **45% of help-channel questions resolved with no human reply in the thread within 24 h**, and gates it on **zero permission leaks in a 500-probe red-team set**. Out of scope: Slack Connect, actions (opening tickets, granting access) and the HR, Legal and Finance compensation folders.

**The trap.** Treating this as a search problem only. Name permissions as the hard requirement in your first minute.

**Rubric criteria earned:** user and job in one sentence; questions per day and peak per second from 25,000 a month; metric with baseline and target gated on zero leaks; out-of-scope list.

### Single View

**The question:** what are the layers, what does each hand over, and why?

**How to reason.** Follow one @mention. Bolt for Python receives the event and acks under 3 s. Then a layer most candidates forget: an **identity resolver** that maps the Slack user to an email and then to Google, Confluence and Jira groups, producing a principal set. Permissions are per person, not per bot, so without this layer there's nothing to filter on. Connectors and sync bring changed documents **and their ACLs**; processing attaches the ACL to every chunk; retrieval filters by principals, reranks and runs the live check; LiteLLM fronts Haiku (rewrite) and Sonnet (answer); a citation check matches each sentence to its chunk; Langfuse traces everything against the 400 labelled questions.

The one idea: permission filtering happens in code before ranking, and again live before the model sees a chunk. The prompt never decides who sees what.

**The trap.** Drawing a single "sync" arrow for content only. Permissions go stale too, and faster.

**Rubric criteria earned:** a layer resolving Slack users into source principals; sync of both content and permissions; filtering in code, not the prompt.

## 5. Pillar B: Build the core

### Data Sources

**The question:** for each source, what's indexed, how are its permissions modelled, and how do changes arrive?

**How to reason.** Name each permission model, because they differ. Confluence: space permissions plus page restrictions inherited from parents. Drive: users, groups, domain and "anyone with link". Jira: a project permission scheme plus issue security levels. Change feeds: Confluence and Jira webhooks; Drive's Changes API with a push channel, polled every 2 minutes as backup. A nightly full reconciliation diffs every source's document list and ACLs against the index to catch missed webhooks.

The key alternative is **per-user OAuth search** (query each source live as the user) versus **service accounts plus a mirrored ACL**. Per-user OAuth is always correct, but it makes every question call three live search APIs, which breaks the 4 s budget. The model answer mirrors ACLs as flat principal lists (`user:`, `group:`, `domain:`), expanding page-restriction inheritance at sync time. Excluded folders are on a denylist **in the connector**, so they're never fetched at all.

**The trap.** Indexing "anyone with the link" files as public. Those links are often shared with one vendor; treat them as visible only to explicit principals.

**Rubric criteria earned:** each source's permission model; a change feed per source plus reconciliation; excluded folders kept out at the connector; link-shared files not treated as public.

### Processing

**The question:** how do documents become chunks that carry their context and permissions, and how do edits flow?

**How to reason.** Each source needs its own parser: Confluence storage format to Markdown, Drive files through Unstructured with Sheets as per-tab tables capped at 200 rows, and each Jira issue as one document built from summary, description, resolution and the last 10 comments. Split on headings to about 400 tokens with 50 overlap, and **prefix each chunk with its breadcrumb** ("Space > Parent > Page > Section") before embedding. A chunk reading "Step 3: restart the service" is unfindable without its title.

For edits, hash chunks, re-embed changed hashes only, keep chunk ids stable and tombstone deletes in the same transaction. State the costs: $12 for a full build, about $0.12 a day for churn. Scan with `detect-secrets` and drop chunks containing keys.

The decision worth saying out loud: **an ACL change rewrites ACL rows only, without re-embedding.** Sharing changes happen daily; re-embedding for them wastes money and delays the revocation (problem incremental-index-sync builds this).

**The trap.** Embedding chunk text alone, without the title in front.

**Rubric criteria earned:** chunk size and rule; breadcrumb context; hash-based updates with tombstones; full-build and daily-churn cost.

### Agents

**The question:** what's the control flow from question to answer, and what bounds it?

**How to reason.** Most questions need one search and one answer. An open agent that searches until satisfied is the alternative, and the model answer reports it spent 4 searches on easy questions and tripled the cost. So: a pipeline with one bounded tool. If the message is in a thread, Haiku rewrites it into a standalone query from the last 6 thread messages (800 tokens in, 40 out). Retrieval hands Sonnet the top 8 allowed chunks. Sonnet gets one tool, `search_knowledge`, for at most one more search; the run is capped at 2 searches and 15 s. If no chunk scores above a rerank threshold of 0.3, **skip generation** and reply "I couldn't find this" with the top 3 links. That's the requirement to say "I don't know" with the closest links.

**The trap.** Answering when retrieval found nothing good. The model will write a plausible IT policy from its training data.

**Rubric criteria earned:** follow-up rewrite to a standalone query; caps on searches and time; abstain below a score threshold.

### Memory

**The question:** what does the bot remember, where, and for how long?

**How to reason.** Slack already stores the thread, so read it with `conversations.replies` on each follow-up instead of keeping a copy. Run logs (query, chunk ids, answer, feedback) go in Postgres for 30 days, matching transcript retention. Principal sets sit in Redis for 10 minutes, flushed on a group-membership change event. Ten minutes is chosen because it's under the 15-minute revocation SLA.

The decision is to have **no cross-user memory**. A fact learned from one person's restricted document could resurface for someone without access.

**The trap.** In the same thread, a second person asks "what about contractors?" and you reuse the first answer's chunks. Re-run retrieval with the new asker's permissions.

**Rubric criteria earned:** Slack thread as memory; principals cached under the SLA; re-retrieval for a new asker.

### MCP Tool Servers

**The question:** which tools exist, and how do they enforce permissions?

**How to reason.** Wrap retrieval in one knowledge MCP server so the bot, and later an IDE assistant, share the same permission logic. Three tools: `search_knowledge(query, sources?, updated_after?)`, `get_document(doc_id, section?)` and `get_jira_issue(key)` (live status via Jira's permission check API). The principal set is **never an argument**; the server resolves it from a signed token carrying the Slack user id. If the model could pass principals, an injected instruction in a document could widen them.

Two subtle details earn rubric points. Errors are typed (`not_found`, `forbidden`), but a forbidden document returns "not found", because a title like "Layoffs Q3 plan" is itself a leak. And source OAuth tokens refresh with a single-flight lock, so 20 concurrent calls after expiry trigger one refresh (problem oauth-single-flight-refresh).

**The trap.** Returning "forbidden" with the document title.

**Rubric criteria earned:** tools with arguments; principals from caller identity; no title leaks in errors; single-flight refresh.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** how does the bot meet Slack's 3-second rule, and where does the latency go?

**How to reason.** Slack retries any event not acked in 3 s, so the shape is fixed: ack in about 150 ms, enqueue, and answer from an asyncio worker. Routes: `/slack/events`, `/slack/commands` (ack with "Searching..."), `/slack/interactions` for feedback buttons, and three signature-verified source webhooks. Dedupe on Slack's `event_id` in Redis for 24 h, because retries carry `X-Slack-Retry-Num`. Post a placeholder in the thread and edit it at most once a second with `chat.update` to stay under Slack's rate tier. Then show the 2,120 ms stage table.

Run Events API over HTTP on two Fargate tasks behind an ALB; keep Socket Mode for local development.

**The trap.** Doing the work before acking. Slack retries after 3 s and the user gets three identical answers.

**Rubric criteria earned:** ack before work; dedupe by event id; a stage table under 4 s; throttled edits.

### Caching

**The question:** what's cached, what isn't, and what does a question cost?

**How to reason.** Show both columns of the cost table ($278 versus $368 a month), then say why the gap is small. Every permission-related cache must expire under 15 minutes: principal sets for 10, live checks per (user, doc) for 5. Query embeddings cache safely for 1 hour by normalized text.

The decisive "no": **a shared answer cache across users**. Two people asking the same question may be allowed different documents, so a cached answer can leak.

**The trap.** Spending a week on prompt caching. Dropping from 12 to 8 chunks saved more than the cache does (problem context-packing).

**Rubric criteria earned:** per-question and monthly cost with and without caching; permission caches under the SLA; shared answer cache rejected.

### Data Stores

**The question:** where do chunks, vectors and ACLs live, how big are they, and how does a filtered query run?

**How to reason.** The design choice is to put vectors and ACLs **in the same database** so the filter and the search run in one query. RDS Postgres with pgvector holds 1.5M chunks as `halfvec(1536)` under HNSW (about 4.6 GB of vectors, 6 GB of text), ACL arrays under a GIN index, and the run log. Redis holds dedupe and permission caches, S3 holds about 25 GB of raw exports, Langfuse about 1 GB of traces a month.

The query: `WHERE acl && :principals AND NOT deny && :principals`, vector top 40 and `tsvector` top 40, fused with RRF (k = 60). Enable `hnsw.iterative_scan` (pgvector 0.8) so a tight ACL filter still returns enough rows. Rerank the top 30 with Cohere Rerank 3.5 while live-checking the same 30 against the source APIs, and keep the top 8 that pass both (problem acl-aware-retrieval, problem hybrid-search-rrf).

**Pre-filter versus post-filter** is the decision to argue. Post-filtering a top 10 can leave a contractor with 1 result, or none.

**The trap.** Trusting the mirror alone. The live check on the final candidates is what meets the 15-minute SLA.

**Rubric criteria earned:** vector size from count and dimensions; ACL pre-filter in the query; keyword plus vector fusion with rerank; live check on final candidates.

### Output

**The question:** what does an answer look like, and how does it differ between a DM and a channel?

**How to reason.** A Block Kit message built from a Pydantic model: up to 6 sentences with `[n]` markers, up to 4 sources with title, space or drive and last-updated date, a staleness note when a cited doc is over 12 months old, and Helpful / Not helpful buttons plus "Ask in #ask-it".

The channel rule is the part the prompt explicitly asks about. In a public channel everyone reads the answer, so retrieval uses only documents whose ACL holds the `domain:` principal (or the guest group's if the channel has guests). If better restricted documents exist, the asker gets an ephemeral note suggesting a DM. In DMs, use the asker's full permissions.

**The trap.** Posting a DM-quality answer in #general because the asker had access. Every channel member just read a restricted doc.

**Rubric criteria earned:** linked sources with dates; channel answers limited to what all members can see; feedback on every answer.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** for each rule protecting data or trust, what enforces it if the model ignores its instructions?

**How to reason.** Build the rule-and-enforcer table: asker's permissions by the SQL pre-filter plus live check; channel mode set from the Slack channel type in code; excluded folders by the connector denylist; no external users by refusing when `is_stranger` is set or the team id differs; no secrets by `detect-secrets` at index time. Then the soft layers: wrap retrieved text as quoted data (an injection can't widen access anyway); check each sentence against its cited chunk at token overlap of at least 0.5, drop unsupported sentences, and abstain if fewer than half survive (problem citation-hallucination-check). Run the 500 permission probes weekly from contractor and new-hire test users; any hit fails CI.

**The trap.** Revoking someone's access and forgetting the cache.

**Rubric criteria earned:** permissions and channel mode in code; per-sentence citation check with abstention; external users blocked by Slack attributes; probes that fail CI.

### Key Impact

**The question:** what number moves, and how do you prove the bot moved it?

**How to reason.** Headline: help-channel questions resolved with no human reply in 24 h, 0% to 45%. Supporting: median time to first answer from 47 minutes to under 10 s, helpful rate 75% or higher, citation accuracy 95% or higher on a weekly sample of 100, permission leaks 0. Attribution comes from a **holdout**: the bot is off in 2 of the 6 help channels for 4 weeks. Offline, grade the 400 labelled questions in CI for recall@8 above 0.85 and correct abstention on the 40 unanswerable ones. Then the dollars: 2,500 hours, about $225,000 a month.

**The trap.** Reporting thumbs-up rate alone. People click Helpful on confident wrong answers.

**Rubric criteria earned:** baseline and target; holdout channels; offline recall@k; hours or dollars.

### Failure Modes

**The question:** what breaks, and what catches each failure?

**How to reason.** Order by severity, and here the worst failure is a leak, not a wrong answer. A revocation lags in the mirror: the live check on the final 30 drops the doc, and the 5-minute cache keeps the worst case under 15 minutes. A webhook is missed: the nightly reconciliation finds it, with an alert above 0.5% drift. Slack 429s on `chat.update`: stop streaming edits, post once. A source token expires: single-flight refresh, or skip that source and say so. Provider outage: LiteLLM to Claude on Amazon Bedrock, then links only. Alerts in Datadog on sync lag over 10 minutes, abstention over 25% and any probe hit; a per-source kill switch.

The decision: **fail closed**. When a permission check errors or times out, drop the document.

**The trap.** Failing open on a slow permission API to keep latency down.

**Rubric criteria earned:** stale ACL after revocation; missed webhooks; fail closed; provider fallback.

### Build Order

**The question:** in what order, and what number unlocks each step?

**How to reason.** Permissions before breadth. Week 1: 400 labelled questions and 500 probes. Week 2: Confluence only, ACL mirror, DM-only bot for IT, recall@8 above 0.85 and zero probe hits. Week 3: Drive and Jira with sync lag p95 under 5 minutes. Week 4: live check and citation check, 95% citation accuracy and a revocation test under 15 minutes. Week 5: channel mode in 4 help channels, first text p95 under 4 s. Week 6: company-wide with the 2-channel holdout, 45% resolved. Roll out by Slack user group: IT, engineering, everyone.

**The trap.** Launching company-wide in week 2 because the demo looked good on public pages.

**Rubric criteria earned:** labelled set and probes first; one source with correct ACLs first; a number per step.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| How permissions apply | Retrieve top 10, then drop what the user can't see | Pre-filter by principals inside the vector query, then live-check the final 30 |
| Channel versus DM | Same answer everywhere, using the asker's access | Channels use org-wide documents only; full access only in DMs |
| Where the money goes | A week on prompt caching | Fewer, better chunks; the cache is worth about $90 a month here |

## 9. Common mistakes

- Never mentioning permissions until the interviewer asks.
- Per-user OAuth search across three APIs on every question, which can't meet 4 s.
- Re-embedding on every ACL change, which is slow and delays revocations.
- A shared answer cache, which leaks across users with different access.
- Doing retrieval before the Slack ack, which produces duplicate answers.
- Failing open when a permission API is slow.
- Showing a "forbidden: <title>" error.

## 10. Follow-ups an interviewer might ask

- *An employee leaves a group at 10:00. Walk me through when they stop seeing its documents.* A group-membership event flushes their Redis principal set at once; without the event the principal cache expires within 10 minutes and the live-check cache within 5. The live check on final candidates catches any mirror lag, so the worst case stays under 15 minutes.
- *A contractor asks in a public channel. Whose permissions apply?* Neither the contractor's nor a full employee's: channel mode uses only documents visible to everyone in the channel, the guest group's if the channel has guests.
- *Your retrieval returns nothing for contractors on half their questions. Why might that be?* Post-filtering after top-k. Pre-filter inside the query and turn on `hnsw.iterative_scan` so tight filters still fill the candidate list.
- *How would you add an "open a ticket" action?* It's out of scope now. It would go on the MCP server as a write tool with the identity taken from the session, behind a confirm step, the same pattern as problem 201 (returns-refunds-agent).
- *How do you know a reranker change didn't hurt?* The 400 labelled questions in CI gate recall@8 above 0.85 and correct abstention on the 40 unanswerable ones.
