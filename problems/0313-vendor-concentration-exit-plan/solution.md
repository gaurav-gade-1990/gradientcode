# Vendor Concentration and Exit Plan: model answer

## 1. Situation

The board isn't really asking for a document. It's asking whether onboarding, a critical function, survives the incumbent provider failing, and whether the company could leave it within 90 days, without giving up the discount the CFO has already booked. The answer depends on one number: what a week without the incumbent costs.

| What | Number | What it forces |
|---|---|---|
| Onboarding capacity without AI | 60 × 30 h × 60 / 35 = 3,086 a week, against 11,000 | Manual fallback covers 28% of demand |
| Weekly backlog in an outage | 11,000 − 3,086 = 7,914 applications | The 24-hour limit is about onboarding |
| Cost of a week | 7,914 × 12% abandon × €4,200 = €3.99M of first-year revenue | About €570k a day |
| Three-year spend at list | €3.6M + €4.68M + €6.08M = €14.36M (30% growth, assumed) | The commitment is sized on this forecast |
| The discount | 25% of €14.36M = €3.59M over 3 years | The CFO's number |

**How:**
1. Restate the ask as two tests: onboarding degraded for no more than 24 hours, and every critical workload movable within 90 days.
2. Tier the workloads: onboarding is critical; disputes and support have human fallbacks; internal tools can stop for a week.
3. Out of scope: the fraud models, which don't use this provider, and moving clouds for the rest of the platform.

**Decision.** Treat this as buying continuity for one critical workload at a known price, and keep the other three on cheaper fallbacks.

**Trap.** Treating all LLM traffic as equally critical. That turns a targeted fix into an expensive active-active build for coding tools.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| Board risk committee | The risk appetite met and evidence it works | A tested failover, with drill results each quarter |
| Supervisor | A credible exit strategy for critical functions, not a binder | A live second provider for onboarding and an exit runbook with dates |
| CFO | The 25% discount kept | 90% of traffic stays on the incumbent, which still meets the €9M commitment |
| Chief Risk Officer | Concentration reduced in the register | Onboarding on two providers and two clouds |
| Head of Operations | No onboarding backlog | Failover in hours; the 60 reviewers handle the 1.3-point quality gap |
| Procurement and legal | A contract that supports exit | Termination assistance, version-retirement notice, data deletion and price protection in the renewal |
| Incumbent provider | The €9M commitment | Commitment signed, with exit terms attached |
| Platform engineers | A build that isn't thrown away | Gateway routing and per-provider evals, reused for every future model change |

**The one idea to hold:** the board, the supervisor and the CFO all get what they want if exit readiness is bought for the one critical workload and paid for by keeping the rest on the discount.

## 3. Options

Four options, scored on the 24-hour limit, the 90-day exit, the commitment and three-year cost.

| | A. Paper plan, full commit | B. Warm standby for onboarding | C. Active-active 50/50 | D. Self-hosted fallback |
|---|---|---|---|---|
| Onboarding within 24 h | No: manual covers 28% | Yes: second provider already live on 25% of onboarding | Yes | Yes, at 89% quality |
| Exit within 90 days | On paper; never tested | Onboarding already moved; the others ported in parallel, about 6 weeks each (assumed from the onboarding port) | Yes | Onboarding only |
| €9M commitment | Met, 100% of traffic | Met: 90% × €14.36M × 75% = €9.70M | Not met; 10% tier only | Met |
| 3-year cost (section 5) | €10.77M | €11.85M | €15.00M | €12.43M |

**How:**
1. B sends 10% of all traffic to the second provider: a quarter of onboarding (10% / 40%), enough to keep it live and measured.
2. C sends €7.18M to each side, below the €9M commitment, so it falls back to 10% off and loses most of the discount.
3. D keeps everything on the incumbent but fails over to a model that scores 89%, 7.4 points below the incumbent, so reviewers would catch far more errors in a crisis.

**Decision.** Shortlist B. Keep D as the answer only if no second provider passes the evaluation.

**Trap.** Calling A an exit plan. A plan that has never been run meets neither of the board's limits.

## 4. Decision and Trade-offs

