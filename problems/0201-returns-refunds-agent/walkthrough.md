## 1. What the problem is really asking

Strip away the apparel story and this is a **chat agent that can move money**. Answering policy questions is ordinary retrieval-augmented generation. The hard part is the 15% of conversations where the agent issues a refund or a return label, because a language model will, sooner or later, do whatever a clever customer talks it into.

So the core tension is: the business wants the agent to act on its own, and the agent is the one component you can't trust to follow a rule. Every strong answer resolves that tension the same way. **The model chooses words and proposes actions; code computes amounts, checks limits and moves money.** Hold that sentence and most of the fifteen sections write themselves.

Three decisions carry the design:

- **Where the limits live.** The $200-per-order and $400-per-customer-per-30-days caps are enforced inside the refund tool, which reads a local ledger. The prompt only explains them.
- **Live data versus policy text.** Orders and payments change every minute, so they're read live through tools. Only the slow-moving prose policy is indexed and retrieved.
- **Who presses the button.** The model proposes a refund; the customer confirms it on a separate endpoint the model can't call; the server re-checks everything and calls Stripe with an idempotency key so a retry can't pay twice.

## 2. The numbers that drive the design

Do this arithmetic out loud in the first few minutes. Every later choice (no queue, no GPU, a cached prompt prefix) follows from it.

**Traffic.**

| Step | Arithmetic | Result |
|---|---|---|
| Turns a month | 60,000 conversations × 4 turns | 240,000 turns |
| Turns a day | 240,000 ÷ 30 | 8,000 turns |
| Busiest hour | 10% of a day's turns, tripled for the holidays: 8,000 × 0.10 × 3 ÷ 3,600 s | about 0.7 turns/s |
| Plan for | round up with headroom | 2 turns/s |

Two turns a second is tiny. It says one small FastAPI service on two Fargate tasks, no message queue and no self-hosted model. If you find yourself drawing Kafka here, the numbers have already told you to stop.

**Money.** 15% of conversations need an action, at an average refund of $68. The caps are $200 per order and $400 per customer per 30 days. The read path gets ordinary care; the write path gets idempotency, a ledger and a human click.

**Latency.** Time to first token p95 under 1.5 s. The model answer spends it like this:

| Stage | p95 |
|---|---|
| API, auth, input guard | 120 ms |
| Router plus retrieval plus order lookup, in parallel | 300 ms |
| Sonnet 5.5 first token on a cached prefix | 600 ms |
| First-sentence citation check | 150 ms |
| Total | 1,170 ms |

120 + 300 + 600 + 150 = 1,170 ms, which leaves 330 ms of slack under 1.5 s. The full refund flow has 20 s; Stripe (1.5 s) plus the Shopify return (1 s) is about 3 s with checks.

**Cost per turn.** Sonnet 5.5 is $2 input, $10 output, $0.20 cached input per million tokens.

| Piece | Arithmetic | Cost |
|---|---|---|
| Cached prefix | 4,500 tokens × $0.20 / 1M | $0.0009 |
| Uncached chunks, thread, question | 2,500 × $2 / 1M | $0.0050 |
| Output | 220 × $10 / 1M | $0.0022 |
| Router and tool follow-ups (averaged) | from the model answer | $0.0009 |
| Per turn | sum | $0.009 |
| Per month | $0.009 × 240,000 | $2,160 |

The prefix is 1,500 tokens of system rules + 1,000 of tool schemas + 2,000 of core policy summary = 4,500. Without the cache those 4,500 tokens cost $2 / 1M instead of $0.20 / 1M, about $0.009 instead of $0.0009, so the turn costs about $0.017 and the month about $4,100. That's over the $3,000 budget. **The prompt cache is the difference between fitting and not fitting**, which is exactly what the prompt asked you to show.

**Corpus.** 1,800 chunks × about 350 tokens is 630,000 tokens, roughly a cent to re-embed everything. 1,800 vectors × 1,536 dimensions × 4 bytes is about 11 MB. That number alone rules out a dedicated vector database.

**Impact.** 55% containment of 60,000 conversations is 33,000 contained conversations; at $6.10 of agent time each that is about $200,000 a month. $2,160 ÷ 33,000 is about $0.065, under the $0.07 cost-per-resolution target.

## 3. How to spend your time

The session is 45 minutes. Aim to say the full answer in about 25 and keep the rest for questions.

