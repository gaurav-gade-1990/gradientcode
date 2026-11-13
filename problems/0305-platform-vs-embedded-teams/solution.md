# Platform Team vs Embedded AI Teams: model answer

## 1. Situation

The board's question is about risk, the CFO's about spend and the CTO's about structure, and they've been bundled into one reorg. Pull them apart. The 90-day control doesn't need anyone to move. Most of the savings come from a shared gateway, not from the org chart. What's left is who owns that gateway, and how few people have to move to staff it.

| What | Number | What it forces |
|---|---|---|
| AI payroll | 150 × $280k = $42M a year | People are the biggest AI cost, and the hardest to move back |
| Duplicated infrastructure | 36 roles, 24% of AI staff; a platform needs 22 | 22 people need to move, not 150 |
| Model spend, next 12 months | $1.5M × (1.05 + 1.05² + … + 1.05¹²) = $1.5M × 16.71 = $25.1M | Large enough that a few levers pay for any platform |
| Month-12 run rate | $1.5M × 1.05¹² = $2.69M a month | Savings grow with it |
| Audit deadline | 90 days, every unit, one owner | A control is needed before any reorg could finish |
| Autos | 40% of spend, launch in month 5, $60M ARR planned | Autos people stay put until month 7 |

**How:**
1. Separate three decisions: the risk control (90 days), the platform (who builds and runs the shared layer), and the operating model (where product AI people sit).
2. Out of scope: the autos pricing advisor itself, and vendor selection beyond enforcing contracts with zero-retention terms.

**Decision.** Meet the deadline with a control that needs no people to move, and size the reorg to the 22 platform roles rather than to all 150.

**Trap.** Treating the incident as proof that everyone must be centralized. The résumé leak was an unapproved vendor call, which a network control stops in weeks.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| CEO | A board-ready answer that doesn't break the autos launch | One page: control by day 90, 22 people moved, autos untouched until month 7, $27.3M net over 3 years |
| Audit committee | One owner for AI risk and a working control in 90 days | You are named owner; the egress allow-list is live 2 weeks after approval; the gateway covers 60% of spend by day 90 and all of it by month 7 |
| CFO | Lower model spend, credible numbers | $6.7M saved in year one, with the levers priced from list prices and the audit |
| CTO | Their centralization proposal | Co-own the shared infrastructure standards; the platform runs on CTO infrastructure; explain why 150 moves cost $2.5M in attrition and risk the launch |
| Autos president | Nobody moves before launch | Agreed: no autos person moves until month 7; the allow-list needs no autos engineering |
| Jobs president | To put the incident behind them | Their gateway is the platform's starting point (assumed the strongest of the five) |
| Other three presidents | Keep their product teams and roadmaps | Product AI stays embedded; only infrastructure roles move; model savings land in their P&Ls |
| 36 infrastructure staff | Clarity, a career path, no surprises | 22 join a platform with a defined charter; 14 move to product work in their units; told before any announcement |
| General Counsel | A good answer for the privacy regulator | The allow-list, the vendor contracts and the named owner, as evidence |

**The one idea to hold:** the board needs an owner, the CFO needs a gateway and the presidents need their teams, and only the first two require anything to change.

## 3. Options

Four operating models over three years, priced on the same model-spend forecast (assumed flat after month 12 at $2.69M a month). Savings come from routing and caching on traffic that passes through a shared gateway (section 5).

| | A. Status quo | B. Centralize all 150 (CTO) | C. Platform from infra roles, product embedded | D. Standards only, no moves |
|---|---|---|---|---|
| People moved | 0 | 150 | 22: 16 at week 8, 6 from autos in month 7 | 0 |
| 90-day control | No | Only with the allow-list | Allow-list, plus gateway at 60% of spend | Allow-list; gateway with no owning team |
| Extra departures (24% − 12% = 12 extra points) | 0 | 150 × 12% = 18, × $140k = $2.52M | 22 × 12% = 2.64, × $140k = $370k | 0 |
| Gateway adoption | None | Full, from month 7 (reorg absorbs two quarters, assumed) | Non-autos from month 4, autos from month 7 | 50% (assumed: no team owns adoption) |
| 3-year savings | $0 | $29.9M | $31.2M | $15.6M |
| Autos launch risk | None | High: up to $5M of revenue deferred per month of slip ($60M / 12) | None | None |

