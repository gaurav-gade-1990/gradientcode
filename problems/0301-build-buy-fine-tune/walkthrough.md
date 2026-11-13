## 1. What the problem is really asking

On the surface this is a technology question: vendor, prompt or fine-tune. Underneath, it's a deadline question with a legal constraint. The CTO isn't asking you to compare three accuracy scores. They're asking which option gets something trustworthy in front of 140 renewing enterprise customers in 6 months, and what that choice costs everyone else in the room.

Three facts in the brief carry the whole case, and they're easy to skim past:

1. **The constraint lands on the customers you're trying to keep.** The 35 percent of ARR under strict contracts is the same enterprise segment whose $12M of renewals is at stake. Any option that needs those customers' permission, or can't learn from their data, is weakened exactly where it matters.
2. **The fine-tune estimate assumes people you don't have.** It needs "all 6 engineers", but only 4 are free. A principal who misses this gets the timeline wrong by months.
3. **The model provider is already a sub-processor; the vendor isn't.** That one line decides whether you need a 90-day notice.

The interviewer is grading level: scope, cost, people and risk. A strong answer makes one recommendation, prices it over three years, says plainly what is given up, and names the trigger that would change it.

## 2. The numbers that drive the decision

Work these out in the first five minutes and write them down. Every later section reuses them.

**Volume and value.**
- Manual queue: 60M × 28% = **16.8M transactions a month**.
- Bookkeeper time today: 16.8M × 20 s = 336M seconds = **93,333 hours a month**.
- If the most confident 75% are auto-applied: 16.8M × 75% = **12.6M a month**, saving 12.6M × 20 s = **70,000 hours a month**.

**Cost per transaction for option B.**
- Haiku on every queued transaction: 1,500 × $0.10/1M + 30 × $0.50/1M = $0.00015 + $0.000015 = **$0.000165**.
- Sonnet on the least confident 10%: 1,500 × $2/1M + 30 × $10/1M = $0.003 + $0.0003 = **$0.0033**.
- Monthly: 16.8M × $0.000165 = $2,772, plus 1.68M × $0.0033 = $5,544, so **$8,316**. That's $8,316 / 16.8M = **$0.000495** per transaction.
- The vendor charges $0.004, about **8 times more**: 16.8M × $0.004 = **$67,200 a month**.

**Option C's serving cost.** 4 GPUs × 730 hours × $2.50 = **$7,300 a month**, plus $15k of retraining.

**Three-year growth factor.** Volume grows 20% a year, so years one to three cost 1 + 1.2 + 1.44 = **3.64** times the year-one run rate. Use the same factor for every option, so the comparison is fair.

**The staffing catch.** Option C's 9 months assumes 6 engineers; with the 4 who are free, 9 × 6/4 = **13.5 months**. Renewal season starts at month 6.

**The contract.** 35% × $180M = **$63M ARR** under the strict clauses.

## 3. How to spend your time

Forty-five minutes, about ten per pillar, with a few minutes at each end.

| Minutes | What you do |
|---|---|
| 0–5 | Read the brief. Write down 16.8M, $0.000495 vs $0.004, 3.64, 13.5 months and $63M. Circle "already a listed sub-processor" and "all 6 engineers". |
| 5–13 | **Pillar A.** State the dated question. Build the stakeholder table, with the CPO's loss in it. |
| 13–27 | **Pillar B.** The options table, the recommendation with its trade-offs and revisit trigger, and the three-year economics. This pillar carries the most marks. |
| 27–37 | **Pillar C.** Owner, a 6-month plan with two gates, and the wrong-postings risk with its number. |
| 37–43 | **Pillar D.** Metrics with guards, and one line per audience. |
| 43–45 | Check that every number you used is derived or labelled as assumed. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what exactly is being decided, by when, and which numbers frame it?

