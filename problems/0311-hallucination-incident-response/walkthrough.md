## 1. What the problem is really asking

On the surface this is a question about an AI bug: the assistant hallucinated a dependent rule. Underneath, it's an incident-command question with two clocks and a capacity limit. The interviewer wants to see whether you can stop harm in hours, size it in numbers, notify the right people over internal pressure, and make the affected employees whole before their deadlines pass.

Three facts in the brief carry the case:

1. **The failure is narrow.** Eligibility answers went from 0.3% wrong to 2.3% wrong; other topics stayed at 0.4%. That means the containment can be narrow too, and that changes everything about the contact-center problem.
2. **Off isn't available.** Switching the assistant off adds about 42,000 contacts a day to a center with room for 2,500. The "safe" answer is the one that breaks enrollment support for 2.6M employees.
3. **The harmed people aren't your customers.** Employees were misled, but employers hold the contract. You reach employees through employers, which is why notifying every affected employer, not just the one who complained, is both required and wise.

A strong answer contains in the first hour, says how many people were affected, declines sales' request with a reason, and changes the release gate so a 97% overall pass can't hide a failing topic again.

## 2. The numbers that drive the decision

**Exposure.**
- Eligibility conversations: 140,000 × 18% = **25,200 a day**.
- Error rate since the release: 46 / 2,000 = **2.3%**, against 3 / 1,000 = 0.3% last month. Other topics: 4 / 1,000 = 0.4%, unchanged.
- Affected so far: 3 days × 25,200 × 2.3% = **1,739 employees**, assuming each conversation is a different employee.
- Added per day if nothing changes: 25,200 × 2.3% = **580**; over the 18 days left, 580 × 18 = **10,433**.

**Contact center.**
- Spare room: 12,000 − 9,500 = **2,500 contacts a day**.
- Assistant off: 140,000 × 30% = 42,000 extra, total **51,500**.
- Eligibility off with a handoff: 25,200 × 30% = 7,560 extra, total **17,060**, over by 5,060.
- Cards for the 70% of questions they cover, handoff for the rest: 25,200 × 30% = 7,560 unanswered, × 30% contact rate = **2,268 extra**, total **11,768**, inside capacity.

**Cost.**
- Cards option overtime: 2,268 × 18 days × $6 = **$245k**.
- Topic off, no cards: 2,500 × 18 × $6 = $270k overtime, plus BPO 5,000 × 14 days × $14 = $980k, and 5,060 × 4 = **20,240 contacts unserved** before the BPO arrives.

**Remediation.**
- Answers to re-check: 3 × 25,200 = 75,600; 8% flagged = **6,048**; × 3 minutes = **302 hours**. 20 lent specialists × 2 days × 8 hours = 320 hours, so it's done by day 5.
- Deadline: 18 days left + 30 days of late-add tolerance = **day 48**.

**Revenue at stake.** $4.1M ARR for the escalating customer. If a mishandled incident cost 5% of Q1 renewals (assumed), $52M × 5% = **$2.6M**.

## 3. How to spend your time

Forty-five minutes, about ten per pillar.

| Minutes | What you do |
|---|---|
| 0–5 | Read the brief. Write down 2.3% vs 0.4%, 1,739, 580 a day, 2,500 room, 2,268, day 48. Circle "5 business days" and "only the customer who complained". |
| 5–13 | **Pillar A.** State the two clocks and the harm. Stakeholders, including employees reached through employers. |
| 13–27 | **Pillar B.** The containment options against the contact center, the call, and the cost of each including doing nothing. |
| 27–37 | **Pillar C.** Incident roles, an hour-by-hour then day-by-day plan, and what changes in the release gate. |
| 37–43 | **Pillar D.** Metrics with guards, and one line per audience. |
| 43–45 | Check each number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** how bad is it, how fast is it growing, and what clocks are running?

**How to reason.** Locate the failure first: compare the sample error rates. Eligibility jumped from 0.3% to 2.3% while other topics held at 0.4%, so the release broke one topic, not the assistant. Then put numbers on the harm: about 1,739 employees so far (label the one-employee-per-conversation assumption) and 580 more each day. Name the two clocks: 18 days left in the window, and day 48, after which carriers may refuse late adds. Then say what you'll do first: contain, then diagnose. The release is the suspect; you don't need proof to roll it back.

**The trap.** Opening with "first we need to understand the root cause". Every hour of analysis adds about 24 wrong answers.

**Rubric criteria earned:** the failure located by comparing rates; affected and per-day harm estimated with the assumption labelled; both clocks; containment before root cause.

### Stakeholders

**The question it answers:** who has a stake, what do they want, and how do you bring them along?

**How to reason.** The interesting tension is sales. They want only the complaining customer notified, to protect renewals. Decline, with two reasons: the contract requires notice within 5 business days of confirming an error, and an employer who learns about it later from their own employees is the renewal you actually lose. Then think about employees. They were harmed, but they're the employer's people; you reach them through the employer, with wording the employer approves. Support's worry is load, and your containment plan has to answer it with a number (2,268 extra contacts, inside 2,500). The AI team needs a blameless review: a 97% eval with 40 eligibility cases is a process gap, not one person's fault.

