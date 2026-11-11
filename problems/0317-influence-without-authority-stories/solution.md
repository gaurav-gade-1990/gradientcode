# Influence Without Authority: Story Bank: model answer

## 1. Situation

The interviewer is testing one thing: can you change another org's plan with evidence and a trade, rather than with a title or an escalation? So the story has to make the missing authority obvious, and it has to put a number on why the change mattered. Here, the number is substitution rejections caused by catalog data I didn't own.

| What | Number | What it forces |
|---|---|---|
| Substitutions | 2.5M orders × 40 items × 8% = 8M a month | Small per-item errors become large totals |
| Rejections | 8M × 22% = 1.76M a month × $1.50 = $2.64M a month | The problem is worth a VP's attention |
| Caused by catalog attributes | 1.76M × 45% = 792k a month × $1.50 = $1.19M a month, $14.26M a year | The fix sits in Catalog's system, not mine |
| Catalog's data-ops load | 2,000 tickets × 20 min = 667 hours a month, 79% of 6 × 140 = 840 hours | Catalog already feels this pain |
| My authority over Catalog | None: a different VP, 40 engineers, two quarters committed | Persuasion is the only route |
| Window | Planning locks in 5 weeks | Miss it and the next chance is two quarters away |

**How:**
1. Pick a story where the other side genuinely could have said no. If your manager could have ordered it, it's a delegation story, not an influence story.
2. Size it to the level you're interviewing for. A principal story crosses an org boundary and moves a quarter of someone else's roadmap.
3. Out of scope: the substitution model itself. Its ranking wasn't the main cause, and retuning it would have hidden the data problem.

**Decision.** Frame the story as Catalog's problem that I could help solve, not my problem that Catalog had to fix. That framing is what made the rest possible.

**Trap.** Telling a story where "we aligned" and nobody had to give anything up. Without a cost to someone, the interviewer can't see any influence.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| VP Catalog (decision-maker) | Portal v1 on the board date; no "cleanup project" | Show the portal imports 90,000 × 18% = 16,200 bad listings unless attributes are fixed first; let them present the plan as theirs |
| Catalog staff engineer and EM | A pipeline they can run, not a handed-over prototype | Walk them through the pilot first; build it in their ingest path, in their sprint |
| Catalog data-ops lead | Relief from 667 hours a month of hand fixes | Show the ticket count falling in the pilot SKUs; make them the reviewer queue's owner |
| My director | My team's roadmap delivered | Agree the trade in writing: 3 engineers lent for one quarter, personalization slips a quarter |
| My VP | No escalation fight with a peer VP | Promise no surprise in the planning meeting; brief them before the pre-read |
| Finance (FP&A) | A saving they can book | Use their $1.50 figure, and report measured savings, not the pilot's projection |
| Food safety lead | No wrong allergen or dietary flags | Allergen changes never auto-apply; they sign off the rule |

**The one idea to hold:** Catalog had to win more than I did, so I gave away the ownership and the credit, and I paid part of the cost from my own roadmap.

## 3. Options

I had four routes to the change. Doing nothing wasn't really one of them, because waiting is a choice with a price.

| | A. Escalate to CTO | B. Fix it in Search myself | C. Co-fund a Catalog quarter | D. Wait for next planning |
|---|---|---|---|---|
| Time to effect | Weeks, if it worked | One quarter | One quarter | Two quarters later |
| Who owns the data | Catalog, unwillingly | Me: a second copy of the truth | Catalog | Catalog |
| Fixes portal's 90k SKUs | Maybe | No: they bypass Search | Yes | Too late |
| Cuts Catalog's tickets | No | No | Yes | Later |
| Cost to relationship | High | Medium | Low | None |
| Feasible | No: my VP won't escalate | Yes | If Catalog agrees | Yes |

**How:**
1. **A** fails twice: my VP won't do it, and an ordered fix gets compliance, not ownership.
2. **B** was the tempting one. My team could store corrected attributes in the search index within a quarter. But it creates a shadow catalog, the portal's new SKUs flow around it, and Catalog's tickets don't change.
3. **D** costs 6 months × $712.8k = $4.28M of avoidable rejections, at the pilot's rate.

**Decision.** C: a co-funded quarter that Catalog owns, with B kept as a fallback if Catalog said no.

**Trap.** Not listing escalation at all. The interviewer will ask why you didn't go over their head, so answer it before they ask.

## 4. Decision and Trade-offs

The ask was specific: 4 Catalog engineers and 3 of mine for one quarter, to put attribute extraction into Catalog's ingest path, backfill the 1.2M SKUs, and route every portal SKU through it. Bulk upload slips 6 weeks; portal v1 keeps its date.

