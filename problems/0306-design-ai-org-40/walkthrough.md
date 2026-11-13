## 1. What the problem is really asking

On the surface the CEO wants an org chart: centralized, embedded, or something in between. Underneath, it's a question about which people you can afford to move this year. Headcount is frozen, a PUC review arrives in 9 months, the board has been promised $12M from the grid operations squad, and the rate case depends on data science staying at 13 or more. Every box you move on the chart is a person whose manager changes, and some of those people leave.

Three facts in the brief carry the case:

1. **The review needs independence, and independence needs people.** Validators can't report to anyone who builds the models they validate. With the headcount frozen, that capacity has to come out of the 40, and the only group that can spare anyone is data science, which can give up at most 3.
2. **The grid operations squad is untouchable this year.** Losing one of its 9 engineers slips a board commitment by 2 months, at $1M a month. Any design that changes its manager carries that risk.
3. **The duplication can be fixed without a reorg.** One contract and one gateway are worth $0.6M a year and 3 engineers of capacity, and you can get both through procurement and architecture review instead of reporting lines.

Put those together and the answer is a small, deliberate set of moves now, with the bigger question of centralization decided at month 12, after the commitment lands. The interviewer is grading whether you price people, not boxes, and whether you can get standards from teams that don't report to you.

## 2. The numbers that drive the decision

Work these out first. Every later section uses them.

**The review window and the workload.**
- Review in 9 months: 9 × 52 / 12 = **39 weeks**.
- Governance work: program 20 + inventory 23 × 1 + validation 6 × 10 = **103 person-weeks**.
- If 3 validators start at week 8, after the board approves at week 6 and HR finishes its review: 3 × (39 − 8) = **93 person-weeks**. That's short of 103, even before any estimate error.
- Outside validation of 3 of the 6 models removes 3 × 10 = 30 person-weeks, leaving **73 of 93**, a **78% utilization**. Cost: 3 × $60k = **$180k**. All 6 outside would cost $360k and leave 43 person-weeks, a 46% utilization.

**The floors.**
- Data science: 16 − 13 = **3** people at most can move.
- Rate case at stake: 6% × $1.4B = **$84M** of revenue.
- Restoration: $12M / 12 = **$1M a month** late; one grid operations departure slips 2 months.

**The duplication.**
- Contracts: $1.5M − $0.9M = **$0.6M a year**, from month 6 when they renew. Over 3 years: 0.6 × 2.5 = **$1.5M**.
- Engineers: 3 squads × 1.5 = 4.5 on integrations, against 1.5 to run one gateway: **3.0 freed**, worth 3 × $260k = **$780k a year** of payroll.

**The cost of moving people.**
- Count who changes manager under each design: everyone (40), builders plus validators (6 + 18 + 3 = 27), or platform plus validators (6 + 3 = **9**).
- Extra departures at 10 points: 4.0, 2.7 or **0.9**, at $130k each: $520k, $351k or **$117k**.
- If the grid operations squad changes manager: 9 × 10% = 0.9 expected extra departures, × 2 months × $1M = **$1.8M** expected slip.

Payroll for context: 40 × $260k = $10.4M a year.

## 3. How to spend your time

Sixty minutes. Pillar B carries the most marks, and the people arithmetic is what separates answers.

| Minutes | What you do |
|---|---|
| 0–8 | Read the brief. Write down 39 weeks, 103 vs 93 person-weeks, the floors (13 and the 9 grid operations engineers), $0.6M a year and 3.0 freed engineers. |
| 8–18 | **Pillar A.** The dated question, the frame table, and the stakeholder table with what the VP of Rates gives up. |
| 18–36 | **Pillar B.** Four structures on one table with "people changing manager" as a row; the recommendation and its revisit triggers; the 3-year net. |
| 36–48 | **Pillar C.** The new structure adding to 40, the plan to month 12 with two gates, and the HR process for the moves. |
| 48–56 | **Pillar D.** Metrics with guards, and the order of announcement. |
| 56–60 | Check that headcounts add up and every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is really being decided, by when, and which numbers frame it?

**How to reason.** Rewrite "design the AI org" as "what is the smallest change that passes the review without touching the restoration commitment or the rate case?" That turns an open-ended design question into a test with three hard floors: 40 heads, data science at 13, and grid operations untouched. Put the frame numbers in a table where each row says what it forces: 39 weeks, 103 person-weeks, $1M a month for restoration, $84M of rate case, $0.6M a year of duplication.

Then split the must-haves (independent validation, one LLM stack) from the nice-to-haves (one AI org, one hiring bar). Name what's out of scope: forecasting methods and the CRO's financial model validation.

**The trap.** Starting with the ideal end-state chart. Under a freeze and a live commitment, the cost of moving people is the main design input.

**Rubric criteria earned:** the decision restated around the review and the floors; 103 person-weeks and 39 weeks derived; the three floors named; something out of scope.

