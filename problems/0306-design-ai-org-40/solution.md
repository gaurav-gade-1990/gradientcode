# Designing a 40-Person AI Org: model answer

## 1. Situation

The CEO asked for an org chart, but the real question is narrower: what is the smallest change to who reports to whom that passes the review at month 9, without touching the restoration commitment or the rate case? Everything else can wait for month 12, when the board commitment has landed.

| What | Number | What it forces |
|---|---|---|
| Review window | 9 months × 52 / 12 = 39 weeks | Validators must be in seat early, about week 8 after the board approves |
| Governance work | 20 + 23 × 1 + 6 × 10 = 103 person-weeks | More than 2 people's full year; it needs dedicated, independent people |
| Restoration commitment | $3M today to $12M by month 12; $12M / 12 = $1M a month late | Don't change anything around the 9 grid operations engineers this year |
| Rate case | 6% × $1.4B = $84M of revenue | Data science can give up at most 16 − 13 = 3 people |
| Duplication | $1.5M of contracts against a $0.9M quote; 3 × 1.5 = 4.5 engineers on 3 integrations | One contract and one gateway are worth having whatever the chart says |
| Payroll | 40 × $260k = $10.4M a year | Frozen: every new role comes out of an existing one |

**How:**
1. Separate the two must-haves (independent validation, one shared LLM stack) from the nice-to-haves (one AI org, one hiring bar, one roadmap).
2. Out of scope: forecasting and rate-case methods, which stay with the VP of Rates, and the CRO's financial model validation.
3. Treat the CRO's person-week estimates as estimates; the plan needs slack against them.

**Decision.** Frame the board paper as a two-step design: the changes the review and the duplication force now, and a dated decision at month 12 on how far to centralize.

**Trap.** Drawing the ideal end-state chart first. With headcount frozen, the review in 9 months and a board commitment in flight, the cost of moving people is the main design input, not an afterthought.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| CEO and board | A credible AI story, a clean review and the $12M | A two-step design, its 3-year cost, and the month-12 decision named in advance |
| Chief Risk Officer | Independent validation they can defend to the commission | The 3 validators report to the CRO, and outside validation covers the overflow |
| VP of Rates | The $84M rate case delivered | Gives up 3 of 16; gets a promise that data science backfills come first if anyone leaves |
| SVP of Electric Operations | The $12M run-rate, which is their commitment too | The grid operations squad's reporting line doesn't change this year |
| Heads of Billing and Service | Control of their squads' priorities | Squads stay with them; they keep the 1.5 engineers each that the gateway frees |
| CIO | The platform team and architecture standards | Platform moves to you; the CIO's architecture review enforces gateway use |
| The 40 staff | To know whether their job, manager, level or pay changes | Most hear "no change to your manager"; nobody's level or pay changes |
| The 3 who move to the CRO | A real career path, not a demotion to "compliance" | Volunteers first, same level and pay, a validation career track under the CRO |

**The one idea to hold:** every leader here is protecting a commitment they have already made in public, so the design moves only the people the review and the duplication force you to move.

## 3. Options

Four structures, scored on the review, the restoration commitment and how many of the 40 change manager. In every option except A, 3 data scientists move to the CRO as validators.

| | A. Change nothing (steering committee) | B. One AI org (all 40 under you) | C. Centralize builders (platform and squads, 24) | D. Hub and spoke |
|---|---|---|---|---|
| What moves | Nothing | Everyone, then 3 to the CRO | Platform 6 + squads 18 to you; 3 to the CRO | Platform 6 to you; 3 to the CRO |
| People changing manager | 0 | 40 | 6 + 18 + 3 = 27 | 6 + 3 = 9 |
| PUC review | 43 person-weeks of program and inventory unowned; no independent validators | Passes | Passes | Passes |
| Grid operations squad | Untouched | Changes manager | Changes manager | Untouched |
| One contract and gateway | No: each business head renews their own | Yes | Yes | Yes, through procurement and architecture review |

**How:**
1. **Validator capacity.** 3 people from week 8 to week 39 give 3 × 31 = 93 person-weeks, short of 103. Outside validation of 3 of the 6 in-scope models removes 30, leaving 73 of 93: a 78% utilization, with slack for estimate error.
2. **Why only 3 move.** Data science can't go below 13, and grid operations can't lose anyone, so there is nowhere else to take validators from.

**Decision.** Shortlist D, and keep C as the month-12 option if the dotted lines don't hold.

