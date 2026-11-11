## 1. What the problem is really asking

On the surface this is an ROI ranking: eight proposals, a $5M budget, sort and cut. Underneath, it's three problems stacked. The claims aren't comparable, two of them count the same calls, and the thing that runs out first isn't money. The CFO isn't asking you to repeat the sponsors' numbers in order. They're asking for a portfolio they can defend to the board, with a line that each sponsor accepts as fair.

Three facts in the brief carry the case:

1. **The evidence is uneven, and finance has already said how to weigh it.** A vendor case study is worth 30 percent of its claim; a production pilot is worth 80. P3's A/B test measured a smaller effect than the sponsor claims. Apply these before you rank anything.
2. **The bottleneck is in-house data engineers on customer data.** Money ($5.45M asked against $5M) and ML engineers (108 against 120) are almost enough. Data engineers on customer data are not: 84 asked, 60 available, no hiring, no contractors. And two proposals (P4, P5) don't touch customer data at all, so contractors can do their data work.
3. **Care calls are counted more than once.** P1 deflects calls, P2 summarizes calls, P8 cuts a subset of calls. You can't add all three.

The interviewer is grading level. A strong answer ranks against the real bottleneck, stages the biggest uncertain bet, makes the board's risk item an explicit exception, and sets up finance to measure the results.

## 2. The numbers that drive the decision

Work these out in the first five minutes.

**Weight every claim.**
- P1: $16.8M × 30% (vendor study) = **$5.04M**. That implies 20% × 30% = **6%** of calls deflected.
- P2: $7.0M × 80% (pilot) = $5.6M; but only 94% of calls reach an agent if P1 runs, so **$5.26M**.
- P3: the A/B measured 0.03 points, not 0.05, so $6.34M × 0.03/0.05 = $3.80M, × 80% = **$3.04M**.
- P4: $1.5M × 60% = **$0.90M**. P5: $1.2M × 60% = **$0.72M** (invoices are historical data).
- P6: $1.8M × 60% (back-test) = **$1.08M**.
- P7: $2.4M × 20% (sponsor estimate) = **$0.48M**.
- P8: $2.02M × 60% = **$1.21M**.
- Total after weights and the P1–P2 overlap: **$17.7M**, against **$39.05M** claimed.

**Find the bottleneck.**
- In-house data-engineer months on customer data: 18 + 8 + 14 + 16 + 10 + 18 = **84** against **60**.
- Non-customer data: P4 12 + P5 2 = **14**, contractor-able at $25k a month.
- ML: 108 of 120. Budget: $5.45M of $5M.

**Rank per bottleneck month (customer-data projects only).**
- P2 **$658k**, P1 **$280k**, P3 **$217k**, P6 **$67.5k**, P8 **$67.2k**, P7 **$48k**.
- Fill 60: P2 8 + P1 18 + P3 14 = 40; then P6 16 = **56**. P8 (18) no longer fits.

**Portfolio cost.**
- New spend: $0.6M + $1.8M + $0.4M + $0.5M + $0.3M + $0.25M, plus contractors 14 × $25k = $0.35M, so **$4.2M**.
- Payroll: 56 in-house data months at $200k / 12 plus 82 ML months at $260k / 12 = **$2.71M**.
- Weighted benefit: **$16.05M**, about **2.3×** year-one cost.

**P2's model.** Sonnet: 1.0M × 12 × (5,000 × $2 + 250 × $10)/1M = **$150k** a year; Haiku **$7.5k**.

## 3. How to spend your time

| Minutes | What you do |
|---|---|
| 0–7 | Read the brief. Weight all eight claims. Mark which use customer data. Write down 84 vs 60, and the 6% deflection overlap. |
| 7–14 | **Pillar A.** Name the bottleneck. Build the stakeholder table, including the two sponsors who lose. |
| 14–28 | **Pillar B.** Compare ranking methods, draw the cut line with P1 staged, and build the economics table. This is most of the marks. |
| 28–37 | **Pillar C.** Who measures benefits, the P1 gate, and the bottleneck's fragility. |
| 37–43 | **Pillar D.** Metrics with guards, and the pre-wiring plan. |
| 43–45 | Check every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is the council really deciding?

**How to reason.** Put the four constraint numbers side by side: budget, ML engineers, data engineers on customer data, and data engineers on other data. Only one is badly over. Say so: the council is really allocating 60 months of in-house data engineering. Then make the claims comparable with finance's weights, and flag the shared call pool (P1, P2, P8). Out of scope: changing the customer-data policy or the hiring freeze.