### Stakeholders

**The question it answers:** who has a stake, what do they want, and how do you bring them along?

**How to reason.** Each leader has already made a public commitment: the SVP of Electric Operations to $12M, the VP of Rates to the rate case, the CRO to a clean review, the CEO to the board. Your design must not break any of them. The VP of Rates is the one who loses something concrete, 3 of 16 people, so say so and offer something back: data science backfills go first.

Don't stop at leaders. The 40 staff want to know whether their manager, level or pay changes. The 3 who move to the CRO are a group of their own; done badly, "validation" sounds like being sent to compliance. Offer volunteers first, the same level and pay, and a real career track.

**The trap.** A table where everyone is aligned. A reorg always has someone who loses, and the interviewer wants to see you name them.

**Rubric criteria earned:** the CEO, CRO, VP of Rates and SVP of Electric Operations each with a distinct want; the VP of Rates's loss and the offer back; staff and the 3 movers; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the real structures, and how does each do on the review, the restoration commitment and people?

**How to reason.** Lay out four options on one table: change nothing (a steering committee), one AI org, centralize the builders, and hub and spoke. Add a row most candidates forget: **how many people change manager**. That row (0, 40, 27, 9) drives both the attrition cost and the restoration risk.

Then do the validator capacity check. Three is the most data science can spare, and three people from week 8 give 93 person-weeks against 103 needed. So every option that passes the review also buys outside validation. Change nothing fails outright: 43 person-weeks of program and inventory work have no owner, and nobody independent validates.

**The trap.** Treating one AI org as the mature answer. It moves 40 people, including the 9 the board commitment depends on, to solve a problem that 9 moves solve.

**Rubric criteria earned:** change nothing included; people changing manager counted; the 93-vs-103 gap shown; one comparable table.

### Decision and Trade-offs

**The question it answers:** what org do you recommend, what do you give up, and what would make you change it?

**How to reason.** Recommend hub and spoke: platform to you, validators to the CRO, squads and data science where they are, with dotted lines to you for standards and hiring. Then write the give-ups as a table: direct control of 18 squad engineers, data science at its floor, a hiring bar enforced by dotted line rather than reporting line, and a less tidy board story.

Reversibility is the subtle part. Each reporting change costs attrition, so reorgs are close to one-way doors. Centralizing later stays possible; centralizing now and undoing it costs two rounds of moves. Give measurable triggers for the month-12 revisit: LLM traffic outside the gateway above 5% after month 8, two squads building the same thing, or the business heads asking for it.

**The trap.** Presenting the org as final. The board should hear on day one that a month-12 decision exists.

**Rubric criteria earned:** one recommendation with governance outside the AI and business lines; named give-ups; reversibility; a dated revisit with triggers.

### Economics

**The question it answers:** what does each option cost or save over three years?

**How to reason.** Use the same rows for every option: contract savings, outside validation, extra departures, the expected restoration slip and the PUC finding. The two labelled assumptions are HR's 10-point rule and General Counsel's $2M. Hub and spoke comes out at +$1.20M; centralizing the builders at −$0.83M; one AI org at −$1.0M; change nothing at −$2.36M. Reveal the model answer for the full table.

Keep cash apart from capacity. The 3.0 freed engineers ($780k a year) are payroll you already pay, and they show up in every option that consolidates. They're the carrot for the business heads, not a saving for the CFO. Name the opportunity cost too: 3 data scientists' rate-case work and data science's slack.

**The trap.** Pricing a reorg as boxes on a chart. The expected restoration slip alone, $1.8M, turns one AI org from attractive into the second-worst option.

**Rubric criteria earned:** contract savings over the same horizon; attrition priced from movers with the assumption labelled; the restoration risk priced; cash separated from capacity.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who reports to whom, and who decides what?

**How to reason.** Write the structure with headcounts and check they add to 40: hub 6, squads 18, data science 13, validators 3. Put validators under the CRO, because the commission will ask who they answer to. Then explain how standards bind teams that don't report to you. Use mechanisms: procurement signs only the enterprise contract, architecture review blocks LLM calls outside the gateway, and nothing ships without an inventory entry. Name one owner for review readiness (you) and one for validation opinions (the CRO).

**The trap.** Putting governance in your hub because it looks tidy. That fails the very independence test the review checks.

**Rubric criteria earned:** a structure adding to 40; validators under the CRO; standards enforced by contract, gateway and inventory; one review owner.

### Plan and Milestones

**The question it answers:** what happens between the board meeting and month 12?

**How to reason.** Move people early and decide the end state late. The board approves at week 6, the moves land at week 8, and the inventory is done by month 3 (Gate 1: 23 of 23 with an owner and a risk tier). The enterprise contract is signed as the three renew at month 6. Validation finishes at month 7 (Gate 2: 6 of 6), two months before the review, so findings get fixed rather than explained. All squads are on the gateway by month 8. The revisit comes at month 12 with a decision record.

