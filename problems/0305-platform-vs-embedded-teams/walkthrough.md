## 1. What the problem is really asking

On the surface this is an org-design question: central AI platform or embedded teams. Underneath, three separate demands have been bundled into one reorg, and the strongest move is to unbundle them. The audit committee wants a risk owner and a working control in 90 days. The CFO wants model spend down. The CTO wants structure. Only one of these actually requires people to move, and it requires far fewer than the CTO's 150.

Three facts carry the case:

1. **The incident was an unapproved vendor call.** That is stopped by a control on outbound traffic and contracts, not by changing anyone's reporting line. Once you see that, the 90-day deadline stops depending on the reorg.
2. **The duplication is in 36 infrastructure roles, not 150 people.** Each unit runs its own gateway, eval harness and vector store. Product AI work, the part that makes autos' pricing advisor different from jobs' matching, isn't duplicated. A platform needs 22 people.
3. **Autos can't move, and it carries 40 percent of spend.** Any plan that needs autos people before month 5 fails. Any plan that needs autos traffic on the gateway for the 90-day control also fails. So the control has to work without autos engineering.

This is a Hard case: board-level, a regulator, a reorg that's hard to undo. The interviewer is grading whether you can make a decision with exec stakes, price the people cost honestly, and sequence it so the irreversible part is as small as possible.

## 2. The numbers that drive the decision

Work these out in the first eight minutes.

**People.**
- AI payroll: 150 × $280k = **$42M a year**.
- Infrastructure roles: 10 + 8 + 7 + 6 + 5 = **36** (24% of staff). Platform needs **22**, so **14** go to product work.
- Non-autos infrastructure roles: 8 + 7 + 6 + 5 = 26; take 16 now. Autos has 10; take 6 at month 7.

**Attrition.** Moved staff leave at 24% instead of 12%, so **12 extra points**.
- Platform option: 22 × 12% = **2.64** extra departures × $140k = **$370k**.
- Full centralization: 150 × 12% = **18** × $140k = **$2.52M**.

**Model spend.**
- Next 12 months at 5% monthly growth: $1.5M × (1.05 + … + 1.05¹²) = $1.5M × 16.71 = **$25.1M**. Not 12 × $1.5M = $18M.
- Month-12 run rate: $1.5M × 1.05¹² = **$2.69M a month**.

**The saving on gateway traffic**, as shares of today's spend:
- Routing: 45% of Opus (60%) is 27% of spend, moved to Sonnet at exactly half the price (Opus $4/$20, Sonnet $2/$10). Opus becomes 33%, Sonnet 35% + 13.5% = 48.5%. Total **86.5%**.
- Caching: half of uncached input becomes cache reads. Input is 65% of each model's spend. Opus saves 95% on those tokens ($4 → $0.20), Sonnet 90% ($2 → $0.20). Opus: 33% × 65% × 50% × 95% = 10.2%. Sonnet: 48.5% × 65% × 50% × 90% = 14.2%. Haiku has no cache price, so leave it.
- Left: 86.5% − 24.4% = **62.1%**, a saving of **37.9%**.

**Phasing.** Non-autos traffic (60%) on the gateway from month 4, autos from month 7: **$6.74M** in year one. Years 2 and 3, assuming spend flat at $2.69M a month: $64.7M × 37.9% = **$24.5M**. Three years: **$31.2M**.

**Net, three years.**
- Platform option: $31.2M − $0.37M − $3.6M tooling = **$27.3M**.
- Full centralization: savings start at month 7 for everyone (assumed), $29.9M − $2.52M − $3.6M = **$23.8M**, before any launch slip.
- Standards only, 50% adoption (assumed): $15.6M − $3.6M = **$12.0M**.
- Each month the autos launch slips defers up to $60M / 12 = **$5M** of revenue.

## 3. How to spend your time

Sixty minutes. The extra fifteen go to stakeholders and sequencing, which is where Hard cases are won.

| Minutes | What you do |
|---|---|
| 0–8 | Read the brief. Compute 36 and 22, the attrition numbers, $25.1M, $2.69M and the 37.9% saving. Circle "within 90 days" and "nobody on my AI team moves". |
| 8–18 | **Pillar A.** Unbundle the three decisions. Build the stakeholder table: CEO, audit committee, CFO, CTO, the presidents, the movers, General Counsel. |
| 18–36 | **Pillar B.** Four options over three years, the recommendation with its give-ups and triggers, and the savings derivation. |
| 36–50 | **Pillar C.** Decision rights, the sequenced plan with the allow-list first, and the people risk. |
| 50–57 | **Pillar D.** Metrics with velocity as the guard, and the order in which people hear the news. |
| 57–60 | Check every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is really being decided?

