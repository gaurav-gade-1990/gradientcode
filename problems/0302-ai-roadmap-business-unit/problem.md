### Context

You are the new Director of AI for the Contractor Solutions business unit of a national industrial distributor of electrical and maintenance supplies. The unit sells $640M a year at a 24 percent gross margin, through 38 branches and 110 inside sales reps who turn contractors' requests for quotes (RFQs) into priced quotes. Six BU leaders have each sent you an AI initiative, and together they need more people than you have. The BU general manager wants a 12-month AI roadmap at the quarterly business review in three weeks, and has already told the CEO the unit will show $3M a year of AI-driven gross profit by month 12.

### What you have

- **Team.** 8 engineers and a PM. One engineer runs the existing demand-forecast model all year, so 7 are free: 84 engineer-months. Fully loaded cost is assumed at $230k per engineer a year.
- **Budget.** New year-one spend (APIs, tools, seats, contractors) is capped at $900k. Existing salaries don't count against it.
- **The quote business.** 12,000 RFQs a month by email, PDF and spreadsheet, averaging 12 lines and $4,800 each. A rep spends about 40 minutes matching lines to SKUs. Quotes sent within 4 business hours win 31 percent of the time; later ones win 22 percent. Today 25 percent go out within 4 hours. Reps have about 140 productive hours a month each (assumed by sales ops).
- **The six initiatives.** Effort is the team's estimate in engineer-months.

| Initiative | Sponsor | What it does | Effort | Writes to ERP? | Sponsor's case |
|---|---|---|---|---|---|
| Quote Assist, draft-only | VP Inside Sales | Reads the RFQ, matches lines to SKUs, shows a draft the rep re-keys into ERP | 30 | No | Prototype: 40 → 25 minutes per RFQ |
| Quote Assist, write-back | VP Inside Sales | Writes the draft straight into ERP as a quote | +12 on top of draft-only | Yes | Prototype: 40 → 15 minutes |
| Catalog enrichment | Product management | Extracts attributes from supplier PDFs into the product-information system for 420,000 SKUs | 10 | No | Raises Quote Assist's top-1 SKU match from 71% to 86% on a test set |
| Site search and substitutes | E-commerce | Fixes zero-result searches on the $96M-a-year contractor portal (14% of searches today); needs catalog enrichment first | 20 | No | +2% portal revenue |
| AR dispute triage | BU finance | Routes 2,600 invoice disputes a month and drafts credit memos | 16 | Yes | $400k a year in collector time and earlier cash |
| Rep account briefs | VP Field Sales | Pre-call briefs from CRM history | 14 | No | No estimate; the CRM vendor sells a built-in copilot at an assumed $50 per user a month |

- **Quote speed.** Sales ops expects draft-only to get 45 percent of quotes out within 4 hours, and write-back 60 percent (their estimate from the prototype).
- **Model use.** Quote Assist on Sonnet 5.5: about 12,000 input and 1,500 output tokens per RFQ. Catalog enrichment on Haiku 5.5: 3,000 input and 400 output tokens per SKU, with the hardest 10 percent re-run on Sonnet 5.5. Per million tokens, Haiku 5.5 costs $0.10 input and $0.50 output; Sonnet 5.5 costs $2 and $10.

### The constraint

The group is moving to a new ERP, with cutover in month 6. From month 4 through month 9, quote, order and invoice objects are frozen: no new integrations and no writes from new systems. Read-only access to the reporting replica stays open. The group's last two system cutovers slipped by 2 and 3 months.

### What a strong answer covers

- What goes in which quarter, what is cut or deferred, and why the freeze drives the order.
- How much of the $3M promise is credible, and what you tell the GM.
- What each initiative is really worth once you stop taking sponsors' numbers at face value.
- What happens if the ERP cutover slips.
- How you bring six sponsors along when some of them won't get what they asked for this year.
