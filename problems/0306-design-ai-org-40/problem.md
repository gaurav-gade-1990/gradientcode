### Context

You are the newly hired VP of AI at a mid-size electric and gas utility: $3.2B of annual revenue, 2.1M electric and gas customers, 4,800 employees. AI grew bottom up. Today 40 people do AI work across four reporting lines, there are three separate LLM vendor contracts, and nobody keeps a single list of the models in production. The CEO wants a target org design for the board in 6 weeks. In 9 months the state public utility commission (PUC) starts a review that, for the first time, will examine the company's AI governance program.

### What you have

- **The 40 people today.**
  - Central data science, 16 people, reporting to the VP of Rates: demand forecasts and cost-of-service models, including the general rate case.
  - Grid operations AI squad, 9, reporting to the SVP of Electric Operations: outage prediction and crew dispatch.
  - Billing AI squad, 5, reporting to the VP of Customer Billing: meter-to-cash exception review.
  - Customer service AI squad, 4, reporting to the Head of Service: the chat and email assistant.
  - ML platform, 6, reporting to the CIO: feature store and model serving.
- **Cost.** Fully loaded cost is assumed at $260k per person a year.
- **Board commitment.** The outage restoration program must reach $12M of annual run-rate savings (fewer truck rolls and less storm overtime) by month 12. It is at $3M today. The SVP of Electric Operations estimates that losing one of the 9 grid operations engineers this year slips the ramp by 2 months.
- **Duplication.** Each of the three squads runs its own LLM vendor contract and integration. The contracts total $1.5M a year and all renew within 6 months; procurement holds a single enterprise quote at $0.9M a year. Each squad spends about 1.5 engineers' time running its own integration. The platform lead estimates one shared gateway would take 1.5 engineers to run.
- **Models.** 23 in production (14 classical, 9 LLM-based). 6 of them influence decisions about customers (disconnection for non-payment, payment-plan eligibility, billing exceptions and restoration priority) and are in the review's scope.
- **Governance work before the review** (Chief Risk Officer's estimate): a written AI governance program and bias-testing standard, 20 person-weeks; an inventory of all 23 models, 1 person-week each; independent validation of each in-scope model, 10 person-weeks each. An outside validation firm has quoted $60k per model. The CRO's 2-person model risk team is fully booked validating financial and commodity-hedging models and has no ML or LLM experience.
- **Budget.** $1.2M of non-headcount spend in year one (vendors, contractors, consultants).
- **People risk.** AI staff attrition runs at 15% a year. HR's rule of thumb (assumed): a change of manager adds 10 points of attrition for the affected people over the next year. Backfills are allowed under the freeze; each departure is assumed to cost $130k (recruiting plus ramp, half a year's loaded cost).
- **Legal.** General Counsel estimates an adverse PUC finding on AI governance at $2M in penalties and remediation (assumed).

### The constraint

Headcount is frozen at 40 for 12 months, and the review requires validators who don't report to anyone who builds the models they validate. That independent capacity has to come from the 40. But the VP of Rates needs at least 13 data scientists to deliver the general rate case, which supports a 6% increase on $1.4B of residential revenue, and the grid operations squad can't lose anyone this year without putting the board commitment at risk.

### What a strong answer covers

- Which options are really on the table, from "change nothing" to "one AI org", and what each does to the review, the restoration commitment and the rate case.
- Where the independent validators come from, and whether that capacity is enough by the review.
- What a reorg costs in people, not just in boxes on a chart, and which moves are hard to undo.
- How you get shared standards and one LLM contract from teams that don't report to you.
- How you bring the board, the CEO, the business heads, the VP of Rates and the CRO along, and what the 40 people hear.
