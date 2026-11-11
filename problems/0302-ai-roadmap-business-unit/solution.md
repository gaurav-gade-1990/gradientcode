# 12-Month AI Roadmap for a Business Unit: model answer

## 1. Situation

This is a sequencing problem, not a ranking problem. The ERP freeze from month 4 to month 9 decides when anything that writes to quotes, orders or invoices can ship, so the roadmap is built around the freeze, and only then around value. The second job is to reset the GM's $3M promise before the quarterly review makes it a commitment.

| What | Number | What it forces |
|---|---|---|
| Capacity | 7 engineers × 12 months = 84 engineer-months | Requests total 30 + 12 + 10 + 20 + 16 + 14 = 102, so 18 must go |
| Capacity per quarter | 7 × 3 = 21 engineer-months | The post-freeze window (months 10–12) holds only 21 |
| Quote volume | 12,000 × $4,800 = $57.6M quoted a month | Small win-rate moves are worth millions |
| Rep time on RFQs | 12,000 × 40 min = 8,000 hours a month; 110 × 140 = 15,400 hours, so 52% of rep time | Quote speed is a capacity problem |
| Today's win rate | 25% × 31% + 75% × 22% = 24.25% | The baseline for every quote number |
| ERP freeze | Months 4–9, past slips of 2 and 3 months | Write-back and AR triage can't ship before month 10, maybe not this year |

**How:**
1. Sort the six initiatives by whether they write to ERP: two do (write-back, AR triage), four don't.
2. Fix the frame: the roadmap is judged on gross-profit run-rate at month 12, not on how many initiatives start.
3. Out of scope: anything inside the ERP programme itself, and the demand-forecast model.

**Decision.** Build the roadmap around the freeze: ship read-only value during it, and put ERP writes in the one window after it, with a plan for that window disappearing.

**Trap.** Ranking initiatives by value and filling the year from the top. The highest-value item, write-back, can't ship until month 10 at the earliest, so a value-ranked plan stalls in month 4.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| BU General Manager | $3M of AI gross profit to show the CEO by month 12 | A floor and an upside: $1.95M without write-back, $3.07M with it; commit to $2M |
| VP Inside Sales | Quote Assist with write-back, now | Draft-only in month 4, write-back in months 10–12, gated on a stable ERP |
| Product management | Clean catalog data, long wanted | Catalog enrichment ships first, because Quote Assist and search both need it |
| E-commerce lead | Better portal search | Search ships in month 9 on the enriched catalog, untouched by the freeze |
| BU finance | AR dispute triage | Deferred to next year, with the reason (credit memos are frozen) and a funded start date |
| VP Field Sales | Account briefs | Not built: a 20-seat trial of the CRM vendor's copilot instead, for $12k |
| Group ERP programme lead | Nothing touching ERP during the freeze | A written promise of no writes in months 4–9, and one week of rework planned at cutover |

**The one idea to hold:** the freeze, not anyone's priority, decides the order, which lets you say no to sponsors without ranking them against each other.

## 3. Options

Three ways to fill the year, each tested against the freeze, the 84 engineer-months and the month-12 run-rate.

| | A. Value-ranked | B. Freeze-aware | C. Wait for the new ERP |
|---|---|---|---|
| Months 1–3 | Write-back build, AR build | Catalog (10), draft-only MVP (11) | Catalog, account briefs |
| Months 4–9 | Blocked: nothing can go live | Draft-only rollout (19), search (20) | Search, then idle on ERP work |
| Months 10–12 | Both launch, if the ERP is ready | Write-back (12), if the ERP has been stable 4 weeks | Write-back and AR start |
| Engineer-months used | 102: over capacity | 72, with 12 held for run and slip | 10 + 14 + 20 = 44 of the 63 available by month 9; 19 idle |
| Month-12 run-rate | $0 if the cutover slips | $1.95M floor, $3.07M with write-back | About $0.46M (search only) |

**How:**
1. Draft-only reads the reporting replica and writes nothing, so it can go live during the freeze.
2. Catalog enrichment writes to the product-information system, not ERP, and lifts Quote Assist's match rate from 71% to 86%, so it goes first.
3. AR triage needs 16 engineer-months after month 9; the window holds 21 and write-back needs 12, so both can't fit.

**Decision.** B: read-only value during the freeze, ERP writes after it, and AR triage moved to next year.