| I gave up | Why it was worth it |
|---|---|
| Personalization ranking slips a quarter | It removes $8.55M a year of rejections, about 16× the $540k delay (section 5) |
| 3 of my 12 engineers for 13 weeks | Catalog couldn't staff it alone without missing the portal date |
| The credit | The VP Catalog presented it at planning; ownership was the point |
| A Search-side fix I fully controlled | One source of truth, which covers the portal's SKUs too |

**How:**
1. **Easy to stop:** a week-6 checkpoint. If audited precision of auto-applied attributes was below 97%, or the portal's date was at risk, my engineers would return and Catalog would keep the pilot as a ticket tool.
2. **Reversible:** yes. A quarter of lent people is a two-way door; the only lasting change is a pipeline Catalog chose to keep.

**Decision.** I made the trade myself and put my own roadmap on the table first, because a cost the asking side won't share is just a request.

**Trap.** Saying "we decided". The interviewer is scoring what *you* decided and what *you* gave up.

## 5. Economics

The numbers that mattered: what was at stake, what the quarter cost, and how fast it paid back. All figures are a year unless stated.

| Item | Derivation | Amount |
|---|---|---|
| At stake | 792k × $1.50 × 12 | $14.26M a year |
| Addressable at the pilot's 60% | 792k × 60% = 475.2k × $1.50 = $712.8k a month | $8.55M a year |
| Engineers (on payroll) | 7 × 0.25 year = 1.75 × $240k (assumed) | $420k |
| Personalization delay | $360M × 0.6% = $2.16M a year ÷ 4 (assumed linear) | $540k |
| Bulk upload slip | $18M × 15% × 120/300 = $1.08M a year × 6/52 (assumed linear) | $124.6k |
| Review of low-confidence SKUs | 1.2M × 15% × 40 s = 2,000 h × $32 (assumed) | $64k |
| Allergen review | 50,000 changes (assumed) × 40 s = 556 h × $32 | $17.8k |
| Model, backfill | 1.2M × ($0.0003 + 10% × $0.006) = 1.2M × $0.0009 | $1,080, then $54 a month |

**How:**
1. **Per-SKU model cost:** Haiku 2,000 × $0.10/1M + 200 × $0.50/1M = $0.0003; Sonnet 2,000 × $2/1M + 200 × $10/1M = $0.006.
2. **Split the cost:** new spend $82.9k; payroll $420k; opportunity cost $664.6k; total $1.17M.
3. **Payback:** $1.17M ÷ $712.8k = 1.6 months at the pilot rate.

**Decision.** Lead with the $8.55M and the 1.6-month payback, and show that the model cost is about $1,000. The constraint was never money; it was people and a date.

**Trap.** Leaving out your own give-up. The $540k personalization delay is the most credible number in the story, because it's the one you paid.

## 6. Org and Ownership

Catalog owned the outcome from day one; I was the technical lead for a quarter with no reporting line over anyone on it.

| Role | Who | Owns |
|---|---|---|
| Accountable | VP Catalog | Attribute quality as a Q1 OKR |
| Delivery | Catalog EM, 4 Catalog and 3 lent engineers | Pipeline, backfill, portal path |
| Technical lead, one quarter | Me | Design, eval set, week-6 checkpoint |
| Review queue | Catalog data-ops lead | Low-confidence and allergen review |
| After handover | Catalog | Pipeline, data contract, on-call |

**How:**
1. A data contract: attribute completeness of 95% or better for top-selling SKUs, with Search as a named consumer.
2. A dated handover in week 13, with on-call moving to Catalog.

**Decision.** I wrote myself out of the plan at week 13. If I'd stayed as owner, Catalog would have treated it as Search's project.

**Trap.** Offering to run it for them forever. That's a shadow catalog with extra steps.

## 7. Plan and Milestones

Five weeks of influence before planning, then a 13-week quarter with one checkpoint.

| When | What I did | Checkpoint |
|---|---|---|
| Week −5 | Sampled 2,000 rejections; found 45% were attribute-driven | — |
| Week −4 | One-to-ones with Catalog's staff engineer and data-ops lead | They agree the problem is real |
| Weeks −4 to −3 | Two-week pilot on 5,000 SKUs with their data-ops lead reviewing | Rejections −60% on pilot SKUs |
| Week −2 | Joint one-page plan written with Catalog's EM | My director signs the 3-engineer trade |
| Week −1 | Pre-read with VP Catalog, one-to-one | No surprises at planning |
| Weeks 1–5 | Pipeline into Catalog ingest; backfill starts | — |
| Week 6 | Checkpoint | Precision ≥ 97%, portal on track |
| Weeks 7–13 | Backfill done, portal path live, data contract signed | Handover |

