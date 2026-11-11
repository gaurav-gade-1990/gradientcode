# Production Hallucination Incident Response: model answer

## 1. Situation

This is a live incident with two clocks: every day the assistant stays as it is, about 580 more employees get a wrong eligibility answer, and every employee already misled has a deadline after which the mistake may be permanent. The job is to stop the harm in hours, not to find the root cause first, without breaking the support the enrollment window depends on.

| What | Number | What it forces |
|---|---|---|
| Eligibility conversations | 140,000 × 18% = 25,200 a day | The failure is in one topic, so the fix can be narrow |
| Error rate since release | 46 / 2,000 = 2.3%, against 0.3% last month; other topics flat at 0.4% | The release is the likely cause; the rest of the assistant is not broken |
| Employees affected so far | 3 days × 25,200 × 2.3% = 1,739 (assumed one employee per conversation) | A remediation list, not just a fix |
| Added harm per day | 25,200 × 2.3% = 580 | Containment is measured in hours |
| Contact center room | 12,000 − 9,500 = 2,500 contacts a day | Switching the assistant off is not available |
| Deadlines | 18 days left in the window; carriers accept late adds up to 30 days after, so day 48 | Remediation has a hard end date |

**How:**
1. Declare a severity-1 incident and name one incident commander before anything else.
2. Contain first, diagnose second: the release is the prime suspect, but the fix shouldn't wait for proof.
3. Out of scope today: re-architecting the assistant, or a new vendor. Both come after the window.

**Decision.** Treat this as a harm-to-employees incident with a 48-day remediation clock, not a model-quality bug, and size every action against the 580-a-day number.

**Trap.** Starting with root cause. The team will want to explain why it happened before acting, and each hour of analysis is another 24 wrong answers.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| CEO | Control of the story by noon; no repeat | A one-page brief: harm so far, containment done, notification plan, cost |
| Escalating HR director | Their employees fixed, and to be told the truth first | A call from you within 4 hours: what happened, the number affected at their company, the plan and the date |
| All affected employers | To hear it from us, not from employees or social media | Written notice inside the 5-business-day contract window, with their own affected list |
| Employees | A correct answer and a way to fix their enrollment | Outreach through their employer, with the right rule and the steps to correct |
| Chief Revenue Officer and sales | Renewals protected; notify only the complainer | Show the contract requires notice and that a customer finding out later is the bigger renewal risk |
| General Counsel | Contract compliance; careful wording | Approves the notice template; owns the 5-business-day clock |
| Head of Support | No flood of contacts in peak season | Narrow containment that adds 2,268 contacts a day, inside the 2,500 of room |
| AI team | A fix without blame | A blameless review; the eval gap is a process failure, not a person's |
| Carrier relations | Late-add requests they can process | One batch per employer, well before day 48 |

**The one idea to hold:** the people who were harmed, employees, are not our customers, so we reach them through the employers who are, and that only works if employers hear it from us first.

## 3. Options

Four ways to contain, scored on harm stopped, contact-center load and speed.

| | A. Keep running, add a disclaimer | B. Switch the assistant off | C. Eligibility topics off, hand off to humans | D. Roll back, plus answer cards for eligibility |
|---|---|---|---|---|
| Wrong eligibility answers a day | 580 | 0 | 0 | 0 from cards; the remaining 30% get a handoff |
| Extra contacts a day | 0 | 140,000 × 30% = 42,000 | 25,200 × 30% = 7,560 | 25,200 × 30% unanswered × 30% = 2,268 |
| Load vs 12,000 capacity | 9,500 | 51,500: impossible | 17,060: over by 5,060, and BPO's 5,000 only arrives on day 5 | 11,768: fits |
| Time to effect | Now | 20 minutes | 20 minutes | Flag now; cards in 8 hours |

**How:**
1. Option C fails the contact center: 5,060 contacts a day unserved for the 4 days before the BPO arrives, 20,240 in all.
2. Option D works in two steps: switch eligibility topics to a handoff message now, then switch to cards when they're live at hour 8.
3. Roll back the release in all cases except A: it costs 20 minutes and removes the most likely cause for the other topics too.

