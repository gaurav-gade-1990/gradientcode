## 1. What the problem is really asking

On the surface this is a prioritization exercise: six initiatives, not enough engineers, pick the best. Underneath, it's a calendar problem with an expectations problem on top. The GM isn't asking you to rank ideas. They're asking what the unit will actually have running, and earning, by month 12, and they've already told the CEO a number.

Three facts in the brief carry the case:

1. **The freeze decides the order.** From month 4 to month 9, nothing new may write to quotes, orders or invoices. Two initiatives write to ERP. If you rank by value and fill from the top, your best item can't go live until month 10, and the cutover has slipped before.
2. **Quote Assist comes in two halves.** The draft-only version reads the reporting replica and writes nothing, so it can go live during the freeze. Spotting this is the single biggest move in the case.
3. **The $3M is a promise you didn't make.** A director's job is to work out what's credible and reset it before the quarterly review turns it into a commitment.

The interviewer is grading level: scope, cost, people and risk. A strong answer places work by quarter, cuts things out loud, turns a sponsor's estimate into a defensible gross-profit number, and has a plan for the ERP slipping.

## 2. The numbers that drive the decision

Work these out in the first five minutes.

**Capacity.**
- 7 free engineers × 12 = **84 engineer-months**. Requests: 30 + 12 + 10 + 20 + 16 + 14 = **102**. You must cut 18.
- Per quarter: 7 × 3 = **21**. The window after the freeze (months 10–12) holds only 21.

**The quote business.**
- Quoted a month: 12,000 × $4,800 = **$57.6M**.
- Rep time on RFQs: 12,000 × 40 min = **8,000 hours** of 110 × 140 = 15,400, so **52%** of rep time.
- Today's win rate: 25% × 31% + 75% × 22% = **24.25%**.

**What faster quotes are worth.**
- Draft-only, 45% fast: 45% × 31% + 55% × 22% = **26.05%**, a gain of 1.8 points. 1.8% × $57.6M × 12 = **$12.4M** revenue, × 24% = **$2.99M** gross profit.
- Write-back, 60% fast: 60% × 31% + 40% × 22% = **27.4%**, a gain of 3.15 points: **$21.8M** revenue, **$5.23M** gross profit.
- Halve both, as an assumption, because fast quotes are partly easy quotes: **$1.49M** and **$2.61M**.
- Search: 2% × $96M = $1.92M revenue × 24% = **$461k**.
- Month-12 run-rate: **$1.95M** without write-back, **$3.07M** with it.

**Value per engineer-month in the post-freeze window.**
- Write-back adds $2.61M − $1.49M = $1.12M for 12, about **$93k each**.
- AR triage claims $400k for 16, **$25k each**.

**Model cost.** Quote Assist per RFQ: 12,000 × $2/1M + 1,500 × $10/1M = $0.024 + $0.015 = **$0.039**, so 12,000 × $0.039 = **$468 a month**. Catalog: 420,000 × $0.0005 = $210 on Haiku plus 42,000 × $0.01 = $420 on Sonnet. Model spend is noise against the $900k cap.

**Risk.** 12,000 RFQs × 12 lines = 144,000 lines a month; at 86% top-1, **20,160** are wrong.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–5 | Read the brief. Mark which initiatives write to ERP. Write down 84 vs 102, 21 per quarter, 24.25%, $57.6M. |
| 5–12 | **Pillar A.** Frame it as a sequencing problem around the freeze. Stakeholder table, including the ERP programme lead and the two sponsors who don't get their ask. |
| 12–27 | **Pillar B.** Two or three whole-year sequences, the recommendation by quarter, and the run-rate floor and upside. This pillar carries the most marks. |
| 27–37 | **Pillar C.** Owners, a quarterly plan with the month-9 checkpoint, and the wrong-SKU risk with its number. |
| 37–43 | **Pillar D.** Metrics with guards, and the line that resets the GM's $3M. |
| 43–45 | Check every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is being decided, and which numbers and dates frame it?

**How to reason.** Before anything else, sort the six initiatives into "writes to ERP" (write-back, AR triage) and "doesn't" (the rest). That one sort turns a ranking problem into a sequencing problem. Then put the frame numbers in a table: capacity against demand, the 21-engineer-month post-freeze window, the quoted volume, rep time and today's win rate. Each row should say what it forces.

Name the judging standard: gross-profit run-rate at month 12, which is what the GM promised. And say what's out of scope: the ERP programme itself and the forecast model.

**The trap.** Value-ranking first. The best initiative is blocked until month 10, so a value-ranked plan has nothing to show in the middle of the year.