Recommend B: sign the €9M commitment, run a quarter of onboarding live on a second provider on a different cloud, drill failover quarterly, give disputes and support documented fallbacks, and negotiate exit terms into the renewal.

| We give up | Why it's worth it |
|---|---|
| €1.08M over 3 years compared with A | It's less than two days of an onboarding outage (€570k a day) |
| €359k of discount on the 10% that moves | The rest of the €3.59M is kept: €3.23M |
| 1.3 points of KYB accuracy on a quarter of onboarding | Reviewers check every case already; the gap is measured each week |
| One engineer permanently on the standby | Drills are what turn the plan into evidence |

**How:**
1. **Reversibility:** routing is a gateway setting, so the split can change daily. The commitment is the one-way door, which is why the forecast it depends on is a trigger.
2. **Revisit** if:
   - growth falls below about 22% a year: at that rate, 90% of traffic only just meets €9M (solve 0.9 × 0.75 × €3.6M × (1 + x + x²) = €9M, so x = 1.219);
   - the second provider's KYB score falls more than 2 points behind;
   - a drill takes longer than 24 hours.

**Decision.** B, because it is the only option that meets both board limits and keeps the commitment the CFO has booked.

**Trap.** Signing the commitment without checking it against the traffic you plan to move. The discount looks free until diversification makes the minimum hard to reach.

## 5. Economics

Three years, the same 30% growth for every option, with new spend kept apart from engineers already on payroll.

| | A. Paper plan | B. Warm standby | C. Active-active | D. Self-hosted |
|---|---|---|---|---|
| Incumbent spend (new) | €14.36M × 75% = €10.77M | 90% × €14.36M × 75% = €9.70M | 50% × €14.36M × 90% = €6.46M | €10.77M |
| Second provider or GPUs (new) | — | 10% × €14.36M = €1.44M | 50% × €14.36M = €7.18M | 8 × 8,760 h × €2.30 × 3 = €0.48M |
| Build (payroll) | — | 3 × 0.5 y × €180k = €0.27M | 5 × 0.5 × €180k = €0.45M | €0.27M |
| Run, 2.5 years (payroll) | — | 1 × 2.5 × €180k = €0.45M | 2 × 2.5 × €180k = €0.90M | €0.90M |
| **3-year total** | **€10.77M** | **€11.85M** | **€15.00M** | **€12.43M** |
| Year-one new spend | €3.6M × 75% = €2.70M | €2.43M + €0.36M = €2.79M | €1.62M + €1.80M = €3.42M | €2.70M + €0.16M = €2.86M |

**How:**
1. **B against A:** €11.85M − €10.77M = €1.08M over three years, which equals €1.08M / €3.99M = 0.27 weeks, about 1.9 days, of onboarding outage.
2. **Year one:** B adds €90k of new spend to the CFO's budget; the engineers are already on payroll.
3. **Opportunity cost:** 1.5 engineer-years of build come off the platform roadmap.
4. **C's real cost** is the lost discount, not the engineering: it pays list on half the traffic and 10% off on the rest.

**Decision.** B costs €1.08M more than doing nothing, which is cheaper than two days of the outage it prevents, and it keeps €3.23M of the €3.59M discount.

**Trap.** Pricing exit readiness against zero. The comparison is against the cost of the outage and the exit, which the paper plan simply doesn't count.

## 6. Org and Ownership

One owner for third-party AI risk, and drills owned by the people who would run a real failover.

| Role | Who | Owns |
|---|---|---|
| Accountable | You, CTO | The exit plan, the routing split and the drill results |
| Platform | Head of AI platform plus 1 engineer | Gateway routing, per-provider evals, quarterly drills |
| Workload owners | Heads of onboarding, disputes and support | Their fallback procedure and staffing for a drill |
| Contract | Procurement with legal | Renewal terms, register entries, notice periods |
| Second line | CRO's ICT third-party risk team | Challenge of the plan; concentration reporting to the board |
| Finance | FP&A | Commitment tracking against the €9M |

**How:**
1. Each workload has a written fallback with a named owner and a tested switch time.
2. FP&A reports commitment progress quarterly, so a shortfall is visible a year before it lands.

**Decision.** The workload owners, not the platform team, own their fallbacks, because they're the ones who staff a real outage.

