# Build vs Buy vs Fine-tune: model answer

## 1. Situation

The real question isn't which technology is best. It's which option gets accurate categorization in front of the enterprise customers who renew in 6 months, without breaking their contracts or the budget. Each option fails a different part of that test.

| What | Number | What it forces |
|---|---|---|
| Manual queue | 60M × 28% = 16.8M transactions a month | Cost per transaction matters: every option is priced on 16.8M a month |
| Bookkeeper time | 16.8M × 20 s = 93,333 hours a month | The customer value is time saved |
| Revenue at stake | $12M ARR in 140 renewals; AI cited in 30 of 80 lost deals (37.5%) | The deadline is renewal season, 6 months out |
| Enterprise contracts | 35% of ARR = $63M | No training on their data; 90 days' notice for a new sub-processor |
| People | 4 of 6 engineers free for 6 months | Anything needing all 6 also slips the compliance release |

**How:**
1. Restate the decision as a dated question: what do enterprise customers see at month 6?
2. Out of scope: replacing the rules engine, which already handles 72% at no marginal cost.
3. Treat the bake-off and prototype accuracy figures as estimates to re-test on enterprise data, which the samples underweight.

**Decision.** Frame it as a time-boxed decision about the renewal season with a planned revisit at month 12, not as a permanent platform choice.

**Trap.** Comparing accuracy percentages first. The 91, 93 and 94 percent figures are close and measured on different data. The contract clause and the calendar decide this case before accuracy does.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| CTO | A recommendation they can defend, and the team kept on its commitments | One page: the recommendation, three options on one table, and the revisit trigger |
| CFO | Spend under the $1.5M cap and a 3-year number that holds | Show new spend and payroll separately, and 3-year totals rather than year one |
| CPO | The consolidation feature, which slips two quarters | Agree the trade explicitly: $12M of renewals against a two-quarter slip, with 2 engineers back at month 6 |
| VP Sales | Something to show at renewal season | A dated beta list of renewing accounts, and exactly what sales may and may not promise |
| General Counsel | No contract breach and no surprise sub-processor notice | Show that option B adds no sub-processor and trains nothing; review the customer-facing wording |
| Enterprise controllers | Books they can sign off on | Opt-in auto-apply, every AI posting labelled and reversible, and a month-end review list |
| AI team (6 engineers) | A plan they believe and no death march | Use the 4 who are free; leave the compliance pair alone |

**The one idea to hold:** each stakeholder is protecting a different asset — renewals, budget, roadmap, contracts or the books — and the recommendation has to name what each one gives up.

## 3. Options

Four real options, each scored on the calendar, the contracts and three-year cost. Doing nothing is one of them.

| | A. Buy vendor | B. Build on hosted API | C. Fine-tune 8B | D. Do nothing |
|---|---|---|---|---|
| Live for enterprise | Month 3 at best (90-day notice), and only if nobody objects | Month 6 | Month 9 on paper; about 13.5 with the 4 free engineers | Never |
| Contract fit | New sub-processor: the $63M segment can object | Provider already listed; per-customer context; no training | Can train only on non-enterprise data | n/a |
| Accuracy (stated) | 91% bake-off | 93% with escalation; 98.5% on the confident 75% | 94% offline, non-enterprise data | Rules only |
| 3-year cost (section 5) | $3.39M | $2.11M | $3.67M | $0, plus churn |

**How:**
1. Option C's estimate assumes all 6 engineers, but only 4 are free: 9 × 6/4 = 13.5 months, which misses renewal season.
2. Option A's 8-week integration runs alongside the 90-day notice, so month 3 is the earliest date. An objection from a renewing customer removes the very segment the feature is for.
3. Option B uses only each customer's own history at inference time, so nothing is trained and nobody new sees the data.

**Decision.** Shortlist B, keep A as the fallback if B's beta fails, and defer C to a dated revisit.

**Trap.** Treating "buy" as the low-risk choice. Here it is the one that needs permission from the customers you are trying to keep.

## 4. Decision and Trade-offs