**Decision.** D. It is the only option that stops wrong eligibility answers and keeps the contact center inside its capacity.

**Trap.** Seeing it as on or off. The failure is in 18% of traffic, so the containment can be 18% wide.

## 4. Decision and Trade-offs

Roll back to the previous version now; turn generated eligibility answers off with a feature flag; publish answer cards at hour 8; keep cards for the rest of the window; notify every affected employer inside 5 business days.

| We give up | Why it's worth it |
|---|---|
| Generated eligibility answers for 18 days | They are wrong 2.3% of the time; cards are filled from each employer's plan data |
| 30% of eligibility questions get a handoff, not an answer | It adds 2,268 contacts a day, which the center can take |
| The new model version's gains on other topics | The previous version had the same 0.4% rate on them |
| Sales' request to notify only one customer | The contract requires notice, and a customer finding out later costs more |

**How:**
1. **Reversibility:** every step is a flag or a rollback; all of it can be undone in minutes. Notification is the one step that can't be, and it's required.
2. **Re-enable generated eligibility answers** only after the window closes, and only if an eligibility eval of at least 400 real questions passes at the old error rate or better, with each answer checked against the employer's plan rules.

**Decision.** Narrow containment and full notification, because it stops the harm at a cost the support center can carry and keeps us inside the contract.

**Trap.** Re-enabling the generated answers once rollback looks clean. Last month's 0.3% was measured in a quiet month; the rollback is unproven on enrollment traffic.

## 5. Economics

The horizon here is the 18 days left in the window, plus the revenue that renews in the next two quarters.

| | A. Keep running | C. Topic off, no cards | D. Rollback and cards |
|---|---|---|---|
| Overtime | — | 2,500 × 18 × $6 = $270k | 2,268 × 18 × $6 = $245k |
| BPO | — | 5,000 × 14 days × $14 = $980k | — |
| Unserved contacts | — | 20,240 in days 1–4 | None |
| More employees misled | 580 × 18 = 10,433 | 0 | 0 |
| Remediation review (3 days so far) | 75,600 × 8% = 6,048 flagged × 3 min = 302 h | 302 h | 302 h |

**How:**
1. **Cost of D:** about $245k of overtime, plus 302 specialist hours already on payroll: 20 implementation specialists (not contact-center staff) for 2 days gives 20 × 2 × 8 = 320 hours.
2. **Revenue side:** the escalating customer is $4.1M ARR, 4 months from renewal. If a mishandled incident cost even 5% of Q1 renewals (assumed), that is $52M × 5% = $2.6M.
3. **Option A** looks free and multiplies the remediation: each further day adds 580 employees to find, contact and correct.
4. **Opportunity cost:** the AI team's roadmap stops for about two weeks while the eval set and the plan-rule check are built.

**Decision.** Spend the $245k. It is under 6% of the escalating customer's ARR alone, and it stops the remediation list growing.

**Trap.** Leaving out the cost of option A. "Do nothing" carries a 10,433-employee remediation bill and the renewal risk.

## 6. Org and Ownership

One incident commander, clear roles, and the AI team kept on the fix rather than in meetings.

| Role | Who | Owns |
|---|---|---|
| Incident commander | You | Decisions, timeline, the noon brief |
| Technical lead | AI engineering manager | Rollback, flag, cards integration, eval set |
| Remediation lead | Head of Support | Re-check of 75,600 answers, affected lists, carrier late-adds |
| Customer notice | General Counsel with customer success | Notice template, 5-business-day clock, employer calls |
| Comms | Head of Communications | Public reply to the screenshot; holding statement |
| Executive sponsor | CEO | Approves the notification decision over sales' objection |

**How:**
1. One channel, one log, updates every 2 hours until containment is confirmed.
2. The postmortem owner is named today and is not the engineer who shipped the release.

**Decision.** You hold the incident command because the containment calls are technical, and you report to the CEO so the notification call has an executive owner.

**Trap.** Letting sales and support each contact customers on their own. Two different stories reach the same HR director by lunchtime.

## 7. Plan and Milestones

Hours for containment, days for notice, weeks for remediation and prevention.