**Decision.** The VP Catalog saw the plan only after their own engineers had helped write it.

**Trap.** Pitching the VP first. A VP who hears it from you before their team will ask their team, and the team will defend the roadmap.

## 8. Risk and Governance

Three kinds of risk: to Catalog's date, to customers, and to the relationship.

| Risk | Size | Control |
|---|---|---|
| Portal date slips | Board commitment | Week-6 checkpoint; my engineers return if the date is at risk |
| Wrong attributes auto-applied | 1.2M × 85% = 1.02M auto-applied × 2% (assumed) = 20,400, against 216k wrong today | Audited precision sample weekly; low-confidence goes to review |
| Wrong allergen or dietary flag | A safety issue, not a cost | Allergen changes never auto-apply; food safety lead signed the rule |
| VP Catalog feels ambushed | Ends the deal | One-to-one pre-read; their team co-wrote the plan |
| My team resents the slip | 3 of 12 lent | Told them first, with the personalization date reset in writing |

**Decision.** The allergen rule was in code, not in a review guideline, because one wrong "nut-free" flag outweighs the whole saving.

**Trap.** Talking only about the project's risks. In an influence story, the relationship is the thing most likely to break.

## 9. Metrics

The result, measured over the 8 weeks after backfill. These outcome figures are the model story's, assumed for this answer.

| Success metric | Before → after | Guard metric |
|---|---|---|
| SKUs with a wrong or missing attribute | 18% → 5% (assumed) | Audited precision of auto-applied attributes ≥ 97% |
| Attribute-driven rejections | −55% (assumed; pilot was −60%): 435.6k fewer a month = $653.4k a month, $7.84M a year | Overall rejection 22% → (1.76M − 435.6k) / 8M = 16.6% |
| Catalog data-ops tickets | 2,000 → 700 a month (assumed): 233 h, 28% of capacity | Time to list a new SKU unchanged |
| Portal v1 | On the board date | Bulk upload: 6 weeks late, as agreed |

**How:** payback on the measured result is $1.17M ÷ $653.4k = 1.8 months.

**Decision.** Report the measured $7.84M, not the $14.26M at stake or the pilot's $8.55M, and lead with Catalog's two numbers: the portal date and the ticket count.

**Trap.** Claiming the whole problem as the result. Interviewers discount any story where the result equals the opportunity.

## 10. Communication

During the work, each audience heard one line; in the interview, the story is told in two minutes in STAR order.

| Audience | One line |
|---|---|
| VP Catalog | "Your portal brings 16,200 bad listings unless we fix attributes first; I'll lend 3 engineers and your date doesn't move." |
| My director | "We lose a quarter on personalization, about $540k, to remove $8.55M a year of rejections." |
| My team | "Three of you go to Catalog for 13 weeks; personalization's new date is in writing." |
| Finance | "We'll report measured savings monthly, at your $1.50 per rejection." |

**The 2-minute STAR version:**
- **Situation.** "I was the principal ML engineer for search and substitutions at a national grocery delivery platform, $2.4B of GMV. Customers rejected 22% of our substitutions, about $2.6M a month. I sampled 2,000 rejections and found 45% came from wrong catalog attributes, in data owned by a different VP whose team was committed to a board-level seller portal."
- **Task.** "I needed Catalog to give up a quarter of capacity, with no authority over them, before planning locked in 5 weeks. Their VP had already said no to a cleanup project twice."
- **Action.** "I started below the VP. I ran a two-week pilot with their data-ops lead that cut attribute-driven rejections 60%. I wrote the plan with their EM, not for them. I reframed it in their terms: the portal would import 16,200 bad listings, and their data-ops team spent 79% of its time on fix tickets. And I put my own roadmap on the table: I lent 3 engineers and slipped my personalization launch a quarter, about $540k. I briefed the VP one-to-one before planning, and they presented it as their OKR."
- **Result.** "Rejections fell from 22% to 16.6%, worth $7.84M a year. Catalog's tickets fell 65%, and the portal shipped on its board date. Catalog still owns the pipeline."
- **Differently.** "I'd sign the data contract in week 1, not week 13. A supplier feed regressed in week 9 and nothing caught it for two weeks."

**Decision.** Spend most of the two minutes on Action, all of it in "I".

**Trap.** A "what I'd do differently" that is really a boast, like "I'd have started sooner". Name a real gap and what it cost.
