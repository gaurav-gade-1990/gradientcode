# Model Risk Sign-off Process: model answer

## 1. Situation

The question isn't whether generative AI needs validation; under the bank's policy it does. It's how much of the $21M can be signed off inside the validator hours left over after MRM closes its own exam finding, without weakening the independence that the finding is about. That leaves 500 hours, and the six use cases need 1,800 if each is validated from scratch.

| What | Number | What it forces |
|---|---|---|
| MRM capacity | 9 × 1,400 = 12,600 hours a year | Fixed: hiring has failed for 7 months |
| Committed | 31 × 160 = 4,960 overdue + 7,140 scheduled = 12,100 | The finding gets these hours first |
| Free | 12,600 − 12,100 = 500 bank-validator hours | Contractors stretch it at most to 1,000 total hours |
| From scratch, all six | 6 × 300 = 1,800 hours, so 900 bank-led | Doesn't fit |
| Value | $21.0M a year at full run rate, $1.75M a month | Each deferred use case has a price |

**How:**
1. Treat 500 bank-led hours as the budget, because policy requires a bank validator for at least half of each validation's hours.
2. Out of scope: using generative AI to make credit decisions, and changing the policy's definition of a model. The committee interprets it; you don't rewrite it.
3. The business-case values are first-line estimates; MRM and finance will discount them, and so should you.

**Decision.** Frame this as allocating 500 independent hours across six use cases, with the finding protected first.

**Trap.** Asking MRM to borrow from the periodic schedule "just this once". That is the backlog the examiners already flagged, and the board's commitment is to close it.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| Head of MRM | Independence, the finding closed, no precedent that weakens the policy | MRM writes the platform validation scope and the tier criteria; you supply evidence, not conclusions |
| Model risk committee | A defensible rule for what is a model, applied the same way every time | Tier criteria as yes/no questions; the committee decides each borderline case on the record |
| CEO and board | The $21M in the plan, and the finding closed | $19.4M of run rate validated in year one, one use case deferred, and the finding untouched |
| Chief Risk Officer | No new risk in credit decisions | Income extraction runs in parallel with human verification before it affects a decision |
| Chief Compliance Officer | Fair treatment and accurate customer notices | Segment testing on income extraction; adverse-action letters deferred to year two |
| Business owners (collections, servicing, marketing, credit) | Their use case first | A published order by value per validator hour, so the queue is a rule, not lobbying |
| Your platform team | One validation that unblocks many use cases | The platform package becomes the template for every later use case |
| Examiners | Evidence that policy is followed for new model types | A validation file per use case, plus a platform file each one references |

**The one idea to hold:** MRM's independence is the asset everyone is protecting, including you, so the process has to make validation cheaper by reusing evidence, never by skipping review.

## 3. Options

Four options, scored on bank-led hours against the 500 free, value enabled and exam risk.

| | A. Each from scratch | B. Platform once, then tiers | C. Exempt generative AI from model risk | D. Wait for the finding to close |
|---|---|---|---|---|
| Bank-led hours | 3 fit: 3 × 300 / 2 = 450 | Platform 400 + tier 1 2 × 160 + tier 2 2 × 80 + tier 3 20 = 900, so 450 bank-led | 0 | 0 |
| Use cases in year one | Income, collections, Q&A | All but adverse-action letters | All six | None |
| Run-rate value enabled | $7.9M + $4.2M + $3.1M = $15.2M | $21.0M − $1.6M = $19.4M | $21.0M | $0 |
| Exam risk | Low | Low, if the committee owns the tier rule | High: policy bypassed while a finding is open | Low |

**How:**
1. In B, adverse-action letters (tier 1, 80 bank-led hours) don't fit: 500 − 450 = 50 hours left.
2. Of the tier-1 cases, adverse-action letters return the least per validator hour ($1.6M for 80 bank-led hours, against $7.9M and $2.8M) and are the most sensitive, because they are notices to declined applicants.
3. C has the most value on paper and would read to examiners as the bank routing around its own policy during an open finding.

**Decision.** Shortlist B. A is the fallback if the committee won't accept the platform validation as evidence for individual use cases.

**Trap.** Treating the number of use cases as the measure. Validating the platform once is what turns 1,800 hours into 900.