| When | Milestone | Gate |
|---|---|---|
| Hour 0–1 | Severity 1; rollback; eligibility flag to handoff; holding statement | Eligibility generation confirmed off in logs |
| Hour 4 | Call with the escalating HR director | — |
| Hour 8 | Answer cards live for 12 questions | Cards spot-checked against 50 employers' plan setups |
| Noon, day 3 | Executive brief | Notification decision signed by the CEO |
| Day 5 | Re-check of 75,600 answers complete (20 implementation specialists, 2 days); affected list per employer | — |
| Day 7 | All affected employers notified, inside 5 business days | 100% of affected employers sent their list |
| Days 7–21 | Employees contacted through employers; corrections made in the window | Share of affected employees reached |
| Day 30 | Postmortem shared with customers; eligibility eval of 400+ cases in the release gate | — |
| Day 40 | Late-add requests to carriers for anyone who couldn't correct in the window | All filed before day 48 |

**Decision.** File carrier late-adds by day 40, not day 48, to leave a week for rejections and resubmission.

**Trap.** Treating containment as the end. The incident closes when the last affected employee is enrolled correctly.

## 8. Risk and Governance

The residual risks are the remediation missing people and the next release repeating the failure.

| Risk | Control |
|---|---|
| Affected employees missed | Re-check every logged eligibility answer, not a sample; employers confirm the list |
| Cards wrong for some employers | Filled from the admin system's plan setup; 50-employer spot check before launch |
| Rolled-back version also wrong on eligibility | Eligibility stays on cards for the whole window regardless |
| Next release repeats it | Release gate needs a pass on each high-impact topic, not just the average; at least 400 eligibility cases |
| Answers drift from plan rules | Automated check of each eligibility answer against the employer's plan rules before it is shown |
| Carrier rejects late adds | Filed by day 40, with the employer's request and our error documented |

**How:**
1. Topic-level slices in the eval: the release passed at 97% overall while failing one topic.
2. Canary new versions on 5% of traffic for 48 hours, with the error rate per topic compared to the old version.

**Decision.** Gate releases on the worst topic, not the average, because averages are how a 2.3% failure on 18% of traffic hides.

**Trap.** Promising "zero hallucinations". The commitment is that wrong answers are caught by checks and a slice-level gate, not that they never happen.

## 9. Metrics

Each recovery metric gets a guard that would catch the harm it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| Wrong eligibility answers shown | 0 a day from hour 1 | Handoff contacts a day, under 2,500 extra |
| Affected employees reached and corrected | 100% by day 40 | Late-add rejections by carriers |
| Employers notified | 100% inside 5 business days | Employers hearing of it first from employees |
| Release error rate per topic | At or below last month's | Coverage: share of eligibility questions answered, not handed off |
| Q1 renewal rate | At or above last year's | Incident named in churn reasons |

**Decision.** Report containment, remediation and renewals together each week through Q1, so a good containment number can't hide unfinished remediation.

**Trap.** Declaring success at "error rate back to normal". The employees misled on days 1–3 are still wrongly enrolled.

## 10. Communication

Fast, honest and consistent, with one owner per audience.

| Audience | One line |
|---|---|
| CEO and executives | "Contained in one hour, about 1,739 employees affected, every one will be found and corrected by day 40, $245k cost." |
| Escalating HR director | "We got this wrong, here are your affected employees, and here's the date each is fixed." |
| All affected employers | "Between days 1 and 3 our assistant gave some of your employees a wrong dependent rule; here's the list and how we're correcting it." |
| Employees (via employer) | "The rule you were told was wrong; here's the correct rule and the steps to update your enrollment." |
| Sales | "Every affected customer is told by us this week; here's what you may say if asked." |
| Public reply | "We found an error in our assistant's dependent answers, have fixed it, and are contacting everyone affected." |

**How:**
1. Updates every 2 hours to executives until containment is confirmed, then daily through day 7, then weekly to day 40.
2. Customers receive the postmortem at day 30, including what changed in the release gate.

**Decision.** Notify every affected employer, over sales' objection, because the contract requires it and a customer who finds out later is the renewal you lose.

**Trap.** A vague public statement about "rare inaccuracies". The screenshot is specific, so the reply has to be too.
