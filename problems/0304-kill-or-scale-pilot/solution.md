# Kill or Scale a Stalled Pilot: model answer

## 1. Situation

The pilot didn't fail; it was graded on the wrong metric. It does nothing measurable in business hours and a lot after hours, when nobody is paid to answer, so overtime was never going to move. The real question is whether the after-hours effect is worth what 2 engineers can build in 8 weeks and then run safely.

| What | Number | What it tells you |
|---|---|---|
| After-hours inquiries at the pilot | 9,000 × 40% = 3,600 a month | The only slice where the assistant changes an outcome |
| After-hours tour lift | 17.5% − 11.0% = 6.5 points; 3,600 × 6.5% = 234 extra tours a month across 40 properties | Real and significant |
| Business-hours lift | 19.2% − 18.8% = 0.4 points, p ≈ 0.24 | No effect: agents already answer fast |
| Days vacant per turnover | 29.1 − 26.8 = 2.3 days; 2.3 / 0.8 = 2.9 standard errors | Probably real; the plausible range (± 2 SE) is 0.7 to 3.9 days |
| Sunk cost | 4 engineers × 5 months = 20 engineer-months, 20 × $250k / 12 = $417k | Spent either way; it must not drive the call |
| Capacity after week 8 | 2 engineers | Rules out anything that needs new integrations now |

**How:**
1. Restate the decision: which version of the assistant, if any, earns 1 permanent engineer from week 8?
2. Drop the overtime metric. Freed daytime minutes don't become cash unless someone changes rosters, and nobody planned to.
3. Out of scope: replacing leasing agents, and PMS-B and PMS-C before the migration ends.

**Decision.** Judge the pilot on vacancy days and after-hours tours, the outcomes it actually moved, and treat the overtime miss as a wrong metric, not a failed product.

**Trap.** Killing it because the headline metric missed, or scaling it because $417k is already spent. One reads the wrong number; the other reads a number that no longer matters.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| VP of Engineering (your manager) | A clear call, and the payments migration staffed on time | One page: the call, the dollar range, what 2 engineers run, and a dated revisit |
| Director of Leasing Operations | Leads handled well; agents not undercut | Daytime stays with agents; the assistant covers nights and weekends; fix the 7% of handoffs that arrive without context |
| Pilot sponsor (VP Operations) | A win to report, after the overtime miss | Reframe the win as vacancy days, which is rent, and stop reporting overtime |
| General Counsel | No fair-housing complaint | Topic blocks in code, a legal-owned eval set, and a gate before any new property goes live |
| Payments migration lead | 2 engineers on week 8, no slip | Confirm the date in writing; nothing in this plan needs them after week 8 |
| Your 4 engineers | Credit for 5 months of work; a sane run load | Name what they proved; the 2 who stay own a smaller, cleaner system |
| Prospective renters | A fast, fair answer at 10 pm | An answer and a tour slot in minutes, with no steering |

**The one idea to hold:** everyone can get what they need from a smaller assistant: nights and weekends only, on one PMS, with fair-housing controls in code.

## 3. Options

Four options, compared on what they need from the team, when they are live and what they are worth a year.

| | A. Kill | B. Extend the pilot as is | C. Scale to all 300 | D. Narrow and scale |
|---|---|---|---|---|
| Scope | Off everywhere | 40 properties, all hours, 3 more months | 300 properties, all hours | 120 PMS-A properties, after hours only |
| Engineers needed | 0 | 4 for 3 months | 12 engineer-months for PMS-B and C (2 × 2 × 3), then run | 4 for 6 weeks, then 1 to run |
| Fits the constraint | Yes | No: 2 leave at week 8 | No: earliest after the migration, if the 2 return (assumed) | Yes |
| Annual value at 2.3 days | $0 | Learns nothing new | 38,100 × 45% × 2.3 × $55 = $2.17M, from month 10 at best | $867.5k (section 5) |
| Fair-housing exposure | None | Unchanged | Highest | Controlled before rollout |

**How:**
1. Daily rent is $1,650 / 30 = $55, so a vacancy day saved on one turnover is worth $55.
2. B buys no information: the after-hours result is already significant, and the business-hours result is already flat.
3. C is the right ambition but the wrong quarter; it becomes a decision for month 7.

