### Context

You are the CTO of a European payment processor, licensed as a payment institution: €620M of net revenue, 85,000 merchants, €140B processed a year. 92 percent of the company's LLM traffic goes to one model provider, through one cloud provider's hosted endpoint. After reviewing the company's register of ICT third-party arrangements, which DORA requires, the national supervisor asked how the company would exit this provider for services that support critical or important functions. The board risk committee wants an exit plan and a recommendation on the provider's renewal offer at its meeting in 10 weeks. The contract renews in 5 months.

### What you have

- **Workloads, by share of LLM spend.**
  - **Merchant onboarding (KYB) document review, 40%.** The company classifies onboarding as a critical or important function in its DORA register.
  - **Chargeback dispute evidence drafting, 25%.** Analysts can fall back to templates, at about twice the time per case.
  - **Merchant support assistant, 20%.** Falls back to the human support queue.
  - **Internal tools (coding, analytics), 15%.** Can stop for a week without customer impact.
- **Spend.** €3.6M a year at list price today, forecast to grow 30 percent a year (finance forecast, assumed).
- **The renewal offer.** Commit €9M over 3 years and get 25 percent off list on everything you buy from the provider. A smaller option: commit €4M for 10 percent off.
- **Onboarding.** 11,000 applications a week. 60 reviewers, with about 30 productive hours a week each (assumed). A review takes 8 minutes with AI and 35 minutes without. Operations data says 12 percent of applicants delayed more than a week abandon, and a lost merchant costs about €4,200 of first-year net revenue.
- **Second provider.** A different model provider, on a different cloud. After 6 weeks of prompt work, it scored 95.1 percent on the KYB evaluation set, against the incumbent's 96.4 percent. Its per-token prices are assumed equal to the incumbent's list prices, with no discount.
- **Self-hosted option.** An open-weight model scored 89 percent on the same evaluation set. Serving it would need 8 H100 GPUs at an assumed €2.30 per GPU-hour.
- **Engineering.** Your platform engineers are on payroll at €180k a year fully loaded (assumed). The team estimates a warm standby for onboarding and disputes at 3 engineers for 6 months, then 1 engineer to run it and its quarterly failover drills; a 50/50 active-active split at 5 engineers for 6 months, then 2 to run it; a self-hosted fallback at 3 engineers for 6 months, then 2.
- **Board risk appetite** (set last quarter): a service supporting a critical or important function must run degraded for no more than 24 hours after a vendor failure, and must be movable off a vendor within 90 days.

### The constraint

The CFO has already booked the 25 percent discount into next year's budget, and the 25 percent requires the €9M commitment to the very vendor the board wants you less dependent on. Every euro of traffic you move to a second provider makes the commitment harder to meet, and a paper exit plan won't meet the board's 24-hour limit for onboarding.

### What a strong answer covers

- What a week without the incumbent would cost in onboarding, and whether any option other than a live second provider meets the 24-hour limit.
- How much traffic can move without missing the €9M commitment, and what forecast that depends on.
- What each option costs over three years, separating new spend from engineers already on payroll.
- What to ask for in the renewal beyond price.
- What the board, the supervisor and the CFO each hear, and what would make you revisit the commitment.
