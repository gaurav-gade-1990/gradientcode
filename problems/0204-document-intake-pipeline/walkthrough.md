## 1. What the problem is really asking

This is an **accounts-payable pipeline that decides whether to pay someone**. Reading invoices is the visible part, and modern OCR plus a mid-size model will extract fields well enough. The part that costs money is everything after extraction: is this a duplicate, does it match the purchase order and the goods receipt, is it over the cap, and did the vendor's bank details just "change"?

The core tension: the CFO wants as many invoices as possible posted with no human, and every auto-posted invoice is a payment that nobody looked at. So the design has to answer *why a field can be trusted* and *what code refuses to post*, not just *how fields get extracted*.

Three decisions carry the design:

- **Confidence comes from evidence, not from the model.** A field is trusted when its value appears verbatim in the cited OCR lines, Textract independently agrees, and Textract's word confidence is at least 0.95. The model's self-reported confidence is ignored.
- **Money rules run in code twice.** The validation step applies the $25,000 cap, the three-way match, duplicate checks and the bank-detail rule; the NetSuite posting tool re-runs them at the ERP boundary.
- **Duplicates are caught in layers.** A content hash at intake catches the same file arriving by email and portal; a unique key on vendor plus normalised invoice number catches the rescan; NetSuite's `externalId` makes a retried post after a timeout return the original bill.

## 2. The numbers that drive the design

**Volume and peak.**

| Step | Arithmetic | Result |
|---|---|---|
| Documents a month | 18,000 invoices + 3,000 other | 21,000 |
| Pages a month | 21,000 × 2.5 | 52,500 |
| Month-end per day | 40% of 21,000 over 5 business days | 1,680 a day |
| Month-end per hour | spread over about 10 working hours | about 170 an hour |
| Busiest hour | about double that | 340 an hour, about 0.1 docs/s |

0.1 documents a second is a queue and a few workers. The month-end spike is absorbed by queueing, not autoscaling heroics.

**Time per document.** The SLA is posted or in review within 15 minutes. The model answer's p95 stages:

| Stage | p95 |
|---|---|
| Intake, virus scan, S3 write | 5 s |
| Split and classify (Haiku 5.5) | 2 s |
| Textract AnalyzeExpense (async) | 20 s |
| Extraction (Sonnet 5.5, about 600 output tokens) | 12 s |
| Validation lookups | 6 s |
| Post to NetSuite | 4 s |
| Total | 49 s |

At 0.1 docs/s and 49 s each, Little's law gives 0.1 × 49 ≈ 5 documents in flight, so 4 worker tasks are enough. Under a minute of work against 15 minutes means a 10-minute backlog is survivable, which is why the alert is on **queue age**, not request latency.

**Cost per document.** Textract is an assumed $0.01 a page; Sonnet 5.5 is $2 / $10 per MTok with $0.20 cached; Haiku 5.5 is $0.10 input.

| Line | Arithmetic | With cache | Without |
|---|---|---|---|
| Textract | 2.5 pages × $0.01 | $0.0250 | $0.0250 |
| Haiku classify | 1,500 × $0.10 / 1M | $0.0002 | $0.0002 |
| Sonnet prefix | 3,000 × $0.20 / 1M, or × $2 / 1M | $0.0006 | $0.0060 |
| Sonnet OCR text and output | 3,000 × $2 / 1M + 600 × $10 / 1M | $0.0120 | $0.0120 |
| Vision fallback, averaged over 10% | from the model answer | $0.0008 | $0.0008 |
| Per document | sum | $0.039 | $0.044 |
| Per month | × 21,000 | about $810 | about $920 |

Two things to notice. OCR is the biggest single line, so caching Textract output by file hash forever matters more than the prompt cache. And the whole pipeline sits well inside the $2,000 budget, so you don't need to squeeze; you need to spend on correctness.