**Trap.** Leaving the exit plan with procurement. A contract clause can't move traffic.

## 7. Plan and Milestones

The second provider is live on onboarding before the renewal is signed, so the commitment is signed knowing the standby works.

| When | Milestone | Gate |
|---|---|---|
| Weeks 0–4 | Renewal terms drafted; exit asks to procurement | — |
| Weeks 0–8 | Second provider integrated behind the gateway for onboarding | **Gate 1:** KYB evaluation at least 95% |
| Week 10 | Board risk committee: recommendation, costs, drill plan | Decision minuted |
| Months 3–4 | 25% of onboarding live on the second provider; first failover drill | **Gate 2:** full onboarding switched in under 4 hours |
| Month 5 | Renewal signed with commitment and exit terms | Terms agreed |
| Months 4–6 | Disputes integrated and drilled; support and internal port runbooks written | Disputes drill under 24 hours |
| Quarterly | Failover drill; results to the board risk committee | Any drill over 24 hours is reported as a breach |

**Decision.** Run the first drill before signing, because a failed drill changes what you should commit to.

**Trap.** Building the standby after signing. Once the commitment is signed, the incentive to finish the standby disappears.

## 8. Risk and Governance

The risks are a standby that silently stops working, a commitment you can't meet, and a contract with no way out.

| Risk | Control |
|---|---|
| Standby degrades unnoticed | It carries live traffic every day, and its KYB score is compared weekly |
| Prompts drift apart between providers | One evaluation set, run on both providers before any prompt change ships |
| Commitment shortfall | FP&A tracks it quarterly; the 22% growth trigger is reviewed each quarter |
| Incumbent retires a model version | Ask for notice of version retirement in the contract (6 months, as a negotiating ask) |
| No exit support from the incumbent | Ask for termination assistance and a transition period, as the company's DORA programme expects for critical functions |
| Both providers fail together | Manual review at 3,086 a week; onboarding prioritises the largest merchants |
| Data left behind on exit | Contract terms for deletion on exit, with confirmation |

**How:**
1. The register of ICT third-party arrangements is updated with both providers and the tested switch time.
2. Concentration is reported to the board as a share of critical-function traffic: 75% on the incumbent for onboarding after the change, down from 100%.

**Decision.** Live traffic on the standby is the control that matters, because a standby that serves nothing is only verified on the day you need it.

**Trap.** Treating contract clauses as the exit. They make an exit cheaper; only a working second path makes it possible.

## 9. Metrics

Each resilience metric is paired with a guard on what it costs or hides.

| Success metric | Target | Guard metric |
|---|---|---|
| Drill switch time for onboarding | Under 4 hours, every quarter | KYB score on the standby, within 2 points of the incumbent |
| Share of critical-function traffic on the incumbent | 75% for onboarding | Commitment progress against €9M |
| Workloads with a tested fallback | 3 of 3 customer-facing by month 6 | Reviewer error rate on standby-processed cases |
| Discount retained | €3.23M of €3.59M | Spend on the second provider against €1.44M |

**Decision.** Report drill results and commitment progress together, so neither resilience nor the discount can drift without the board seeing it.

**Trap.** Measuring the exit plan by whether it exists. The only meaningful metric is how long a real switch took.

## 10. Communication

Each audience hears the number it is accountable for.

| Audience | One line |
|---|---|
| Board risk committee | "Onboarding fails over to a second provider in hours, tested quarterly; €1.08M over three years, less than two days of outage." |
| Supervisor | "A live second provider for our critical function, a dated exit runbook for the rest, and drill evidence." |
| CFO | "We keep €3.23M of the €3.59M discount and add €90k in year one; the €9M is safe while growth stays above about 22%." |
| Incumbent provider | "We'll commit €9M, with exit and version-retirement terms in the contract." |
| Operations | "Failover in hours, with a quarter of onboarding already on the standby." |

**How:**
1. Quarterly drill results to the board risk committee, including any failure.
2. FP&A's commitment report goes to the CFO with the same cadence.

**Decision.** Lead with the drill result, not the plan, because evidence is what the supervisor asked for.

**Trap.** Telling the CFO the discount is fully safe. It depends on 22% growth, and saying so now avoids a surprise in year three.
