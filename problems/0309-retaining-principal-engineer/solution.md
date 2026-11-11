# Retaining a Principal Engineer: model answer

## 1. Situation

This looks like a pay negotiation, but Maya has told you what it's really about: 18 months of maintenance and on-call, and a new piece of work she wants to lead. The decision is what to offer within your own authority in 10 days, and how to make the refresh safe whichever way she decides.

| What | Number | What it forces |
|---|---|---|
| Offer against current pay | $520k − $360k = $160k, a 44% gap | Cash alone inside policy can't close it |
| Offer against band maximum | $520k − $400k = $120k above the band | Anything above $400k needs a committee that meets after her deadline |
| Deadline against committee | 10 days against 6 weeks | You can only offer what you control |
| Refresh | Due in 10 weeks; only Maya has run it; runbook half done | Key-person risk exists whether she stays or goes |
| Last refresh slip | Misses up 2.1×; 2 customers, $1.1M ARR, left | The cost of a missed refresh has a precedent |
| BEC | $3M first-year ARR; lead search 3 months, no finalist | The role she wants is the role you can't fill |

**How:**
1. Hold a stay conversation before you make any offer: what would make her want to stay, what she'd want to stop doing, and what the money needs to be.
2. Unknown: whether a role change without a cash match is enough. Only she can say.
3. Out of scope: rebuilding the principal band this week. That is a committee decision.

**Decision.** Frame the decision as a role-first offer within policy, plus a refresh plan that works whether she stays or not.

**Trap.** Treating it as a bidding war. Matching cash answers a question she didn't ask and leaves her doing the work she wants to stop.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| Maya | Meaningful work, off maintenance and on-call; fair pay | A stay conversation first; the BEC lead role in writing; cash and equity within policy |
| Your manager (VP Engineering) | Detection quality held, BEC launched, no policy exception | Both outcomes priced; the offer stays inside your authority |
| HR | A defensible offer that doesn't break the band | The raise stops at the $400k maximum; equity within the grant limit; flag the equity effect on the other principals |
| Ravi | A real step up, not just extra load | Owns this refresh, with Maya reviewing; visible, promotable work |
| On-call rotation | No heavier load | A senior engineer joins so the rotation stays at 4 |
| The two other principals | Pay that is consistent for the same level | HR reviews principal pay at the next cycle, using the market data Maya's offer reveals |
| BEC sales and product | A lead and a launch date | A named lead now, instead of an open search |

**The one idea to hold:** fix the reason she wants to leave and the risk her leaving would expose, because both need fixing even if she goes.

## 3. Options

Five options, scored on the 10-day deadline, fairness and the refresh.

| | A. Let her go well | B. Match $520k in cash | C. Role-first counter | D. Promise future pay or promotion | E. Cash and equity, no role change |
|---|---|---|---|---|---|
| Can you offer it in 10 days? | Yes | No: committee in 6 weeks | Yes | Only as a promise | Yes |
| Addresses her reason | No | No | Yes | No | No |
| Fairness | Fine | $135k above the next principal, $120k above band | Within band; $15k above the next principal | Undermines the process | Within band |
| Refresh | Ravi runs it on a half runbook | Maya, unchanged | Ravi runs it, Maya reviews | Unchanged | Maya, unchanged |
| BEC lead | Still open | Still open | Filled | Still open | Still open |

**How:**
1. **B and D both make promises you can't keep.** You don't control the committee, and a promotion promised to close a decision is one the process may not support.
2. **E pays her to keep doing what she wants to stop.** It may delay the resignation by a year.

**Decision.** Shortlist C, and prepare A in case she declines.

**Trap.** Leading with the money. If you open with a number, the conversation becomes about the $160k gap, not about the work.

## 4. Decision and Trade-offs

Recommend C. Maya becomes the BEC lead now and leaves the on-call rotation. Her pay moves to the $400k band maximum, and she gets the full $150k retention grant over 2 years. Year one is $400k + $150k / 2 = $475k, which is $45k below the offer, and you say so.

| We give up | Why it's worth it |
|---|---|
| Maya as the person who runs the refresh | Ravi runs it with Maya reviewing, which fixes the key-person risk |
| The external lead search | It found no finalist in 3 months; she's ready now |
| A cash match | It isn't in your authority, and it isn't her main reason |
| Pay compression with the other principals | She is at the band maximum for a bigger scope; HR reviews principal pay at the next cycle |

**How:**
1. **Reversibility.** The role is reversible; the raise and grant are not. The refresh plan is worth doing either way.
2. **Revisit at 6 months**, and change course if:
   - BEC is more than a month behind its launch plan;
   - Maya is back on maintenance or on-call more than a day a week;
   - the refresh needed Maya to do more than review.

**Decision.** C, because it addresses her real reason, fits inside your authority and the 10 days, and fixes the refresh risk whatever she decides.

**Trap.** Overselling. Saying "we'll get you to $520k" when the committee might refuse breaks trust at exactly the moment you're asking for it.

## 5. Economics

Three years for both sides, with all pay figures as the brief's assumed ones.

