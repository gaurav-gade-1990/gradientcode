# AI Governance Operating Model: model answer

## 1. Situation

The board isn't asking for a policy document. It's asking whether, in 6 months, the group can show a supervisor that it knows every AI system it runs, who answers for each one, and that the riskiest ones were assessed properly. Today it can't do the first, and the way it does the third has created an 11-week queue that pushes countries to build around it.

| What | Number | What it forces |
|---|---|---|
| Unknown systems | 72 of 212 (34%) found only by the census; 51 of them in 3 countries | Discovery is a people problem, not a tooling one |
| Work due by month 6 | Inventory 212 + queue 46 + new 6 × 8 = 48, so 306 items | Every item needs some assessment before the review |
| Full assessment for all | 306 × 120 h = 36,720 h | Impossible: the one-size review must go |
| Tiered | 20 high × 120 + 93 material × 24 + 193 low × 3 = 2,400 + 2,232 + 579 = 5,211 h | Still more than any central team can do |
| Central capacity to month 6 | 4 × 130 × 6 = 3,120 h, plus 4 hires × 130 × 3 = 1,560 h, so 4,680 h | Central-only runs at 5,211 / 4,680 = 111% |
| Cost of the queue | €38M / 12 = €3.17M of claims savings deferred per month of delay (assumed linear) | Speed is a board-level number too |

The tier counts include the queue and six months of new proposals: high 14 + 3 + 3 = 20, material 61 + 17 + 15 = 93, low 137 + 26 + 30 = 193.

**How:**
1. Restate the ask as three tests for month 6: a complete inventory with owners, all high-risk assessments evidenced, and board oversight on record.
2. Out of scope before month 6: ISO/IEC 42001 certification, and rewriting the actuarial model risk policy. Both are year-two work.
3. Treat legal's tiering as preliminary; tier rules get written as yes/no questions so countries apply them the same way.

**Decision.** Frame this as a capacity and incentive problem with a fixed date, and decide the operating model from the hours, not from an org chart preference.

**Trap.** Answering with a committee and a policy. A policy doesn't find the 72 unknown systems, and a committee is still a queue.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| Board risk committee | No material supervisory finding; proof it oversees AI | A quarterly AI risk report with the inventory, tiers and open issues; minutes that show challenge |
| Lead supervisor | A group that knows what it runs and can show independent review | One accountable executive, a complete inventory and evidence for every high-risk system; offer a progress meeting at month 3 |
| CEO | A credible answer in 3 weeks, without stalling the claims programme | One page: the model, the hours, the cost and the date each test is met |
| CRO | Independence of the second line, and no new unfunded duty | Approval of high-risk systems sits in a committee the CRO chairs; the central office reports to the CRO |
| CFO | Headcount freeze respected; €1.5M cap held | 4 hires, €1.22M of year-one new spend; the country leads come from existing teams |
| Country CEOs (3 with data science teams) | Speed and control of their P&L | Their own lead clears material systems in weeks; a 30-day amnesty to register without blame |
| Country CEOs (other 6) | Not to pay for a problem they don't have | 0.5 of a person each, mostly for the material tier they already run |
| Claims programme lead | The 9 queued material assessments cleared | Cleared by country leads in months 2–3, not after the high-risk work |
| Data science teams | No 11-week wait; no blame for past systems | Published tier rules, service levels per tier, and the amnesty |

**The one idea to hold:** the supervisor will test whether the group knows what it runs, but the country teams decide whether it does, so the operating model has to make registering a system cheaper than hiding it.

## 3. Options

Four options, scored on the month-6 tests, the hours, country buy-in and three-year cost.

| | A. Central, tiered | B. Federated | C. Hub and spoke, tiered | D. Freeze until review |
|---|---|---|---|---|
| Who assesses | 8 central reviewers do all tiers | Each country does all its own | Central: high-risk, low-tier checks, 25% sampling; countries: material | Central, after a stop on new deployments |
| Hours vs capacity to month 6 | 5,211 vs 4,680: 111% | Countries 5,211 vs 9 × 130 × 5 = 5,850 (1 person each, assumed) | Central 3,537 vs 4,680 (76%); countries 2,232 vs 2,925 (76%) | Fits, by stopping new work |
| Supervisor tests | Independent, but the inventory stays incomplete | Fails: high-risk assessed 9 ways, no independent review | Meets all three | Meets them, late for the business |
| Country buy-in | Low: the queue gets longer | High | Medium to high: their own lead, fast service | None |
| 3-year cost (section 5) | €4.92M | €6.18M | €6.63M | €2.67M, plus value deferred |

