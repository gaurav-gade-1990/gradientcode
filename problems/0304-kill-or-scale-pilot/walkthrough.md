## 1. What the problem is really asking

On the surface this is a yes-or-no question: kill the leasing assistant or scale it. Underneath, it's a question about reading a pilot honestly and then fitting the result to the people you'll have in 8 weeks. Your VP isn't asking whether AI chat is a good idea. They're asking what your team should keep running, and whether you can defend that call with numbers.

Three facts in the brief carry the case, and each is easy to skim past:

1. **The pilot was graded on the wrong metric.** Overtime fell 2 percent against a 30 percent target, so it looks like a failure. But the assistant only changed outcomes after hours, when no leasing agent is on duty and nobody is earning overtime. A metric that can't move is not evidence that the product doesn't work.
2. **The results split cleanly by time of day.** Business hours: 0.4 points, not significant. After hours: 6.5 points, significant. Vacancy days fell by 2.3, with a standard error of 0.8. That split tells you which version of the product to keep.
3. **The constraint is people, not money.** In 8 weeks you have 2 engineers. Scaling to all 300 properties needs two new PMS integrations, which is 12 engineer-months. Whatever you recommend must be built by week 8 and run by 2.

This is an Easy case: one team, and the call sits with you and your manager. The interviewer is still grading level. A strong answer refuses the binary, prices the value with its uncertainty, ignores the sunk cost out loud, and puts the legal risk under control before anything grows.

## 2. The numbers that drive the decision

Work these out in the first five minutes. Every later section reuses them.

**What the pilot showed.**
- After-hours inquiries at the pilot: 9,000 × 40% = **3,600 a month**.
- After-hours tour lift: 17.5% − 11.0% = **6.5 points**, so 3,600 × 6.5% = **234 extra tours a month** across 40 properties.
- Business-hours lift: 19.2% − 18.8% = **0.4 points**, p ≈ 0.24. No effect.
- Vacancy: 29.1 − 26.8 = **2.3 days** per turnover. 2.3 / 0.8 = **2.9 standard errors**; ± 2 SE gives a plausible range of **0.7 to 3.9 days**.

**What a vacancy day is worth.**
- Daily rent: $1,650 / 30 = **$55**.
- Units per property: 38,100 / 300 = **127**.
- At the 120 PMS-A properties: 120 × 127 = 15,240 units × 45% turnover = **6,858 turnovers a year**.
- Value at 2.3 days: 6,858 × 2.3 × $55 = **$867.5k a year**. At 0.7 days: **$264.0k**.
- All 300 properties at 2.3 days: 38,100 × 45% × 2.3 × $55 = **$2.17M a year**.

**What it costs to run.**
- After-hours conversations at 120 properties: 9,000 / 40 = 225 per property, × 120 × 40% = **10,800 a month**.
- Per Opus call: 4,000 cached × $0.20/1M + 1,000 × $4/1M + 300 × $20/1M = $0.0008 + $0.004 + $0.006 = **$0.0108**. Six calls: **$0.0648 a conversation**, so about **$700 a month**.
- Sonnet would be $0.0348 a conversation, saving only **$3,888 a year**.
- The engineer: $250k a year, about 97% of the run cost.

**The sunk cost.** 4 engineers × 5 months = 20 engineer-months = **$417k**. Write it down so you can say it doesn't count.

**The legal risk.** 4 / 500 = **0.8%** of conversations; at 10,800 a month that's about **86 a month** if unfixed.

## 3. How to spend your time

Forty-five minutes. Easy cases give you room to be precise, so use it.

| Minutes | What you do |
|---|---|
| 0–5 | Read the brief. Write down 6.5 vs 0.4 points, 2.3 ± 0.8 days, $55, 6,858, 10,800 and 0.8%. Circle "2 of your 4 engineers" and "PMS-A at 120 properties". |
| 5–12 | **Pillar A.** Reframe the pilot, name the sunk cost, build the stakeholder table with the sponsor's new metric. |
| 12–26 | **Pillar B.** Four options including the narrow one, the recommendation with its kill and expand triggers, and the 3-year economics at both ends of the range. |
| 26–36 | **Pillar C.** Owner and backup, a 6-week plan with the fair-housing gate, and the risk table with its numbers. |
| 36–43 | **Pillar D.** Metrics with guards and a control group, and one line per audience. |
| 43–45 | Check every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is actually being decided, and what did the pilot show?

**How to reason.** Start by separating the product from its metric. The overtime target assumed the assistant would take daytime work off agents. It didn't, because agents already answer fast in the daytime (0.4 points, within noise). It did change outcomes at night, when control properties make renters wait until morning (6.5 points). So restate the decision: which version of the assistant, if any, earns one permanent engineer from week 8?

Put the frame numbers in a table, each with what it tells you. Then say the sunk cost out loud: 20 engineer-months, $417k, already spent whatever you decide. Name what's out of scope: replacing agents, and the other two PMS products until the migration ends.