**Trap.** Treating "one AI org" as the mature answer. Here it moves 40 people, including the 9 the board commitment depends on, to solve a problem that 9 moves solve.

## 4. Decision and Trade-offs

Recommend D, hub and spoke. The hub (platform 6) reports to you and owns the shared gateway, the model inventory tooling and the AI standards. Validation reports to the CRO. Squads and data science stay where they are, with a dotted line to you for standards and hiring.

| We give up | Why it's worth it |
|---|---|
| Direct control of 18 squad engineers' priorities | Business heads keep them, and the grid operations team stays stable through month 12 |
| Data science at its floor of 13 | It is the only source of independent validators under the freeze |
| One hiring bar enforced by reporting line | You run the AI interview loop and leveling for all 40 through the dotted line |
| A simple "one AI org" story for the board | A design that costs 9 moves, not 40 |

**How:**
1. **Reversibility.** Every reporting change costs attrition, so a reorg is close to one-way. Centralizing later is still possible; centralizing now and undoing it would cost two rounds of moves.
2. **Revisit at month 12**, after the restoration commitment, and move squads to you (option C) if any holds:
   - LLM traffic outside the gateway is above 5% after month 8;
   - two squads build the same capability twice in the year;
   - the business heads ask for it.

**Decision.** D, because it is the only design that passes the review, keeps the grid operations squad stable and costs fewer than 10 moves.

**Trap.** Presenting the org as final. The board should hear on day one that the month-12 decision exists and what will trigger it.

## 5. Economics

Three-year view. Cash and freed capacity are separated, and assumptions are labelled. Contract savings start when the contracts renew, at month 6: ($1.5M − $0.9M) × 2.5 years = $1.5M.

| | A. Change nothing | B. One AI org | C. Centralize builders | D. Hub and spoke |
|---|---|---|---|---|
| Contract savings | $0 | +$1.5M | +$1.5M | +$1.5M |
| Outside validation | 6 × $60k = −$360k | 3 × $60k = −$180k | −$180k | −$180k |
| Extra departures (10 pts × movers) | 0 | 4.0 × $130k = −$520k | 2.7 × $130k = −$351k | 0.9 × $130k = −$117k |
| Restoration slip, expected (assumed) | $0 | 9 × 10% × 2 months × $1M = −$1.8M | −$1.8M | $0 |
| PUC finding (assumed) | −$2.0M | $0 | $0 | $0 |
| **3-year net** | **−$2.36M** | **−$1.0M** | **−$0.83M** | **+$1.20M** |

**How:**
1. **Freed capacity, not cash.** The gateway frees 4.5 − 1.5 = 3.0 engineers, 3 × $260k = $780k a year of payroll, about $1.95M over 2.5 years. It applies to B–D and stays in the squads.
2. **Year-one spend.** $180k of the $1.2M non-headcount budget, leaving $1.02M.
3. **Opportunity cost.** 3 data scientists' rate-case work ($780k a year of payroll) moves to validation, and data science loses its slack for the rate case.

**Decision.** D is the only option with a positive 3-year net, and its biggest benefit, 3 engineers of freed capacity, needs no reporting change.

**Trap.** Pricing a reorg as boxes on a chart. Its real cost is people leaving and commitments slipping, which is why "one AI org" goes from attractive to the second-worst option here.

## 6. Org and Ownership

Headcounts add up to 40: hub 6, squads 9 + 5 + 4 = 18, data science 13, validators 3.