**How to reason.** Rewrite "build, buy or fine-tune" as a dated question: *what do enterprise customers see at month 6?* That turns a technology debate into a test the three options can pass or fail. Then put the frame numbers in a small table: queue size, bookkeeper hours, revenue at stake, contract share and free engineers. Each row should say what it forces. The 16.8M queue makes per-transaction price matter, and the 6-month calendar makes timeline matter.

Say what's out of scope. The rules engine already handles 72% at no marginal cost, so you aren't replacing it. And flag that the bake-off and prototype accuracies were measured on samples that underweight enterprise data, so they are estimates to re-test.

**The trap.** Leading with "the fine-tune is most accurate at 94%". The figures are close, and they're measured on different data. The contracts and the calendar decide the case first.

**Rubric criteria earned:** the decision restated around month 6; the 16.8M queue and its hours derived; the contract named as the deciding constraint; something out of scope.

### Stakeholders

**The question it answers:** who has a stake, what do they want, and how do you bring them along?

**How to reason.** Ask what asset each person is protecting. The CFO protects the budget, and they'll check the 3-year number. The CPO protects the roadmap, and *loses* here: consolidation slips two quarters. Name that loss, agree it explicitly, and offer the 2 engineers back at month 6. Sales protects renewals and needs a dated beta list. Legal protects the contracts and wants proof there is no new sub-processor and no training. Don't forget the enterprise customers' controllers. They have to sign off on books that now contain AI postings.

Close with one idea that ties the table together. The model answer's version: each stakeholder is protecting a different asset, and the recommendation must name what each one gives up.

**The trap.** A table where everyone "is aligned". A leader's job is to surface the conflicting interests, especially the person who loses.

**Rubric criteria earned:** CFO, CPO, sales and legal each with a distinct want; the CPO's trade made explicit; controllers included; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the real options, and how does each do on the calendar, the contracts and cost?

**How to reason.** Put all four options, including doing nothing, on one table with the same rows. Then look for the hidden failure in each:

- **Buy** looks fastest (8 weeks), but the vendor is a new sub-processor. The 90-day notice runs alongside integration, so month 3 is the earliest go-live, and any enterprise customer can object. An objection removes exactly the segment you're doing this for.
- **Fine-tune** looks most accurate (94%), but that's measured on non-enterprise data, because it may only train on consenting customers. And it needs 6 engineers where 4 are free: 13.5 months, not 9.
- **Build on the API** uses a provider that is already listed and trains nothing. It reads each customer's own history at inference time. It's the only option that clears both the calendar and the contracts.

Keep A alive as the fallback. If B's beta fails, you start the vendor's 90-day notice then.

**The trap.** Treating "buy" as the safe default. Here it's the option that needs permission from the customers you're trying to keep.

**Rubric criteria earned:** do nothing included; buy's sub-processor problem shown; fine-tune's staffing gap shown; one comparable table.

### Decision and Trade-offs

**The question it answers:** what do you recommend, what do you give up, and what would change your mind?

**How to reason.** Make one call: B, with Haiku first, the least confident 10% escalated to Sonnet, and auto-apply only above a confidence threshold. Then list what it costs, as a table of "we give up / why it's worth it":

- consolidation slips two quarters;
- 2 engineers run the service permanently;
- 1–2 points of accuracy against the fine-tune;
- dependence on one provider.

Say whether it's reversible. It is: corrections keep flowing in with consent flags, so fine-tuning stays possible. Give a dated revisit at month 12 with triggers you can measure: spend above $40k a month (about 5× today's $8,316), accuracy stalling below target, or consented data reaching 80% of the volume.

**The trap.** Presenting the choice as final. Without a revisit trigger it sounds like preference, not judgment.

**Rubric criteria earned:** one clear recommendation; named give-ups including the roadmap slip and the run team; reversibility; dated, measurable triggers.

### Economics

**The question it answers:** what does each option cost over three years, and what's the opportunity cost?

**How to reason.** Build the table in three rows: run cost at year-one volume, 3-year run cost (× 3.64), and people in engineer-years at the assumed $250k. Label every assumption the brief doesn't give, such as the vendor run team of 0.5, the fine-tune run team of 3, and GPUs scaling with volume.