**How:**
1. B moves 128 product people who weren't the problem, and moves autos' team weeks before its launch.
2. D gets the gateway built but leaves nobody accountable for adoption, which the audit committee won't accept as an owner.

**Decision.** C, with the risk control decoupled from the reorg so the 90-day date doesn't depend on moving anyone.

**Trap.** Picking between "central" and "embedded" as if they were the only two. The duplication is in 36 infrastructure roles; the product work is fine where it is.

## 4. Decision and Trade-offs

Recommend C: a 22-person AI platform team reporting to you, built from the units' infrastructure roles, owning the gateway, vendor contracts, the eval service and AI risk controls. Product AI stays in the units. An egress allow-list goes live 2 weeks after approval for every unit, autos included.

| We give up | Why it's worth it |
|---|---|
| The CTO's single AI org | Saves about $2.15M in extra attrition against B and keeps the autos launch safe |
| Six months of autos savings | Autos joins at month 7; the launch is worth more than $5M a month |
| Units' freedom to sign their own model contracts | It's the control that stops the next résumé leak |
| 22 people's reporting lines | Smallest move that gives the platform an owning team |

**How:**
1. **Reversibility:** mostly a two-way door. The 22 can be re-embedded if the platform becomes a bottleneck; moving 150 would not be undone without losses.
2. **Revisit at month 12** with three triggers:
   - the gateway carries less than 95% of model spend;
   - median time for a unit to launch a new use case rises above today's;
   - moved-staff attrition passes 24%.

**Decision.** C, because it meets the audit deadline, protects the autos launch and captures nearly all the savings while moving 15% of the people.

**Trap.** Presenting the reorg as the savings. The gateway saves the money; the reorg only decides who owns it.

## 5. Economics

The savings come from two levers on gateway traffic, worked as shares of today's spend mix (cache writes assumed small and ignored).

| Step | Calculation | Share of spend left |
|---|---|---|
| Today | Opus 60%, Sonnet 35%, Haiku 5% | 100% |
| Route 45% of Opus to Sonnet at half the price | Opus 60% × 55% = 33%; Sonnet 35% + 27% × 0.5 = 48.5% | 86.5% |
| Cache half of uncached input | Opus 33% × 65% × 50% × 95% = 10.2%; Sonnet 48.5% × 65% × 50% × 90% = 14.2% | 62.1% |
| **Saving on covered traffic** | 100% − 62.1% | **37.9%** |

**How:**
1. **Discounts:** a cached Opus input token costs $0.20 instead of $4 (95% off); Sonnet $0.20 instead of $2 (90% off). Haiku has no cache price, so it's left out.
2. **Year one, option C:** non-autos (60% of spend) from month 4, autos from month 7: $6.74M.
3. **Years 2 and 3:** $2.69M × 24 = $64.7M of spend × 37.9% = $24.5M. Three-year total $31.2M.
4. **Net for C:** $31.2M − $0.37M attrition − $3.6M tooling ($1.2M × 3) = **$27.3M**. B nets $23.8M before launch risk; D $12.0M.
5. **People on payroll:** the 22 platform staff cost 22 × $280k = $6.16M a year, already paid. Freeing 14 roles returns 14 × $280k = $3.92M a year of capacity to product work, not cash.

**Decision.** Budget the platform centrally in year one, and bill model spend to units at cost, so the savings land in the units' P&Ls and they have a reason to adopt.

**Trap.** Counting the 14 freed roles as headcount savings. Nobody is being cut; they go to product work, and saying otherwise starts the attrition you're trying to avoid.

## 6. Org and Ownership

Clear decision rights matter more than the boxes. The platform owns the shared layer; units own what they build on it.

| Decision | Platform (you) | Business units |
|---|---|---|
| Model vendors and contracts | Owns: allow-list, zero-retention terms, renewals | Request additions |
| Gateway, routing, caching, cost attribution | Owns | Use, with per-unit budgets |
| Eval service and release gates | Owns the service and minimum gates | Own their eval sets and thresholds |
| Use cases, prompts, product roadmap | Advises | Own |
| Model choice | Sets the allow-list | Choose within it, gated by evals |
| AI risk | Accountable to the audit committee | Responsible within their products |