**How:**
1. Central-only is over capacity even after tiering, and it would do the 17 high-risk systems first, so the claims programme's material assessments wait until about month 7.
2. Federated is fast but has no independent check, and that is exactly what the supervisor will test.
3. Hub and spoke: central hours are 2,400 high + 579 low + 25% × 2,232 = 558 sampled, so 3,537.

**Decision.** Shortlist C. Keep A as the fallback for any country whose material work fails sampling.

**Trap.** Picking federated because the countries prefer it. It solves speed and fails the one test the supervisor is coming to run.

## 4. Decision and Trade-offs

Recommend C: a central AI governance office in the second line under the CRO, a country AI risk lead in each of the 9 countries, three tiers with different assessments, and a 30-day amnesty to register systems without blame.

| We give up | Why it's worth it |
|---|---|
| €1.71M more over 3 years than central-only | One month of claims savings is €3.17M |
| 4.5 people of country operational-risk time | They assess the material systems they already run |
| One standard reviewer for every system | Sampling 25% keeps one standard at a cost the hours allow |
| Approval of the group's own builds by you | The CRO's committee approves high-risk systems, so builders never approve their own |

**How:**
1. **Reversibility:** a two-way door per country. Any country's material tier can be pulled back to central without redesigning the rest.
2. **Revisit at month 12**, or earlier for a country, if:
   - sampling finds more than 10% of a country's material assessments deficient;
   - median wait for any tier exceeds its service level for two months;
   - more than 5 unregistered systems are found after the amnesty closes.

**Decision.** C, because it is the only option that passes the supervisor's tests on hours we can actually staff.

**Trap.** Naming yourself the approver because you're the accountable executive. Whoever runs the AI platform can't also sign off on what it builds.

## 5. Economics

Three years, the same 8-person central office where relevant, with new spend kept apart from people already on payroll.

| | A. Central | B. Federated | C. Hub and spoke | D. Freeze |
|---|---|---|---|---|
| Existing 4 reviewers (payroll) | 4 × €160k × 3 = €1.92M | €1.92M | €1.92M | €1.92M |
| 4 central hires (new) | 9 months × €640k / 12 = €480k, then €640k × 2, so €1.76M | — | €1.76M | — |
| Country people (payroll) | — | 9 × €130k × 3 = €3.51M (1 person each, assumed) | €585k × 11/12 + €585k × 2 = €1.71M | — |
| Tool (new) | €250k × 3 = €750k | €750k | €750k | €750k |
| External assurance (new) | 14 × €35k = €490k | — | €490k | — |
| **3-year total** | **€4.92M** | **€6.18M** | **€6.63M** | **€2.67M** |
| Year-one new spend | €480k + €250k + €490k = €1.22M | €250k | €1.22M | €250k |

Country leads cost 9 × 0.5 × €130k = €585k a year, from month 2. Assurance is year one only; repeat assurance is a later budget decision (assumed).

**How:**
1. **Cap:** C spends €1.22M of the €1.5M, leaving €280k for a second assurance round if one is failed.
2. **Opportunity cost:** the 4.5 country people stop some operational-risk work, and the CRO has to accept that.
3. **Delay (assumed linear):** C clears the claims programme's 9 material assessments by month 3; A clears them about month 7. Four months × €3.17M = €12.7M of savings deferred, against C's €1.71M extra cost.
4. **Instant-issue product:** €210M of planned premium rides on one high-risk model. It's assessed first in either option, so it doesn't separate them, but it must not slip.

**Decision.** C costs most on paper and least in practice. Its extra cost is half a month of the savings that the queue is holding up.

**Trap.** Counting country leads as free because they're already on payroll, or presenting freeze as the cheap option. Freeze only costs less if deferred savings are ignored.

## 6. Org and Ownership

Three lines, one accountable executive, and approval kept away from the people who build.

| Role | Who | Owns |
|---|---|---|
| Oversight | Board risk committee | Risk appetite for AI; quarterly AI risk report |
| Accountable executive | You, Group Chief AI Officer | The AI policy, the inventory, tier rules and first-line standards |
| Approval of high-risk | AI risk committee, chaired by the CRO | Go or no-go for every high-risk system, and exceptions |
| Second line | Central AI governance office, 8 people, under the CRO | High-risk assessments, low-tier checks, 25% sampling, the policy text |
| First line, country | 9 country AI risk leads, dotted line to the central office | Material assessments; the country's inventory |
| System owner | A named business owner per system | Keeping its entry and controls current |
| Third line | Internal audit | Auditing the operating model at month 9 |

**How:**
1. Every system in the inventory has one named business owner, not a team.
2. The office reports to the CRO, not to you. You're accountable for the framework working; you don't approve systems.

**Decision.** Put the reviewers under the CRO and the standards under you, so the supervisor sees independence and the countries see one rulebook.