**The trap.** Two opposite mistakes. Killing it because the headline metric missed, or scaling it because so much has been spent. Both let an irrelevant number decide.

**Rubric criteria earned:** overtime named as the wrong metric; business and after hours separated; the 2.3-day gain with its range; the sunk cost named and set aside.

### Stakeholders

**The question it answers:** who has a stake, what do they want, and how do you bring them along?

**How to reason.** Even on a one-team case there are people outside the team with real stakes. Your VP wants a call and the migration staffed. The leasing operations director wants leads handled well and agents not undercut; giving agents the whole daytime and fixing the lost handoffs is your offer. The pilot sponsor needs a new way to call this a win, so give them vacancy days, which is rent. Legal needs the fair-housing problem fixed before anything grows. The payments lead needs to hear that the 2 engineers arrive on week 8, no matter what. And your engineers need credit for five months and a run load they can live with.

Close with one idea. The model answer's: everyone can get what they need from a smaller assistant.

**The trap.** Forgetting the payments lead. Your plan only works if it doesn't quietly borrow their engineers past week 8.

**Rubric criteria earned:** VP, operations, legal and payments covered; the sponsor's new measure; the engineers included; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the real options, and which fit 2 engineers after week 8?

**How to reason.** Lay out four options on one table: kill, extend the pilot as is, scale to all 300, and narrow and scale (after hours only, all 120 PMS-A properties). Then test each against the constraint:

- **Extend** needs 4 engineers for 3 more months, and 2 leave at week 8. Worse, it learns nothing: the after-hours effect is already significant and the business-hours one already flat.
- **Scale to all 300** needs PMS-B and PMS-C: 2 integrations × 2 engineers × 3 months = 12 engineer-months. The 2 who stay can't do that and run the system. It's a decision for after the migration.
- **Narrow and scale** reuses the PMS-A integration, so it needs no new integration at all. That's why it fits.

Keep kill as the fallback if the fair-housing gate fails.

**The trap.** Framing it as kill or scale. The data and the constraint both point to a third option, and finding it is the point of the case.

**Rubric criteria earned:** kill included plus an option between; the 12 engineer-months for full scale; why extending buys nothing; one table.

### Decision and Trade-offs

**The question it answers:** what do you recommend, what do you give up, and what would change your mind?

**How to reason.** Recommend D, and say what gets switched off: business-hours mode at the 40 pilot properties, which adds no measurable value but still carries risk and cost. Then the give-ups: the 180 PMS-B and PMS-C properties for now ($1.30M a year at the central estimate), one engineer permanently on run, and the overtime story.

Say it's reversible: a per-property flag can turn it off in minutes. Give a dated revisit at month 7 with two triggers, one each way. Expand to PMS-B if the vacancy gap holds at 1.5 days or more. Kill if it falls below 0.7 days (the low end of today's range), or on any substantiated fair-housing complaint.

**The trap.** Saying "scale" without saying what you switch off. Narrowing is what makes the run load fit.

**Rubric criteria earned:** one recommendation with what is switched off; give-ups including PMS-B and C; reversibility; expand and kill triggers.

### Economics

**The question it answers:** what are the value and cost over three years, and how sure are you?

**How to reason.** Value comes from vacancy days, not tours. More tours don't create more apartments; they fill the empty ones sooner. So value is turnovers × days saved × daily rent: $867.5k a year at 2.3 days, $264.0k at 0.7.

Costs over three years: build at 4 engineers for 1.5 months ($125k), run at 1 engineer for months 3 to 36 ($708k), and model spend of about $24k. That's $857k. Value over the same period, with year one counting 10 months: $2.46M at the central estimate (2.9×) and $748k at the low end (0.87×). Say both. A downside that roughly breaks even is a strong position.

Then dismiss the model question with numbers: switching to Sonnet saves $3,888 a year, less than an engineer-week of evals.

**The trap.** Optimizing the token bill. At $700 a month it's noise; the engineer is the cost.

**Rubric criteria earned:** value derived from turnovers, days and rent; the low end shown; cost per conversation from tokens and prices; people shown as almost all the cost.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owns what once half the team has left?

**How to reason.** You're accountable. One engineer runs it from week 8 with the second as a named backup and a runbook. The PM owns after-hours scope and the handoff format. The leasing operations director owns the morning queue. Legal owns the definition of a fair-housing failure, and engineering owns meeting it. Any prompt or model change passes the fair-housing eval first. Write down a run budget, so if run work grows past one person, the backlog pays, not the migration.

**The trap.** One engineer as the only person who understands the system. That's a single point of failure with a legal exposure attached.

**Rubric criteria earned:** a single owner; run engineer with backup and runbook; legal owns the failure definition; changes behind the eval.

### Plan and Milestones

**The question it answers:** what gets done before week 8, and where can it be stopped?