**Rubric criteria earned:** the freeze named as the driver; capacity against demand and the window; the win-rate baseline and quoted volume; the $3M named as a claim to test, plus something out of scope.

### Stakeholders

**The question it answers:** who has a stake, what do they want, and how do you bring them along?

**How to reason.** There are six sponsors including the GM, and two of them don't get their ask this year. For each, say what they get instead. BU finance gets a funded start for AR triage next year, with the reason: credit memos are frozen. The VP Field Sales gets a $12k trial of the CRM vendor's copilot instead of 14 engineer-months. Don't forget the ERP programme lead. Their freeze is the constraint, and promising in writing that nothing writes to ERP in months 4–9 is what earns you read access and their help at cutover.

Close with one idea. The model answer's: the freeze decides the order, which lets you say no without ranking sponsors against each other.

**The trap.** A table where every sponsor gets something this year. That's the five-half-funded-projects plan.

**Rubric criteria earned:** the GM and four or more sponsors; what finance and field sales get instead; the ERP lead; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the real ways to fill the year?

**How to reason.** Here the options are whole-year sequences, not single initiatives. Put three on one table:

- **Value-ranked:** write-back and AR first. Over capacity at 102, and nothing can go live during the freeze.
- **Freeze-aware:** catalog and a draft-only MVP in months 1–3 (10 + 11 = 21), draft-only rollout and search during the freeze (19 + 20 = 39), write-back after (12). That's 72 of 84, with 12 held for run and slip.
- **Wait for the new ERP:** do the non-ERP work, then build Quote Assist once against the new system. Only 44 of 63 engineer-months used by month 9, and almost nothing live at month 12.

Then the AR question: AR needs 16 after month 9, write-back needs 12, and the window holds 21. Both don't fit, and write-back earns almost four times as much per engineer-month.

**The trap.** Treating the freeze as dead time. Draft-only puts most of Quote Assist's value live in month 4 without touching ERP.

**Rubric criteria earned:** whole-year sequences compared; draft-only spotted as freeze-safe; the window too small for both; one table.

### Decision and Trade-offs

**The question it answers:** what roadmap do you recommend, what do you give up, and what would change it?

**How to reason.** State the roadmap by quarter. Then the give-ups: AR triage this year, built account briefs, 10 minutes per RFQ until write-back lands, and the $3M promise. Say which parts are reversible. The second half of the year is a two-way door; catalog enrichment is a one-way investment, but it pays for two initiatives.

The key move is the month-9 checkpoint. If the cutover has slipped, write-back moves to next year, and its 12 engineer-months go to AR design or the rollout. Agree that branch now, so a slip is a plan, not a crisis.

**The trap.** Giving every sponsor a slice. Spread across six, nothing reaches month 12 finished.

**Rubric criteria earned:** a roadmap by quarter; cuts named with reasons; reversibility; a dated checkpoint with a pre-agreed alternative.

### Economics

**The question it answers:** what is each initiative worth at month 12, and what does the plan cost?

**How to reason.** Turn the 4-hour share into a win rate, the win rate into revenue on $57.6M a month, and revenue into gross profit at 24%. Then apply the haircut and label it: fast quotes are partly easy quotes, so assume only half the gap is caused by speed. That gives a floor of $1.95M and an upside of $3.07M. Take search at the sponsor's figure but say why: it's 15% of the total, so the decision doesn't depend on it.

Keep the two money columns apart. People on payroll: 72 engineer-months, $1.38M, already paid. New spend: about $102k of the $900k cap, of which model spend is about $6k. The budget isn't what limits you; money can't buy you through a freeze. Hold $250k (assumed) for an ERP contractor after cutover.

**The trap.** Adding rep hours saved on top of the win-rate gain. The freed hours are how quotes get faster, so counting both double-counts.

**Rubric criteria earned:** win rate turned into gross profit; the haircut labelled; floor and upside; new spend separated from payroll.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owns the roadmap, each initiative and the number?

**How to reason.** You own the roadmap and the gates. Each initiative has a tech lead. Sponsors own adoption, not just the request: the VP Inside Sales signs up to the 45% target. And BU finance, not your team, reports the run-rate, so when you say $2M the GM believes it. Keep a regression eval on 500 labelled RFQs in front of prompt changes.

**The trap.** Measuring the AI team on launches. A tool reps don't use is a launch and a loss.

**Rubric criteria earned:** a single owner; sponsors own adoption; finance reports value.

### Plan and Milestones

**The question it answers:** what ships when, and where can it be stopped?

**How to reason.** Lay it out by month, with gates: top-1 match of at least 85% at month 3; 40% of quotes within 4 hours at the pilot branches by month 7; the month-9 checkpoint on ERP stability. Two details show you've thought about the freeze in practice. First, the reporting replica itself changes at cutover, so plan a week to re-point the read layer in month 6. Second, write-back starts at 3 branches, not 38.