**The trap.** Leaving out the employers who haven't complained. Most affected employers don't know yet.

**Rubric criteria earned:** the escalating customer, all employers, employees, sales, legal and support; sales' request addressed; employees reached through employers; the one idea.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the containment options, and how does each do on harm, load and speed?

**How to reason.** Four options on one table:

- **Keep running with a disclaimer.** No load, but 580 more misled employees a day.
- **Assistant off.** No harm, but 51,500 contacts a day against 12,000 of capacity. It breaks enrollment support.
- **Eligibility off with a human handoff.** No harm, 17,060 contacts a day, and the BPO's extra 5,000 doesn't arrive until day 5: 20,240 contacts unserved.
- **Rollback plus answer cards.** Cards cover 70% of eligibility questions from each employer's own plan data, with no model involved; the rest get a handoff. 11,768 contacts a day, inside capacity.

Notice the sequence inside the last option: flag eligibility to the handoff now (20 minutes), switch to cards at hour 8. The first 8 hours run at the higher handoff load, about 7,560 × 8/24 = 2,520 extra contacts, and the other 16 hours add 2,268 × 16/24 = 1,512, so today has about 4,032 extra contacts against 2,500 of room. Say so: today has long queues and overtime, and every day after fits.

**The trap.** Framing it as on or off. The failure is in 18% of the traffic.

**Rubric criteria earned:** keep-running and shutdown included; extra contacts against 2,500 for each; the no-cards overload shown; one table.

### Decision and Trade-offs

**The question it answers:** what do you do, what do you give up, and when do you restore generated answers?

**How to reason.** The call: roll back, flag eligibility off, cards at hour 8, cards for the rest of the window, and notice to every affected employer. Then list the give-ups:

- generated eligibility answers for 18 days;
- a handoff for 30% of eligibility questions;
- the new version's gains on other topics;
- sales' request.

Separate what can be undone from what can't. Flags and rollback reverse in minutes. Notification can't be taken back, which is why it's a CEO-signed decision. Set a condition for restoring generated eligibility answers: after the window, and only when a 400-case eligibility eval passes at last month's rate or better, with a check against the employer's plan rules in front of every answer.

**The trap.** Turning generated answers back on because the rollback looks fine. Last month's 0.3% came from a quiet month, not enrollment traffic.

**Rubric criteria earned:** rollback plus narrow containment; give-ups named; reversible and irreversible steps separated; a measurable re-enable condition.

### Economics

**The question it answers:** what does each option cost through the window, and what's at stake?

**How to reason.** The horizon is 18 days, not three years. Price each option from the brief: the recommended option costs $245k of overtime; the no-cards option costs $1.25M and still leaves 20,240 contacts unserved. Keep-running costs nothing in cash and adds 10,433 employees to the remediation list. Then the remediation itself: 302 hours of review, done by 20 lent specialists in 2 days, so it doesn't take contact-center capacity. Compare against revenue: $245k is under 6% of the escalating customer's $4.1M ARR, and 5% churn on Q1 renewals (assumed) would be $2.6M.

**The trap.** Calling keep-running free. Its cost arrives as remediation and renewals.

**Rubric criteria earned:** overtime and BPO priced; remediation sized and staffed; keep-running costed in people; response cost against ARR with the assumption labelled.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who runs the incident, and who owns each workstream?

**How to reason.** One incident commander (you), because the containment calls are technical. Separate owners for the three workstreams that run in parallel:

- **Containment and the fix:** the AI engineering manager.
- **Remediation:** the head of support.
- **Customer notice:** the general counsel with customer success.

Comms handles the public reply. The CEO signs the notification decision, because it overrides sales. Name the postmortem owner today, and make it someone other than the engineer who shipped.

**The trap.** Sales and support contacting customers separately. Two stories reach one HR director.

**Rubric criteria earned:** one commander; separate owners per workstream; an executive owner for notice; a blameless postmortem with an independent owner.

### Plan and Milestones

**The question it answers:** what happens in the first hour, the first week and the next six weeks?

**How to reason.** Three time scales. Hours: rollback and the flag in hour 1, a call to the escalating HR director by hour 4, cards at hour 8, the executive brief at noon. Days: re-check done by day 5, every affected employer notified with their list by day 7, inside 5 business days. Weeks: employees corrected through employers during the window; postmortem and new release gate at day 30; carrier late-adds filed by day 40, a week before the day-48 limit, so rejections can be resubmitted. Put a checkable gate on each step: generation confirmed off in logs, cards spot-checked against 50 employers.

**The trap.** Closing the incident at containment. It closes when the last affected employee is enrolled correctly.

**Rubric criteria earned:** containment in hour 1; notice inside 5 business days; late-adds with slack; checkable gates.

