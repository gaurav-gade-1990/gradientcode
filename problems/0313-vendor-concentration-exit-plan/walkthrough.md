## 1. What the problem is really asking

On the surface this is a contract question: should we sign the incumbent's commitment, and do we need a second vendor? Underneath, it's a question about buying resilience for one critical workload at a price the board can see, while keeping a discount the CFO has already spent. The supervisor's letter and the board's risk appetite make exit readiness compulsory; the commitment makes it expensive. The candidate has to find the split that satisfies both.

Three facts in the brief carry the case:

1. **Only onboarding is critical.** It's 40% of spend. Disputes and support have human fallbacks, and internal tools can stop for a week. Readiness for all four is the expensive mistake.
2. **A week without the incumbent costs about €4M.** Manual onboarding covers 28% of demand. That number makes the cost of a standby look small.
3. **The commitment has headroom, but not much.** Moving 10% of traffic still meets €9M, but only if growth stays above about 22% a year. That's the trigger the CFO needs to hear about now.

The interviewer wants to see the candidate size the outage, check the commitment arithmetic, choose the narrowest option that meets both board limits, and test it before signing.

## 2. The numbers that drive the decision

**Onboarding in an outage.**
- Manual capacity: 60 reviewers × 30 hours × 60 / 35 minutes = **3,086 a week** (28% of 11,000).
- With AI: 60 × 30 × 60 / 8 = 13,500 a week, comfortably above demand.
- Backlog per week without AI: 11,000 − 3,086 = **7,914**.
- Cost: 7,914 × 12% × €4,200 = **€3.99M a week**, about **€570k a day**.

**Spend.**
- List spend with 30% growth: €3.6M, €4.68M, €6.08M, so **€14.36M** over three years.
- Full commitment at 25% off: €14.36M × 75% = **€10.77M**; the discount is worth **€3.59M**.

**Moving 10% of traffic (option B).**
- Incumbent: 90% × €14.36M × 75% = **€9.70M**, above the €9M commitment by €0.70M (7.7%).
- Second provider: 10% × €14.36M = **€1.44M** at list.
- 10% of all traffic is a quarter of onboarding: 10% / 40% = **25%**.
- Discount kept: €9.70M / 75% × 25% = **€3.23M**.

**The growth trigger.** At what growth does 90% of traffic only just meet €9M? Solve 0.9 × 0.75 × €3.6M × (1 + x + x²) = €9M. So 1 + x + x² = 3.704 and x = **1.219**: about **22% growth a year**.

**Three-year totals.**
- A, paper plan: **€10.77M**.
- B, warm standby: €9.70M + €1.44M + build 3 × 0.5 × €180k = €0.27M + run 1 × 2.5 × €180k = €0.45M, so **€11.85M**.
- C, 50/50: the commitment isn't met, so 10% off on half: €7.18M × 90% = €6.46M, plus €7.18M at list, plus €0.45M build and €0.90M run, so **€15.00M**.
- D, self-hosted: €10.77M + GPUs 8 × 8,760 × €2.30 × 3 = €0.48M + €0.27M build + €0.90M run, so **€12.43M**.

**The comparison that matters.** B − A = **€1.08M**, which is €1.08M / €3.99M = 0.27 weeks, about **1.9 days** of onboarding outage.

## 3. How to spend your time

Sixty minutes, about twelve per pillar.

| Minutes | What you do |
|---|---|
| 0–7 | Read the brief. Write down 3,086, 7,914, €3.99M a week, €14.36M, €9.70M against €9M, 22%. Circle "already booked" and "24 hours". |
| 7–17 | **Pillar A.** The two board tests, workload tiers, and stakeholders including the incumbent. |
| 17–35 | **Pillar B.** Four options against the limits and the commitment, the call with the growth trigger, three-year economics. |
| 35–50 | **Pillar C.** Owners, a plan that drills before signing, and the contract asks. |
| 50–57 | **Pillar D.** Drill-time metrics and one line per audience. |
| 57–60 | Check every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is the board really asking, and what does failure cost?

**How to reason.** Turn the request into the board's two limits: onboarding degraded for at most 24 hours, and every critical workload movable within 90 days. Then size the outage: manual reviewers cover 3,086 of 11,000 applications a week, so 7,914 back up, and 12% of those abandon at €4,200 each, about €3.99M a week. Tier the workloads: onboarding is critical; disputes and support have human fallbacks; internal tools can wait. Say what's out of scope: fraud models, and the rest of the cloud estate.

**The trap.** Treating 92% concentration as the problem to solve everywhere. The problem is the one critical workload that has no fallback.

**Rubric criteria earned:** the two limits; manual capacity and backlog derived; the outage priced; workloads tiered.

### Stakeholders

**The question it answers:** who has a stake, and how do you bring them along?