**Trap.** Treating the freeze as dead time. Draft-only puts most of Quote Assist's value live in month 4 with zero ERP writes.

## 4. Decision and Trade-offs

Adopt B: catalog enrichment and a draft-only Quote Assist first, site search during the freeze, write-back in the post-freeze window, AR triage next year, and a bought copilot trial instead of building account briefs.

| We give up | Why it's worth it |
|---|---|
| AR triage this year ($400k claimed) | It writes credit memos, so it can't ship before month 10, and write-back earns more per engineer-month after the freeze |
| Built account briefs | No value estimate; a $12k vendor trial tests the idea without 14 engineer-months |
| 10 minutes per RFQ until write-back | Draft-only still saves 15 of 40 minutes, live 6 months earlier |
| A $3M promise | $2M is credible; $3M needs the ERP on time |

**How:**
1. **Reversibility:** quarters 3 and 4 are two-way doors; only the catalog work is a one-way investment, and it pays for both Quote Assist and search.
2. **Month-9 checkpoint:** if the cutover has slipped, write-back moves to next year and its 12 engineer-months go to AR triage's design or the quote rollout.
3. **Revisit next year's roadmap at month 12** with real win-rate data.

**Decision.** B, because it is the only plan that delivers value before month 10 and still uses the post-freeze window for the highest-return work.

**Trap.** Letting every sponsor keep a slice. Five half-funded initiatives deliver nothing by month 12.

## 5. Economics

Gross-profit run-rate at month 12, with the sponsors' claims tested and the quote causality cut in half (assumed: fast quotes also tend to be easy quotes, so only half the win-rate gap is caused by speed).

