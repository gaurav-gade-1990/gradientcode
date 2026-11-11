# A Low Performer on a Critical Project: model answer

## 1. Situation

There are two problems here, and the strongest answer keeps them apart. One is a go-live that depends on a single person. The other is a person, until recently a strong one, who hasn't yet had clear feedback or been offered support. Fix the first with a re-plan this week. Handle the second with a fair process that takes as long as it needs.

| What | Number | What it forces |
|---|---|---|
| Dana's recent rate | 4 of 11 tickets = 36% of plan | The harness can't stay with one person at that rate |
| Harness at that rate | 5 days × 60% × 4/11 = 1.1 engineer-days a week; 15 / 1.1 ≈ 13.75 weeks | Done around week 14, not week 6 |
| Go-live if nothing changes | 13.75 + 4 weeks of tuning and launch = week 17.75, 7.75 weeks late | Past the 4-week line, so the $4.8M chain can terminate |
| Team capacity | 6 × 50 × 60% = 180, minus 20 = 160 against 150 needed | Only 10 engineer-days of slack |
| Dana's shortfall | 30 planned − 30 × 4/11 = 19.1 days | 9.1 days short overall, on top of the critical-path problem |
| Peer cost | 2 × 3 hours a week | The team is already paying for it quietly |

**How:**
1. Write down what is known: missed tickets, reverted PRs, missed meetings. Each is an observable fact with a date.
2. Write down what isn't known: why. A parent's illness may be part of it, but you don't diagnose it, and you don't assume it.
3. Out of scope: Dana's long-term future on the team. That is decided later, by a process, not this week.

**Decision.** Treat this as a delivery re-plan now and a feedback-and-support conversation now, with any formal step decided later and only if needed.

**Trap.** Treating it as one problem. Fixing the project by "managing Dana out" is unfair and slow; helping Dana while leaving the harness alone loses the customer.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| Dana | To be treated fairly, to keep their privacy, and to have room to recover | A private conversation first; clear written expectations; support offered before any formal step |
| HR partner | A fair, documented, consistent process | Briefed before the conversation; reviews the written expectations |
| Your manager | The go-live and no surprises | The risk in numbers and the re-plan, this week |
| Lee, the new harness owner | A fair workload and credit for the work | Lee's own price-matching work moves to the contractor |
| The two reviewing peers | Their 6 hours a week back | The re-plan stops the hidden review workload |
| The chain | Go-live in week 10 at 97% accuracy | Status in milestones; nothing about any individual |
| The rest of the team | A plan they believe | A re-plan explained as de-risking the critical path |

**The one idea to hold:** protect the project with the plan and protect Dana with the process, so neither has to give way to the other.

## 3. Options

Four options, scored on the go-live and on fairness to Dana.

| | A. Wait, cover quietly | B. Formal PIP now, Dana keeps the harness | C. Talk, write expectations, support, re-plan | D. Remove Dana now |
|---|---|---|---|---|
| Harness done | About week 14 | About week 14 | Week 6 under Lee | Week 6 or later; Lee learns it without Dana's help |
| Go-live | 7.75 weeks late | 7.75 weeks late | Week 10, with 11.9 days of slack | Week 10 at best, with no slack |
| Fair to Dana | No feedback, then a surprise later | Blocked by HR: no documented feedback yet | Feedback, support, time | No feedback, no support |
| HR and legal | Weak record | Fails policy | Follows policy | Weak record; exposure if challenged |

**How:**
1. **B fails twice.** HR policy requires documented feedback first, and a PIP puts the go-live in the hands of the person under the most pressure.
2. **C's capacity.** Even if Dana stays at 36%, 160 − 19.1 + 21 contractor days = 161.9 against 150: 11.9 days of slack.

**Decision.** Shortlist C. Keep the formal process as a later step, used only if the written expectations aren't met.

**Trap.** Reaching for the PIP first. A PIP without prior feedback reads as a paper trail for an exit, and HR won't approve it.

## 4. Decision and Trade-offs

Recommend C. This week: a private conversation with Dana, written expectations, support offered, and a re-plan that makes Lee the harness owner with Dana on a defined part of it. A contractor takes Lee's price-matching work for 6 weeks.

| We give up | Why it's worth it |
|---|---|
| Dana's sole ownership of the harness | The go-live no longer depends on one person's hardest weeks |
| Lee's planned work and focus | The contractor takes it; Lee gets credit for the gate |
| $36k of the $40k contractor budget | It is the cheapest protection against $320k of credits |
| A quick resolution | A fair process takes weeks, and the plan doesn't need it to be quick |

**How:**
1. **Reversibility.** The re-plan is fully reversible: if Dana recovers, ownership can come back after go-live. A formal PIP is not easily reversed, so it is a later, deliberate step.
2. **Checkpoint at week 4**, with written criteria agreed in week 0:
   - expectations met: keep supporting, return scope gradually;
   - not met and no new context: with HR, start the formal process;
   - Dana takes leave: the plan already works without Dana.

**Decision.** C, because it is the only option that gets the harness done by week 6 and gives Dana the feedback and support they haven't yet had.

**Trap.** Moving the harness without telling Dana why. Done silently, a re-plan feels like a demotion and arrives before the feedback did.

## 5. Economics

Compare costs over the window that matters: go-live in 10 weeks and the chain's renewal at 5 months.