**The trap.** Ranking by ROI per dollar. Money isn't what runs out first.

**Rubric criteria earned:** the bottleneck named with its numbers; budget and ML shown not binding; claims not additive; the shared call pool spotted.

### Stakeholders

**The question it answers:** who has a stake, and how do you bring them along?

**How to reason.** Five executives sponsor proposals, and the CFO chairs. Give each a line about what they get, especially the losers. The SVP Care gets two of three, with P8 first in line if P1's gate fails. The SVP Retail gets an invitation back with a measured pilot. The CISO gets P6 as an explicit risk call. Include the data engineers: they're the bottleneck, and a plan that books them at 100% fails with one resignation.

Close with one idea. The model answer's: a common ruler is what makes "no" feel fair.

**The trap.** Leaving the losers out of the table. Their reaction is what decides whether the portfolio survives the council.

**Rubric criteria earned:** CFO and four or more sponsors; what P7 and P8 get instead; data engineers included; one idea.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the real ways to build the portfolio?

**How to reason.** Here the options are methods, because each method produces a different portfolio. Compare three on one table:

- **By claimed benefit:** funds P1, P2, P3, P7, P5. It counts P5 against the 60, which pushes P4 out, funds P7 on a guess, and leaves the board's SIM-swap request unanswered. Weighted value: $14.5M.
- **Spread the bottleneck:** everyone gets 71% of their request. Nothing finishes on time.
- **Per data-engineer-month, staged:** P4 and P5 move to contractors, P1 is staged, P6 is a risk call. Weighted value: $16.0M on 56 months.

**The trap.** Spreading to avoid conflict. It feels fair and delivers little.

**Rubric criteria earned:** two or more methods compared; contractors free the bottleneck; spreading shown; one table.

### Decision and Trade-offs

**The question it answers:** which proposals are in, and what would change the line?

**How to reason.** Draw the line: P2, P1 (staged), P3, P6 in; P4 and P5 on contractors; P7 and P8 out; $0.8M and 4 months in reserve. Then justify the close call. P6 and P8 are almost tied per month ($67.5k against $67.2k). P6 wins because P8 overlaps P1's call pool and because the board asked for P6. Say it's a risk decision, not an ROI one.

Stage P1: 6 months and $0.5M (assumed split) to prove deflection, then 12 months and $1.3M. Set the gate (10% deflection, no rise in repeat calls) and the fallback (16 freed months go to P8).

**The trap.** Funding P1 in full because its claim is the biggest. Its evidence is the weakest that isn't a guess.

**Rubric criteria earned:** a clear line; P1 staged with a gate; a fallback for freed capacity; P6 as a risk decision.

### Economics

**The question it answers:** what is each proposal worth, and what does the portfolio cost?

**How to reason.** Build one table: weighted benefit, value per in-house month, new spend, payroll, and benefit over year-one cost. Show the overlap calculation explicitly (6% deflection, so P2 at 94%). Show P3 at its measured effect. Then total it: $16.05M weighted, $4.2M new spend, $2.71M payroll. Note that these are run-rates, so this year's realized benefit is lower because projects go live through the year.

Add one model-cost check that shows you know where the money goes: P2 on Sonnet is $150k a year, on Haiku $7.5k. An eval decides.

**The trap.** Presenting $39M. Finance will apply its own weights, and you'll look as if you didn't.

**Rubric criteria earned:** weights and measured P3; overlap removed; ranking per month; new spend and payroll separate.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who decides, who owns each benefit, and who measures it?

**How to reason.** The council decides and re-allocates. You own the ranking, the data-engineer allocation and the P1 gate. Each sponsor signs their benefit at the weighted figure. Finance measures realized benefit, which also lets next year's weights be tuned. Moving months between projects is a council decision.

**The trap.** Sponsors reporting their own benefits. Every project succeeds on paper.

**Rubric criteria earned:** a single owner; sponsors own weighted benefits; finance measures; re-allocation is a council call.

### Plan and Milestones

**The question it answers:** what happens through the year?

**How to reason.** Quarter by quarter: Q1 starts P2's rollout, P3's scale-up, P1 phase 1, P6's build and the contractor projects. Month 4 is P1's gate. P6 runs in shadow mode before it blocks anyone. Every quarter the council compares measured to weighted benefit, and a project under 50% for two quarters stops. Month 12 builds next year's portfolio from the results.