| Minutes | What you do |
|---|---|
| 0–3 | Restate the job, ask about the ticket mix and the caps, write the traffic and money numbers on the board |
| 3–8 | **Pillar A:** Scenario with the containment metric and its guard; draw the Single View |
| 8–15 | **Pillar B:** sources and their clocks, chunking, the fixed graph, memory tiers, the tool table |
| 15–21 | **Pillar C:** endpoints and the latency budget, the cache cost table, Postgres plus Redis, output events |
| 21–26 | **Pillar D:** guardrails table, impact with holdout, failure modes, six-week plan |
| 26–45 | Follow-ups, deep dives on idempotency or injection |

If you're short on time, never skip the guardrail table or the cost table. They answer two of the six "strong answer" bullets directly.

## 4. Pillar A: Frame

### Scenario

**The question:** who is the user, what is the job, and what number proves it works?

**How to reason.** The user is the retailer's customer in web chat; the job is "get my return answered or refunded in one conversation instead of nine hours." For the metric, the tempting choice is containment alone. Ask yourself what an agent that refunds everything would score: very high containment. So the model answer pairs **55% containment** (resolved with no human and no reopen within 7 days) with **a wrong-refund rate under 0.3%** against a 1.9% baseline. It grounds both in a tagged sample of 1,000 past Zendesk tickets: 58% answer only, 15% refund or label, 27% need a person. It also names what's out of scope: exchanges for a different product, warranty claims, wholesale accounts.

**The trap.** Writing "accurate and safe" as a requirement. Each of those words must become a number with an audit behind it.

**Rubric criteria earned:** user and job in one sentence; turns per month and peak turns per second derived from 60,000 conversations; a success metric with a target paired with the wrong-refund guard; at least one out-of-scope item.

### Single View

**The question:** what are the layers, what does each hand to the next, and why does each exist?

**How to reason.** Walk a single refund request through the system and name each place a decision is made. The widget sends the message plus a session JWT. The API verifies identity, so the model never supplies a `customer_id`. A LangGraph orchestrator owns the order of steps and the stop rule. Retrieval returns five cited policy chunks. A commerce MCP server holds the limits and idempotency. LiteLLM fronts two model sizes. Guardrails check citations and redact PII. Zendesk receives handoffs. Langfuse traces every turn and runs the 300-conversation eval in CI.

The rubric wants orchestration, retrieval, tools and guardrails as **separate** layers, and it wants the customer's Confirm visible on the diagram. Then close with the one idea: the model chooses words and proposes; the tool server computes, checks and moves money.

**The trap.** One box labelled "LLM agent" with arrows to Shopify and Stripe. That diagram hides every place the money rules could live.

**Rubric criteria earned:** separate orchestration, retrieval, tool and guardrail layers; the customer confirms a refund; one idea separating model decisions from code decisions.

## 5. Pillar B: Build the core

### Data Sources

**The question:** which sources feed the agent, how fresh must each be, and how does each reach the model?

**How to reason.** Sort sources by how fast they change. The 420 help-center articles change about 10 times a week: index them and re-sync on Zendesk's `article.published` webhook. Shopify orders and Stripe charges change every minute: an indexed copy is stale the moment it's written, so read them live through tools. The 30-page internal playbook is the subtle one. It's policy, so your instinct is to index it. But it contains goodwill exceptions that staff grant at their discretion, and a model will quote them as customer policy. The model answer translates the playbook's rules (30-day window, final-sale items, damaged-on-arrival) into a versioned Python rules module reviewed by the returns lead, and never shows the text to customers.

**The trap.** Indexing the internal playbook. It's the single most common way this design leaks a discount.

**Rubric criteria earned:** orders and payments read live through tools; a webhook sync trigger for policy; playbook text kept out of what customers see.

### Processing

**The question:** how do policy pages become citable chunks, and how do edits flow through?

**How to reason.** The alternatives are fixed-size windows or heading-based chunks. Returns policy is written as rules with exceptions under the same heading ("final sale, except damaged items"); a fixed window can cut the rule from its exception. So split on headings to about 350 tokens with 40 tokens of overlap, keep tables whole, and attach `article_id`, `section`, `region`, `updated_at` and `policy_version`. Those fields are used later: citations show the section, and a `region` filter keeps one region's rule from answering another region's customer.

For edits, hash each chunk's text and re-embed only changed hashes, deleting orphans, so a publish is searchable within 2 minutes. State the corpus size: 630,000 tokens, about $0.01 to re-embed in full with `text-embedding-3-small`.

**The trap.** Rebuilding the whole index on every edit and serving a half-built index for the 40 seconds it takes. Upsert by hash in a transaction.

**Rubric criteria earned:** heading chunks with a stated token size; metadata used later; re-embed by content hash; corpus size or embedding cost.

### Agents

**The question:** what is the control flow, and what makes it stop?