**Impact.** 18,000 invoices × (6 − 1.5) minutes = 81,000 minutes, about 1,350 clerk hours a month.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–3 | Restate the job; write volume, pages, month-end peak and the $25,000 cap on the board |
| 3–8 | **Pillar A:** straight-through rate gated on posted-bill accuracy; draw the pipeline with a queue |
| 8–16 | **Pillar B:** two channels and live ERP reads, OCR with coordinates, a state machine, per-vendor profiles, the ERP server |
| 16–22 | **Pillar C:** 49 s budget and queue age, cost table, evidence-carrying field store with an outbox, three end states |
| 22–27 | **Pillar D:** the rule table including bank details, shadow period, failure modes, a capped rollout |
| 27–45 | Follow-ups, often the $86,000 fraud case or the timeout-and-retry case |

The prompt's context hands you two war stories: duplicates from two channels, and a fake bank-details invoice. Make sure your answer visibly defeats both.

## 4. Pillar A: Frame

### Scenario

**The question:** who is the user, what is the job, and which numbers shape the design?

**How to reason.** The users are the nine AP clerks and the controller; the job is "invoices read, checked and posted without keying, with the risky ones put in front of a clerk with the reason." Derive the month-end peak (section 2). Get ground truth cheaply: 1,000 recent NetSuite bills with their PDFs are free labels. Time the current process: 6 minutes keying, 3-day backlog, 0.3% paid twice.