Recommend B: build on the hosted API, with Haiku 5.5 first, the least confident 10% escalated to Sonnet 5.5, and auto-apply only above a confidence threshold. Ship to opted-in enterprise customers at month 6.

| We give up | Why it's worth it |
|---|---|
| Consolidation slips two quarters | It protects $12M of renewals that start in month 6 |
| 2 engineers run the service permanently | That is still $1.28M less than buying over 3 years |
| 1–2 points of accuracy against the fine-tune | C misses the deadline and can't learn from enterprise data |
| Dependence on one model provider | The model sits behind our gateway with an eval set, so it can be swapped |

**How:**
1. **Reversibility:** this is a two-way door. Corrections keep flowing in with consent flags, so fine-tuning stays possible later.
2. **Revisit at month 12** if any of these holds:
   - model spend passes $40k a month, about 5× today's;
   - accuracy plateaus below target;
   - consented data covers 80% of the volume.

**Decision.** B, because it is the only option that meets the date, the contracts and the budget at the same time.

**Trap.** Presenting the decision as permanent. A recommendation without a revisit trigger reads as preference, not judgment.

## 5. Economics

Compare over three years, keep new spend separate from people already on payroll, and use the same volume growth for every option (factor 1 + 1.2 + 1.44 = 3.64).

| | A. Buy | B. Build (API) | C. Fine-tune |
|---|---|---|---|
| Run cost, year-one volume | 16.8M × $0.004 = $67,200 a month | Haiku 16.8M × $0.000165 = $2,772, plus Sonnet 1.68M × $0.0033 = $5,544, so $8,316 a month | 4 GPUs × 730 h × $2.50 = $7,300, plus $15k retraining, so $22,300 a month |
| 3-year run cost | $806.4k × 3.64 = $2.94M | $99.8k × 3.64 = $363k | GPUs $87.6k × 3.64 = $319k, plus retraining $540k |
| People (engineer-years) | Integrate 0.33 + run 0.5 a year (assumed): 1.83 = $458k | Build 2.0 + run 2 engineers from month 6: 7.0 = $1.75M | Build 4.5 + run 3 from month 9 (assumed): 11.25 = $2.81M |
| **3-year total** | **$3.39M** | **$2.11M** | **$3.67M** |
| Year-one new spend | 10 months × $67.2k = $672k | 6 months × $8.3k = $50k | GPUs and retraining from month 9 = $67k, plus initial training runs (not in the brief) |

**How:**
1. **Cost per transaction:** B is $8,316 / 16.8M = $0.000495, about 8 times cheaper than the vendor.
2. **Opportunity cost:** B uses 2.0 engineer-years already on payroll, and the consolidation feature slips two quarters.
3. **Revenue side (assumed):** if the gap costs even 10% of the $12M, that's $1.2M ARR a year, larger than any year-one cost difference.
4. **Customer value:** auto-applying 75% of the queue saves 12.6M × 20 s = 70,000 bookkeeper hours a month.

**Decision.** B costs least over three years and spends $50k of the $1.5M year-one cap. People are its main cost, so the run team of 2 is the number to defend.

**Trap.** Comparing year-one vendor fees with "free" internal engineers. People already on payroll still cost money, and they were going to build something else.

## 6. Org and Ownership

One accountable owner, a small team, and named decision rights for the parts that can hurt customers.

| Role | Who | Owns |
|---|---|---|
| Accountable | You, the principal architect | The recommendation, the eval gates and the revisit at month 12 |
| Delivery | EM plus the 4 moved engineers | Build, beta and GA |
| Product | Categorization PM | Auto-apply UX, opt-in and the review list |
| Finance partner | FP&A | Monthly model spend against the $40k trigger |
| Legal | Privacy counsel | Contract mapping and customer-facing wording |
| After GA | 2 AI-team engineers | Model service, eval set and threshold changes |

**How:**
1. Any change to the confidence threshold or the prompt needs a passing eval run. Nobody changes them on their own say-so.
2. The 2 compliance engineers are out of scope for this project, in writing.

**Decision.** Keep the model service in the AI team and the product experience in the categorization team, so each part has exactly one owner.

