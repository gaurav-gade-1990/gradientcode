### Context
A building-supplies distributor pays about 2,400 vendors, and nine accounts-payable clerks key every invoice into NetSuite by hand. Keying takes about 6 minutes an invoice, the month-end backlog reaches 3 days, and the company pays $14,000 a month in late fees while missing early-payment discounts. About 0.3% of invoices get paid twice, usually because the same invoice arrived by email and through the vendor portal. Last quarter a fake "our bank details have changed" invoice nearly cost $86,000. The CFO wants invoices and vendor forms read, checked and posted automatically, with people reviewing only what needs them.

### Requirements
- Accept documents from the `ap@` Microsoft 365 mailbox and from uploads on the vendor portal.
- Split multi-document PDFs, classify each document (invoice, credit note, statement, W-9, other) and extract the fields and line items.
- Validate each invoice against the vendor master, the purchase order and the goods receipt, then post it to NetSuite as a vendor bill.
- Send anything uncertain, out of tolerance or risky to a review queue that shows the page with the extracted fields highlighted.
- Never post a duplicate, and never change where a vendor gets paid based on a document.

### Scale and constraints
- 18,000 invoices and 3,000 other documents a month, 2.5 pages on average; 85% PDF, 10% phone photos or scans, 5% Excel or Word.
- 40% of the monthly volume arrives in the last 5 business days.
- About 60 new vendors a month; the top 200 vendors send 70% of invoices.
- Each document must be posted or waiting in the review queue within 15 minutes of arrival.
- Auto-post limit: $25,000 per invoice. Above that, a person approves.
- OCR plus LLM budget: $2,000 a month. Team: three engineers, no GPUs.
- Originals kept 7 years for tax; W-9s carry taxpayer ids (sometimes SSNs).

### What a strong answer covers
- How each extracted field gets a confidence you can trust, and what routes a document to review.
- Which checks are rules in code, and what stops a well-formed but fraudulent invoice from being paid.
- How duplicates are caught across channels and across a NetSuite timeout and retry.
- The cost and processing time per document, and how the month-end peak is absorbed.
- How you measure straight-through rate and field accuracy, and how reviewer corrections improve the system.