**How to reason.** The tension is between the board and supervisor (less dependence) and the CFO (the discount that needs dependence). Show both can win: 90% stays on the incumbent and still meets €9M; 10% buys a live second path for onboarding. Include the incumbent as a party: they want the commitment, and that's your leverage for exit terms. Operations needs a failover in hours, and the CRO needs concentration reported in the register.

The one idea: exit readiness is bought for the one critical workload and paid for by keeping the rest on the discount.

**The trap.** Treating the CFO as an obstacle. Their booked discount is a real number, and the recommendation has to keep most of it.

**Rubric criteria earned:** board, supervisor, CFO, CRO and operations; the incumbent as a negotiating party; both constraints met; the one idea.

## 5. Pillar B: Decide

### Options

**The question it answers:** which options meet the limits, and what do they do to the commitment?

**How to reason.** Four options:

- **Paper plan, full commitment.** Cheapest, but in an outage manual review covers 28%. It fails the 24-hour limit and has never been tested.
- **Warm standby for onboarding.** A quarter of onboarding runs live on a second provider on another cloud; failover is a routing change. Incumbent spend is €9.70M, above €9M.
- **Active-active 50/50.** Meets both limits, but €7.18M to the incumbent misses €9M, so most of the discount goes.
- **Self-hosted fallback.** Keeps the commitment, but the model scores 89% against 96.4%, so in a crisis reviewers catch far more errors exactly when they're overloaded.

**The trap.** Calling the paper plan an exit plan.

**Rubric criteria earned:** the paper plan shown to fail; commitment checked per option; active-active's lost discount; the self-hosted quality gap.

### Decision and Trade-offs

**The question it answers:** what do you recommend, what's given up, and when do you revisit?

**How to reason.** Recommend B with the €9M commitment, quarterly drills, documented fallbacks for disputes and support, and exit terms in the renewal. Give-ups:

- €1.08M over three years against the paper plan;
- €359k of discount on the moved 10%;
- 1.3 points of KYB accuracy on a quarter of onboarding;
- one engineer permanently on the standby.

Separate the doors. Routing is two-way: a gateway setting. The commitment is one-way for three years, so it gets the trigger. Solve for the growth at which 90% of traffic only just meets €9M: about 22% a year. Other triggers: the standby falling more than 2 points behind on the KYB evaluation, or a drill taking over 24 hours.

**The trap.** Signing the commitment without checking it against the traffic you plan to move.

**Rubric criteria earned:** commitment plus standby; give-ups including lost discount; the one-way door named; the 22% trigger.

### Economics

**The question it answers:** what does each option cost over three years, against an outage?

**How to reason.** Use one growth forecast (30%, labelled) for every option. Put incumbent spend, second-provider or GPU spend (new), and build and run engineers (payroll) on separate rows. Totals: A €10.77M, B €11.85M, C €15.00M, D €12.43M. Then the comparison that sells it: B costs €1.08M more than A, which is about 1.9 days of outage. Year one, B adds €90k of new spend to the CFO's budget (€2.79M against €2.70M). Name the opportunity cost: 1.5 engineer-years off the platform roadmap.

**The trap.** Comparing readiness against zero instead of against the outage it prevents.

**Rubric criteria earned:** three-year totals on one forecast; new spend and payroll apart; readiness against outage; year-one new spend.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owns the plan, the fallbacks and the contract?

**How to reason.** You own the exit plan and drill results. The platform team owns routing, per-provider evaluations and the drills. Each workload owner (onboarding, disputes, support) owns their fallback and staffs drills, because they'd staff a real outage. Procurement and legal own the contract and register entries; the CRO's third-party risk team challenges the plan; FP&A tracks the commitment quarterly.

**The trap.** Giving the exit plan to procurement. A clause doesn't move traffic.

**Rubric criteria earned:** one owner; workload owners own fallbacks; second-line challenge; commitment tracked.

### Plan and Milestones

**The question it answers:** what happens before the renewal is signed?

**How to reason.** The key sequencing call: have the second provider live and drilled before signing. In weeks 0–8, integrate onboarding behind the gateway (Gate 1: KYB evaluation at least 95%). Week 10, the board decision. Months 3–4, a quarter of onboarding live and the first drill (Gate 2: full switch in under 4 hours). Month 5, sign the renewal with exit terms. Months 4–6, drill disputes and write runbooks for support and internal tools. Then drills every quarter, with results to the board.

**The trap.** Building the standby after signing, when there's no longer any pressure to finish it.

**Rubric criteria earned:** drilled before signing; measurable gates; quarterly drills to the board; fits the 10-week and 5-month dates.

### Risk and Governance

**The question it answers:** what could make the plan fail, and what goes in the contract?

