## 1. What the problem is really asking

On the surface this is a question about how to validate LLMs. Underneath, it's a resource-allocation question inside a regulatory commitment. The bank has 500 spare validator hours, a board promise to examiners that eats everything else, and six use cases that would need 1,800 hours if handled the old way. The interviewer wants to see whether you protect the finding first, find a way to make validation cheaper without making it weaker, and accept deferring something.

Three facts in the brief carry the case:

1. **The finding is on MRM's own backlog.** Any plan that borrows from the overdue validations "temporarily" is the plan that gets the bank a second finding about the same team.
2. **The 50% rule halves what contractors can do.** Contractors are cheap and available, but a validation counts only if a bank validator does at least half of it. So 500 free bank hours cover at most 1,000 total hours.
3. **Most of the cost is shared.** Five of the six use cases run on the same model, guardrails and evaluation harness. Validating that once and reusing the evidence is what turns 1,800 hours into 900.

A strong answer also gets the politics right: MRM must scope its own platform validation, and the model risk committee, not you, decides which use cases count as models.

## 2. The numbers that drive the decision

**Validator hours.**
- Capacity: 9 × 1,400 = **12,600 hours a year**.
- Overdue: 31 × 160 = **4,960 hours**.
- Committed: 4,960 + 7,140 = **12,100 hours**.
- Free: 12,600 − 12,100 = **500 bank-validator hours**.

**From scratch.** 6 × 300 = **1,800 hours**, of which at least 900 bank-led. Only 3 fit: 3 × 300 / 2 = 450.