**How:**
1. An AI risk council (you, General Counsel, the CISO and one AI lead per unit) meets monthly.
2. The CTO co-chairs architecture standards; the platform runs on CTO infrastructure.
3. Platform requests have a published queue and a 2-week service target.

**Decision.** The platform reports to you because the audit committee's owner must control the gateway; units keep everything that makes their products different.

**Trap.** A platform with authority but no service target. Units route around a team that makes them wait.

## 7. Plan and Milestones

The control first, then the platform, then autos after its launch. Times run from today; the board meets at week 6.

| When | Milestone | Gate |
|---|---|---|
| Week 6 | Board approves the model | — |
| Week 8 | Egress allow-list live for all five units, built by the network team | 0 calls to non-contracted vendors |
| Week 8 | Platform team formed: 16 infrastructure staff from property, jobs, goods and services | Every mover told one to one before the announcement |
| Day 90 | Gateway carries non-autos traffic (60% of spend); owner named; contracts carry zero-retention terms | **Audit committee review** |
| Months 4–6 | Routing and caching, gated by each use case's evals | No eval regressions |
| Month 5 | Autos launch, untouched | — |
| Month 7 | 6 autos infrastructure staff join; autos traffic on the gateway | Gateway carries ≥ 95% of spend |
| Month 12 | Revisit against triggers; decide chargeback for year 2 | Decision record |

**Decision.** The allow-list is the 90-day control, because it needs network changes, not autos engineers.

**Trap.** Making the audit date depend on the reorg. If people moves slip, so does the board's control.

## 8. Risk and Governance

Two risks dominate: losing people during the move, and the regulator's inquiry.

| Risk | Control |
|---|---|
| Moved staff leave | 22 × 24% = 5.3 expected departures in 12 months; one-to-one conversations, a platform charter, retention for key engineers |
| The platform becomes a bottleneck | 2-week service target; units can self-serve within the allow-list |
| Autos launch disrupted | No autos moves or gateway migration before month 7 |
| A repeat of the résumé leak | Egress allow-list in code; zero-retention terms in every contract |
| Routing hurts quality | Each use case's own evals gate any model change |
| Vendor concentration after consolidation | At least two vendors stay behind the gateway |

**Decision.** The prevention control is in the network and the gateway, not in a policy document the jobs unit already had.

**Trap.** Answering the regulator with an org chart. The inquiry wants evidence that the data flow is blocked, and the allow-list is that evidence.

## 9. Metrics

Each success metric gets a guard metric that would catch the harm it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| Model spend through the gateway | 60% at day 90, ≥ 95% at month 7 | Median days for a unit to launch a new use case |
| Saving on covered spend | 37.9% | Eval pass rates and quality complaints per use case |
| Calls to non-contracted vendors | 0 | Exception requests waiting over 5 days |
| Moved-staff attrition | Under 24% | Engagement scores in the 14 re-tasked roles |
| Autos launch | Month 5, as planned | Autos model spend per dealer |

**Decision.** Report savings and unit velocity together, so the platform can't save money by slowing the units down.

**Trap.** Measuring the platform on savings alone. A gateway that blocks everything has excellent cost numbers.

## 10. Communication

Each audience hears the part of the decision that touches them, in order: movers first, board last.

| Audience | One line |
|---|---|
| Board and audit committee | "One owner, a vendor block live in 8 weeks, the gateway at 60% of spend by day 90 and 100% by month 7." |
| CEO | "Move 22 people, not 150; protect the autos launch; $27.3M net over three years." |
| CFO | "$6.7M saved in year one from routing and caching on list prices; units see it in their P&Ls." |
| CTO | "Your standards, your infrastructure, without moving 128 product people." |
| Autos president | "Nobody moves until month 7; the vendor block needs no work from your team." |
| Infrastructure staff | "22 of you form the platform with a clear charter; 14 move to product work; no one is cut." |

**How:**
1. Movers hear it one to one before any announcement; presidents the day before.
2. Monthly report to the audit committee until the inquiry closes; quarterly to the board.

**Decision.** Tell the 36 infrastructure staff before the presidents announce anything, because attrition is the main cost of this plan.

**Trap.** Announcing the reorg at an all-hands first. People learn their reporting line from a slide and start interviewing.