| | A. Wait | B. PIP now | C. Re-plan and support | D. Remove Dana |
|---|---|---|---|---|
| SLA credits | 7.75 weeks late: 8 × $40k = $320k | Same as A | $0 if the plan holds | $0 at best, no slack |
| Revenue at risk | $4.8M a year (termination right) | $4.8M | Low | Medium: no slack |
| Direct spend | $0 | $0 | 6 weeks × 40 h × $150 = $36k (assumed rate) | Backfill: $230k / 2 = $115k (assumed), 4 months to hire |
| Hidden cost | Peers: 2 × 3 h × 10 weeks = 60 hours | Same | None | Lost knowledge; a backfill who arrives after go-live |

**How:**
1. **Contractor days.** 6 weeks × 5 days × 80% = 24, minus 3 to onboard = 21 engineer-days, which covers the 9.1-day shortfall twice over.
2. **Why the exit isn't cheaper.** 5 engineers give 5 × 30 − 20 = 130 days; with the contractor, 151 against 150. No slack, no Dana knowledge, and a backfill in month 4.
3. **Assumptions:** $150 an hour, 80% contractor focus, 60% team focus, the backfill cost and time.

**Decision.** C spends $36k to remove a $320k credit risk and protect $4.8M of revenue, and it doesn't depend on how Dana's situation turns out.

**Trap.** Seeing the exit as the fast, cheap option. It costs $115k, arrives after go-live, and removes the only person who knows the harness.

## 6. Org and Ownership

For 10 weeks, every critical piece has an owner who isn't single-threaded.

| Work | Owner | Support |
|---|---|---|
| Evaluation harness (go-live gate) | Lee | Dana, on the test-set loader and scoring slice, with dated tasks |
| Price-matching rules | Contractor | Lee reviews for the first week |
| Accuracy tuning, weeks 7–9 | Rest of the team | Lee |
| Dana's expectations and check-ins | You | HR partner |
| Customer status | You | — |

**Decision.** Dana keeps real, visible work on the harness, scoped so a missed date doesn't move go-live.

**Trap.** Taking Dana off everything. That reads as a verdict before any feedback, and it wastes the person who knows the harness best.

## 7. Plan and Milestones

Two tracks run in parallel: the project and Dana's process.

| Week | Project | Dana |
|---|---|---|
| 0 | Brief HR; re-plan agreed with Lee; contractor booked | Private conversation; written expectations within 2 days; support options from HR |
| 1 | Lee takes over the harness; contractor onboarded | Weekly 30-minute check-in starts |
| 2 | — | Written check-in against expectations |
| 4 | — | **Checkpoint:** met, not met, or new context; decided with HR |
| 6 | **Gate 1:** harness scores the 2,000-menu-page set end to end | — |
| 9 | **Gate 2:** ≥ 97% field accuracy | — |
| 10 | Go-live | Scope review |

**Decision.** The conversation with Dana happens before the re-plan is announced to the team, so Dana hears it first and from you.

**Trap.** Announcing the re-plan at standup and talking to Dana afterwards.

## 8. Risk and Governance

A fair process is specific, documented, supported and consistent.

| Risk | Control |
|---|---|
| Expectations are vague or about character | Written as observable outcomes with dates: named harness tasks, PRs passing CI before merge, notice before missing meetings |
| Inconsistent standard | The same bar as other L5s; HR checks it |
| Support is offered but not real | EAP, flexible hours, leave options explained by HR; you don't ask for medical details |
| Dana takes family leave | Approved through HR with no effect on assessment; the plan already covers it |
| The record is one-sided | Dana can respond in writing; notes kept factual and shared |
| Lee burns out | Contractor takes Lee's work; you watch after-hours workload |

**Decision.** HR is in before the first conversation and before any formal step, and nothing formal starts before the week-4 checkpoint.

**Trap.** Documenting only the misses. A fair record shows the feedback given, the support offered and the time allowed, not just the problems.

## 9. Metrics

Each success metric is paired with a guard.

| Success metric | Target | Guard metric |
|---|---|---|
| Harness complete | Week 6 | Lee's after-hours work |
| Field accuracy | ≥ 97% by week 9 | Any scope quietly cut to reach it |
| Dana's expectations | Met at weeks 2 and 4 | Check-ins held and support offered as promised |
| Peer review workload | From 6 hours a week to near zero | Review quality on the critical path |

**Decision.** Track the support you promised as carefully as the expectations you set; that is what makes the process fair.

**Trap.** Tracking only Dana's output. If the check-ins didn't happen, the process failed, not Dana.

## 10. Communication

What each audience hears, and what stays private.

| Audience | One line |
|---|---|
| Dana | "Your work slipped over six weeks; here is what I need, in writing, the support available, and a check-in every week." |
| HR partner | "Before I talk to Dana: here are the facts, my draft expectations, and the support I want to offer." |
| Your manager | "The harness was heading for week 14; with the re-plan and $36k it lands at week 6." |
| Lee | "You own the go-live gate; the contractor takes your price-matching work." |
| Team | "We've re-planned the critical path so no single person carries it." |
| Restaurant chain | "On track for week 10; the gates are at weeks 6 and 9." |

**How:**
1. Dana first, then Lee, then the team.
2. Weekly check-ins with Dana; weekly status to your manager.

**Decision.** Nobody outside Dana, HR and your manager hears anything about Dana's performance or circumstances.

**Trap.** Explaining the re-plan to the team by talking about Dana. Privacy is part of dignity, and part of a defensible process.