**Trap.** Calling the project a "shared" responsibility. With nobody accountable for thresholds, precision drifts until a customer's auditor finds it.

## 7. Plan and Milestones

Six months to GA, with two gates that can stop the project, timed to land before renewal season.

| Month | Milestone | Gate |
|---|---|---|
| 0 | Decision; consolidation paused; CPO and CFO sign the trade | — |
| 1–2 | Eval sets held out per segment (enterprise separately); confidence calibration; cost guard | **Gate 1:** ≥ 98% precision at ≥ 60% coverage on the enterprise holdout |
| 3–4 | Suggestions-only beta: 20 renewing enterprise customers (opt-in) and 500 SMB customers | **Gate 2:** suggestion acceptance and override rate within target |
| 5 | Auto-apply for opted-in customers; month-end review list | Precision holds for 4 weeks |
| 6 | GA before renewal season; sales enablement | — |
| 12 | Revisit fine-tuning against the triggers | Decision record |

**Decision.** The beta starts with renewing enterprise accounts, because that is where both the revenue and the hardest charts of accounts are.

**Trap.** Planning one big launch at month 6. With no gate before it, you find out at renewal season that enterprise accuracy is lower than the prototype's.

## 8. Risk and Governance

The biggest risk is quiet wrong postings, not an outage. At 75% auto-apply and 98.5% precision, 12.6M × 1.5% = 189,000 postings a month are wrong, about 21 per customer.

| Risk | Control |
|---|---|
| Wrong postings reach the books | AI postings are labelled and reversible; month-end review list; enterprise threshold set to 99%; opt-in per customer |
| Contract breach | Context retrieved only from the customer's own history, with an isolation test in CI; no training; consent flag stored on every correction |
| Provider price or model change | Gateway plus eval set, so the model can be swapped in weeks; 8× cost headroom against the vendor |
| Silent regressions | Prompt and threshold changes gated by the regression eval |
| Beta fails Gate 2 | Ship suggestions-only at renewal season, and start the vendor's 90-day notice as the fallback |

**Decision.** The precision floor and the per-customer opt-in are in code and in the product, not in a policy document.

**Trap.** Reporting only overall accuracy. 98.5% sounds safe until it's multiplied by 12.6M postings a month.

## 9. Metrics

Each success metric gets a guard metric that would catch the harm it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| Share of the 16.8M queue auto-applied | 60% at GA, 75% by month 12 | Precision of auto-applied postings ≥ 98.5% (≥ 99% enterprise) |
| Bookkeeper hours saved | 70,000 a month at 75% | 30-day reversal rate of AI postings |
| Enterprise renewal rate | At or above last year | AI cited in lost-deal notes, down from 30 of 80 |
| Cost per categorized transaction | ≤ $0.0006 | Model spend against the $40k-a-month revisit trigger |

**Decision.** Report renewal impact and precision together each month, so a coverage push can't buy revenue with bad books.

**Trap.** Measuring accuracy on all suggestions. What matters to a controller is the precision of what was applied without them.

## 10. Communication

One message, cut for each audience, with a regular cadence until GA.

| Audience | One line |
|---|---|
| CTO and staff | "Build on the API we already use: live for enterprise in 6 months, $2.11M over 3 years, revisit fine-tuning at month 12." |
| CFO | "$50k of new spend in year one, against $672k to buy; the real cost is 2 engineer-years we already pay." |
| CPO | "Consolidation slips two quarters to protect $12M of renewals; you get 2 engineers back at month 6." |
| Sales | "Beta for 20 named renewing accounts from month 3; promise time saved, not an accuracy number." |
| Enterprise customers | "Opt-in, every AI posting labelled and reversible, and your data trains nothing." |

**How:**
1. Weekly status at staff meeting through GA; monthly metrics to the exec team after.
2. Gate results go out on the day, including a failed gate.

**Decision.** Lead with the date and the trade, not the technology. That's what every audience is deciding on.

**Trap.** Letting sales quote the prototype's 93%. That number is measured on a different mix, and it becomes a contractual expectation.