- **A:** $806.4k × 3.64 = $2.94M in fees, plus 1.83 engineer-years ($458k), for **$3.39M**.
- **B:** $99.8k × 3.64 = $363k in model spend, plus 7.0 engineer-years ($1.75M), for **$2.11M**.
- **C:** $319k for GPUs, $540k for retraining and 11.25 engineer-years ($2.81M), for **$3.67M**.

Then the two numbers a CFO actually asks about. Year-one new spend against the $1.5M cap is $50k for B against $672k for A. And the opportunity cost of B is 2.0 engineer-years already on payroll, plus the consolidation slip. Add the revenue side, labelled as an assumption: losing even 10% of the $12M is $1.2M ARR a year. That's bigger than any year-one cost difference.

**The trap.** Comparing the vendor's fees with "free" internal engineers. People on payroll still cost money, and they were going to build something else. Notice that B's biggest cost is people, not tokens, so the run team of 2 is the number to defend.

**Rubric criteria earned:** 3-year totals; per-transaction cost derived from tokens and prices, including the escalation; new spend separated from payroll; assumptions labelled.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owns what, during the build and after it?

**How to reason.** One accountable owner (you), an EM and the 4 engineers for delivery, the categorization PM for the auto-apply experience, an FP&A partner who watches spend against the $40k trigger, and privacy counsel for contracts and wording. After GA, split ownership cleanly: the AI team owns the model service, eval set and thresholds; the product team owns the user experience. Put changes to thresholds or prompts behind a passing eval, not a person's approval. And write down that the compliance pair is off-limits.

**The trap.** "Shared ownership." When nobody owns the threshold, precision drifts until a customer's auditor notices.

**Rubric criteria earned:** a single accountable owner; the model service split from the product experience; changes behind an eval gate.

### Plan and Milestones

**The question it answers:** how do you launch before renewal season, and where can you stop?

**How to reason.** Work backwards from month 6, and put gates where a failure is still cheap:

- **Gate 1 at month 2:** at least 98% precision at 60% coverage on a held-out enterprise set, scored separately from SMB.
- **Gate 2 at month 4:** a suggestions-only beta with 20 renewing enterprise accounts (opt-in) and 500 SMB customers, checking acceptance and override rates.

Auto-apply comes at month 5 and has to hold for four weeks. GA lands at month 6. The month-12 revisit is a milestone with a decision record, not a someday.

**The trap.** One big launch at month 6 with no gate before it. You'd learn at renewal season that enterprise accuracy is below the prototype's.

**Rubric criteria earned:** GA before month 6; a measurable gate; beta starting with renewing enterprise accounts; the month-12 revisit.

### Risk and Governance

**The question it answers:** what goes wrong at this volume, and what controls it?

**How to reason.** Multiply first. 98.5% precision on 12.6M auto-applied postings means 12.6M × 1.5% = **189,000 wrong postings a month**, about 21 per customer across 9,000 customers. That's the real risk, far bigger than an outage. Then list the controls:

- AI postings are labelled and reversible;
- a month-end review list;
- a stricter 99% threshold for enterprise;
- opt-in per customer;
- per-customer context with an isolation test in CI, and no training;
- a consent flag stored on every correction for later;
- model swappable behind the gateway;
- prompt and threshold changes gated by regression evals.

And a fallback if Gate 2 fails: ship suggestions-only at renewal season, and start the vendor's 90-day notice.

**The trap.** Quoting 98.5% as if it settles the question. At this scale a small error rate is a large number of wrong entries in customers' books.

**Rubric criteria earned:** wrong postings quantified; data kept to each customer's own context, untrained and tested; a fallback; controls in code and product, not policy alone.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how will you know it worked, and what would show it is causing harm?

**How to reason.** Pair every success metric with a guard metric:

| Success metric | Guard metric |
|---|---|
| Share of the queue auto-applied (60% at GA, 75% by month 12) | Precision of auto-applied postings (≥ 98.5%, ≥ 99% enterprise) |
| Hours saved | 30-day reversal rate |
| Renewal rate | AI cited in lost-deal notes, down from 30 of 80 |
| Cost per transaction (≤ $0.0006) | Spend against the $40k trigger |

Measure precision on what was *applied*, not accuracy across all suggestions. The controller only cares about what went into the books without them.

**The trap.** Reporting coverage on its own. Coverage can be pushed up by lowering the threshold, which raises revenue on paper and errors in the books.

**Rubric criteria earned:** guard metrics paired; precision of applied postings; a metric tied to renewals; cost tracked against the trigger.

### Communication

**The question it answers:** what does each audience hear, and how often?

**How to reason.** Write one line per audience, built from numbers you've already derived:

- **The CTO:** the recommendation, the date, the 3-year cost and the revisit.
- **The CFO:** $50k of new spend against $672k, and the payroll cost said out loud.
- **The CPO:** the two-quarter slip, and the engineers back at month 6.
- **Sales:** named beta accounts, and "promise time saved, not an accuracy number".
- **Enterprise customers:** opt-in, labelled, reversible, and their data trains nothing.

Then set a cadence: weekly status through GA, monthly metrics after, and gate results the same day, even when a gate fails.

**The trap.** Letting the prototype's 93% reach a sales deck. It was measured on a different mix of customers, and it becomes a contractual expectation.

**Rubric criteria earned:** four or more audiences; the CFO's two numbers kept apart; sales stopped from quoting accuracy; a cadence that includes bad news.

## 8. The decisions that separate strong answers

**Seeing that the constraint and the revenue are the same customers.** Weak answers treat the contract clause as a compliance footnote. Strong answers notice it applies to the $63M segment that holds the $12M of renewals. That's why "buy" is risky and why the fine-tune's 94% is the wrong number.

**Checking the plan against the people.** The fine-tune estimate silently assumes all 6 engineers. Catching that (13.5 months, not 9) is the kind of check a director is hired to make.

**Pricing people honestly.** Option B's tokens cost $363k over three years; its people cost $1.75M. Saying so, and defending the run team of 2, is more convincing than claiming the build is nearly free.

## 9. Common mistakes

- **Picking the highest accuracy number.** The figures are measured on different data and differ by 1–3 points. The calendar and contracts matter more.
- **Year-one comparisons.** The vendor looks cheap in a pilot and expensive at 16.8M transactions a month, growing 20% a year.
- **No give-ups.** Every option costs someone something. Here, the CPO pays.
- **Ignoring wrong postings.** 189,000 a month needs a control story, not a percentage.
- **No revisit.** A permanent decision made on prototype data is a red flag at principal level.
- **Tool talk.** Naming frameworks instead of costs, people and risk reads as senior-engineer level, not leadership.

## 10. Follow-ups an interviewer might ask

**What if Gate 2 fails at month 4?**
Ship suggestions-only for renewal season. That still saves time, because bookkeepers accept with one click. Then start the vendor's 90-day notice as the fallback, so the enterprise segment has an answer by month 7.

**The CEO wants it in 3 months, not 6. What do you say?**
Only "buy" can hit month 3, and only if no enterprise customer objects to the new sub-processor. Offer a suggestions-only beta for named accounts at month 3 under option B instead, and be explicit that auto-apply stays gated.

**When would fine-tuning win?**
When the month-12 triggers fire: spend passes about $40k a month, accuracy stalls below target, or consented data covers 80% of the volume. At that point a fine-tune trained on more representative data could beat the API on both cost and accuracy.

**The vendor offers $0.002 per transaction. Does that change your answer?**
Their fee halves to $33.6k a month, still about 4× option B's model cost. The sub-processor notice and objection risk are unchanged, and the notice is what blocks month 6. The answer holds, though the fallback becomes cheaper.

**An enterprise customer asks whether their data trains your model. What's your answer?**
No. Their own history is used only as context for their own transactions, the provider keeps nothing, and nothing is trained. Point to the isolation test as the evidence.