**Decision.** Shortlist D, with A as the fallback if the fair-housing gate fails, and C as a dated question once the migration ends.

**Trap.** Treating it as a binary of kill or scale. The data says the product works in one slice, and the constraint says you can afford one slice.

## 4. Decision and Trade-offs

Recommend D: switch business-hours mode off, run the assistant after hours only at all 120 PMS-A properties, ship fair-housing controls first, and hand it to 1 engineer at week 8.

| We give up | Why it's worth it |
|---|---|
| Daytime mode at the 40 pilot properties | It adds 0.4 points that aren't significant, plus risk and cost |
| 180 PMS-B and PMS-C properties for now, worth 180 × 127 × 45% × 2.3 × $55 = $1.30M a year | Integrations need 12 engineer-months the team doesn't have until the migration ends |
| 1 engineer permanently on run | Still about 3.4× cheaper than the value at the 2.3-day estimate |
| The overtime story | It was never going to be true |

**How:**
1. **Reversibility:** a two-way door. The assistant is behind a per-property feature flag, so any property can be switched off in minutes.
2. **Revisit at month 7**, when the migration ends:
   - expand to PMS-B (110 properties, 6 engineer-months) if the vacancy gap at the 120 holds at 1.5 days or more over 3 months;
   - kill if it falls below 0.7 days, or on any substantiated fair-housing complaint.

**Decision.** D, because it is the only option that keeps the proven effect, fits 2 engineers and fixes the legal risk before it grows.

**Trap.** Recommending "scale" without saying what is switched off. Narrowing is what makes the run load fit the people you have.

## 5. Economics

Three years, people priced at the assumed $250k, value taken at both the 2.3-day estimate and the low end of its range (0.7 days). Turnovers at the 120 properties: 120 × 127 units = 15,240 × 45% = 6,858 a year.

| | A. Kill | D. Narrow and scale |
|---|---|---|
| Annual value at 2.3 days | $0 | 6,858 × 2.3 × $55 = $867.5k |
| Annual value at 0.7 days | $0 | 6,858 × 0.7 × $55 = $264.0k |
| Build | $0 | 4 engineers × 1.5 months = 6 engineer-months = $125k |
| Run | $0 | 1 engineer from month 3 to 36 = 34 months = $708k |
| Model | $0 | 10,800 conversations × $0.0648 = $700 a month; × 34 = $24k |
| **3-year cost** | **$0** | **$857k** |
| **3-year value** | **$0** | **$2.46M at 2.3 days (2.9×); $748k at 0.7 days (0.87×)** |

**How:**
1. **Conversations:** 9,000 / 40 = 225 inquiries per property a month; 120 × 225 × 40% = 10,800 after-hours conversations.
2. **Per conversation on Opus:** 4,000 × $0.20/1M + 1,000 × $4/1M + 300 × $20/1M = $0.0108 a call, × 6 = $0.0648. Cache writes are assumed small and ignored.
3. **Sonnet would cost** $0.0348, saving 10,800 × $0.03 × 12 = $3,888 a year. That isn't worth an engineer-week of evals now.
4. **Value timing:** live from month 3, so year one counts 10 months; years 2 and 3 are full.
5. **Opportunity cost:** the run engineer's time, which would otherwise go to the backlog (unpriced).

**Decision.** D pays back about 3× at the central estimate and roughly breaks even at the pessimistic end, so the downside is small and the upside is real.

**Trap.** Leading with model cost. At $700 a month it is a rounding error; the engineer is 97% of the cost.

## 6. Org and Ownership

A small team needs a clear owner for each piece, especially the parts legal cares about.

| Role | Who | Owns |
|---|---|---|
| Accountable | You | The call, the gates and the month-7 revisit |
| Run | 1 engineer from week 8, the second as backup | Uptime, the handoff fix, evals, the flag per property |
| Product | Team PM | After-hours scope, renter wording, handoff format |
| Operations | Director of Leasing Operations | The morning handoff queue and agent feedback |
| Fair housing | Legal | The blocked-topic list, the eval set and the monthly sample |
| Decision | VP of Engineering | Signs off now and at month 7 |

**How:**
1. Any prompt or model change must pass the fair-housing eval before it ships; nobody overrides it alone.
2. Write down a run budget: if run work passes 1 engineer, the backlog pays first, not the migration.