**How to reason.** A standby that serves nothing rots, so keep it on live traffic and compare scores weekly. Prompts drift between providers, so one evaluation set runs on both before any change ships. The commitment can fall short, so FP&A tracks it against the 22% trigger. Then the contract asks, framed as negotiation or as the company's DORA programme, not as legal fact: termination assistance and a transition period, notice before a model version is retired, deletion of data on exit, and price protection. Update the register with both providers and the tested switch time. Plan for both failing: manual review at 3,086 a week, with the largest merchants first.

**The trap.** Believing contract clauses are the exit. They lower its cost; only a working second path makes it possible.

**Rubric criteria earned:** live traffic on the standby; exit terms as asks; one evaluation set; register updated.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how do you know it works?

**How to reason.** Pair them:

| Success metric | Guard metric |
|---|---|
| Drill switch time under 4 hours | Standby KYB score within 2 points |
| Onboarding traffic on the incumbent at 75% | Commitment progress against €9M |
| Tested fallbacks for 3 customer-facing workloads | Reviewer error rate on standby cases |
| €3.23M of discount kept | Second-provider spend against €1.44M |

**The trap.** "We have an exit plan" as the metric. The real metric is how long the last switch took.

**Rubric criteria earned:** paired metrics; switch time; commitment beside resilience; the quality gap.

### Communication

**The question it answers:** what does each audience hear?

**How to reason.** One line each:

- **The board:** onboarding fails over in hours, tested quarterly, €1.08M over three years.
- **The supervisor:** a live second provider for the critical function, a dated runbook for the rest, and drill evidence.
- **The CFO:** €3.23M of €3.59M kept, €90k more in year one, and safe while growth stays above about 22%.
- **The incumbent:** the commitment, with exit terms.
- **Operations:** failover in hours.

Quarterly drill results to the board, failures included.

**The trap.** Telling the CFO the discount is fully safe. It depends on the forecast.

**Rubric criteria earned:** four or more audiences; the CFO told about the forecast; quarterly drills reported; evidence first.

## 8. The decisions that separate strong answers

**Pricing the outage first.** Weak answers argue resilience in principle. Strong answers say a week costs about €4M, so €1.08M over three years is less than two days of it.

**Checking the commitment against the plan.** The trap in the offer is that diversifying makes the minimum harder to hit. Solving for the 22% growth trigger shows the candidate read the contract as a finance instrument, not just a price.

**Narrowing to the critical workload.** Active-active for everything is what a cautious engineer proposes. A leader buys readiness where the board's limit applies and uses cheaper fallbacks elsewhere.

## 9. Common mistakes

- **A binder instead of a drill.** The supervisor asked how you'd exit; evidence is a timed switch.
- **Active-active everywhere.** It costs €15.00M and gives up most of the discount for coding tools that can stop for a week.
- **Self-hosting as the default answer.** It keeps the commitment, but 89% quality in a crisis loads reviewers further when they're already short.
- **Ignoring the commitment arithmetic.** €9.70M against €9M is fine at 30% growth and not at 20%.
- **Inventing legal requirements.** Describe exit terms as negotiation asks or company policy under its DORA programme, not as specific articles.
- **Signing first.** The drill should inform the commitment, not follow it.

## 10. Follow-ups an interviewer might ask

**The incumbent refuses any exit terms. Do you still sign?**
Yes, if the standby passes its drill, because the standby is the exit; the terms only make it cheaper. Report the refusal to the board risk committee as a residual risk in the register.

**Growth comes in at 15% in year one. What now?**
Re-solve the commitment. At 15% a year, 90% of traffic gives 0.9 × 0.75 × €3.6M × (1 + 1.15 + 1.3225) = €8.44M, short of €9M by about €0.56M. With all traffic on the incumbent the total would be €9.38M, so at least 9 / 9.38 = 96% must stay there. Cut the standby's live share to about 4% of traffic (a tenth of onboarding), which keeps it warm and verified, or pay the shortfall; tell the CFO in the quarter it's visible.

**The second provider's score drops 3 points after its own model update.**
That breaches the 2-point trigger. Route its share back to the incumbent, re-tune prompts against the shared evaluation set, and re-run the drill before restoring the split. Meanwhile, onboarding's 24-hour limit relies on a weaker standby, and the board hears that.

**Why not self-host as the second path instead of a second vendor?**
It costs more (€12.43M against €11.85M), and the model scores 7.4 points lower on KYB. It's the right answer only if no second provider passes the evaluation, or if both commercial providers share a dependency you can't diversify.

**How does this change if disputes were classified as critical too?**
Disputes join the standby. Running all of disputes live there as well would put 10% + 25% = 35% of traffic on the second provider and leave 65% × €14.36M × 75% = €7.00M with the incumbent, below €9M. So integrate and drill disputes, keep only a small slice live, and re-check the commitment.