### Risk and Governance

**The question it answers:** what could still go wrong, and what stops a repeat?

**How to reason.** Two residual risks. First, the remediation misses people: re-check every logged eligibility answer, not a sample, and have employers confirm the list. Second, the next release repeats the failure: the eval passed at 97% overall while failing one topic, so gate on the worst topic, with at least 400 eligibility cases. Add a runtime check that compares each eligibility answer to the employer's plan rules before it's shown, and a 48-hour, 5% canary that compares error rates topic by topic.

**The trap.** Promising zero hallucinations. Commit to catching them, not to their absence.

**Rubric criteria earned:** every answer re-checked; a per-topic release gate; a plan-rule check at runtime; no zero-error promise.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how do you know the response worked, and what would it hide?

**How to reason.** Pair each metric:

| Success metric | Guard metric |
|---|---|
| Wrong eligibility answers shown: 0 from hour 1 | Extra handoff contacts, under 2,500 a day |
| Affected employees corrected: 100% by day 40 | Carrier late-add rejections |
| Employers notified inside 5 business days | Employers who heard it first from employees |
| Per-topic error rate at or below last month | Share of eligibility questions answered, not handed off |
| Q1 renewal rate | Incident named in churn reasons |

**The trap.** Declaring victory when the error rate is back to normal, while 1,739 employees are still wrongly enrolled.

**Rubric criteria earned:** paired metrics; affected employees tracked; handoff load tracked; renewals.

### Communication

**The question it answers:** what does each audience hear, when, and from whom?

**How to reason.** Be specific, because the screenshot is. One line each:

- **Executives:** contained in an hour, about 1,739 affected, all corrected by day 40, $245k.
- **The escalating HR director, by phone from you:** we got it wrong, here's your list and the date each person is fixed.
- **Every affected employer:** what happened, their list, the correction plan.
- **Employees, through employers:** the right rule and the steps to fix their enrollment.
- **Sales:** what they may say.
- **The public reply:** what was wrong, that it's fixed, and that everyone affected is being contacted.

Cadence: every 2 hours to executives during containment, daily to day 7, weekly to day 40. Share the postmortem with customers at day 30.

**The trap.** "Rare inaccuracies may occur." A vague statement against a specific screenshot reads as hiding.

**Rubric criteria earned:** four or more audiences including employers and employees; a personal, early call; a tightening cadence; the postmortem shared.

## 8. The decisions that separate strong answers

**Narrow containment over a kill switch.** Weak answers switch the assistant off and stop. Strong answers see that the failure is in 18% of traffic, do the contact-center arithmetic, and contain only that topic, with deterministic cards to keep most employees answered.

**Notifying everyone over sales' objection.** The contract and the renewal logic point the same way. A leader who can say why in one sentence, and get the CEO to sign it, shows the level being tested.

**Fixing the gate, not the prompt.** The real failure is a release gate that averaged away a broken topic. Changing the prompt fixes this incident; changing the gate fixes the next one.

## 9. Common mistakes

- **Root cause before containment.** About 24 more wrong answers an hour while the team investigates.
- **No count of affected people.** "Some employees" can't be remediated; 1,739 named people can.
- **Ignoring the contact center.** The shutdown plan sounds responsible and fails on day one.
- **Notifying only the complainer.** It breaches the contract and loses the renewals sales wanted to protect.
- **Forgetting the deadline.** Employees misled on day 1 need correcting before day 48, or the error is permanent for the plan year.
- **Blame.** Naming the engineer who shipped makes the next incident get reported later.

## 10. Follow-ups an interviewer might ask

**What if the re-check finds 4,000 affected, not 1,739?**
The review hours don't change, because every logged answer is re-checked anyway (302 hours). What grows is the outreach: more than twice as many employees to contact through employers, and more late-add requests, so customer success and carrier relations need more people. Employer notices still go by day 7.

**The escalating customer demands the assistant be off for their employees for the rest of the year.**
Agree; it's a per-employer flag. Assuming their employees use the assistant at the average rate, that's 140,000 × 38,000 / 2.6M = 2,046 conversations a day, and × 30% = 614 contacts, of which about 33 were already counted. The center goes to about 12,350, over its 12,000, so book the BPO today and run overtime until it arrives on day 5. Say yes anyway: it's the cheapest trust you can buy with a $4.1M renewal 4 months away.

**Legal says notice "could create liability". Does that change the plan?**
No. The contract requires notice, and the liability exists whether or not you notify. Legal shapes the wording; it doesn't decide whether to send it.

**How do you stop this happening with the next model upgrade?**
A release gate that judges each high-impact topic separately with enough cases (400 or more for eligibility), a runtime check against plan rules, and a 5% canary for 48 hours comparing topic error rates. Problems 0149 and 0147 cover the gate and the canary logic.

**Would you ever leave a known-wrong topic running?**
Only if every alternative caused more harm, for example if no human channel existed. Here the cards and handoff exist, so no.