## 4. Decision and Trade-offs

Recommend B: MRM validates the shared platform once, then each use case by tier; the model risk committee rules on what is a model; adverse-action letters move to year two.

| We give up | Why it's worth it |
|---|---|
| Adverse-action letters, $1.6M a year, for about 15 months | The hours don't fit, and they're the most sensitive use case |
| Speed on income extraction: a 2-month parallel run | It feeds credit decisions; parallel results are the evidence MRM needs |
| Changes to the platform become validated events | A version change can't silently alter five validated use cases |
| $112.5k of contractor spend | It doubles what the 500 free hours can cover |

**How:**
1. **Reversibility:** the platform validation and tier rule can be tightened at any time; a use case can be moved up a tier. Deferring adverse-action letters costs value, not options.
2. **Revisit at month 6 and month 12** if:
   - MRM's overdue count isn't falling on plan (the finding comes first, and generative AI work pauses);
   - more than 1 in 10 sampled outputs fails its tier's acceptance test;
   - a validator requisition is filled, which adds about 1,400 hours a year and brings adverse-action letters forward.

**Decision.** B, because reusing validated evidence is the only way to fit five use cases into 500 hours without touching the finding or MRM's independence.

**Trap.** Writing the tier rule yourself and asking MRM to accept it. If the first line decides what counts as a model, the examiners will see the first line marking its own homework.

## 5. Economics

Three years of value against the same 500 free hours a year. Launch months are assumed from the hours and the parallel run; value counts from the month a use case goes live.

| | A. From scratch | B. Platform and tiers |
|---|---|---|
| Year-one launches (assumed) | Q&A month 5, collections month 6, income month 11 | Q&A month 4; collections and marketing month 5; complaints month 7; income month 10 |
| Year one | $3.1M × 8/12 + $4.2M × 7/12 + $7.9M × 2/12 = $5.83M | $3.1M × 9/12 + $5.6M × 8/12 + $2.8M × 6/12 + $7.9M × 3/12 = $9.43M |
| Year two | $15.2M + remaining three from month 16: $5.8M × 9/12 = $19.55M | $19.4M + adverse-action from month 16: $1.6M × 9/12 = $20.6M |
| Year three | $21.0M | $21.0M |
| **3-year value** | **$46.38M** | **$51.03M** |
| Contractors (new spend) | 450 h × $250 = $112.5k | 450 h × $250 = $112.5k |

**How:**
1. **Model spend:** $55k × 12 = $660k a year at full volume, the same for any option that ships, so it doesn't separate them.
2. **People already on payroll:** your first-line testing, 5 × 120 = 600 hours in year one, and the platform team of 5.
3. **Opportunity cost:** each month adverse-action letters wait costs $1.6M / 12 = $133k; a filled requisition would bring them forward.
4. **What isn't counted:** the cost of C going wrong in an exam. It isn't a number you can put in a plan, and that's the point.

**Decision.** B delivers $4.65M more over three years for the same contractor spend, and $3.60M more in year one.

**Trap.** Comparing on value alone and picking C. Its extra value is real; its cost arrives as a second finding about the same function.

## 6. Org and Ownership

Three lines, with the boundary between your team and MRM written down.

| Role | Who | Owns |
|---|---|---|
| Accountable for use and first-line evidence | You | Development documentation, testing, monitoring, the platform |
| Use-case owner | Each business head | Business case, human review procedure, outcomes |
| Independent validation | Head of MRM | Platform validation scope, each use case's validation, findings |
| What counts as a model | Model risk committee | Tier ruling for each use case, minuted |
| Fair treatment | Chief Compliance Officer | Segment testing on income extraction; adverse-action content |
| Third line | Internal audit | Reviews the new process within a year |

**How:**
1. Your team never edits a validation report; disagreements go to the committee.
2. Every use case has a named business owner who signs the human review procedure.

**Decision.** MRM scopes its own platform validation, so the evidence you produce answers their questions, not yours.

**Trap.** A "joint" AI validation team. Joint means not independent.

## 7. Plan and Milestones

Platform first, then the use cases in value-per-hour order, with income extraction proving itself in parallel.