**How to reason.** Work backwards from week 8. Decide at week 2 and switch business-hours mode off. Spend weeks 2 to 4 on blocked topics in code, a 300-case adversarial eval set built with legal, and the handoff fix. Gate at week 5: zero fair-housing failures on the eval set and on 1,000 re-run past transcripts, with legal's sign-off. Roll to the 80 new properties in two waves of 40 during weeks 5 to 7. Hand over at week 8. Revisit at month 7.

**The trap.** Rolling out first and fixing guardrails after. The people who would fix them are gone at week 8.

**Rubric criteria earned:** done before week 8; a measurable fair-housing gate; waves; the month-7 revisit.

### Risk and Governance

**The question it answers:** what could go wrong at 120 properties, and what controls it?

**How to reason.** Multiply first. 0.8% of 10,800 is about 86 fair-housing problems a month if nothing changes, each a potential $50k to $150k defense. Then make the statistical point that separates strong answers: a clean sample of 1,000 only tells you the rate is probably below 3 in 1,000 (the rule of three), which is still up to 32 a month. Sampling can't prove safety, so the control has to be in code: blocked topics with a fixed, legal-approved reply, and an adversarial eval that blocks releases. Then the operational risks: 287 handoffs a month without context at the new volume, wrong bookings, and the single run engineer.

**The trap.** Calling 4 in 500 small. Multiplied by volume, it's a complaint a week.

**Rubric criteria earned:** problems a month quantified; why a clean sample isn't proof; the control in code; the handoff number.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how will you know at month 7 whether to expand or kill?

**How to reason.** Make vacancy days the primary outcome and pair it with fair-housing failures as the guard. Pair after-hours tour rate with no-show rate, so the assistant can't pad bookings. Pair share finished without a human with handoffs missing context. And use the PMS-B and C properties as the control group from now on: they're untouched, so the month-7 call compares like with like.

**The trap.** Reporting "62% handled by AI". It's an activity number, not an outcome.

**Rubric criteria earned:** guards paired; vacancy days as primary; a control group named; fair-housing as a guard.

### Communication

**The question it answers:** what does each audience hear, and how often?

**How to reason.** One line each, built from your numbers. The VP gets the call, the run load, the dollar estimate and the month-7 date. Leasing operations hears that agents own daytime. The sponsor hears that the win is vacancy days and the overtime target is retired. Legal hears that nothing goes live without their sign-off. The payments lead hears week 8. The team hears what they proved. Weekly status with the VP until week 8, monthly after, and a failed gate reported the same day.

**The trap.** Letting the overtime target linger. If you don't retire it now, it shows up at the next review as a miss.

**Rubric criteria earned:** four or more audiences; the overtime target retired; the payments lead reassured; cadence including bad news.

## 8. The decisions that separate strong answers

**Splitting the result before judging it.** Weak answers average the pilot into one verdict. Strong answers notice that business hours and after hours behave differently, and keep only the part that works.

**Pricing uncertainty, not just a point estimate.** The 2.3-day gain has a standard error of 0.8. Showing that the low end roughly breaks even, while the central estimate returns about 3×, is what makes the call defensible to a skeptical VP.

**Fitting the plan to next quarter's team.** The constraint isn't a footnote. A recommendation that needs 4 engineers after week 8 is not a recommendation.

## 9. Common mistakes

- **Killing on the headline metric.** The overtime miss says the metric was wrong, not the product.
- **Scaling on sunk cost.** $417k is spent either way.
- **Ignoring the integration cost of "scale everywhere".** PMS-B and C are 12 engineer-months.
- **Valuing tours instead of vacancy days.** Tours are an input; filled units are the outcome.
- **Treating a clean sample as proof.** Zero in 1,000 still allows 32 problems a month.
- **Optimizing model cost.** $3,888 a year is not the decision.

## 10. Follow-ups an interviewer might ask

**The sponsor insists on keeping daytime mode "for consistency". What do you say?**
Daytime adds 0.4 points that aren't significant, multiplies conversations by 2.5 (all hours are 100%, after hours 40%), and the fair-housing exposure with them, and gives agents a reason to resent the tool. Offer it back only if a daytime test at 10 properties shows a measurable gain.

**What if the vacancy gap at the 120 comes in at 1.0 day at month 7?**
That's inside today's range and above the kill line, so you don't kill it, and you don't expand either. Value at 1.0 day is 6,858 × $55 = $377k a year against about $258k of run cost, so keep it running and re-test at month 10.

**Your VP asks you to also free the second engineer for the backlog. Can it run on half a person?**
Only if handoffs and evals are stable. Agree a trial: if pages and fixes stay under a day a week for a month, the backup moves to the backlog and stays on call.

**Legal wants every transcript reviewed by a human. Is that reasonable?**
10,800 a month is not reviewable. Offer the code control plus the eval gate, a 200-a-month sample, and an instant flag to stop any property. Explain the rule of three so legal sees why sampling can't be the main control.

**When would you kill it outright?**
On any substantiated fair-housing complaint, or if the vacancy gap drops below 0.7 days for 3 months, the low end of the range at which it stops paying for its engineer.