**The trap.** Asking the grid operations squad to migrate its own integration during its ramp. The platform team does that work.

**Rubric criteria earned:** validators by week 8 and validation before the review; consolidation timed to renewals; measurable gates; the month-12 revisit.

### Risk and Governance

**The question it answers:** what could go wrong, including the reorg's own HR and legal process?

**How to reason.** Treat the moves as a process with fairness requirements: written criteria (validation and statistics skills), volunteers first, no change to level, pay or title family, and HR and legal review before anyone is told. Then cover the structural risks: data science at 13 losing one more person (its backfill goes first, and the outside firm can take a 4th model), squads bypassing the gateway (no other contract gets signed), validation overrunning (78% planned utilization), and a business head resisting the dotted line (the CEO chairs a quarterly review).

**The trap.** Treating the reorg as a slide. How people are chosen and told carries more review risk than the inventory does.

**Rubric criteria earned:** criteria, volunteers and unchanged pay; the data-science floor risk; gateway bypass; HR and legal review first.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how do you know the org works, and what would show it is causing harm?

**How to reason.** Pair each success metric with a guard. Zero PUC findings is guarded by median validation time, so validation doesn't become a bottleneck. Gateway share of traffic is guarded by squad delivery. The restoration run-rate is guarded by outage restoration times and complaints. Attrition in the 9 who moved is reported separately from the other 31, with data science headcount at 13 or more as its guard, because that's where the design's assumption can fail.

**The trap.** Measuring the org by its chart. The test is whether the review, the restoration number and the people all hold.

**Rubric criteria earned:** paired guards; attrition of movers against the 15% baseline; the restoration run-rate; validation time measured.

### Communication

**The question it answers:** what does each audience hear, and in what order?

**How to reason.** Order is half the answer. The 3 movers and the 6 platform engineers hear first, in person, then their old managers, then the 40, then the company. Write one line per audience from numbers you've already derived: the board hears 9 moves now and a month-12 decision; the CEO hears +$1.2M against one AI org's −$1.0M; the VP of Rates hears 3 people and backfills first; the business heads hear that their squads stay and keep the freed engineers; the 31 hear that their manager doesn't change.

**The trap.** One all-hands announcement. Nobody should learn they're moving from a slide.

**Rubric criteria earned:** five or more audiences; movers told first and in person; the board told the cost and what is deferred; a cadence and an order.

## 8. The decisions that separate strong answers

**Counting people who change manager.** Weak answers compare structures on elegance. Strong answers add a row for movers (0, 40, 27, 9) and price it, which turns the chart decision into a cost decision.

**Putting validation under the CRO.** The tempting design gives the new VP of AI a governance team. The commission's first question is who the validators answer to, and only the CRO is the right answer.

**Getting standards without reporting lines.** One contract, one gateway and one inventory give you most of what centralization promises, at 9 moves instead of 40.

## 9. Common mistakes

- **Centralizing everything because it's "mature".** It moves the 9 grid operations engineers and costs an expected $1.8M slip.
- **Ignoring the freeze.** Proposing a new governance team of 5 without saying where the heads come from.
- **Forgetting the validator capacity check.** 3 people can't do 103 person-weeks by the review alone.
- **Taking more than 3 from data science.** That breaks the $84M rate case.
- **No people process.** Moving people without criteria, volunteers or HR review is a legal and morale risk.
- **No revisit.** A permanent reorg decided under a freeze reads as preference.

## 10. Follow-ups an interviewer might ask

**The CEO says the board wants "one AI org" for the story. What do you do?**
Show the table: one AI org is −$1.0M over 3 years against +$1.2M, mostly because of the restoration risk. Offer the month-12 revisit as the path to it, with triggers. If the CEO still insists, move the grid operations squad last, after month 12.

**One of the three validators resigns at month 4. What now?**
Month 4 is about week 17. By then 3 × 9 = 27 of the 73 in-house person-weeks are done, leaving 46, while 2 people have 2 × 22 = 44 left: a 105% utilization. Send a 4th model to the outside firm at $60k from the remaining $1.02M, which brings it to 36 of 44, about 82%, and backfill the role.

**The VP of Customer Billing refuses to move off their vendor contract.**
Procurement won't renew it, and the architecture review blocks calls outside the gateway. Offer the carrot first: they keep the 1.5 engineers the gateway frees.

**The freeze lifts at month 6 with 4 new heads. Where do they go?**
First a data science backfill to restore slack above 13, then validation, which grows as the inventory does. Squads come after the restoration commitment.

**Why not let the CRO's two financial-model validators learn ML?**
They're fully booked on financial models, and learning LLM validation in 9 months while doing their current work isn't credible. They join the team and cross-train after the review.