| Month | Milestone | Gate |
|---|---|---|
| 1 | Committee approves the tier criteria; MRM scopes the platform validation | Tier ruling for all six, minuted |
| 1–3 | Platform validation (400 h, half contractors) | **Gate 1:** platform validated with no high-severity findings |
| 4 | Staff policy Q&A live (tier 3) | 20-hour sample check passed |
| 5 | Collections summaries and marketing drafts live (tier 2) | Reviewer override rate within agreed range |
| 7 | Complaint classification live (tier 1) | Agreement with second-review labels at the agreed threshold |
| 6–9 | Income extraction parallel run, no effect on decisions | **Gate 2:** accuracy and segment gaps within tolerance |
| 10 | Income extraction affects decisions, with human verification near cut-offs | — |
| 12 | Revisit; MRM's overdue validations closed | Finding closed first |
| 16 | Adverse-action letters, if hours allow | Tier 1 validation |

**Decision.** Run income extraction in parallel for two months before it touches a decision, because parallel results are both the validation evidence and the fair-lending test.

**Trap.** Launching the highest-value use case first. It's the riskiest, and it needs the platform evidence everything else builds on.

## 8. Risk and Governance

The risks are a wrong number in a credit decision, a silent model change, and the process itself becoming a shortcut.

| Risk | Control |
|---|---|
| Wrong extracted income changes a decision | Parallel run; human verification when the extracted figure moves an applicant across a decision cut-off |
| Errors fall unevenly across applicant groups | Segment testing by document type and applicant group, reviewed by compliance before Gate 2 |
| Provider changes the model version | Versions pinned; a change re-runs the validated eval suite and MRM reviews the differences: 24 h each, 2 a year (assumed), 24 bank-led hours, inside the 50 spare |
| Tier 3 tools drift into customer use | Quarterly attestation; any customer-facing use triggers re-tiering |
| Human review becomes a rubber stamp | Override and edit rates monitored; a reviewer who never edits is sampled |
| Generative AI work crowds out the finding | Overdue count reported monthly; generative AI validations pause if it slips |

**How:**
1. Every validated use case has acceptance thresholds in its validation report, and monitoring alerts when they're breached.
2. The platform file and each use-case file reference each other, so an examiner can follow the evidence in either direction.

**Decision.** Model-version changes get a defined, short change-validation path, because without one the first provider update either stops five use cases or bypasses MRM.

**Trap.** Calling human review a control without measuring it. A reviewer who accepts 100% of drafts is not reviewing.

## 9. Metrics

Each delivery metric is paired with a guard on what it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| Run-rate value validated | $19.4M by month 10 | MRM overdue validations: 31 to 0 by month 12 |
| Validation cycle time per tier | Tier 3 two weeks, tier 2 six weeks, tier 1 three months | Findings per validation, by severity |
| Income extraction accuracy | At or above the human baseline in parallel | Largest gap between applicant segments |
| Reviewer override rate on tier 2 | Within the range agreed at validation | Share of reviewers with zero edits |

**Decision.** The overdue count is the guard on every generative AI number, reported on the same page, because the finding is the commitment the board made first.

**Trap.** Reporting "use cases live" as the headline. Five live use cases with an open finding is a worse outcome than three with it closed.

## 10. Communication

Each audience gets the number it will be held to.

| Audience | One line |
|---|---|
| Model risk committee | "Validate the platform once, then each use case by tier; you rule on what is a model, and the overdue validations keep their hours." |
| Board | "$19.4M of the $21M validated in year one, the finding closed on schedule, adverse-action letters in year two." |
| Head of MRM | "You scope the platform validation and own every conclusion; we bring evidence and $112.5k of contractor hours." |
| Business owners | "Order is value per validator hour; yours is month 4, 5, 7 or 10." |
| Examiners | "Every use case has its own validation file, built on a validated platform, under the existing policy." |

**How:**
1. Monthly to the model risk committee: hours used against 500, overdue count, gates.
2. Quarterly to the board risk committee with the finding's status first.

**Decision.** Lead every update with the finding's status, so nobody can say generative AI was bought with the exam commitment.

**Trap.** Promising business owners dates before the committee has ruled on tiers. A re-tiered use case misses its date, and the promise is what people remember.