| | Draft-only | With write-back | Search |
|---|---|---|---|
| Quotes within 4 hours | 45% | 60% | — |
| Win rate | 45% × 31% + 55% × 22% = 26.05% | 60% × 31% + 40% × 22% = 27.4% | — |
| Gain over 24.25% | 1.8 points × $57.6M × 12 = $12.4M revenue | 3.15 points × $57.6M × 12 = $21.8M revenue | 2% × $96M = $1.92M revenue (sponsor's figure) |
| Gross profit at 24% | $2.99M | $5.23M | $461k |
| After the 50% haircut | $1.49M | $2.61M | $461k (not haircut; 15% of the total) |
| **Month-12 run-rate** | **$1.49M + $461k = $1.95M** | **$2.61M + $461k = $3.07M** | |

**How:**
1. **Value per engineer-month:** write-back adds $2.61M − $1.49M = $1.12M for 12, or $93k each; AR claims $400k for 16, or $25k each.
2. **People on payroll:** 72 engineer-months × $230k / 12 = $1.38M, already paid.
3. **New spend:** Quote Assist 12,000 × (12,000 × $2/1M + 1,500 × $10/1M) = 12,000 × $0.039 = $468 a month, $5.6k a year. Catalog 420,000 × $0.0005 on Haiku = $210, plus 42,000 × $0.01 on Sonnet = $420. Search hosting $4k a month for 6 months (assumed) = $24k. Eval labelling $60k (assumed). Copilot trial 20 × $50 × 12 = $12k. Total about $102k of the $900k cap.
4. **Rep time:** draft-only frees 12,000 × 15 min = 3,000 hours a month, about 21 reps' worth. It goes into speed, so it isn't counted again as savings.

**Decision.** Plan on $1.95M, aim for $3.07M, and keep $250k of the budget (assumed) for a post-cutover ERP contractor to start AR triage early next year.

**Trap.** Adding rep hours saved to the win-rate gain. The hours are how the speed gain happens; counting both double-counts.

## 6. Org and Ownership

One owner for the roadmap, one owner per initiative, and one person who speaks to the ERP programme.

| Role | Who | Owns |
|---|---|---|
| Accountable | You | Roadmap, gates, the month-9 checkpoint, the run-rate number |
| Quote Assist | Tech lead plus 4 engineers | Draft-only, then write-back |
| Catalog and search | Tech lead plus 2–3 engineers | Enrichment, then search |
| Business owners | VP Inside Sales; e-commerce lead | Adoption targets, rep training |
| ERP liaison | You, with the ERP programme lead | The freeze calendar and the replica interface |
| Value tracking | BU finance partner | Monthly win-rate and run-rate figures |

**How:**
1. Sponsors own adoption, not just the request: VP Inside Sales signs up to the 45% within-4-hours target.
2. Changes to matching prompts pass a regression eval on 500 labelled RFQs.

**Decision.** Finance, not the AI team, reports the run-rate, so the $2M number is believed.

**Trap.** Measuring the AI team on launches. Draft-only can launch and still lose if reps don't use it.

## 7. Plan and Milestones

Quarterly, with a gate at each step and the checkpoint before the post-freeze window.

| Month | Milestone | Gate |
|---|---|---|
| 1 | Roadmap agreed; freeze calendar signed with the ERP programme; 500 RFQs labelled | — |
| 3 | Catalog enriched; draft-only MVP | **Gate 1:** top-1 SKU match ≥ 85% on the labelled set |
| 4 | Draft-only pilot at 3 branches | — |
| 6 | ERP cutover; replica re-pointed in a planned week | Draft-only still serving |
| 7 | Draft-only at all 38 branches | **Gate 2:** within-4-hours share ≥ 40% at pilot branches |
| 9 | Search live | **Checkpoint:** ERP stable 4 weeks? Write-back go or move to next year |
| 10–12 | Write-back at 3 branches, then all | Line-error rate no worse than draft-only |
| 12 | Run-rate review; next year's roadmap with AR triage | Decision record |

**Decision.** The month-9 checkpoint is booked with the GM now, so a slipped cutover is a planned branch, not a surprise.

**Trap.** Scheduling write-back for month 10 as if the cutover will be on time. Two of the last two slipped.

## 8. Risk and Governance

The biggest risk is wrong parts on quotes. At 86% top-1, 12,000 × 12 = 144,000 lines a month leaves 144,000 × 14% = 20,160 wrong matches a month for reps to catch.

| Risk | Control |
|---|---|
| Wrong SKU reaches a customer | Every line shows match confidence; low-confidence lines are flagged; reps confirm before sending |
| Margin leak | AI never sets price; price comes from ERP contract pricing |
| Cutover slips | Month-9 checkpoint; write-back moves; $1.95M floor already live |
| Replica changes at cutover | A thin read layer; one week of rework planned in month 6 |
| Write-back writes bad quotes | Writes as draft status only; 3-branch pilot first |

**Decision.** Pricing stays in ERP and every line is confirmed by a rep, so AI errors cost rep minutes, not margin.

**Trap.** Calling 86% "good enough" without multiplying. It's 20,000 wrong lines a month.

## 9. Metrics

Each success metric gets a guard metric.

| Success metric | Target | Guard metric |
|---|---|---|
| Quotes out within 4 hours | 25% → 45% (month 7) → 60% (month 12) | Lines changed after sending, and returns for wrong parts |
| Win rate | 24.25% → 26% or more | Gross margin per won quote, so reps don't win on discount |
| Minutes per RFQ | 40 → 25 → 15 | Share of reps using Quote Assist weekly |
| Portal zero-result searches | 14% → under 5% | Return rate on suggested substitutes |
| GP run-rate (finance) | $1.95M floor | Model and hosting spend against the $102k plan |

**Decision.** Finance compares pilot and non-pilot branches on win rate, so the 50% haircut is replaced by a measurement within two quarters.

**Trap.** Reporting minutes saved as the result. The GM promised gross profit, so the roadmap is judged on win rate and margin.

## 10. Communication

The same roadmap, said in the terms each audience cares about.

| Audience | One line |
|---|---|
| GM | "Tell the CEO $2M by month 12; $3M if the ERP cutover holds. We'll know at month 9." |
| VP Inside Sales | "Draft-only Quote Assist at 3 branches in month 4 and all branches by month 7; write-back after the freeze." |
| BU finance | "AR triage starts next year, because its credit memos are frozen; it's funded and first in line." |
| VP Field Sales | "We won't build briefs this year; trial the CRM copilot with 20 reps for $12k and tell us if it's worth more." |
| ERP programme lead | "Nothing writes to ERP in months 4–9, and we've planned a week to re-point at cutover." |
| Reps | "It drafts, you decide: every line and every price is yours." |

**How:**
1. Monthly roadmap review with the GM; quarterly to the BU leadership team.
2. Gate results go out on the day, including a failed one.

**Decision.** Reset the $3M before the quarterly review, in private, with the floor and the upside.

**Trap.** Letting $3M stand. Repeated at the review, it becomes the number you missed.