**The trap.** Scheduling write-back for month 10 as if the cutover will be on time. Both of the last two slipped.

**Rubric criteria earned:** something live during the freeze; a measurable gate; the replica change planned; the month-9 checkpoint.

### Risk and Governance

**The question it answers:** what could go wrong, and what controls it?

**How to reason.** Multiply first: 144,000 lines a month at 86% means 20,160 wrong matches for reps to catch. Then the controls: confidence shown on every line, low-confidence lines flagged, and a rep confirming each line before sending. Crucially, AI never sets price; contract pricing stays in ERP, so a wrong match costs rep minutes, not margin. Add the cutover slip (the checkpoint) and write-back safety (writes in draft status only, pilot first).

**The trap.** Calling 86% good enough without multiplying it by volume.

**Rubric criteria earned:** wrong matches quantified; pricing kept in ERP; a slip fallback; human confirmation per line.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how will you know it worked, and what would show harm?

**How to reason.** The headline is the one the GM promised: gross profit, through win rate. Guard it with margin per won quote, so nobody wins by discounting. Pair quote speed with lines changed after sending and wrong-part returns. Pair minutes per RFQ with weekly usage. And have finance compare pilot and non-pilot branches, so the 50% haircut becomes a measurement within two quarters.

**The trap.** Reporting minutes saved as the outcome. It's the mechanism, not the result.

**Rubric criteria earned:** guards paired; margin guards win rate; a pilot versus non-pilot comparison; gross profit as the headline.

### Communication

**The question it answers:** what does each audience hear, and how often?

**How to reason.** The most important line is the private one to the GM, before the review: "Tell the CEO $2M by month 12; $3M if the ERP cutover holds. We'll know at month 9." Then one line each for the VP Inside Sales (dates for both halves of Quote Assist), BU finance (AR next year, funded, with the reason), the VP Field Sales (trial the copilot), the ERP lead (no writes in the freeze) and reps (it drafts, you decide). Monthly reviews with the GM, quarterly to leadership, gates reported the day they're run.

**The trap.** Letting $3M stand. Once it's said at the review, it's the number you're measured on.

**Rubric criteria earned:** four or more audiences; the $3M reset; deferred sponsors told when and why; a cadence including failures.

## 8. The decisions that separate strong answers

**Splitting Quote Assist in two.** Weak answers treat Quote Assist as one blocked project. Strong answers see that the read-only half carries most of the value and ships during the freeze.

**Discounting the sponsor's logic, not just the number.** The win-rate gap between fast and slow quotes is real, but it isn't all caused by speed. Saying so, halving it as a labelled assumption, and planning to measure it is what a GM trusts.

**Planning for the slip.** Two of the last two cutovers slipped. A month-9 checkpoint with a pre-agreed alternative shows you plan with the organization you have.

## 9. Common mistakes

- **Value-ranking without the calendar.** The top item is blocked for six months.
- **Funding everyone a little.** Five half-done projects are worth nothing at month 12.
- **Taking win-rate correlation as causation.** Fast quotes are partly easy quotes.
- **Double-counting rep hours and win rate.** One is how the other happens.
- **Spending the budget because it's there.** $900k doesn't buy you through a freeze.
- **Accepting the GM's number.** A director resets expectations before they harden.

## 10. Follow-ups an interviewer might ask

**The GM says the CEO won't accept $2M. What do you do?**
Show what $3M depends on: write-back live by month 10 and 60% of quotes out fast. Offer to protect it: ask the ERP programme for a 2-week write slot in month 10 and fund the $250k contractor then. But don't promise the cutover date; it isn't yours.

**The cutover slips 3 months. What changes?**
The freeze runs to month 12, so write-back moves to next year and the run-rate at month 12 is $1.95M. The 12 engineer-months go to designing AR triage against the new ERP, and both ERP items start in next year's first quarter.

**Finance escalates AR triage to the GM. How do you respond?**
Show value per engineer-month in the only window it could use: $25k for AR against $93k for write-back. Then offer the funded start next year and the contractor reserve to bring it forward.

**What if draft-only adoption is low at month 7?**
That's Gate 2. Below 40% fast quotes at the pilot branches, stop the rollout, sit with the reps, and fix the workflow before adding branches. Don't start write-back on a tool reps aren't using.

**Why not build account briefs? Reps would love them.**
There's no value estimate and it would take 14 engineer-months. A 20-seat trial of the CRM vendor's copilot costs $12k and answers whether reps use briefs at all.