**How to reason.** There are only four kinds of turn here: a policy question, an order-status question, a refund or label, and "get me a person". When the paths are known in advance, a free-roaming planner adds risk and buys nothing. Use one agent in a fixed graph: Haiku 5.5 routes each turn (1,200 tokens in, 15 out, about 250 ms), and Sonnet 5.5 handles the chosen path.

The clever move is speculative parallelism. Start retrieval and the recent-orders lookup *while* the router runs, and discard whichever the chosen path doesn't need. It costs about $0.0001 a turn and saves 250 ms of a 1.5 s budget. For refunds, Sonnet picks the order lines, calls `check_eligibility`, and presents the result; nothing runs until the customer presses Confirm.

The stop rule is in code: 8 tool steps, 20 s, two failed eligibility checks, or one explicit "agent please", then `handoff_to_human`.

**The trap.** Letting the model decide when it's done. The model answer notes early versions looped on `get_order` because nothing said the answer was already in context (problem 102, agent-loop-detection, builds that guard).

**Rubric criteria earned:** a fixed graph with routing in code; a step limit and a time limit with numbers; refund only after explicit confirmation; when to hand off.

### Memory

**The question:** what does the agent remember within and across conversations, and where?

**How to reason.** Ask who already owns each fact. Refunds issued and open tickets already live in the refund ledger and Zendesk; those are the customer-level memory and never expire. Within a conversation, keep the last 6 turns verbatim plus typed fields (order id, lines, promised action) in LangGraph's Postgres checkpointer for 90 days, matching the transcript retention. Per-turn tool results and chunks die at the end of the turn. Checkpoint after every step keyed by `thread_id`, so a deploy in the middle of a refund resumes rather than restarts. After 6 turns, compact the older ones into the typed fields with one Haiku call (problem 107, memory-under-token-budget).

This is why the model answer adds no memory product such as Mem0: everything worth remembering already has a system of record.

**The trap.** Putting the customer's name and order list at the top of the system prompt. It breaks the prompt cache on every call. Put per-customer data after the cache breakpoint.

**Rubric criteria earned:** turn, thread and customer tiers each with a store and expiry; checkpointing so a crash resumes; per-customer data kept out of the cached prefix.

### MCP Tool Servers

**The question:** which tools, with what arguments, and what does each enforce?

**How to reason.** Design the tool signatures so that the dangerous arguments don't exist. Three choices do that:

- `customer_id` is **not an argument**. It's injected from the verified JWT at the transport, so the model can't pass someone else's.
- `create_refund(line_ids, reason, idempotency_key)` takes **line ids, not a dollar amount**. The server computes the amount, so the model can't ask for $250 on a $68 shirt.
- The idempotency key is forwarded as Stripe's `Idempotency-Key`, backed by a unique index on `order_line_id` in the ledger.

The rest is a short table: `get_orders`/`get_order` (read, filtered by session customer), `check_eligibility` (read, rules module, returns reasons), `create_return_label` (write, one per line), `handoff_to_human` (write, always allowed). Every tool has a strict JSON schema with `additionalProperties: false` and typed refusal codes the model can act on (problem tool-args-schema-validation builds this).

**The trap.** A tool description that just says "refund the customer". Describe the arguments, the limits and the refusal codes, or the model guesses.

**Rubric criteria earned:** each tool with arguments and read/write; customer id from the session; amount computed server-side; idempotency key on the refund.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what is the API surface, and how is the latency budget spent?

**How to reason.** Three routes and two webhooks: create a session (binding the Shopify customer), post a message (an SSE stream), and **confirm an action**. Confirm is separate because it's the only path where money moves, and the model has no way to call it; it needs a human click carrying the `action_id` the server issued. On Confirm, re-run eligibility and the caps, because the order may have changed since the proposal.

Then split the 1.5 s first-token budget by stage (the 1,170 ms table in section 2). Streaming details matter for the rubric: send a `status` event within 300 ms, number every event, and resume from `Last-Event-ID` after a dropped connection. Verify webhook HMAC signatures and dedupe on the event id. Rate limit 20 turns per customer per 10 minutes in Redis.

**The trap.** Measuring total response time. A 12 s answer that starts in one second feels fast; a 4 s answer that arrives all at once feels broken.

**Rubric criteria earned:** streaming with resume; a staged TTFT budget that fits 1.5 s; confirmation on a route the model can't call; webhook signatures verified.

### Caching

**The question:** what do you cache, what do you never cache, and what does it do to cost?

**How to reason.** There are three candidate caches. The **prompt prefix cache** is the big one: order the prompt stable-first (rules, tool schemas, policy summary), place a `cache_control` breakpoint, then the variable chunks, thread and question. That's the $2,160 versus about $4,100 difference from section 2. Watch `cache_read_input_tokens` in Langfuse and alert if the 24 h hit rate falls under 80%.