| Group | People | Reports to | Owns |
|---|---|---|---|
| AI platform (hub) | 6 | You | Shared gateway, model inventory, eval and release standards |
| Grid operations, billing, service squads | 18 | Business heads; dotted line to you | Use cases, roadmaps, delivery |
| Data science | 13 | VP of Rates; dotted line to you | Forecasting, cost of service, rate case |
| AI validation | 3 (plus the CRO's 2 financial-model validators) | CRO | Independent validation, bias testing, review evidence |
| AI council | You, CRO, VP of Rates, business heads | Chair: you | Standards, the inventory, monthly priorities |

**How:**
1. **Standards bind through mechanisms, not lines.** Procurement signs only the enterprise contract; the CIO's architecture review blocks LLM calls outside the gateway; no model ships without an inventory entry.
2. **Review owner.** You are accountable for review readiness; the CRO owns the validation opinions.

**Decision.** Validation sits under the CRO because the commission will ask who the validators answer to, and "the VP who ships the models" is the wrong answer.

**Trap.** Putting governance in the hub. It looks tidy, but it fails the independence test the review is checking.

## 7. Plan and Milestones

Twelve months, with the moves made early and the end-state decision made after the restoration commitment.

| When | Milestone | Gate |
|---|---|---|
| Week 6 | Board approves the two-step design | — |
| Week 8 | 3 validators and platform move; outside firm contracted for 3 models | Volunteers confirmed, HR review done |
| Month 3 | Inventory of all 23 models complete | **Gate 1:** 23 of 23 registered with an owner and a risk tier |
| Month 6 | Enterprise contract signed as the three renew; gateway live | — |
| Month 7 | All 6 in-scope models validated | **Gate 2:** 6 of 6 validated, findings fixed or accepted by the CRO |
| Month 8 | All three squads on the gateway; the platform team does the grid operations migration itself | ≥ 95% of LLM traffic through the gateway |
| Month 9 | PUC review begins | — |
| Month 12 | Restoration savings at $12M; org revisit | Decision record to the board |

**Decision.** Validation finishes at month 7, two months before the review, so findings can be fixed rather than explained.

**Trap.** Asking the grid operations squad to do its own gateway migration during its savings ramp. The platform team does that work, so grid operations capacity stays on the $12M.

## 8. Risk and Governance

The reorg is itself an HR and legal process, and the people risks are bigger than the technical ones.

| Risk | Control |
|---|---|
| The 3 moves feel arbitrary or like a demotion | Written criteria (validation and statistics skills), volunteers first, same level, pay and title family; HR and legal review before anyone is told |
| Data science at 13 loses one more person | Its backfill goes first in the hiring queue; the outside firm can take a 4th model at $60k from the remaining budget |
| Squads bypass the gateway | No other LLM contract is signed; architecture review blocks it; traffic share reported monthly |
| Validation workload overruns | 78% planned utilization; a 4th model can go to the outside firm |
| A grid operations engineer leaves anyway | Grid operations backfill is second in the queue after data science |
| A business head resists the dotted line | The AI council sets standards, and the CEO chairs a quarterly review |

**Decision.** Put the people process in writing (criteria, volunteers, no change to level or pay) and have HR and legal sign it off before the first conversation.

**Trap.** Treating the reorg as a slide. Who moves, how they are chosen, and what they are told carry more risk to the review than the model inventory does.

## 9. Metrics

Each success metric gets a guard metric for the harm it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| PUC findings on AI governance | Zero material findings | Median validation time per model release, so validation doesn't stall delivery |
| Gateway share of LLM traffic | ≥ 95% by month 8 | Squad delivery against roadmap, so migration doesn't stall features |
| LLM contract spend | $0.9M a year from month 6 | Outages or latency from the shared gateway |
| Restoration savings run-rate | $12M by month 12 | Outage restoration times and customer complaints |
| Attrition in groups that changed manager | At or below the 15% baseline | Data science headcount at or above 13 |

**Decision.** Report the attrition of the 9 who moved separately from the other 31, because that is where the design's assumption can fail.

**Trap.** Measuring the org by its chart, such as "everyone has a dotted line". The test is whether the review, the restoration number and the people all hold.

## 10. Communication

Order matters: the people who move hear it first, in person, before anyone else.

| Audience | One line |
|---|---|
| Board | "Two steps: 9 moves now to pass the review and cut $0.6M a year of duplicate contracts, then a decision at month 12 on centralizing the squads." |
| CEO | "+$1.2M over 3 years; one AI org would cost about $1M and put the $12M at risk." |
| CRO | "You own 3 validators and the opinions; validation is done by month 7." |
| VP of Rates | "You give up 3 people and stay at 13; your backfills go first." |
| Business heads | "Your squads stay with you and keep the 1.5 engineers each the gateway frees; one contract and the AI standards are non-negotiable." |
| The 3 who move | "Same level and pay, a new career track under the CRO, and you were chosen for skills we can name." |
| All 40 | "For 31 of you, nothing changes about your manager; here is who moves and why." |

**How:**
1. Order: the 3 movers and the 6 platform engineers, then their old managers, then the 40, then the company.
2. Monthly AI council; quarterly board update through the review and month 12.

**Decision.** Lead with what doesn't change, because "reorg" makes 40 people update their CVs.

**Trap.** Announcing to everyone at once. The people who move must never learn about it from an all-hands slide.