**Decision.** Legal owns the definition of a fair-housing failure; engineering owns making the system meet it.

**Trap.** Leaving one engineer as the only person who understands the system. Name a backup and keep a runbook.

## 7. Plan and Milestones

Six weeks of build with all 4 engineers, one hard gate, then hand-over before week 8.

| When | Milestone | Gate |
|---|---|---|
| Week 2 | Decision with the VP; business-hours mode off at the 40 | — |
| Weeks 2–4 | Blocked topics in code; eval set of 300 adversarial cases built with legal; handoff fix | — |
| Week 5 | Re-run 1,000 past after-hours transcripts and the eval set | **Gate:** 0 fair-housing failures on both, and legal signs |
| Weeks 5–7 | Roll out to the 80 new PMS-A properties in two waves of 40 | Handoffs without context under 1% |
| Week 8 | 2 engineers leave; runbook and on-call handed over | — |
| Month 7 | Revisit PMS-B with 3 months of data from the 120 | Decision record |

**Decision.** The fair-housing gate comes before any new property goes live, not after the rollout.

**Trap.** Rolling out first and fixing guardrails later. The engineers who would fix them leave at week 8.

## 8. Risk and Governance

The biggest risk is legal, not technical. Unfixed, 4 / 500 = 0.8% of 10,800 conversations is about 86 fair-housing problems a month at 120 properties, against $50k to $150k to defend each complaint.

| Risk | Control |
|---|---|
| Steering or demographic answers | Blocked topics in code with a fixed, legal-approved reply; adversarial eval in CI |
| Sampling gives false comfort | 0 failures in 1,000 only bounds the rate below 3 / 1,000 = 0.3% (rule of three), still up to 32 a month, so the control is the code |
| Lost handoffs | 10,800 × 38% handed off × 7% = 287 renters a month start over; conversation attached to every handoff |
| Wrong tour bookings in PMS-A | Booking confirmed back to the renter; agents see a daily list |
| One engineer runs it all | Backup engineer, runbook, and a flag to turn any property off |

**Decision.** The fair-housing rule lives in code and in an eval that blocks releases; legal's monthly sample of 200 transcripts checks it rather than being it.

**Trap.** Quoting "4 in 500" as small. At 10,800 conversations a month it is a complaint waiting to happen.

## 9. Metrics

Each success metric gets a guard metric that would catch the harm it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| Days vacant per turnover at the 120 vs PMS-B and C properties | Gap of 1.5 days or more | Fair-housing failures in legal's monthly sample: 0 |
| After-hours tour-booking rate | 17% or more | Tour no-show rate, so bookings aren't padded |
| Conversations finished without a human | 62% or more | Handoffs without context: under 1% |
| Cost per conversation | About $0.065 | Run engineer's time: 1 person or less |

**Decision.** Use the PMS-B and C properties as the control group from now on, so the month-7 call rests on a comparison, not a trend line.

**Trap.** Reporting "62% handled by AI" as success. It says nothing about whether units lease faster.

## 10. Communication

The same call, in a sentence each audience can act on.

| Audience | One line |
|---|---|
| VP of Engineering | "Keep it, narrowed: nights and weekends at the 120 PMS-A properties, built by week 7, run by 1 engineer; about $0.87M a year at the central estimate; PMS-B decision at month 7." |
| Leasing Operations | "Your agents own daytime. The assistant covers nights and weekends and hands over with the full conversation." |
| Pilot sponsor | "The win is 2.3 fewer vacant days per turnover, which is rent; stop reporting overtime." |
| Legal | "No new property goes live until the eval and 1,000 transcripts show zero fair-housing failures and you sign." |
| Payments lead | "Your 2 engineers start on week 8, as agreed." |
| The team | "You proved where it works. Now we make that part safe and run it well." |

**How:**
1. Weekly status in your 1:1 with the VP until week 8; monthly vacancy and fair-housing results after.
2. A failed gate is reported the same day, with the fallback (kill) on the table.

**Decision.** Lead with the reframe: the pilot worked at night, and nights are what we keep.

**Trap.** Telling the sponsor the pilot "succeeded" without retiring the overtime target. It comes back at the next review as a miss.
