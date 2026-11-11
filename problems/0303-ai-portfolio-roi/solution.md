# Prioritizing an AI Portfolio by ROI: model answer

## 1. Situation

The council thinks it is choosing between eight ideas worth $39M. It is really allocating 60 months of in-house data engineering, the one resource every customer-data project needs and nobody can add this year. The job is to make the claims comparable, rank against that bottleneck, and fund in stages where the evidence is thin.

| What | Number | What it forces |
|---|---|---|
| Claimed benefits | $16.8M + $7.0M + $6.34M + $1.5M + $1.2M + $1.8M + $2.4M + $2.02M = $39.05M | Claims rest on four kinds of evidence; they can't be added as they are |
| After finance's weights and overlaps | $17.7M (section 5) | Less than half of the claimed total survives |
| In-house data engineering | 84 months requested on customer data, 60 available | The binding constraint: 24 months must go |
| Non-customer data work | P4 12 + P5 2 = 14 months | Contractors can do it, so it shouldn't compete for the 60 |
| ML engineering | 108 requested of 120 | Not binding |
| New spend | $5.45M requested against $5M | Barely binding once contractors are added |

**How:**
1. Put every claim through finance's weights, using measured effects where they exist (P3's A/B measured 0.03 points, not 0.05).
2. Find double counting: P1, P2 and P8 all draw on the same 1.0M care calls.
3. Out of scope: hiring exceptions and changing the customer-data policy.

**Decision.** Rank by risk-adjusted benefit per in-house data-engineer-month, and move non-customer work to contractors so it stops competing for the bottleneck.

**Trap.** Ranking by claimed benefit or by ROI per dollar. Money is not what runs out first; data engineers are.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| CFO (council chair) | Benefits that show up in the P&L, under $5M | Finance's own weights applied to every claim; a payroll line next to new spend; $0.8M held back |
| COO (your manager) | Lower care cost and a portfolio the council accepts | Two care projects funded, one staged; one page with the cut line |
| SVP Care | P1, P2 and P8, all three | P2 now; P1 in two stages with a gate at month 4; P8 first in line for P1's freed engineers if the gate fails |
| CMO | P3 at $6.34M, and P5 | P3 funded at its measured effect ($3.04M); P5 funded on contractors |
| CISO | P6, which the board asked for | Funded, explicitly as a risk decision, not on ROI alone |
| SVP Retail | P7 | Not funded: a sponsor estimate on 10 scarce engineer-months; invited back with a measured store pilot |
| CTO Network | P4 | Funded with contract data engineers, because network data isn't customer data |
| 5 in-house data engineers | A plan that doesn't burn them out | 56 of 60 months allocated, 4 held as buffer |

