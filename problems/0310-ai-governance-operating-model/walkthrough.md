## 1. What the problem is really asking

On the surface this is an org-design question: central, federated or something in between. Underneath, it's a capacity question with a fixed date and an incentive problem. The supervisor is coming in 6 months to test three things, and the group can't pass the first one today because a third of its AI systems were unknown to the centre until last month.

Three facts in the brief carry the case:

1. **The hours don't fit any central team.** A full 120-hour assessment for everything due by month 6 is 36,720 hours. Even with tiering, central-only needs 5,211 hours against 4,680 available. A candidate who doesn't do this arithmetic will recommend "strengthen the central team" and be wrong.
2. **The unknown systems came from the queue.** The 11-week wait is why three countries built around governance. Any model that makes the queue longer creates more unknown systems, and the supervisor's first test is the inventory.
3. **Independence is the test federated fails.** Countries assessing their own high-risk systems is fast, but the supervisor will ask who checked the people who built it.

The interviewer is grading level. A strong answer sizes the work before drawing boxes, keeps approval away from builders (including the candidate's own platform), prices the delay the current queue causes, and gives triggers that would change the model country by country.

## 2. The numbers that drive the decision

Work these out first. Every later section reuses them.

**Work due by month 6.**
- Inventory: 212 systems (14 high, 61 material, 137 low).
- Queue: 46 proposals (3 high, 17 material, 26 low).
- New proposals over 6 months: 6 × 8 = 48 (3 high, 15 material, 30 low).
- Totals by tier: high 14 + 3 + 3 = **20**, material 61 + 17 + 15 = **93**, low 137 + 26 + 30 = **193**, so **306 items**.

**Hours.**
- Everything at full assessment: 306 × 120 = **36,720 hours**.
- Tiered: 20 × 120 + 93 × 24 + 193 × 3 = 2,400 + 2,232 + 579 = **5,211 hours**.

**Capacity to month 6.**
- Existing central team: 4 × 130 × 6 = **3,120 hours**.
- 4 hires start at month 4 (3-month hiring), so 4 × 130 × 3 = **1,560 hours**.
- Central total: **4,680 hours**. Central-only tiered runs at 5,211 / 4,680 = **111%**.
- Country leads from month 2: 9 × 0.5 × 130 × 5 months = **2,925 hours**.

**Hub and spoke split.** Countries do material assessments (2,232 h, which is 76% of 2,925). Central does high-risk (2,400 h), low-tier checks (579 h) and re-performs 25% of material ones (558 h): **3,537 hours**, which is 76% of 4,680.

**Money.**
- Year-one new spend: hires 4 × €160k × 9/12 = €480k, tool €250k, assurance 14 × €35k = €490k, so **€1.22M** against the €1.5M cap.
- Country leads: 9 × 0.5 × €130k = **€585k a year**, on payroll.
- Cost of delay: €38M / 12 = **€3.17M a month** of claims savings (assumed linear).

**Shadow share.** 72 / 212 = **34%** of systems unknown to the centre; 51 of those 72 (71%) sit in 3 countries.

## 3. How to spend your time

Sixty minutes, about twelve per pillar, with time at each end.

| Minutes | What you do |
|---|---|
| 0–7 | Read the brief. Write down 306 items, 36,720 h, 5,211 h, 4,680 h, €3.17M a month and 34%. Circle "will not route every AI change" and "one named accountable executive". |
| 7–17 | **Pillar A.** Turn the letter into three month-6 tests. Build the stakeholder table and split the countries into two groups. |
| 17–35 | **Pillar B.** Options with hours against capacity, the recommendation and its triggers, three-year economics with the delay cost. This pillar carries the most marks. |
| 35–50 | **Pillar C.** Three lines with named owners, a plan with a mock review at month 5, and controls that produce evidence. |
| 50–57 | **Pillar D.** Paired metrics and one line per audience. |
| 57–60 | Check every number is derived or labelled as assumed. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is the board actually asking for, by when, and how big is the problem?

**How to reason.** Rewrite the supervisor's letter as three tests you can pass or fail at month 6: a complete inventory with an owner per system, a risk assessment on file for every high-risk system, and records showing the board oversees AI risk. Then size the work. The trick is to count what is due by month 6, not just what is in production today: the 46 queued proposals and roughly 48 new ones also need some assessment, which brings the total to 306. Show that the current one-size review (120 hours) would need 36,720 hours, and that even a tiered version done centrally (5,211 hours) is more than the 4,680 hours a central team can deliver. Add one number for the cost of doing nothing: the queue holds up €3.17M of claims savings a month.

Name what's out of scope: ISO/IEC 42001 certification and the actuarial model risk policy rewrite are year-two work.

**The trap.** Opening with "we need an AI policy and an ethics committee". Neither finds the 72 unknown systems, and a committee is just another queue.

**Rubric criteria earned:** the ask as month-6 tests; 306 items counted including the queue and new proposals; the hours shown not to fit; the queue's cost.

### Stakeholders

**The question it answers:** who has a stake, what do they want, and how do you bring them along?

**How to reason.** The board and the supervisor want evidence. The CRO wants independence without an unfunded mandate. The CFO wants the freeze respected. The hard part is the country CEOs, and they aren't one group: the 3 with their own data science teams own 51 of the 72 unknown systems and are the ones threatening to route around the centre; the other 6 mostly run material systems and don't want to pay for a problem they don't have. Offer the first group speed (their own lead, a 3-week service level) and a 30-day amnesty so registering a past system carries no blame. Tell the second group it costs them half a person each.

The one idea to hold: the supervisor tests whether the group knows what it runs, but the countries decide whether it does, so registering must be cheaper than hiding.

**The trap.** Treating the countries as resistance to be overruled. Overruling them is how the 72 unknown systems happened.

**Rubric criteria earned:** the board, supervisor, CRO, CFO and country CEOs with distinct wants; the two country groups separated; a concrete offer for registering; the one idea.

## 5. Pillar B: Decide

### Options

**The question it answers:** which operating models are possible, and how does each do on the supervisor's tests and the hours?

**How to reason.** Put four options on one table:

- **Central, tiered.** Independent, but at 111% of capacity, and it does the 17 high-risk systems first, so the claims programme's material assessments wait until about month 7. The queue grows and so do the unknown systems.
- **Federated.** Each country does all its tiers. Fast, and the countries like it, but nobody independent checks a high-risk underwriting model. That fails the test the supervisor is coming to run.
- **Hub and spoke, tiered.** Central does high-risk, low-tier checks and re-performs 25% of material assessments (3,537 hours, 76%); country leads do material assessments (2,232 hours, 76%). Both sides have headroom.
- **Freeze.** Stop new deployments until the review. It fits the hours by not doing the business.

Give each a three-year cost so the comparison isn't only qualitative.

**The trap.** Choosing federated because it wins over the countries. It fixes speed and fails independence.

**Rubric criteria earned:** four options on one table including freeze; hours against capacity per option; federated's independence gap; three-year costs.

### Decision and Trade-offs

**The question it answers:** what do you recommend, what do you give up, and what would change your mind?

**How to reason.** Recommend hub and spoke: a central office under the CRO, a lead in each country, three tiers and an amnesty. Then list the give-ups:

- €1.71M more over three years than central-only;
- 4.5 people of country operational-risk time;
- one reviewer standard for every system, replaced by 25% sampling;
- your own approval rights over what your platform builds.

That last one is what separates a principal answer. You are the accountable executive, but you also run the AI platform, so the CRO's committee approves high-risk systems, including yours.

Reversibility: it's a two-way door per country. If sampling finds more than 10% of a country's material assessments deficient, that country goes back to central review without redesigning the rest. Other triggers: a tier missing its service level for two months, or more than 5 unregistered systems found after the amnesty.

**The trap.** "I'll chair the approvals since I'm accountable." That's the builder approving the build, and the supervisor will notice.

**Rubric criteria earned:** one recommendation with tiers and a country first line; approval kept from builders; per-country reversibility; measurable triggers.

### Economics

**The question it answers:** what does each option cost over three years, and what does the delay cost?

**How to reason.** Build the table from the same rows for every option: existing reviewers (payroll, €1.92M), new hires (new spend, €1.76M over three years), country people (payroll), the tool (€750k) and external assurance (€490k, year one only, labelled as assumed). Totals: central €4.92M, federated €6.18M (assuming 1 person per country), hub and spoke €6.63M, freeze €2.67M.

Then the two numbers the CFO and CEO care about. Year-one new spend is €1.22M against the €1.5M cap. And the delay: hub and spoke clears the claims programme's 9 assessments by month 3; central-only clears them around month 7. Four months × €3.17M = €12.7M of savings deferred, against €1.71M of extra cost. Label that the delay maps one-for-one to savings; it's an assumption.

**The trap.** Presenting freeze as the cheapest option. It's cheapest only if deferred savings count as zero. The other trap is calling the country leads free because they're on payroll.

**Rubric criteria earned:** three-year totals with new spend and payroll separated; €1.22M against €1.5M; the delay priced and labelled; the country leads' opportunity cost.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who is accountable, who approves, and who does the work?

**How to reason.** Use the three lines of defense, because the supervisor will:

- **Oversight:** the board risk committee, with a quarterly AI risk report.
- **Accountable executive:** you, for the policy, inventory, tier rules and first-line standards.
- **Approval:** an AI risk committee chaired by the CRO, with go or no-go on every high-risk system.
- **Second line:** the central office of 8, reporting to the CRO.
- **First line:** 9 country leads, plus a named business owner for every system.
- **Third line:** internal audit, reviewing the model at month 9.

**The trap.** An ethics board with no decision rights. When the supervisor asks who decided, "we discussed it" isn't an answer.

**Rubric criteria earned:** one accountable executive; approval and reviewers in the second line; a named owner per entry; internal audit dated.

### Plan and Milestones

**The question it answers:** what happens between now and the review, and where can you still correct course?

**How to reason.** Work backwards from month 6 and front-load two things: the high-risk systems (the supervisor's test) and the claims programme's queue (the business case). Three gates:

- **Gate 1, month 2:** every inventory entry has a named owner, when the amnesty closes.
- **Gate 2, month 4:** first sampling results, with at most 10% defects per country.
- **Gate 3, month 5:** an internal audit dry run finds no gap in the three tests.

Check the central hours: through month 5 there are 4 × 130 × 3 + 8 × 130 × 2 = 3,640 hours, against 17 high-risk systems at 120 hours (2,040) and 163 low-tier checks at 3 hours (489).

**The trap.** Making month 6 the first real test. A dry run at month 5 leaves a month to fix what it finds.

**Rubric criteria earned:** high-risk done before month 6; the claims queue cleared early; measurable gates; a mock review.

### Risk and Governance

**The question it answers:** what could undermine the model, and which controls produce evidence?

**How to reason.** The biggest risk is systems the group doesn't know it runs. The strongest control is technical: model API keys are issued only through the group gateway, and only against an inventory id. Add monthly procurement and cloud-billing checks for anything that slips past. Then the second risk: country leads rubber-stamping. 25% re-performance with a pull-back rule handles it. A fallback for the instant-issue product: if the underwriting model fails its assessment, launch with human underwriting on that segment.

Use frameworks as structure, not as goals. The NIST AI RMF's four functions make a good template so every country writes to the same headings; ISO/IEC 42001 is a sensible year-two target for the management system.

**The trap.** Listing policies as controls. A supervisor asks for evidence that a control ran.

**Rubric criteria earned:** unregistered systems as the main risk, with a technical control; sampling with a consequence; a fallback for the underwriting model; frameworks used without a certification deadline.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how will you know the model works, and what would show it's being gamed?

**How to reason.** Pair each metric:

| Success metric | Guard metric |
|---|---|
| Inventory entries with an owner (100% by month 2) | Unregistered systems found after the amnesty |
| Median review time per tier | Sampling defect rate per country |
| High-risk systems with complete evidence (14 of 14 by month 5) | Open external assurance findings |
| Claims savings unblocked | Incidents in material systems after launch |

Speed and defects go on the same page, so a country can't buy speed with sloppy assessments.

**The trap.** Counting trainings, policies or meetings. Those measure activity, and the supervisor tests outcomes.

**Rubric criteria earned:** paired metrics; review time against service levels; unregistered systems tracked; no activity metrics.

### Communication

**The question it answers:** what does each audience hear, and how often?

**How to reason.** One line each:

- **The board:** every system owned by month 2, every high-risk system assured by month 5, €1.22M of new spend.
- **The supervisor:** one accountable executive, approval independent of builders, and an inventory kept by the gateway.
- **The CFO:** 4 hires inside the freeze, plus 4.5 existing people, named as the real cost.
- **The country CEOs:** a 3-week service level and a no-blame amnesty.
- **The claims programme:** cleared by month 3.

Cadence: monthly to the board risk committee until the review, quarterly after, and gate failures reported the week they happen.

**The trap.** Selling the model to countries as "light-touch". The sampling and pull-back rule are the point, and hiding them costs trust the first time they're used.

**Rubric criteria earned:** four or more audiences including the supervisor and countries; new spend and people kept apart; a cadence; failures reported.

## 8. The decisions that separate strong answers

**Sizing before structuring.** Weak answers draw an org chart. Strong answers count 306 items, show that 36,720 hours is absurd and that 5,211 hours still doesn't fit a central team, and let the arithmetic pick the model.

**Seeing that the queue made the shadow systems.** The 72 unknown systems aren't a discipline problem; they're what an 11-week wait produces. A model that lengthens the queue fails the inventory test in a year.

**Separating accountability from approval.** You can be the named executive without approving your own platform's work. Saying so unprompted is a strong level signal.

## 9. Common mistakes

- **Counting only the 212 in production.** The queue and new proposals add 94 items before month 6.
- **Recommending federated for speed.** It fails independent review, the one thing the supervisor will test.
- **No delay cost.** The queue already costs €3.17M a month; leaving that out makes the hub look expensive.
- **Treating certification as the goal.** ISO/IEC 42001 is a sensible target, but it isn't what the supervisor asked for in 6 months.
- **Controls that are documents.** A gateway rule produces evidence; a policy doesn't.
- **Inventing regulatory detail.** Quote what the letter asks for, and frame everything else as the group's policy.

## 10. Follow-ups an interviewer might ask

**The CFO refuses the 4 hires. What changes?**
Central capacity drops to 3,120 hours against 3,537 needed. Cut sampling from 25% to 15% (saving 223 hours), move low-tier checks to the country leads (579 hours), so central needs 3,537 − 223 − 579 = 2,735 hours, inside 3,120, and countries rise to 2,232 + 579 = 2,811 of their 2,925. Use the €480k for external assurance on more systems. Say plainly that lower sampling means less evidence of first-line quality.

**One of the three data science countries refuses to name a lead.**
Their systems go through central review at central service levels, and their CEO is told the 11-week wait is now their choice. Escalate to the CEO only if they also skip the amnesty, because then the inventory test is at risk.

**The supervisor asks why you, as builder-in-chief, are the accountable executive.**
Because accountability for the framework working should sit with the person who can change how AI is built. Approval of high-risk systems sits with the CRO's committee, so nothing you build is approved by you.

**Sampling finds 18% defects in one country at month 4.**
Pull that country's material tier back to central for the rest of the period, re-perform its assessments in priority order, and report it to the board risk committee that month. It is a trigger working, not a failure of the model.

**Should you pursue ISO/IEC 42001 certification?**
In year two, once the inventory, tiers and sampling have run for a year and produced evidence. Before month 6 it would compete for the same reviewer hours as the high-risk assessments.