**Platform and tiers.**
- Platform: 400 hours.
- Tier 1 (feeds a credit decision or a regulatory report): complaint classification, income extraction, adverse-action letters, 160 hours each.
- Tier 2 (a person reviews every output first): collections summaries, marketing drafts, 80 hours each.
- Tier 3 (internal tool the committee agrees isn't a model): policy Q&A, 20 hours.
- All six: 400 + 3 × 160 + 2 × 80 + 20 = **1,060 hours**, so 530 bank-led. Doesn't fit.
- Without adverse-action letters: 1,060 − 160 = **900 hours**, so 450 bank-led. Fits, with 50 to spare.

**Value per bank-led hour (tier 1).** Income extraction $7.9M / 80, complaints $2.8M / 80, adverse-action $1.6M / 80. Adverse-action letters return the least and are the most sensitive.

**Value enabled in year one.** From scratch: $7.9M + $4.2M + $3.1M = **$15.2M**. Platform and tiers: $21.0M − $1.6M = **$19.4M**.

**Three-year value (launch months assumed).**
- From scratch: year one $5.83M, year two $19.55M, year three $21.0M, so **$46.38M**.
- Platform and tiers: year one $9.43M, year two $20.6M, year three $21.0M, so **$51.03M**, which is $4.65M more.

**Spend.** Contractors 450 × $250 = **$112.5k** either way. Model API $55k × 12 = **$660k a year** at full volume.

**Model-version changes.** 2 a year × 24 hours (assumed) = 48 hours, so 24 bank-led, inside the 50 spare.

## 3. How to spend your time

Sixty minutes, about twelve per pillar.

| Minutes | What you do |
|---|---|
| 0–7 | Read the brief. Write down 500 free, the 50% rule, 1,800 vs 900, 450 bank-led, $19.4M. Circle "the finding is on MRM's own backlog" and "the committee agrees is not a model". |
| 7–17 | **Pillar A.** The hour budget, out-of-scope items, and stakeholders with MRM's independence at the centre. |
| 17–35 | **Pillar B.** Four options with hours, the call and what's deferred, and three-year value. |
| 35–50 | **Pillar C.** The line between first line and MRM, the sequence with a parallel run, and the controls including version changes. |
| 50–57 | **Pillar D.** Metrics guarded by the overdue count, and one line per audience. |
| 57–60 | Check every number is derived or labelled. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what is being decided, and how many hours are really available?

**How to reason.** Derive the budget before anything else: 12,600 hours of capacity, 12,100 committed, 500 free. Then apply the policy: bank validators do at least half of every validation, so 500 bank hours cover 1,000 total at most. Show that six from-scratch validations (1,800 hours) don't fit. State that the finding's hours are untouchable. Name what's out of scope: generative AI making credit decisions, and rewriting the policy's definition of a model. Flag that $21M is a first-line estimate.

**The trap.** Proposing that MRM "flex" the periodic schedule. That schedule is the commitment the board made to examiners.

**Rubric criteria earned:** 500 free hours; the 50% rule applied; from-scratch shown not to fit; the finding protected and scope stated.

### Stakeholders

**The question it answers:** who has a stake, and how do you bring them along?

**How to reason.** The head of MRM is the person whose agreement makes or breaks this, and what they're protecting is independence. So hand them control: MRM scopes the platform validation and writes the acceptance thresholds; you supply evidence. The model risk committee wants a rule it can apply consistently; give it tier criteria as yes/no questions and let it rule, on the record, on each case. Compliance cares about fair treatment, which points at income extraction and adverse-action letters. Business owners each want to go first; a published order by value per validator hour turns lobbying into a rule. And remember the examiners, who will read the files.

The one idea to hold: MRM's independence is the asset everyone is protecting, including you, so validation gets cheaper by reusing evidence, not by skipping review.

**The trap.** Casting MRM as the blocker. The finding makes them your most important ally: their credibility is the bank's.

**Rubric criteria earned:** MRM, the committee, the board, compliance and business owners; MRM scopes its own work; examiners included; the one idea.

## 5. Pillar B: Decide

### Options

**The question it answers:** what are the options, and how many use cases fit under each?

**How to reason.** Four options on one table:

- **From scratch.** 300 hours each; 3 fit (450 bank-led). Pick by value: income, collections, Q&A, so $15.2M.
- **Platform once, then tiers.** 900 hours for five use cases, 450 bank-led; adverse-action letters don't fit. $19.4M.
- **Exempt generative AI from model risk.** All six, fast, $21M on paper, and examiners see a bank routing around its own policy during an open finding.
- **Wait for the finding to close.** Zero value in year one.

Then choose what to defer with a rule: value per bank-led hour and sensitivity. Adverse-action letters are lowest on value ($1.6M for 80 hours) and highest on sensitivity, since they're notices to declined applicants.

**The trap.** Counting use cases instead of hours. The platform validation is what makes the arithmetic work.

**Rubric criteria earned:** exempt and wait options included; bank-led hours for each; five fit and the sixth doesn't; deferral chosen by rule.

### Decision and Trade-offs

**The question it answers:** what do you recommend, what's given up, and what would change it?

**How to reason.** Recommend platform and tiers, with the committee ruling on tiers. The give-ups:

- adverse-action letters, $1.6M a year, for about 15 months;
- a 2-month parallel run on income extraction;
- platform changes becoming validated events;
- $112.5k of contractor spend.

It's reversible in the right direction: a use case can always move to a higher tier, and the tier rule can tighten. Triggers to revisit at month 6 and 12: the overdue count falling behind plan (generative AI pauses), more than 1 in 10 sampled outputs failing a tier test, or a filled requisition (1,400 more hours a year) bringing adverse-action letters forward.

**The trap.** Writing the tier rule yourself. The first line deciding what counts as a model is the first line marking its own homework.

**Rubric criteria earned:** the committee rules; deferred use case named and valued; reversibility; triggers including the overdue count.

### Economics

**The question it answers:** what value does each option deliver over three years, and at what cost?

**How to reason.** Use the same 500 free hours a year for both options and label the launch months as assumptions. Platform and tiers: Q&A month 4, collections and marketing month 5, complaints month 7, income month 10 after its parallel run. That gives $9.43M in year one. From scratch launches its three a month later each (no shared evidence; assumed), giving $5.83M. Over three years: $51.03M against $46.38M. Contractor spend is the same, $112.5k. Model spend ($660k a year) is the same for anything that ships, so say so and move on. First-line testing (600 hours) and the platform team are already on payroll. The deferral costs $133k a month.

**The trap.** Picking the exempt option on value. Its cost is a second finding, and that isn't a line in a plan.

**Rubric criteria earned:** three-year value with labelled launch months; contractors as new spend and first-line hours as payroll; model spend explained; deferral priced.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** where's the line between your team and MRM?

**How to reason.** Three lines, written down:

- **You:** development evidence, testing, monitoring and the platform.
- **Business owners:** the use case, its human review procedure and its outcomes.
- **MRM:** the validation scope and every conclusion.
- **Model risk committee:** each tier ruling, minuted.
- **Compliance:** segment testing on income extraction.
- **Internal audit:** the new process within a year.

Your team never edits a validation report.

**The trap.** A joint AI validation team. It sounds collaborative; it ends independence.

**Rubric criteria earned:** conclusions with MRM; business owners named; compliance owns fair-treatment testing; no joint team.

### Plan and Milestones

**The question it answers:** in what order, and where are the gates?

**How to reason.** Platform first (months 1–3), because every later validation references it. Then in order of risk and readiness: Q&A (tier 3) at month 4, collections and marketing (tier 2) at month 5, complaint classification at month 7. Income extraction runs in parallel from month 6 to 9, with no effect on decisions, and goes live at month 10 only after Gate 2: accuracy and segment gaps within tolerance. The finding closes at month 12; adverse-action letters follow at month 16 if hours allow.

**The trap.** Highest value first. Income extraction is also the riskiest, and it needs the platform evidence.

**Rubric criteria earned:** platform first; a parallel run; measurable gates; the finding ahead of the deferred case.

### Risk and Governance

**The question it answers:** what could go wrong, and how are model changes handled?

**How to reason.** Three risk areas:

- **Credit decisions.** A wrong extracted income can change a decision. Add human verification when the figure moves an applicant across a cut-off, and test errors by document type and applicant group before go-live.
- **Silent model changes.** A provider version change could alter five validated use cases at once. Pin versions and define a change-validation path: re-run the validated evals, MRM reviews the differences, 24 hours each and 2 a year (assumed). That's 24 bank-led hours, inside the 50 spare.
- **The process itself.** Measure human review, since a reviewer who never edits isn't reviewing. Pause generative AI validations if the overdue count slips.

**The trap.** Treating human review as a control without evidence it happens.

**Rubric criteria earned:** segment testing; a change-validation path that fits the budget; measured human review; the pause rule.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how do you know it works, and what would it hide?

**How to reason.** Pair them:

| Success metric | Guard metric |
|---|---|
| Run-rate value validated ($19.4M by month 10) | Overdue validations, 31 to 0 by month 12 |
| Cycle time per tier | Findings per validation by severity |
| Income extraction accuracy vs human baseline | Largest gap between applicant segments |
| Reviewer override rate | Share of reviewers who never edit |

The overdue count sits next to every generative AI number.

**The trap.** "Use cases live" as the headline. Five live with an open finding is worse than three live with it closed.

**Rubric criteria earned:** paired metrics; the overdue guard; segment gap; cycle times per tier.

### Communication

**The question it answers:** what does each audience hear?

**How to reason.** One line each:

- **The committee:** the process, and that it decides tiers.
- **The board:** $19.4M validated in year one, the finding closed on time, one use case deferred.
- **MRM:** they scope and conclude; you bring evidence and contractor hours.
- **Business owners:** their month, and why.
- **Examiners:** a file per use case on a validated platform, under the existing policy.

Monthly to the committee with hours against 500; quarterly to the board with the finding first.

**The trap.** Giving business owners dates before tier rulings. A re-tiered use case slips, and the promise is what's remembered.

**Rubric criteria earned:** four or more audiences; finding status first; cadence; no premature dates.

## 8. The decisions that separate strong answers

**Seeing the 50% rule.** Weak answers solve capacity with contractors. Strong answers notice the policy caps contractors at half of each validation, so the real budget is 500 bank hours.

**Reusing evidence without reducing scrutiny.** The platform validation is the idea that makes the case. It's cheaper because shared components are reviewed once, not because anything is reviewed less.

**Giving away the tier decision.** Letting the committee decide what counts as a model costs you control and buys the whole process its credibility.

## 9. Common mistakes

- **Borrowing from the overdue work.** It risks the commitment the board made to examiners.
- **Exempting generative AI.** Fast and valuable on paper; a second finding in practice.
- **Ignoring model-version changes.** The first provider update would otherwise stop five use cases or bypass MRM.
- **No parallel run for income extraction.** It's the one use case that touches credit decisions.
- **Deferring by politics.** Use value per validator hour and sensitivity, and publish the rule.
- **Inventing regulation.** Talk about the bank's policy and SR 11-7-style guidance in general terms, not specific rules you can't cite.

## 10. Follow-ups an interviewer might ask

**MRM refuses to accept platform evidence for individual validations.**
Fall back to from scratch: three use cases, $15.2M. Ask MRM to pilot the platform approach on one tier-2 case in year two, and let the result decide.

**A requisition is filled at month 5. What changes?**
Seven months × about 117 hours a month (1,400 / 12) is roughly 817 hours. After the finding's work, adverse-action letters (80 bank-led hours) come forward to year one.

**The CEO asks why policy Q&A needs any review at all.**
Because "not a model" is the committee's ruling, and a 20-hour sample check is what makes that ruling defensible. If staff start quoting it to customers, it gets re-tiered.

**The provider announces it will retire your pinned model in 90 days.**
Run the change-validation path: re-run the validated evals on the new version, MRM reviews the differences (24 hours), and use cases whose results move outside their thresholds go back to a full tier validation.

**Could you use an LLM to help MRM validate faster?**
Possibly for drafting test documentation, but only as a tool MRM chooses and controls. Proposing it from the first line looks like the developer helping the reviewer.
