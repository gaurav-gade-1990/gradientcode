# Document Intake Pipeline: model answer

## 1. Scenario
Accounts-payable clerks need invoices read, checked and posted without keying them, and they need the risky ones put in front of them with the reason. The pipeline extracts and validates; code decides what posts; people handle the exceptions.

| What | Number | What it drives |
|---|---|---|
| Volume | 21,000 documents, 52,500 pages a month | OCR is the biggest line item |
| Peak | 40% in the last 5 business days: 1,680 a day, about 170 an hour, 340 in the busiest hour (0.1 docs/s) | A queue absorbs month-end; no autoscaling heroics |
| SLA | Posted or queued for review within 15 minutes | Async pipeline, not a request/response API |
| Money | $25,000 auto-post cap, three-way match, no duplicates, no bank-detail changes | Rules in code, before the ERP call |
| Budget | $2,000 a month for OCR plus LLM | Small model to classify, mid model to extract |

**How:**
1. Pull 1,000 recent invoices from NetSuite with their PDFs; the posted bills are free ground-truth labels.
2. Time the current process: 6 minutes keying per invoice, 3-day month-end backlog, 0.3% paid twice.
3. Agree the success metric with the controller: straight-through rate (posted with no human touch and no correction within 30 days).
4. Out of scope: paying invoices (treasury's weekly run stays as is), expense receipts, and vendor onboarding beyond reading the W-9.

**Decision.** Target 65% straight-through with key-field accuracy of 99.5% on what posts. Straight-through alone would reward posting wrong bills.

**Trap.** Measuring OCR accuracy instead of posting accuracy. A perfect transcription of a duplicate invoice is still a duplicate payment.

## 2. Single View

| Layer | What runs here and what it hands over | Why we need it |
|---|---|---|
| Intake | Microsoft Graph mail subscription and portal upload; virus scan; file stored in S3 by SHA-256. Hands over a `doc_id` | One door for two channels, and the first duplicate check |
| Queue and state | SQS plus a Postgres status table with leases and retries. Hands over one job per document | Month-end bursts wait in a queue instead of failing |
| Split and classify | Claude Haiku 5.5 labels each page. Hands over typed documents with page ranges | One PDF often holds three invoices and a statement |
| OCR | AWS Textract AnalyzeExpense. Hands over words, boxes, confidences and its own field guesses | Text with coordinates is what makes highlights and evidence possible |
| Extraction | Claude Sonnet 5.5 fills a strict JSON schema, citing the OCR line ids for every field. Hands over fields with evidence | Normalizes 2,400 vendor layouts into one shape |
| Validation | Rules in Python: arithmetic, vendor match, PO and receipt match, duplicates, bank details, cap. Hands over post, review (with reasons) or reject | The model never decides what gets paid |
| ERP MCP server | Vendor, PO and receipt lookups; `create_vendor_bill` with an idempotency key. Hands over a NetSuite bill id | Limits and idempotency live next to the ERP |
| Review app (Retool) | Page image with highlighted spans, reason codes, edit and approve. Hands over corrections | Clerks fix the 35% in about 3 minutes, not 6 |
| Evals and traces (Langfuse) | 500 golden documents nightly, every call traced, corrections logged | Accuracy per field and per vendor, every day |

**The one idea to hold:** a field is trusted because its evidence checks out in code, not because the model said it was confident.

## 3. Data Sources
Two inbound channels and one system of record. The channels overlap, which is where duplicates come from.

| Source | Volume | How it arrives |
|---|---|---|
| `ap@` mailbox (Microsoft 365) | 80% of documents | Graph change notification, then fetch attachments |
| Vendor portal uploads | 20% | Multipart POST to the intake API |
| NetSuite vendor master | 2,400 active vendors, about 60 new a month | Read through the ERP MCP server |
| NetSuite POs and item receipts | About 6,000 open POs | Read live at validation time |

**How:**
1. Subscribe to Graph `messages` notifications on the mailbox; renew the subscription every 2 days with a scheduled job, and run a 15-minute delta sweep as a backstop for missed notifications.
2. Save every attachment and the email body to S3 keyed by SHA-256; an identical file from the other channel is linked to the existing `doc_id`.
3. Read vendor, PO and receipt data at validation time, never from a nightly copy: a receipt booked at 10:02 must match an invoice at 10:05.

**Decision.** Content-hash dedupe at intake catches the exact resend. Invoice-number dedupe in validation catches the rescanned copy.

**Trap.** Relying on Graph webhooks alone. Subscriptions expire silently and the inbox fills while the dashboard looks quiet.

## 4. Processing
Every document is turned into page images and OCR text with coordinates before any model sees it.

**How:**
1. Normalize inputs: PDFs as-is, photos deskewed and converted with Pillow, Excel and Word rendered to PDF with LibreOffice headless. Reject encrypted files and anything over 60 pages to review.
2. Classify each page with Haiku 5.5 (first page of invoice, continuation, credit note, statement, W-9, other) and split on first pages.
3. Run Textract AnalyzeExpense per document (async API); store the JSON in S3 under the file hash.
4. If Textract's mean word confidence is under 0.80 (bad phone photos, about 10%), also send page images to Sonnet 5.5 for the extraction step.

**Decision.** Textract and Sonnet extract independently, and agreement between them is the main confidence signal. One extractor cannot tell you when it is wrong.

**Trap.** Sending raw PDFs straight to the model. You lose word coordinates, so the review screen cannot highlight where a number came from.

## 5. Agents
This is a pipeline with two model calls, not an agent. The steps never change, so there is nothing for a planner to decide.

**How:**
1. Run the steps as a state machine in the worker: `received`, `split`, `ocr_done`, `extracted`, `validated`, then `posted`, `in_review` or `rejected`.
2. Give the extraction call no tools: OCR lines and the vendor profile in, schema JSON out, with structured output enforcing the schema.
3. Use one small agentic step for exceptions: when a PO number is missing, Haiku drafts a vendor email asking for it; a clerk approves before it sends.

**Decision.** No tools for the extractor. A model that can only return JSON cannot be talked into posting anything by text printed on an invoice.

**Trap.** Building a ReAct agent that "looks up the PO and decides". It turns a deterministic match into a probabilistic one.

## 6. Memory
The memory that matters is per vendor: how their documents look and what reviewers have corrected.

| Tier | Holds | Lives in | Expires |
|---|---|---|---|
| Job | OCR, extraction, validation results for one document | Postgres status table, S3 | 7 years with the document |
| Vendor profile | PO number format, usual currency and tax, 2 corrected examples | Postgres `vendor_profiles` | Rebuilt weekly from corrections |
| Corrections | Field, predicted value, corrected value, reviewer | Postgres `corrections` | Never; it is the eval source |

**How:**
1. After each review, write one `corrections` row per changed field.
2. Weekly, pick each vendor's two most recent corrected documents as few-shot examples for its profile.
3. Insert the profile after the prompt cache breakpoint so the shared prefix stays cached.

**Decision.** Per-vendor few-shot examples instead of fine-tuning. The top 200 vendors send 70% of invoices, and a profile update takes effect the same week.

**Trap.** Letting a correction on one invoice rewrite the vendor master. Corrections change the profile; vendor-master changes go through NetSuite approval.

## 7. MCP Tool Servers
One ERP server built with the Python MCP SDK wraps NetSuite's REST API. The pipeline, the review app and any future agent hit the same guards.

| Tool | Does | Guard in code |
|---|---|---|
| `find_vendor(name, tax_id, remit_to)` | Fuzzy vendor match | Returns a score and the bank details on file |
| `get_po(po_number)`, `get_receipts(po_number)` | PO lines and received quantities | Read only |
| `find_bills(vendor_id, invoice_number, total, date_range)` | Duplicate search | Read only |
| `create_vendor_bill(doc_id, fields, idempotency_key)` | Posts the bill | Re-runs every validation rule; refuses above $25,000 without an approver id |

**How:**
1. Authenticate with a NetSuite integration role that can create bills but cannot edit vendors or create payments.
2. Set NetSuite `externalId` to the `doc_id`, so a retried post updates the same bill instead of creating a second one.
3. Return typed errors (`DUPLICATE`, `PO_MISMATCH`, `OVER_CAP`) that map directly to review reason codes.

**Decision.** The posting tool re-checks the rules itself. If a bug in the worker skips validation, the ERP boundary still holds.

**Trap.** Giving the integration role vendor-edit rights "for convenience". That is the permission a bank-detail fraud needs.

## 8. Endpoints
The pipeline is asynchronous; the endpoints accept documents, report status and serve the review app.

| Route | Purpose |
|---|---|
| `POST /v1/documents` | Portal upload; returns `doc_id` |
| `POST /hooks/graph` | Mail notification; validates the client state secret |
| `GET /v1/documents/{id}` | Status, reason codes, NetSuite bill id |
| `GET /v1/review/queue`, `POST /v1/review/{id}` | Review list; submit corrections and approve or reject |

Processing time per document at p95 (2.5 pages):

| Stage | p95 |
|---|---|
| Intake, virus scan, S3 write | 5 s |
| Split and classify (Haiku 5.5) | 2 s |
| Textract AnalyzeExpense (async) | 20 s |
| Extraction (Sonnet 5.5, about 600 output tokens) | 12 s |
| Validation with vendor, PO and receipt lookups | 6 s |
| Post to NetSuite | 4 s |
| **Total** | **49 s** |

**How:**
1. Run FastAPI on one ECS Fargate service and the workers as a second service of 4 tasks; at 0.1 docs/s and 49 s each, about 5 documents are in flight at peak.
2. Cap Textract and NetSuite concurrency per worker so the busiest hour stays under their rate limits.
3. Alert when the oldest queued document is older than 10 minutes.

**Decision.** Queue depth, not request latency, is the SLO signal. Under 1 minute of work against a 15-minute SLA leaves room for a 10-minute backlog.

**Trap.** Processing inside the webhook handler. Graph expects a reply within 3 seconds and stops sending notifications after repeated timeouts.

## 9. Caching
OCR output is the expensive thing to recompute, so it is cached by file hash forever.

| Per document (list prices; Textract $0.01 a page assumed) | With cache | Without |
|---|---|---|
| Textract, 2.5 pages | $0.0250 | $0.0250 |
| Haiku 5.5 classify, 1,500 tokens in | $0.0002 | $0.0002 |
| Sonnet 5.5: 3,000 prefix tokens ($0.20 or $2 per MTok) | $0.0006 | $0.0060 |
| Sonnet 5.5: 3,000 OCR tokens in, 600 out | $0.0120 | $0.0120 |
| Vision fallback, averaged over 10% of documents | $0.0008 | $0.0008 |
| **Per document / per month at 21,000** | **$0.039 / $810** | **$0.044 / $920** |

**How:**
1. Put the system rules and the JSON schema (3,000 tokens) first, then a `cache_control` breakpoint, then the vendor profile and the OCR text.
2. Key stored Textract JSON by SHA-256; re-extraction after a prompt change costs only LLM tokens.
3. Cache vendor-master lookups in a Postgres table for 10 minutes; never cache PO receipts or duplicate searches.

**Decision.** Use the Message Batches API (50% off) for the nightly replay of the 500 golden documents, about $95 a month instead of $190, but not for live invoices: batch results can take hours and the SLA is 15 minutes.

**Trap.** Caching the duplicate search. Two copies of one invoice arriving a minute apart both pass a cached "no match".

## 10. Data Stores
S3 and one Postgres. Nothing here needs a vector database.

| Store | Holds | Size |
|---|---|---|
| S3 | Originals, page images, Textract JSON | About 17 GB a month, 1.4 TB at 7 years; Glacier after 1 year |
| RDS Postgres | Status table, fields with evidence, corrections, vendor profiles, posting ledger | About 2 GB a year |
| Langfuse | Traces of every model call | About 1 GB a month |

**How:**
1. Store each field as `(doc_id, field, value, ocr_line_ids, textract_value, confidence, source)`, so any number on a bill traces back to a box on a page.
2. Keep a posting ledger with `UNIQUE(vendor_id, normalized_invoice_number)` and write it in the same transaction as the outbox row that triggers the NetSuite post.
3. Turn on S3 Object Lock in compliance mode for the 7-year retention.

**Decision.** Transactional outbox for posting. The ledger row and the "post this" message commit together, so a crash never leaves a bill posted with no record, or recorded but never posted.

**Trap.** Normalizing the invoice number only by trimming spaces. `INV-00123`, `inv 123` and `00123` are the same invoice; strip prefixes, punctuation and leading zeros per vendor.

## 11. Output
Each document ends in one of three states, and each produces something typed.

| State | Output |
|---|---|
| `posted` | NetSuite vendor bill with the PDF attached and a link back to the evidence |
| `in_review` | Queue item with reason codes, highlighted fields and a suggested fix |
| `rejected` | Reason (not an invoice, unreadable, duplicate) and a reply to the sender if needed |

**How:**
1. Validate extraction output against a Pydantic schema; on failure, re-ask once with the validation error, then send to review.
2. Write amounts as integer cents with an ISO currency code, and dates as ISO 8601.
3. Show reviewers the reason codes in order of risk: bank details, duplicate, over cap, PO mismatch, low confidence.

**Decision.** A review item always says why it is there. "Low confidence" alone sends clerks hunting; "total does not equal subtotal plus tax by $40.00" takes ten seconds.

**Trap.** Posting a partly extracted bill and letting a clerk "fix it in NetSuite". The corrections never reach the eval set.

## 12. Guardrails
Every rule that protects money runs in code before the ERP call, and again inside the posting tool.

| Rule | Enforced by |
|---|---|
| Auto-post only up to $25,000 | Validation and `create_vendor_bill` |
| Three-way match: price within 2% or $50, quantity not above received | PO and receipt lookups |
| No duplicates | Ledger unique key rejects; a fuzzy match (same vendor, same total, dates within 7 days) goes to review |
| Invoices with no PO (utilities, services) | Always review, routed to the budget owner in NetSuite |
| Remit-to bank details must equal the vendor master | Any difference is a hold; documents never update the master |
| Arithmetic: lines sum to subtotal, subtotal plus tax equals total within $0.01 | Validation |
| TINs and SSNs never reach the model | W-9 pages use Textract only; values masked in logs |

**How:**
1. Compute each field's confidence from evidence: value found verbatim in the cited OCR lines, Textract agrees, Textract word confidence at least 0.95. Any key field failing goes to review.
2. A bank-detail mismatch triggers a callback to the phone number already on file, by the AP lead, outside the system.
3. Treat document text as data: instructions printed on an invoice have no tool to act on.

**Decision.** Limits that protect money, permissions or privacy live in code, never in a prompt. The prompt never even mentions the cap.

**Trap.** Trusting the model's own confidence score. It reports 0.97 on a misread total as readily as on a correct one.

## 13. Key Impact
One headline and four that explain it.

| Metric | Baseline | Target | Measured by |
|---|---|---|---|
| Straight-through rate | 0% | 65% | Posted, no human touch, no correction in 30 days |
| Key-field accuracy on posted bills | n/a | 99.5% | 100 posted bills a week audited by a senior clerk |
| Duplicate payments | 0.3% of invoices | Under 0.02% | Ledger plus treasury clawbacks |
| Clerk minutes per invoice | 6 | Under 1.5 on average | Review app timings |
| Late fees | $14,000 a month | Under $2,000 | NetSuite late-fee GL account |

**How:**
1. Run in shadow for two weeks: extract and validate every document but let clerks key as usual, then compare field by field.
2. Report field accuracy per field and per vendor from the `corrections` table every morning.
3. Translate: 18,000 invoices from 6 to 1.5 minutes frees about 1,350 clerk hours a month.

**Decision.** Accuracy is audited on posted bills, not on the review queue. The posted ones are where an error costs money unseen.

**Trap.** Counting reviewed-and-unchanged documents as model errors. They show the routing is too cautious, which is a threshold problem, not an accuracy one.

## 14. Failure Modes
Month-end is when everything is busiest and when every failure costs the most. Each failure needs a named catch.

- **Textract throttles at month-end.** Workers back off with jitter and the queue absorbs it; queue age above 10 minutes pages the on-call.
- **NetSuite times out after creating the bill.** The retry carries the same `externalId` and returns the existing bill; the ledger is unchanged.
- **A vendor changes its invoice layout.** That vendor's daily field accuracy drops under 97%; its documents route to review until the profile is rebuilt.
- **Model provider outage.** LiteLLM fails over to Claude on Amazon Bedrock; if both fail, documents wait in the queue, which the SLA can absorb for about 10 minutes.
- **Poison document** (encrypted, 400 pages, corrupt). Three attempts, then the dead-letter queue and a review item.

**How:**
1. Write each row as an integration test with the fault injected.
2. Alert in Datadog on queue age, dead-letter count, per-vendor accuracy and bank-detail holds.
3. Keep a flag that turns off auto-posting and sends everything to review, without a deploy.

**Decision.** When in doubt, route to review. A one-day delay costs a late fee at worst; a wrong post costs the payment.

**Trap.** Retrying a post with a new idempotency key after a timeout. That creates the duplicate the system exists to prevent.

## 15. Build Order
1. **Week 1:** 500 golden documents labeled from posted NetSuite bills. Number: baseline keying time and duplicate rate.
2. **Week 2:** intake, OCR and the review app with Textract fields only. Number: key-field accuracy of Textract alone.
3. **Week 3:** Sonnet extraction with evidence and agreement scoring. Number: accuracy above 99% on golden documents marked high-confidence.
4. **Week 4:** validation rules and the ERP server, in shadow mode. Number: rule decisions match clerk decisions on 98% of documents.
5. **Week 5:** auto-post under $5,000 for the top 50 vendors. Number: zero duplicates, accuracy 99.5% in the weekly audit.
6. **Week 6:** raise to $25,000 and all vendors. Number: straight-through rate 65%.

**How:**
1. Gate each week in CI on its number; a missed number blocks the next week.
2. Raise the cap and the vendor list by config, not by deploy.
3. Add every reviewer correction to the golden set weekly, capped at 50 new documents per vendor.

**Decision.** Review app before automation. Clerks use it from week 2, so the corrections that train the vendor profiles start flowing early.

**Trap.** Turning on auto-posting for all vendors at once. Start where volume is high and layouts are stable.