An **order cache** in Redis for 60 s per customer absorbs repeat lookups and saves you during Shopify 429s. **Never cache** `check_eligibility` or `create_refund`; a stale eligibility answer is a wrong refund.

A **semantic answer cache** is the one to argue about. First-turn policy questions do repeat, but the model answer estimates a hit would save only about $100 a month, and it risks serving an answer from before the last policy edit. Reject it with that reason.

**The trap.** A timestamp or session id in the system prompt. One changing byte at the top turns every token after it into a cache miss.

**Rubric criteria earned:** stable-first ordering with a breakpoint; per-turn and monthly cost with and without the cache (the model answer gives the monthly no-cache figure; say the per-turn one too); refund and eligibility never cached; a position on a semantic cache.

### Data Stores

**The question:** which stores hold what, how big are they, and why these?

**How to reason.** Three engineers, 11 MB of vectors. One RDS Postgres with pgvector holds the 1,800 chunks under an HNSW index, the refund ledger, the checkpoints and the transcripts (about 1 GB a month, 3 GB at 90 days). One ElastiCache Redis holds rate limits, the 60 s order cache and the stream resume buffer. Langfuse holds traces. Run hybrid search as one SQL query: `tsvector` rank and HNSW cosine, top 20 each, fused with reciprocal rank fusion (k = 60), keep 5 (problem hybrid-search-rrf).

Justify pgvector over Pinecone with a measured number: recall@5 is 0.91 on the golden set and p95 query time is 15 ms. Make the ledger append-only with `UNIQUE(order_line_id)` and `UNIQUE(idempotency_key)`. Delete transcripts after 90 days nightly; keep the ledger 7 years for finance.

**The trap.** Writing refunds only to Stripe. Without a local ledger the 30-day cap needs a slow Stripe search on every request.

**Rubric criteria earned:** each store with contents and size; a local ledger with uniqueness constraints; a measured vector-store justification; transcript retention.

### Output

**The question:** what shapes does the agent return, and which parts come from the model versus the system?

**How to reason.** Free text isn't enough when some of the screen is a financial record. The model answer defines four typed SSE events as Pydantic models: `token` (text with `[n]` markers, from the model), `citation` (from retrieval), `action_proposal` (lines, amount, method, `action_id`, from the tool server) and `receipt`/`handoff` (Stripe refund id or Zendesk ticket, from the tool server). Only the first one comes from the model.

Render receipts only from tool results, and strip any model text claiming "refund processed" when no receipt exists. For handoffs, the human gets a Zendesk internal note: intent, order, what was checked, why it stopped, and a suggested reply.

**The trap.** Letting the model announce a refund in prose. A screenshot of "your refund is on its way" with no refund behind it is a chargeback.

**Rubric criteria earned:** typed shapes beyond free text; amounts and receipts from tool results; what the human receives on handoff.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** for each rule that protects money, data or trust, what enforces it if the model ignores its instructions?

**How to reason.** Use that exact question as a filter. Write each rule in one column and the code that enforces it in the other. Caps: `create_refund` sums the ledger before calling Stripe. Own orders only: `customer_id` from the JWT in every query. No double refund: the unique index plus the Stripe key. No invented policy: every sentence cites a chunk, and numbers must match the chunk exactly. No card data: Stripe returns last 4 only; Presidio redacts emails and phones in traces.

Then the softer layers. Treat order notes, pasted emails and gift messages as quoted data and screen inputs with Lakera Guard (about 60 ms; problem prompt-injection-quarantine). Check each streamed sentence: a citation is present, token overlap with the cited chunk is at least 0.5, and any number or day count appears verbatim. Red-team monthly with Promptfoo using 150 attacks and keep failures as CI cases.

**The trap.** Calling the injection classifier *the* defence. It catches most attempts; the tool server makes the rest harmless.

**Rubric criteria earned:** caps enforced in code; pasted text and notes treated as untrusted; answers checked against cited chunks while streaming; card data and PII out of the model and logs.

### Key Impact

**The question:** what business number moves, and how do you prove the agent caused it?

**How to reason.** The headline is containment, 0% to 55%, gated by wrong refunds, 1.9% to under 0.3%, measured on 200 refunds a week audited by the returns lead. Supporting metrics: median first response 9 h to 5 s, CSAT 4.1 to 4.4 or higher, and LLM cost per resolved conversation under $0.07.