**Trap.** An AI ethics board with no decision rights. Without go or no-go power it's a discussion, and the supervisor will ask who decided.

## 7. Plan and Milestones

Work back from month 6, doing the high-risk systems and the claims queue first.

| When | Milestone | Gate |
|---|---|---|
| Week 3 | Board risk committee approves the model | — |
| Month 1 | AI policy v1; tier questions; 30-day amnesty opens; low-tier self-attestations | — |
| Month 2 | 9 country leads named and trained; amnesty closes | **Gate 1:** inventory has an owner for 100% of entries |
| Months 2–3 | Claims programme's 9 material assessments cleared; 7 of 14 high-risk done | Median material wait under 3 weeks |
| Month 4 | 4 hires start; first sampling results | **Gate 2:** sampled defect rate ≤ 10% per country |
| Month 5 | All 14 high-risk assessed and externally assured; internal audit dry run | **Gate 3:** dry run finds no gap in the three tests |
| Month 6 | Supervisor's thematic review | — |
| Month 9 | Internal audit of the model | Report to the board |
| Month 12 | Revisit against the triggers | Decision record |

Central hours to month 5: 4 × 130 × 3 + 8 × 130 × 2 = 3,640, against 17 high-risk × 120 = 2,040 plus 163 low checks × 3 = 489.

**Decision.** Run the mock review at month 5, not month 6, so a gap is found while there's still a month to close it.

**Trap.** Leaving the amnesty open-ended. A deadline turns "we'll register it later" into a decision someone has to own.

## 8. Risk and Governance

The biggest risk is not a bad model; it's systems the group doesn't know it runs. Every control below is something a supervisor could test.

| Risk | Control |
|---|---|
| Systems stay unregistered | Amnesty; model API keys issued only through the group gateway with an inventory id; procurement and cloud-billing checks monthly |
| Country leads rubber-stamp | 25% re-performed by the central office; above 10% defects, that country's material tier returns to central |
| High-risk evidence incomplete at month 6 | High-risk first; external assurance; dry run at month 5 |
| Underwriting model fails assessment | Instant-issue launches with human underwriting on that segment until it passes |
| Wrong tier | Tier rules as yes/no questions; a wrong tier found in sampling counts as a defect |
| The queue comes back | Service levels: low 3 days, material 3 weeks, high 8 weeks, reported monthly |

**How:**
1. Use the NIST AI RMF functions (govern, map, measure, manage) as the structure of the assessment template, so every country writes to the same headings.
2. Treat ISO/IEC 42001 as the year-two target for the management system, not a month-6 deliverable.

**Decision.** The gateway rule is the control that matters most, because it makes an unregistered system unable to call a model, rather than relying on people to remember.

**Trap.** Counting policies as controls. The supervisor will ask for evidence a control ran, and a policy produces none.

## 9. Metrics

Each metric that shows progress is paired with one that would catch it being gamed.

| Success metric | Target | Guard metric |
|---|---|---|
| Inventory entries with a named owner | 100% by month 2 | Unregistered systems found by gateway and billing checks after the amnesty |
| Median review time by tier | Low 3 days, material 3 weeks, high 8 weeks | Sampling defect rate per country ≤ 10% |
| High-risk systems with complete evidence | 14 of 14 by month 5 | Open findings from external assurance |
| Claims savings unblocked | Programme live by month 4 | Incidents in material systems after launch |

**Decision.** Report speed and defects side by side every month, so neither the countries nor the office can win one by losing the other.

**Trap.** Reporting the number of policies, trainings or committee meetings. Those measure activity, and the supervisor tests outcomes.

## 10. Communication

One message for the board, cut for each audience, with bad news reported on the same schedule as good.

| Audience | One line |
|---|---|
| Board risk committee | "Hub and spoke: every system owned by month 2, every high-risk system assessed and assured by month 5, €1.22M of new spend." |
| Supervisor | "One accountable executive, approval independent of the builders, and an inventory found by census and kept by the gateway." |
| CFO | "4 hires inside the freeze and €1.22M in year one; the country leads are 4.5 existing people, and that's the real cost." |
| Country CEOs | "Your lead clears material systems in 3 weeks; register in 30 days and nobody is blamed for the past." |
| Claims programme | "Your 9 assessments clear by month 3." |
| Data science teams | "Tier questions are published; low-risk work is self-attested in 3 days." |

**How:**
1. Monthly to the board risk committee until month 6, quarterly after.
2. Gate results and sampling defects go to the CRO the week they're known, including a failed gate.

**Decision.** Lead with the three month-6 tests and the date each is met, because that's what the board will be asked about.

**Trap.** Telling country CEOs this is "light-touch". The 25% sampling and the pull-back rule are the point, and they'll feel misled when the first country hits them.