**The one idea to hold:** every sponsor is competing for the same 5 data engineers, so a common ruler (finance's weights, per data-engineer-month) is what makes a "no" feel fair.

## 3. Options

Three ways to build the portfolio, compared on what they fund, what they use and what they're worth.

| | A. Rank by claimed benefit | B. Spread the bottleneck | C. Rank per data-engineer-month, staged |
|---|---|---|---|
| Method | Fund from the biggest claim down until 60 months run out | Every customer-data project gets 60 / 84 = 71% of its request | Weighted benefit per in-house month; non-customer work to contractors; P1 staged; P6 as a risk call |
| Funded | P1, P2, P3, P7, P5 | All eight, at reduced scope | P2, P1 (staged), P3, P6, P4, P5 |
| In-house months used | 18 + 8 + 14 + 10 + 2 = 52 | 60 | 8 + 18 + 14 + 16 = 56 |
| Risk-adjusted benefit | $14.5M | Unknown: most projects slip into next year | $16.0M |
| SIM-swap plan for the board | No | Partly | Yes |

**How:**
1. A treats P5's 2 months as competing for the 60, which also pushes P4 out, though both could use contractors.
2. A funds P7, whose only evidence is a sponsor estimate, ahead of P6, which the board asked for.
3. B gives everybody something and finishes almost nothing.

**Decision.** C: it funds more risk-adjusted value with fewer in-house months, and covers the board's risk.

**Trap.** Spreading the bottleneck to avoid saying no. Eight projects at 71% staffing usually means eight late projects.

## 4. Decision and Trade-offs

Fund six: P2, P3, P6 and P1 (staged) on in-house data engineers; P4 and P5 on contract data engineers. Don't fund P7 or P8 this year. Hold $0.8M and 4 data-engineer-months in reserve.

| We give up | Why it's worth it |
|---|---|
| P8 ($1.21M weighted) | Ties with P6 per month ($67.2k against $67.5k), but overlaps P1's call pool and answers no board risk |
| P7 ($0.48M weighted) | Weakest evidence and lowest value per month ($48k) |
| P1 at full speed | Phase 1 (6 months of data engineering, $0.5M, both assumed) proves deflection before phase 2 (12 months, $1.3M) |
| $0.8M of budget unspent at the start | Covers a P1 overrun or a mid-year re-allocation |

**How:**
1. **Reversibility:** staging makes P1 the main reversible bet; the others are small enough to stop at a quarterly review.
2. **Month-4 gate for P1:** measured deflection of at least 10% on the two pilot call types, with no rise in 7-day repeat calls. If it fails, P1's 12 phase-2 months plus the 4 in reserve (16) go to P8, scoped down from 18.
3. **Revisit at every quarterly council** against measured, not claimed, benefits.

**Decision.** C as above, because it has the highest weighted value on the bottleneck and keeps a funded fallback for the biggest uncertain bet.

**Trap.** Funding P1 in full because it has the biggest number. Its evidence is a vendor case study, the weakest kind short of a guess.

## 5. Economics

Each claim is weighted by finance's rule, then the overlaps are removed. People are priced at the assumed $200k (data) and $260k (ML) a year; contractors at $25k a month.

| | Weighted benefit | Per in-house month | New spend | People on payroll | Benefit / year-one cost |
|---|---|---|---|---|---|
| P2 | $7.0M × 80% × 94% = $5.26M | $658k | $0.6M | $350k | 5.5× |
| P1 | $16.8M × 30% = $5.04M | $280k | $1.8M | $820k | 1.9× |
| P3 | $6.34M × 0.03/0.05 × 80% = $3.04M | $217k | $0.4M | $623k | 3.0× |
| P6 | $1.8M × 60% = $1.08M | $67.5k | $0.5M | $570k | 1.0× |
| P4 | $1.5M × 60% = $0.90M | contractors | $0.3M + 12 × $25k = $0.6M | $260k | 1.0× |
| P5 | $1.2M × 60% = $0.72M | contractors | $0.25M + 2 × $25k = $0.3M | $87k | 1.9× |
| **Portfolio** | **$16.05M** | **56 months** | **$4.2M** | **$2.71M** | **2.3×** |

**How:**
1. **Overlap:** P1's weighted claim implies 20% × 30% = 6% of calls deflected, so P2 summarizes only 94% of calls.
2. **Unfunded:** P8 $2.02M × 60% = $1.21M; P7 $2.4M × 20% = $0.48M. Their year-one ratios are 0.9× and 0.4×.
3. **P2 model choice:** Sonnet costs 1.0M × 12 × (5,000 × $2 + 250 × $10)/1M = $150k a year; Haiku $7.5k. An eval decides; the $142.5k gap is inside P2's $0.6M.
4. **Timing:** these are annual run-rates; projects go live through the year, so this year's realized benefit will be lower.

**Decision.** $4.2M of new spend and $2.71M of payroll for $16.05M of weighted annual benefit, with $0.8M unspent until P1's gate.

**Trap.** Presenting $39M to the CFO. Finance applies its weights anyway, and you lose credibility for not doing it first.

## 6. Org and Ownership

The council decides; you own the portfolio; each project has a sponsor who owns its benefit.

| Role | Who | Owns |
|---|---|---|
| Decides | AI Investment Council (CFO) | Funding, the cut line, quarterly re-allocation |
| Accountable | You | The ranking, the data-engineer allocation, the P1 gate |
| Benefit owner | Each sponsor | Their benefit number and adoption |
| Measurement | Finance partner | Realized benefit per project, quarterly |
| Data engineering | Data engineering lead | The 56 allocated months and the 4 in reserve |
| Contractors | CTO Network's and CMO's teams, with your standards | P4 and P5, on non-customer data only |

**How:**
1. Moving data-engineer months between projects is a council decision, not a hallway deal.
2. Sponsors sign the benefit figure as weighted, not as claimed.

**Decision.** Finance measures benefits, so next year's weights can be adjusted with evidence.

**Trap.** Letting sponsors report their own benefits. Every project then succeeds on paper.

## 7. Plan and Milestones

A year of quarters, with the one real gate on P1.

| When | Milestone | Gate |
|---|---|---|
| Week 4 | Council approves the portfolio and the cut line | — |
| Q1 | P2 rolls out to all agents; P3 scales from 5% of the base; P1 phase 1 on 2 call types; P6 build; P4 and P5 contractors start | — |
| Month 4 | P1 phase-1 review | **Gate:** deflection ≥ 10%, no rise in 7-day repeat calls |
| Q2 | P1 phase 2 or P8 starts; P6 live in shadow mode | P6 false-positive rate near the back-test's |
| Q3 | P6 blocking live; P4 live | — |
| Each quarter | Council: measured against weighted benefit | Projects under 50% of weighted benefit for two quarters are stopped |
| Month 12 | Next year's portfolio, with weights updated from results | Decision record |

**Decision.** P1's gate is set now, with its fallback (P8) named, so the decision at month 4 is mechanical.

**Trap.** Approving the portfolio once a year and never re-allocating. The bottleneck should follow the evidence.

## 8. Risk and Governance

The biggest risk is that the benefits don't arrive. The second is the bottleneck itself: 56 of 60 months is 93% allocated, so one data engineer leaving costs about 12 months a year.

| Risk | Control |
|---|---|
| Claimed benefits don't materialize | Weighted figures, finance measurement, a two-quarter stop rule |
| A data engineer leaves | 4-month buffer; P1 phase 2 is the first thing to slow |
| Contractors touch customer data | Contractors only on P4 and P5 datasets; access reviewed by privacy |
| P1 deflects calls that come back | 7-day repeat-call guard in the gate |
| P6 blocks legitimate SIM changes | Shadow mode first; a fast human override |

**Decision.** The customer-data rule is enforced in access controls, not just in project plans.

**Trap.** Ignoring the bottleneck's own fragility. A plan at 100% of 5 people fails with the first resignation.

## 9. Metrics

Each success metric gets a guard metric.

| Success metric | Target | Guard metric |
|---|---|---|
| Realized benefit per project (finance) | ≥ 80% of weighted | Sponsor-reported figures not accepted |
| P1 deflection | ≥ 10% on pilot call types | 7-day repeat calls |
| P2 seconds saved per call | 50 s | Agent-flagged summary errors |
| P3 churn cut | 0.03 points | Offer cost per subscriber kept |
| P6 fraud losses | Down 45% | Legitimate SIM changes blocked |

**Decision.** Report portfolio results quarterly as weighted against measured, project by project.

**Trap.** Reporting the portfolio total only. One strong project hides two failing ones.

## 10. Communication

One cut line, explained to each executive in their own terms.

| Audience | One line |
|---|---|
| CFO | "$16.05M of weighted benefit for $4.2M of new spend and $2.71M of payroll; $0.8M held until P1's gate." |
| SVP Care | "Agent assist now; the virtual agent in two stages; bill-shock is first in line if stage one fails." |
| CMO | "Churn targeting funded at the effect your A/B measured; content generation on contractors." |
| CISO | "SIM-swap is funded as a board risk decision." |
| SVP Retail | "Not this year; bring a measured two-store pilot and it competes next round." |
| CTO Network | "Alarm triage is funded with contract data engineers." |

**How:**
1. Pre-wire each sponsor one to one before the council, so nobody hears "no" in the room.
2. Quarterly council reviews, with failed gates and missed benefits reported.

**Decision.** Pre-wire the "no" for P7 and P8 privately.

**Trap.** Announcing the cut line at the council. Sponsors who are surprised in public fight it there.