**The trap.** Approving once a year. The bottleneck should move with the evidence.

**Rubric criteria earned:** a dated P1 gate; a quarterly stop rule; P6 in shadow first; next year's portfolio from results.

### Risk and Governance

**The question it answers:** what could go wrong, and what controls it?

**How to reason.** The portfolio's biggest risk is benefits that don't arrive; the controls are weights, finance measurement and the stop rule. The second is the bottleneck: 56 of 60 is 93% booked, and one resignation costs about 12 months a year. Keep the 4-month buffer and decide in advance that P1 phase 2 slows first. Then the policy: contractors stay off customer data, enforced by access controls. And the project risks: deflection that returns as repeat calls, and fraud blocks on legitimate customers.

**The trap.** Booking the bottleneck at 100%.

**Rubric criteria earned:** the bottleneck's fragility quantified; access controls; the repeat-call guard; a rule for missed benefits.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how will the council know whether it worked?

**How to reason.** At portfolio level, realized against weighted benefit per project, measured by finance. At project level, pair each target with a guard: deflection with repeat calls, seconds saved with summary errors, churn cut with offer cost, fraud losses with legitimate SIM changes blocked.

**The trap.** Reporting only the portfolio total. One strong project hides two weak ones.

**Rubric criteria earned:** guards paired; realized against weighted; project-by-project reporting.

### Communication

**The question it answers:** what does each executive hear, and how often?

**How to reason.** The CFO hears three numbers kept apart: weighted benefit, new spend, payroll. Each sponsor hears what they get in one line. And the step that separates strong answers: pre-wire every "no" one to one before the council, so nobody is surprised in the room. Quarterly reviews after, including missed benefits.

**The trap.** Announcing the cut line at the council.

**Rubric criteria earned:** four or more audiences; the CFO's three numbers; pre-wiring; a cadence with bad news.

## 8. The decisions that separate strong answers

**Ranking against the right constraint.** Weak answers rank by ROI per dollar or by claimed benefit. Strong answers notice that data engineers on customer data are what runs out, and that two projects don't need them at all.

**Staging the biggest uncertain bet.** P1 has the largest claim and the weakest evidence. Funding a phase that proves deflection, with a named fallback for its capacity, turns the biggest risk into a decision you make at month 4 with data.

**Calling a risk item a risk item.** P6 is roughly break-even on ROI. Funding it as a board-requested risk decision, said plainly, is more credible than stretching its ROI to fit.

## 9. Common mistakes

- **Adding the claims.** $39M rests on four kinds of evidence and counts the same calls twice.
- **Ignoring P3's measured effect.** The A/B said 0.03, not 0.05.
- **Ranking by ROI per dollar.** The budget is nearly enough; the data engineers aren't.
- **Letting P4 and P5 compete for in-house engineers.** They can use contractors.
- **Booking the bottleneck at 100%.** One resignation breaks the plan.
- **Surprising sponsors at the council.** Pre-wire every "no".

## 10. Follow-ups an interviewer might ask

**The SVP Care says P1's vendor will guarantee 20% deflection. Does that change the weight?**
A guarantee changes who pays if it misses, not the evidence. Ask for it in the contract as a fee reduction, keep the 30% weight, and let phase 1 measure the real number.

**The CFO asks you to cut new spend to $3.5M. What goes?**
P4 ($0.6M with contractors, about 1.0×) goes first; it barely pays back in year one and doesn't use the bottleneck, so cutting it costs no in-house capacity. That brings new spend to $4.2M − $0.6M = $3.6M. If the eval lets P2 run on Haiku, its $142.5k model saving brings it to $3.46M, under the cut.

**A data engineer resigns in month 3. What do you do?**
You lose about 9 months for the rest of the year; the 4-month buffer covers part, and P1 phase 2 slows for the rest. Tell the council the same week.

**Why not fund P8 instead of P6? They're nearly tied.**
P8's calls are part of P1's deflection pool, so its value shrinks if P1 works, and the board asked for a SIM-swap plan. If P1's gate fails, P8 gets the freed months.

**How would you set next year's confidence weights?**
From this year's realized-against-weighted results by evidence type. If pilots deliver 90% and vendor studies 15%, the weights move toward those numbers.