| | A. Let her go | B. Match $520k | C. Role-first counter |
|---|---|---|---|
| Pay cost over current | $0 | $160k × 3 = $480k | $40k × 3 + $150k = $270k |
| Recruiting | Agency $70k; 6-month search; 6 months to full speed | $0 | $0 |
| BEC | Lead still missing: about 6 months later, 6 × $250k = $1.5M of first-year ARR deferred (assumed: launch slips one month per month without a lead) | Still missing | Lead in place |
| Refresh | Ravi on a half runbook with no Maya; precedent: $1.1M ARR | Maya | Ravi with Maya reviewing |

**How:**
1. **BEC pace.** $3M / 12 = $250k of first-year ARR per month of delay.
2. **Funding the counter.** The lead role was budgeted at $400k. Converted into a senior ML engineer at $300k, it frees $100k a year, $300k over 3 years, which covers the $270k counter and backfills Maya's maintenance work.
3. **The precedent isn't a forecast.** The $1.1M loss is what happened last time, not an expected value.

**Decision.** C costs $270k over 3 years, about what converting the lead role frees, against a $70k fee, a $1.5M BEC delay and a refresh risk if she leaves.

**Trap.** Comparing her pay with a replacement's pay. The real cost of losing her is the BEC launch and the refresh, not the salary line.

## 6. Org and Ownership

Her role changes, so ownership of everything she held has to move by name.

| Work | Owner | Notes |
|---|---|---|
| BEC detection | Maya | Launch milestone at month 9; she shapes the team |
| Quarterly refresh | Ravi | Maya reviews this one; Ravi runs the next alone |
| On-call | Rotation of 4 | A senior engineer replaces Maya |
| Senior hire (converted lead role) | You, with recruiting | Takes Maya's maintenance work |
| Pay and grant | You, with HR | Inside the band and the grant limit |

**Decision.** Ravi owns the refresh from now on, so the key-person risk ends whatever Maya decides.

**Trap.** Leaving Maya as the refresh owner "for one more quarter". That's the exact work she wants to stop, and the risk stays.

## 7. Plan and Milestones

Ten days for the decision, ten weeks for the refresh.

| When | Milestone | Gate |
|---|---|---|
| Days 1–2 | Stay conversation; brief your manager and HR | — |
| Days 3–5 | HR approves raise to $400k and the $150k grant; written offer of the BEC lead role | Within policy, no committee needed |
| Day 10 | Maya decides | — |
| Week 2 | Ravi leads refresh prep; on-call replacement starts | — |
| Week 6 | Runbook complete; dry run on last quarter's data | **Gate:** Ravi completes the dry run with Maya only reviewing |
| Week 10 | Refresh ships | Detection quality at or above the current model |
| Month 6 | Revisit against the triggers | — |

**Decision.** The runbook and dry run happen in every outcome; if Maya leaves, she spends her notice on them.

**Trap.** Making the refresh plan depend on her answer. Start it on day 1.

## 8. Risk and Governance

The policy and fairness risks matter as much as the retention.

| Risk | Control |
|---|---|
| A promise you can't keep | Offer only what HR has approved; say plainly the committee isn't involved |
| Equity with the other principals | HR is told she'll be $15k and $30k above them, with the scope reason; principal pay reviewed at the next cycle |
| "An outside offer gets you scope" | BEC lead was a role you should have offered; you say so, and open stay conversations with the other senior engineers |
| Maya declines anyway | Ravi's refresh plan already running; she spends her notice on the runbook; the converted lead role is reopened as the BEC lead search |
| Ravi is overloaded | Ravi's other work is spread across the team during refresh prep; you watch his hours |

**Decision.** Everything you offer is within your authority and approved by HR before you say it.

**Trap.** Rewarding the outside offer and ignoring the rest of the team. The next stay conversation should happen before the next offer.

## 9. Metrics

Each success metric is paired with a guard.

| Success metric | Target | Guard metric |
|---|---|---|
| Maya stays and leads BEC | BEC launch on plan at month 9 | Maya's time on maintenance and on-call: zero |
| Refresh ships | Week 10 | Customer-reported misses at or below last quarter |
| Ravi runs the refresh | Next one with Maya only reviewing | Ravi's weekly hours during prep |
| On-call rotation | 4 people | Pages per person per week, against last quarter |

**Decision.** Judge the outcome by BEC milestones and a refresh that doesn't depend on Maya, not by whether she said yes.

**Trap.** Declaring success the day she accepts. The usual failure is a counteroffer that buys a year and changes nothing.

## 10. Communication

What each audience hears, and what stays private.

| Audience | One line |
|---|---|
| Maya | "Lead BEC, off on-call, $400k plus $150k over two years. It doesn't match $520k, and I won't pretend it does." |
| Your manager | "Keeping her costs $270k over 3 years, covered by converting the lead role; losing her risks $1.5M of BEC delay and the refresh." |
| HR | "Within the band and the grant limit; please put principal pay on the next cycle." |
| Ravi | "You own the refresh; Maya reviews this one, and it's yours after that." |
| Team, after she decides | "Maya is leading BEC; Ravi owns the refresh; on-call stays at 4." |

**How:**
1. The outside offer stays between Maya, you, your manager and HR.
2. If she stays: check-ins at 30, 90 and 180 days on whether the change is real.

**Decision.** The team hears about a role change, never about an outside offer.

**Trap.** Telling the team why Maya got the BEC role. It invites everyone to get an offer to get a promotion.