The metric is **straight-through rate**, posted with no human touch and no correction within 30 days, at 65%. On its own it rewards posting wrong bills, so pair it with **key-field accuracy of 99.5% on what posts**. Out of scope: paying invoices (treasury's weekly run stays), expense receipts, and vendor onboarding beyond reading the W-9.

**The trap.** Measuring OCR accuracy. A perfect transcription of a duplicate is still a duplicate payment.

**Rubric criteria earned:** user and job in one sentence; month-end peak from the 40% in 5 days; straight-through with an accuracy guard; payments out of scope.

### Single View

**The question:** draw the pipeline as layers.

**How to reason.** Each layer is one transformation: intake (Graph mail subscription and portal upload, virus scan, S3 keyed by SHA-256), **a queue** (SQS plus a Postgres status table with leases and retries; problem agent-task-queue-leases), split and classify (Haiku per page), OCR (Textract AnalyzeExpense: words, boxes, confidences), extraction (Sonnet fills a strict schema citing OCR line ids for every field), validation (Python rules deciding post, review or reject), an ERP MCP server (lookups and an idempotent `create_vendor_bill`), a review app in Retool (page image with highlighted spans), and Langfuse evals over 500 golden documents nightly.

The one idea: a field is trusted because its evidence checks out in code, not because the model said it was confident.

**The trap.** Drawing extraction and posting as one "AI" step. The rubric wants validation and posting as separate layers from extraction.

**Rubric criteria earned:** separate intake, OCR, extraction, validation, posting and review; a queue after intake; the extraction-versus-posting idea.

## 5. Pillar B: Build the core

### Data Sources

**The question:** where do documents come from, what's checked against, and how fresh?

**How to reason.** Two inbound channels overlap, and that overlap is where the 0.3% duplicates come from: the `ap@` mailbox (80%, Graph change notifications) and portal uploads (20%). Store every attachment in S3 by SHA-256; an identical file from the other channel links to the existing `doc_id`. Graph subscriptions expire, so renew them every 2 days on a schedule and run a 15-minute delta sweep as a backstop.

The system of record is NetSuite: 2,400 vendors (about 60 new a month) and about 6,000 open POs. Read vendors, POs and receipts **live at validation time**, because a receipt booked at 10:02 must match an invoice arriving at 10:05.

**The trap.** Relying on Graph webhooks alone. Subscriptions expire silently and the inbox fills while the dashboard looks quiet.

**Rubric criteria earned:** both channels and their overlap; live PO and receipt reads; a backstop for missed notifications.

### Processing

**The question:** how does a raw file become typed documents with text and coordinates?

**How to reason.** Normalise first: PDFs as-is, photos deskewed with Pillow, Excel and Word rendered to PDF with LibreOffice headless; encrypted files and anything over 60 pages go to review. Haiku classifies each page (first page of invoice, continuation, credit note, statement, W-9, other) and you split on first pages, because one PDF often holds three invoices and a statement.

Run Textract AnalyzeExpense on each document and store the JSON under the file hash. Coordinates are the reason to OCR at all: they're what lets the review screen highlight where a number came from. For bad scans (mean word confidence under 0.80, about 10% of documents), also send the page images to Sonnet. Then Textract and Sonnet have extracted independently, and **their agreement is the confidence signal**. One extractor can't tell you when it's wrong.

**The trap.** Sending raw PDFs straight to the model and losing coordinates.

**Rubric criteria earned:** split and classify; OCR with coordinates and confidences; a low-quality path with a trigger; non-PDF handling.

### Agents

**The question:** is this an agent or a pipeline, and where does the model get to act?

**How to reason.** The steps never change, so nothing needs a planner. Run a state machine with named states: `received`, `split`, `ocr_done`, `extracted`, `validated`, then `posted`, `in_review` or `rejected`. The extraction call gets **no tools**: OCR lines and the vendor profile in, schema JSON out, enforced with structured output. That's also an injection defence: a model that can only return JSON can't be talked into posting by text printed on an invoice.

There's one small agentic step: when a PO number is missing, Haiku drafts an email to the vendor asking for it, and a clerk approves before it sends (problem human-approval-gates).

**The trap.** A ReAct agent that "looks up the PO and decides". It turns a deterministic match into a probabilistic one.

**Rubric criteria earned:** a state machine with named states; no tools and a strict schema for extraction; approval for drafted messages.

### Memory

**The question:** what does the system learn and keep between documents?

**How to reason.** The useful memory is per vendor. A `vendor_profiles` table holds each vendor's PO number format, usual currency and tax, and two corrected examples, rebuilt weekly. Every review writes one `corrections` row per changed field (field, predicted, corrected, reviewer), kept forever as the eval source. Job state lives with the document for 7 years.

Why few-shot profiles instead of fine-tuning? The top 200 vendors send 70% of invoices, so a handful of profiles cover most volume, and an update takes effect the same week. Insert the profile **after** the cache breakpoint so the shared prefix stays cached.

**The trap.** Letting a correction rewrite the vendor master. Corrections change the profile; vendor-master changes go through NetSuite approval. This is also how the bank-detail fraud is kept out of the learning loop.

**Rubric criteria earned:** per-vendor knowledge in a named store; field-level corrections; vendor master kept out of learning.

### MCP Tool Servers

**The question:** what ERP operations are exposed, with what permissions?

**How to reason.** One ERP server (Python MCP SDK) over NetSuite's REST API, shared by the pipeline, the review app and any future agent. Reads: `find_vendor(name, tax_id, remit_to)` (fuzzy match, returning the bank details on file), `get_po`, `get_receipts`, `find_bills` (the duplicate search). One write: `create_vendor_bill(doc_id, fields, idempotency_key)`, which **re-runs every validation rule** and refuses above $25,000 without an approver id.

Three guards: the NetSuite integration role can create bills but **can't edit vendors or create payments**; `externalId` is set to the `doc_id` so a retry finds the same bill; typed errors (`DUPLICATE`, `PO_MISMATCH`, `OVER_CAP`) map straight to review reason codes.

**The trap.** Giving the role vendor-edit rights for convenience. That's exactly the permission a bank-detail fraud needs.

**Rubric criteria earned:** lookup and posting tools with read/write; idempotent posting; money rules re-checked inside the tool; a role that can't edit vendors or pay.

## 6. Pillar C: Serve and store

### Endpoints

**The question:** what's the API surface, and how long does a document take?

**How to reason.** The pipeline is asynchronous, so endpoints only accept, report and serve review: `POST /v1/documents` (portal upload), `POST /hooks/graph` (validates the client state secret), `GET /v1/documents/{id}`, and the review queue routes. Show the 49 s table and the in-flight estimate (about 5 documents at peak, 4 worker tasks). Cap Textract and NetSuite concurrency per worker to stay under their rate limits, and alert when the oldest queued document is older than 10 minutes.

**The trap.** Processing inside the webhook handler. Graph expects a reply within 3 seconds and stops sending notifications after repeated timeouts.

**Rubric criteria earned:** per-stage time within 15 minutes; documents in flight at peak; fast webhook ack; queue age as the alert.

### Caching

**The question:** what do you cache, what do you never cache, and what does a document cost?

**How to reason.** Show the per-document and monthly table ($0.039 and about $810 with the prompt cache; $0.044 and about $920 without). Cache Textract JSON by SHA-256 forever, so re-extracting after a prompt change costs only tokens. Put the 3,000-token rules and schema first, then the breakpoint, then the vendor profile and OCR text. Vendor-master lookups can cache for 10 minutes.

Batch pricing is the other lever. The Message Batches API is 50% off, so the nightly replay of 500 golden documents costs about $95 a month instead of $190. It's wrong for live invoices: batch results can take hours and the SLA is 15 minutes.

**Never cache** PO receipts or duplicate searches. Two copies of one invoice a minute apart would both pass a cached "no match".

**The trap.** Caching the duplicate search.

**Rubric criteria earned:** per-document and monthly OCR and token cost; prompt cache and batch effect; OCR cached by hash; duplicate checks and receipts never cached.

### Data Stores

**The question:** which stores, how big, and how is posting kept consistent?

**How to reason.** S3 holds originals, page images and Textract JSON: about 17 GB a month, 1.4 TB over 7 years, moved to Glacier after 1 year, with Object Lock in compliance mode for retention. RDS Postgres holds the status table, fields with evidence, corrections, profiles and the posting ledger (about 2 GB a year). No vector database is needed.

Two design points earn most of the rubric here. Store each field as `(doc_id, field, value, ocr_line_ids, textract_value, confidence, source)`, so any number on a bill traces back to a box on a page. And use a **transactional outbox**: the ledger row with `UNIQUE(vendor_id, normalized_invoice_number)` and the "post this" message commit in one transaction, so a crash never leaves a bill posted with no record, or recorded but never posted (problem transactional-outbox).

**The trap.** Normalising invoice numbers by trimming spaces only. `INV-00123`, `inv 123` and `00123` are the same invoice; strip prefixes, punctuation and leading zeros per vendor.

**Rubric criteria earned:** storage sized with 7-year retention; values with evidence; vendor plus normalised number unique key; outbox.

### Output

**The question:** what does each document end as, and what does a reviewer see?

**How to reason.** Three typed end states. `posted`: a NetSuite bill with the PDF attached and a link to the evidence. `in_review`: reason codes, highlighted fields, a suggested fix. `rejected`: a reason and, if needed, a reply to the sender. Validate extraction against a Pydantic schema and re-ask once with the error, then send to review (problem structured-output-repair). Amounts are integer cents with an ISO currency code; dates are ISO 8601. Order reason codes by risk: bank details, duplicate, over cap, PO mismatch, low confidence.

The decision: **a review item always says why.** "Low confidence" sends a clerk hunting; "total does not equal subtotal plus tax by $40.00" takes ten seconds.

**The trap.** Posting a partly extracted bill and letting a clerk fix it in NetSuite. The correction never reaches the eval set.

**Rubric criteria earned:** typed end states; specific reason codes; schema validation with a bounded retry.

## 7. Pillar D: Run it safely

### Guardrails

**The question:** what stops a wrong, duplicate or fraudulent invoice from posting?

**How to reason.** Write the rule table, all in code. Cap: $25,000 in validation and in `create_vendor_bill`. Three-way match: price within 2% or $50, quantity not above received. Duplicates: the ledger key rejects; a fuzzy match (same vendor, same total, dates within 7 days) goes to review. No-PO invoices (utilities, services): always review, routed to the budget owner. Bank details: any difference from the vendor master is a hold, and documents never update the master. Arithmetic: lines sum to subtotal, subtotal plus tax equals total within $0.01. TINs and SSNs: W-9 pages use Textract only, values masked in logs.

The fraud case from the prompt is defeated by two of these together: the remit-to mismatch puts the invoice on hold, and the AP lead calls back on **the phone number already on file**, outside the system. A well-formed fake invoice can't change where money goes.

**The trap.** Trusting the model's own confidence. It reports 0.97 on a misread total as readily as on a correct one.

**Rubric criteria earned:** cap and match tolerance in code; bank-detail hold with out-of-band verification; evidence-based confidence; taxpayer ids kept from the model and logs.

### Key Impact

**The question:** what numbers move, and how are they measured?

**How to reason.** Headline: straight-through rate, 0% to 65%. Supporting: key-field accuracy 99.5% on 100 posted bills a week audited by a senior clerk; duplicates from 0.3% to under 0.02%; clerk minutes from 6 to under 1.5; late fees from $14,000 to under $2,000 a month. Before any auto-posting, run **two weeks in shadow**: extract and validate everything while clerks key as usual, then compare field by field. Report per-field and per-vendor accuracy from `corrections` every morning. Translate: about 1,350 clerk hours a month.

**The trap.** Counting reviewed-and-unchanged documents as model errors. They show routing is too cautious, a threshold problem.

**Rubric criteria earned:** straight-through baseline and target; audit with a sample size; shadow period; hours or dollars.

### Failure Modes

**The question:** what breaks, and what catches it?

**How to reason.** Month-end is when everything is busiest and every failure costs most. Textract throttles: jittered backoff, the queue absorbs it, queue age over 10 minutes pages. NetSuite times out after creating the bill: the retry carries the same `externalId` and returns the existing bill. A vendor changes its layout: its daily field accuracy drops under 97% and its documents route to review until the profile is rebuilt. Provider outage: LiteLLM fails over to Claude on Amazon Bedrock; otherwise documents wait, which the SLA absorbs for about 10 minutes. Poison documents: three attempts, then the dead-letter queue and a review item. Keep a flag that turns off auto-posting without a deploy.

**The trap.** Retrying a post with a new idempotency key (problem idempotent-tool-execution).

**Rubric criteria earned:** ERP timeout with idempotent retry; throttling or outage at month-end; per-vendor accuracy monitoring; dead-letter path.

### Build Order

**The question:** in what order, and what number unlocks each step?

**How to reason.** Week 1: 500 golden documents from posted bills. Week 2: intake, OCR and the review app with Textract fields only. Week 3: Sonnet extraction with agreement scoring, above 99% on high-confidence golden documents. Week 4: validation and the ERP server in shadow, matching clerk decisions on 98%. Week 5: auto-post under $5,000 for the top 50 vendors, zero duplicates and 99.5% audited. Week 6: $25,000 and all vendors, 65% straight-through. The cap and vendor list change by config, not deploy.

The decision worth defending: **the review app ships in week 2**, so the corrections that build vendor profiles start flowing early.

**The trap.** Auto-posting for all vendors at once. Start where volume is high and layouts are stable.

**Rubric criteria earned:** golden set first; a number per step; a lower cap and vendor subset first.

## 8. The decisions that separate strong answers

| Decision | Weak answer | Strong answer |
|---|---|---|
| Field confidence | Ask the model how confident it is | Verbatim in cited OCR lines, Textract agrees, word confidence at least 0.95 |
| Fraudulent bank details | "Flag suspicious invoices" | Remit-to must equal the master; documents never update it; callback to the number on file |
| Timeout and retry | Retry the post | Same `externalId`, unique ledger key, outbox so ledger and ERP can't diverge |

## 9. Common mistakes

- Treating it as an OCR accuracy problem and never mentioning the three-way match.
- Giving the extractor tools, or an agent loop that decides what to post.
- Caching the duplicate search, or deduping only on exact invoice-number strings.
- An ERP role that can edit vendors.
- Processing inside the Graph webhook handler.
- Turning on auto-post for every vendor and the full cap on day one.

## 10. Follow-ups an interviewer might ask

- *The same invoice arrives by email and portal, but one is a rescan. Which layer catches it?* Not the content hash, because the bytes differ. The ledger's `UNIQUE(vendor_id, normalized_invoice_number)` catches it, and the fuzzy rule (same vendor, same total, dates within 7 days) sends near-matches to review.
- *An invoice says "our bank has changed, please pay this account". What happens?* Remit-to differs from the vendor master, so it's a hold. The AP lead calls the number on file. The document can't update the master, and the integration role can't edit vendors.
- *A big vendor redesigns its invoice. How quickly do you notice?* Its daily field accuracy from `corrections` drops under 97%, routing its documents to review until the profile is rebuilt with two new corrected examples.
- *Month-end volume doubles next year. What breaks first?* Textract and NetSuite rate limits, not your workers; concurrency caps and queue-age alerting keep you inside the 15-minute SLA while you raise limits.
- *How do reviewer corrections make the system better?* They're stored per field, feed the weekly vendor profiles as few-shot examples, and join the golden set at up to 50 documents per vendor.