The rubric's attribution criterion needs a **holdout**: for 4 weeks, 10% of sessions go straight to humans, so the comparison is fair against seasonality. Define "resolved" with the 7-day reopen join so an abandoned tab doesn't count. Then translate to dollars: 33,000 contained conversations at $6.10 each is about $200,000 a month.

**The trap.** Counting a conversation as resolved when the customer just closed the tab.

**Rubric criteria earned:** baseline and target; holdout; a resolved definition excluding abandonment; result in dollars.

### Failure Modes

**The question:** what breaks, and what catches each failure?

**How to reason.** Go down the dependency list and ask "what if this is slow, down or wrong?" The prompt itself hands you the first one: a refund call times out and the client retries. Stripe may have already paid. Retrying with the **same** idempotency key returns the original refund, and the ledger row commits in the same transaction as the receipt (problem idempotent-tool-execution). Shopify 429s at the holiday peak: back off with jitter, serve the 60 s cache, say the status may be a minute old. Provider outage: LiteLLM fails over to Claude on Amazon Bedrock, and if both fail, answer-only mode from cached FAQs with actions routed to Zendesk. Retrieval misses a new policy: the citation check fails, the agent abstains and hands off; abstention above 8% pages the team. Loops: 8 steps or 20 s, then handoff with the trace.

Make each one testable: fault-inject with Toxiproxy, alert in Datadog on tool errors, abstentions, cap hits and refunds per hour, and keep a kill switch that turns off `create_refund` without a deploy.

**The trap.** Retrying a refund with a new idempotency key. That's exactly how double refunds happen.

**Rubric criteria earned:** payment timeout with idempotent retry; provider outage fallback; retrieval miss with abstention and handoff; an alert or kill switch.

### Build Order

**The question:** in what order, and what number unlocks each step?

**How to reason.** Order by risk, not by demo value. The model answer runs six weeks: golden set and baseline (week 1), policy index and answer-only agent for staff (recall@5 above 0.9, faithfulness above 0.95), streaming and cache (p95 first token under 1.5 s, under $0.01 a turn), read-only order tools (zero cross-customer reads in 500 fuzzed tests), refunds with human approval for every action (98% agreement), then auto-refund under caps at 10% and then 100% of traffic. Each week is gated in CI on its number, everything ships behind a LaunchDarkly flag, and the 10% holdout runs through week 10.

**The trap.** Building the refund flow first because it's the impressive demo.

**Rubric criteria earned:** eval set before features; a number per step; refunds last, first with approval, then behind a flag.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| Refund amount | The model passes `amount` to the refund tool, and the prompt says "never more than $200" | The tool takes line ids, computes the amount, and sums the ledger against both caps |
| Live order data | Index orders nightly alongside the policy | Read orders live through scoped tools; cache 60 s at most |
| Retry safety | "We retry on timeout" | Retry with the same idempotency key, unique ledger indexes, ledger write in the receipt's transaction |

The common thread: each strong answer removes the model's ability to cause the bad outcome, instead of asking it not to.

## 9. Common mistakes

- Using containment as the only metric, so an agent that refunds everything looks great.
- Taking `customer_id` as a tool argument. One injected message and the agent reads someone else's orders.
- Drawing a vector database, a queue and a GPU cluster for 2 turns a second and 11 MB of vectors.
- Showing a cost estimate without the cache, which lands over the $3,000 budget and never explains how to get under it.
- Letting the model write "your refund has been processed" before a receipt exists.
- Building the impressive refund demo in week 1 and the eval set never.

## 10. Follow-ups an interviewer might ask

- *A customer tries to get past the caps by asking for the refund in several separate chats. What stops it?* The per-order cap is computed over the ledger by order, not per request, and the $400 per-customer 30-day cap sums every row for that customer. Both live in `create_refund`, so the number of chats doesn't matter.
- *Traffic triples after Black Friday and Shopify rate-limits you. What changes?* Back off with jitter, serve the 60 s Redis order cache, and tell the customer the status may be a minute old. Two turns a second is still well within two Fargate tasks.
- *How do you know a prompt change didn't make refunds worse?* The 300 golden conversations run in CI with exact checks on tool calls and a Sonnet judge for faithfulness; a change ships on the score. Weekly, the returns lead audits 200 refunds.
- *The policy editors shorten the return window for sale items. How long until the agent uses it?* The Zendesk webhook triggers a re-embed of changed chunks, searchable within 2 minutes. The eligibility rule itself lives in the versioned rules module, so it needs a reviewed code change; the citation check makes the agent abstain if text and rule disagree.
- *Where would you build the confirm-before-refund gate as code?* Problem human-approval-gates builds it, and problem react-tool-loop (101) builds the loop it sits inside.