**How to reason.** Say out loud that there are three decisions: the risk control (90 days), the platform (who builds and runs the shared layer), and the operating model (where product AI people sit). Then put the frame numbers in a table: payroll, the 36 duplicated roles, next year's spend with compounding, the month-12 run rate, the deadline and autos. Each row should say what it forces. Out of scope: the autos product itself, and choosing vendors beyond enforcing zero-retention contracts.

**The trap.** Reading the incident as proof that everything must be centralized. The leak was one unapproved vendor call. A network block stops that in weeks.

**Rubric criteria earned:** three decisions separated; compounded spend; 36 and 22 identified as the duplication; the autos and deadline clash named.

### Stakeholders

**The question it answers:** who has a stake, and how do you bring them along?

**How to reason.** This table is longer than in a Medium case because more people can block you. The CEO needs a board-ready answer. The audit committee needs an owner and a control. The CFO needs savings they believe. The CTO's proposal isn't adopted, so give them something real: co-ownership of standards and the platform on their infrastructure, and show them the $2.52M attrition number. The autos president gets exactly what they asked for. The jobs president gets their gateway as the starting point. The other presidents keep their product teams, and the model savings show up in their P&Ls. The 36 infrastructure staff need to hear first, one to one. General Counsel needs evidence for the regulator.

Close with one idea. The model answer's: only the owner and the gateway require change; the presidents' teams don't.

**The trap.** Leaving the CTO out, or treating them as an obstacle. A peer whose proposal you're declining needs a role in the answer.

**Rubric criteria earned:** the main execs and two or more presidents; what the CTO gets; the movers included; one idea.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the real operating models, and what does each cost?

**How to reason.** Four options on one table, over the same three years:

- **Status quo:** no savings, no owner, fails the audit committee.
- **Centralize all 150 (the CTO's):** $2.52M of extra attrition, savings delayed while the reorg absorbs two quarters (assumed), and the autos team moved weeks before a $60M launch.
- **Platform from the infrastructure roles, product embedded:** 22 people move, $370k attrition, nearly all the savings.
- **Standards only, no moves:** a gateway with no owning team, adoption assumed at 50%, and an "owner" without a team, which the audit committee won't accept.

For each, show how the 90-day control is met. That row is what reveals that the control doesn't depend on the option.

**The trap.** Debating central against embedded as the only two choices.

**Rubric criteria earned:** status quo, the CTO's option and a hybrid; attrition priced; the 90-day control per option; one table over three years.

### Decision and Trade-offs

**The question it answers:** what do you recommend, and what would change it?

**How to reason.** Recommend the hybrid and say where the platform reports: to you, because the audit committee's owner must control the gateway. Decouple the control: an egress allow-list goes live 2 weeks after approval, built by the network team, covering autos without any autos engineer.

Then the give-ups: the CTO's single org, six months of autos savings, units' freedom to sign contracts, and 22 people's reporting lines. Reversibility: moving 22 can be undone; moving 150 can't, without losses. Revisit at month 12 on three triggers: gateway coverage under 95%, slower use-case launches, or moved-staff attrition over 24%.

**The trap.** Selling the reorg as the source of the savings. The gateway saves the money.

**Rubric criteria earned:** one recommendation with reporting line; control decoupled; reversibility; dated triggers.

### Economics

**The question it answers:** where do the savings come from, and what does each option cost?

**How to reason.** Do the two-lever derivation as a small table (section 2 has the arithmetic): routing leaves 86.5% of spend, caching leaves 62.1%. Then phase by when each unit reaches the gateway, autos last, and extend over three years with the flat-spend assumption labelled. Net out attrition and tooling. Keep payroll separate: the 22 platform staff and the 14 re-tasked roles are already paid. Don't call the 14 a saving.

Close with the funding model, because it decides adoption: platform funded centrally in year one, model spend billed to units at cost, so savings land in the presidents' P&Ls.

**The trap.** Counting freed roles as headcount savings. Nobody is cut, and saying otherwise triggers the attrition you priced.

**Rubric criteria earned:** the 37.9% derived; savings phased; new spend and attrition separate from payroll; assumptions labelled.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who decides what, and who pays?

**How to reason.** A decision-rights table beats a box chart. The platform owns vendors and contracts, the gateway, routing, caching, cost attribution and the eval service. Units own use cases, prompts, roadmaps, their eval sets and model choice within the allow-list. AI risk is accountable to you and responsible in the units. Add an AI risk council, the CTO as co-chair of standards, and a 2-week service target with a published queue.

**The trap.** A platform with authority and no service target. Units will route around it.

**Rubric criteria earned:** a decision-rights table; one AI risk owner; a funding model; a service target.

### Plan and Milestones

**The question it answers:** what happens by day 90, by the autos launch, and after?

**How to reason.** Order is everything. Board approval at week 6. Allow-list live and the 16 non-autos movers formed into the platform at week 8, each told one to one first. Gateway carrying the non-autos 60% of spend by day 90, with contracts on zero-retention terms, for the audit committee. Routing and caching from month 4, gated on evals. Autos launches untouched in month 5. Autos' 6 join and its traffic moves in month 7. Revisit at month 12.

**The trap.** Making the audit date depend on the reorg. If the people moves slip, the board's control slips with them.

**Rubric criteria earned:** a control on every unit before day 90; no autos moves before launch; movers told first; the month-12 revisit.

### Risk and Governance

**The question it answers:** what could go wrong, and what manages it?

**How to reason.** Quantify the people risk first: 22 × 24% = 5.3 expected departures among movers in 12 months. Manage it with one-to-one conversations, a charter and retention for key engineers. Then the platform bottleneck (service target, self-service within the allow-list), the autos launch (no moves before month 7), the leak repeating (allow-list in code, zero-retention contracts), routing quality (each use case's evals), and vendor concentration (at least two vendors behind the gateway).

**The trap.** Answering the regulator with an org chart. They want evidence the data flow is blocked.

**Rubric criteria earned:** departures quantified; the control in code; eval-gated routing; vendor concentration.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how do you know the new model works?

**How to reason.** Pair gateway coverage with the time units take to launch a new use case. Pair the 37.9% saving with eval pass rates and quality complaints. Pair zero non-contracted calls with exception requests waiting too long. Pair moved-staff attrition with engagement among the 14 re-tasked. And keep the autos launch date on the dashboard.

**The trap.** Measuring the platform on savings alone. A gateway that blocks everything looks very cheap.

**Rubric criteria earned:** guards paired; velocity guards savings; coverage against day 90 and month 7; attrition against 24%.

### Communication

**The question it answers:** what does each audience hear, and in what order?

**How to reason.** One line per audience: board, CEO, CFO, CTO, autos president, infrastructure staff. Then the order: movers one to one first, presidents the day before, the wider organization last. Monthly reports to the audit committee until the inquiry closes. And tell the infrastructure staff plainly that nobody is being cut.

**The trap.** Announcing at an all-hands. People learn their new manager from a slide and start interviewing.

**Rubric criteria earned:** five or more audiences; sequencing; audit committee cadence; "nobody is cut" said plainly.

## 8. The decisions that separate strong answers

**Decoupling the control from the reorg.** Weak answers make the audit committee wait for the new org. Strong answers meet the deadline with an egress allow-list that needs no one to move, which also keeps autos out of it.

**Sizing the move to the duplication.** The CTO's plan moves 150 people to fix a problem in 36 roles. Moving 22, and pricing the difference at $2.15M of attrition plus launch risk, is the judgment the board is paying for.

**Being honest about where the money comes from.** Routing and caching save 37.9% of covered spend whatever the org chart says. Saying so, and showing that the org decision is about ownership and adoption (50% adoption without an owning team), is more credible than claiming the reorg saves $31M.

## 9. Common mistakes

- **Treating it as central against embedded.** The answer is a split by layer.
- **Ignoring compounding.** Next year's spend is $25.1M, not $18M.
- **Pricing attrition at zero.** HR gave you the data; use it.
- **Moving autos before launch.** $5M of revenue deferred per month of slip.
- **Calling freed roles savings.** It starts the attrition you're trying to avoid.
- **Policy instead of controls.** The jobs unit already had a policy.

## 10. Follow-ups an interviewer might ask

**The CEO likes the CTO's plan because "one org is simpler". What do you say?**
Simpler on the chart, not in practice: $2.52M of extra attrition, the autos team moved before a $60M launch, and product engineers separated from the products they know. Offer the CTO co-ownership of standards so the simplicity they want, one way to call a model, still happens.

**Autos refuses to put its traffic on the gateway even after launch. Now what?**
The allow-list already covers autos, so the risk control holds. For savings, show autos its own number: 40% of the month-7 run rate, $2.69M × 40% × 37.9% ≈ $408k a month by month 12. If they still refuse, it goes to the CEO as a P&L choice, not a platform fight.

**What if the platform team loses 5 people in the first year, as HR's data predicts?**
That's 5.3 expected, so plan for it: hire behind the moves, and keep the 14 re-tasked roles as the first internal candidates. If attrition passes 24%, it's one of the month-12 triggers.

**The regulator asks who was accountable before the incident. How do you answer?**
Truthfully: nobody owned AI risk across units, which is what the new model fixes. Show the allow-list logs, the contracts with zero-retention terms and the named owner.

**When would you go further and centralize product AI teams too?**
If units keep building the same products separately, say three versions of the same listing-quality model, or if the platform's service target holds and units ask for shared product work. That's a year-two question, decided with data.
