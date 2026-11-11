### Context

You are the VP of AI and Data Science at a regional wireless and home-broadband carrier: 3.2 million mobile subscribers, $2.9B revenue, reporting to the COO. The AI Investment Council, chaired by the CFO, has received eight proposals from five executives, and together they ask for $39M a year in benefits. The council meets in four weeks and wants you to bring a ranked, funded portfolio for next year, with a clear line between what is in and what is out.

### What you have

- **Budget.** $5M of new spend next year (vendors, APIs, contractors). Salaries already on payroll don't count against it.
- **People.** 5 in-house data engineers (60 data-engineer-months a year) and 10 ML engineers (120 ML-engineer-months). Fully loaded cost is assumed at $200k a year for a data engineer and $260k for an ML engineer. A contract data engineer costs an assumed $25k a month.
- **Finance's confidence weights.** The CFO's standard haircut on claimed benefits: measured in a production pilot or A/B test, 80 percent; historical data or back-test, 60 percent; vendor or analyst benchmark, 30 percent; sponsor's own estimate, 20 percent.
- **The proposals.** Benefits are the sponsors' annual claims. DE and ML are engineer-months. "Customer data" means the project needs pipelines on customer call, location or billing records.

| # | Proposal | Sponsor | Sponsor's claimed benefit | Evidence | New spend | DE | ML | Customer data |
|---|---|---|---|---|---|---|---|---|
| P1 | Care virtual agent | SVP Care | Deflect 20% of 1.0M care calls a month at $7 a call: $16.8M | Vendor case study | $1.8M | 18 | 24 | Yes |
| P2 | Agent assist: after-call summaries | SVP Care | Save 50 s on each of 1.0M calls a month at $42 an hour of agent time: $7.0M | 6-week production pilot with 60 agents | $0.6M | 8 | 10 | Yes |
| P3 | Churn-save offer targeting | CMO | Cut monthly churn from 1.25% to 1.20%: 1,600 subscribers kept a month, × $55 ARPU × 6 extra months (sponsor's assumption) × 12: $6.34M | A/B test on 5% of the base measured a 0.03-point cut, not 0.05 | $0.4M | 14 | 18 | Yes |
| P4 | Network alarm triage | CTO Network | 2,500 avoidable truck rolls a year × $600: $1.5M | 12 months of truck-roll history | $0.3M | 12 | 12 | No |
| P5 | Marketing content generation | CMO | Agency fees: $1.2M | Last year's agency invoices | $0.25M | 2 | 4 | No |
| P6 | SIM-swap fraud detection | CISO | Cut $4.0M of annual fraud losses by 45%: $1.8M | Back-test on 12 months of cases | $0.5M | 16 | 14 | Yes |
| P7 | Store associate copilot | SVP Retail | Sales uplift: $2.4M | Sponsor's estimate | $0.9M | 10 | 12 | Yes |
| P8 | Bill-shock explainer | SVP Care | Cut 120,000 bill-shock calls a month (part of the 1.0M) by 20% at $7: $2.0M | Analysis of last year's call drivers | $0.7M | 18 | 14 | Yes |

- **Model use for P2.** A summary averages 5,000 input and 250 output tokens per call. Per million tokens, Haiku 5.5 costs $0.10 input and $0.50 output; Sonnet 5.5 costs $2 and $10. P2's new spend covers transcription and model calls.
- **Board pressure.** Internal audit rated SIM-swap fraud a top-three enterprise risk, and the board's risk committee has asked for a plan this year.

### The constraint

The carrier's policy on customer proprietary network information lets only employees build pipelines on customer call, location and billing records. Contractors may work only on non-customer data. A hiring freeze means no data engineers can be added this year. Six proposals need customer data, and together they need 84 data-engineer-months from a team that has 60.

### What a strong answer covers

- How you turn eight sponsor claims into numbers you can compare, and where two claims count the same calls.
- What the scarce resource really is, and how you rank against it.
- Which proposals are in, which are out, and which are funded in stages.
- What the funded portfolio is worth and costs, separating new spend from payroll.
- How you tell five executives when some of them lose something, and how you'll check the benefits a year from now.
