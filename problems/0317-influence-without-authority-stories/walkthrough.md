## 1. What the problem is really asking

"Tell me about a time you got another org to change direction without authority" sounds like a question about persuasion. Underneath, it's a question about level. The interviewer wants to see how big a thing you can move when nobody has to listen to you: whose roadmap changed, how much money was involved, what you paid to make it happen, and whether the change lasted after you left the room.

Three things separate a leadership answer from a pleasant anecdote:

1. **The missing authority has to be real.** If your manager could have ordered the change, it's a delegation story. Say plainly that the other org reported to someone else, and that escalation wasn't available or wasn't wise.
2. **Someone has to give something up, and part of it should be you.** Influence without a trade is just a request that happened to be granted. The strongest version of this story has you putting your own roadmap on the table.
3. **The other org has to own the result.** If you end up running their system for them, you've built a workaround, not changed their direction.

The background in the brief gives you all of this: a grocery platform losing money to rejected substitutions, a cause in another VP's data, a board-level date in the way, and a 5-week planning window. Use your own story if you have one; the framework is the same.

## 2. The numbers that drive the decision

A story bank answer still needs numbers, and they have to be derived, not remembered vaguely. Work these out first.

**The size of the problem.**
- Substitutions: 2.5M orders × 40 items × 8% = **8M a month**.
- Rejections: 8M × 22% = **1.76M a month**, at $1.50 each = **$2.64M a month**.
- Caused by catalog attributes: 1.76M × 45% = **792k a month**, or $1.19M a month, **$14.26M a year**.
- Addressable at the pilot's 60%: 792k × 60% = 475.2k a month × $1.50 = **$712.8k a month, $8.55M a year**.

**The other org's pain, in their terms.**
- Data-ops tickets: 2,000 × 20 minutes = **667 hours a month**, which is 79% of 6 people × 140 assumed hours.
- The portal's new SKUs: 90,000 × 18% = **16,200 bad listings** arriving with the board-level launch.

**What the change costs.**
- Engineers: 7 for a quarter = 1.75 engineer-years × $240k assumed = **$420k**, already on payroll.
- Your give-up: $360M × 0.6% = $2.16M a year of personalization lift, delayed one quarter = **$540k** (assumed linear).
- Catalog's give-up: $18M × 15% × 120/300 = $1.08M a year, 6 weeks late = **$124.6k**.
- Model cost per SKU: Haiku $0.0003 plus 10% of Sonnet's $0.006 = **$0.0009**; the whole 1.2M-SKU backfill is **$1,080**.
- Total, with review: about **$1.17M**, paid back in **1.6 months** at the pilot rate.

The cheap model bill is a point in itself: the barrier was never money. It was people, a date and ownership.

## 3. How to spend your time

Forty-five minutes. In a real interview you'd have 5–8 minutes, so the last part of the practice is compressing the story.

| Minutes | What you do |
|---|---|
| 0–5 | Pick your story (or the brief's). Write down the one number for scale, the number for the problem, and what you gave up. |
| 5–12 | **Pillar A.** Make the missing authority explicit. Build the stakeholder table, starting with the decision-maker and who you won over first. |
| 12–24 | **Pillar B.** The routes you considered, including escalation; the specific ask; your give-up; the economics. |
| 24–34 | **Pillar C.** Ownership and handover, the sequence of influence steps, and the relationship risk. |
| 34–42 | **Pillar D.** The measured result with a guard, then the 2-minute STAR version, said out loud and timed. |
| 42–45 | Check every "we" in the Action. Turn it into "I" or name who did it. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what was the setting, what was your role, and why couldn't you just tell them?

**How to reason.** Open with three facts: the company type with one number for scale, your role, and the org that had to change and who it reported to. Then put the problem in money: 8M substitutions, 1.76M rejections, 792k caused by catalog data, $14.26M a year. Add the window: planning locked in 5 weeks, and missing it meant two quarters. Say what was out of scope. Here, the substitution model wasn't the main cause, and retuning it would have hidden the data problem.

Size the story to the role. A principal story crosses an org boundary and moves part of another VP's roadmap. A team-level story about convincing a peer to change a library is a senior engineer story, however well told.

**The trap.** A situation with no number, or one where the "other org" was really your own team.

**Rubric criteria earned:** company type, role and scale in three sentences; no reporting line stated; the problem in money with arithmetic; a deadline.

### Stakeholders

**The question it answers:** who had to change, what were they protecting, and how did you bring each one along?

**How to reason.** Start with the decision-maker and what they were protecting: the VP Catalog had a board-level date and had said no twice. Then name the people below them you won over first: the staff engineer, the EM and the data-ops lead, who felt the 667 hours a month of hand fixes. Include your own director, because they paid with 3 engineers and a delayed launch. Add Finance (whose $1.50 you used) and the food safety lead (who owned the allergen risk).

The one idea that ties it together: the other org had to win more than you did, so you gave away ownership and credit and paid part of the cost.

**The trap.** A table of people who "were aligned". Influence only shows when someone was reluctant and you changed that.

**Rubric criteria earned:** the decision-maker and what they protected; someone won over first; your manager's give-up; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** what routes to the change did you consider, and why did most fail?

**How to reason.** There were four:

- **Escalate to the CTO.** Your VP wouldn't, and an ordered fix gets compliance, not ownership.
- **Fix it in Search yourself.** Fast and fully in your control, but it creates a second copy of the truth. The portal's 90,000 new SKUs flow around it, and Catalog's tickets don't change.
- **Co-fund a Catalog quarter.** Catalog owns it, it covers the portal, and it cuts their tickets. But it needs them to agree.
- **Wait for the next planning cycle.** Costs 6 × $712.8k = $4.28M of avoidable rejections.

Put them on one table with the same rows: time to effect, who owns the data, whether it fixes the portal's SKUs, cost to the relationship.

**The trap.** Never mentioning escalation. The interviewer will ask, so answer it first.

**Rubric criteria earned:** escalation and why not; the do-it-yourself route and its long-term cost; waiting, priced; one comparable table.

### Decision and Trade-offs

**The question it answers:** what exactly did you ask for, and what did you give up?

**How to reason.** Make the ask specific: 4 Catalog engineers and 3 of yours for one quarter; extraction in Catalog's ingest path; a backfill of 1.2M SKUs; every portal SKU routed through it. Bulk upload slips 6 weeks, and portal v1 keeps its date. Then list your give-ups: personalization slips a quarter, 3 of 12 engineers are lent, the credit goes to the VP Catalog, and you lose a fix you would have fully controlled.

Make it easy to stop. A week-6 checkpoint (precision of 97% or more, portal on track) means the VP Catalog risks very little by saying yes.

**The trap.** "We decided." The rubric checks for "I".

**Rubric criteria earned:** a sized ask; your own give-up; a checkpoint with a condition; first person.

### Economics

**The question it answers:** what was at stake, and what did the change cost?

**How to reason.** Three numbers: at stake ($14.26M a year), addressable ($8.55M a year at the pilot's rate), and the cost of the quarter (about $1.17M). Split the cost the way a CFO would: $82.9k of new spend (review and model), $420k of payroll, and $664.6k of opportunity cost (your delayed launch and Catalog's slip). Payback is 1.6 months.

Label the assumptions: $240k per engineer, a linear value for delays, 50,000 allergen changes to review.

**The trap.** Leaving out your own give-up. The $540k you paid is the most persuasive number in the story.

**Rubric criteria earned:** value derived from volume and unit cost; your give-up counted; new spend separate from payroll; assumptions labelled.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owned the work, during the quarter and after?

**How to reason.** The VP Catalog was accountable, with attribute quality as their OKR. The Catalog EM ran delivery with 4 of their engineers and 3 of yours. You were technical lead for one quarter, with no reporting line. Their data-ops lead owned the review queue. Two written things made it last: a data contract (95% or better completeness on top SKUs, with Search as a named consumer) and a dated handover at week 13.

**The trap.** Offering to keep running it. That turns their change into your workaround.

**Rubric criteria earned:** the other org owns the result after a dated handover; your role described; a written agreement that outlasts you.

### Plan and Milestones

**The question it answers:** what did you do, in what order, before and after they agreed?

**How to reason.** Most of the influence happened in the 5 weeks before planning:

1. A sample of 2,000 rejections.
2. One-to-ones with Catalog's staff engineer and data-ops lead.
3. A two-week pilot with their data-ops lead reviewing.
4. A one-page plan co-written with their EM.
5. Your director's sign-off on the trade.
6. Only then, a one-to-one pre-read with the VP.

The quarter itself had one checkpoint at week 6 and a handover at week 13.

**The trap.** Pitching the VP first. They'll ask their team, and the team will defend the roadmap.

**Rubric criteria earned:** influence steps before the meeting; who saw it first and why; a checkpoint with a condition; a timeline.

### Risk and Governance

**The question it answers:** what could have gone wrong, for the other org, for customers and for the relationship?

**How to reason.** Cover three kinds of risk:

- **Catalog's date.** The week-6 checkpoint returns your engineers if the portal is at risk.
- **Customers.** At an assumed 98% precision, 1.02M auto-applied SKUs would carry about 20,400 wrong attributes, against 216k wrong today. That is better, but not zero. Allergen and dietary changes never auto-apply, and that rule lives in code, signed off by food safety.
- **The relationship.** The VP saw nothing new at planning, and your own team heard about the slip first.

**The trap.** Listing only project risks. In an influence story, trust is the thing that breaks.

**Rubric criteria earned:** the other org's commitment protected; a customer risk and its control; a relationship risk; one risk quantified.

## 7. Pillar D: Land

### Metrics

**The question it answers:** what was the measured result, and what showed nothing else broke?

**How to reason.** Give before-and-after numbers, labelled as this story's outcome:

- Wrong attributes fell from 18% to 5%.
- Attribute-driven rejections fell 55%, below the pilot's 60%: 435.6k fewer a month, or $7.84M a year.
- Overall rejections fell from 22% to 16.6%.
- Data-ops tickets fell from 2,000 to 700 a month.

Pair each one with a guard: audited precision, time to list a new SKU, and the portal date, which was hit. Lead with the other org's numbers.

**The trap.** Claiming the whole $14.26M opportunity as the result.

**Rubric criteria earned:** before and after; a guard; a result that matters to the other org; measured, not theoretical.

### Communication

**The question it answers:** what did each audience hear, and how do you tell it in two minutes?

**How to reason.** During the work, each audience got one line in its own terms. The VP heard about the portal's 16,200 bad listings. Your director heard $540k against $8.55M. Your team heard their new date. Finance heard that savings would be measured at their $1.50.

In the interview, use STAR:

- **Situation** (2 sentences).
- **Task** (1 sentence).
- **Action:** the longest part, all in "I".
- **Result:** with numbers.
- **What you'd do differently.** Make it a real gap. Here, the data contract came in week 13, and a supplier feed regressed in week 9 without anything catching it.

**The trap.** "I'd have started sooner" as the reflection. It's a boast, not a lesson.

**Rubric criteria earned:** STAR in about two minutes; one line per audience; a specific "differently"; Action longest and first person.

## 8. The decisions that separate strong answers

**Reframing the problem in the other org's terms.** "Your rejections cost $14M" is your problem. "Your portal imports 16,200 bad listings, and your data-ops team spends 79% of its time on tickets" is theirs. Strong answers show the reframe as a deliberate move.

**Paying first.** Lending 3 engineers and slipping your own launch turned a request into a trade. Interviewers at principal level and above listen for what the candidate gave up.

**Giving away ownership.** The VP Catalog presented the plan and owned the OKR. That's why the change outlasted the quarter.

**Building a coalition below the decision-maker.** The VP's own engineers helped write the plan before the VP saw it.

## 9. Common mistakes

- **No real lack of authority.** Your manager's manager could have ordered it.
- **"We" throughout.** The interviewer can't tell what you did.
- **No give-up.** Everyone was aligned and nobody paid.
- **The theoretical result.** Quoting the opportunity instead of the measured change.
- **Escalation as the climax.** "So I took it to the CTO" ends an influence story badly.
- **No reflection, or a fake one.**
- **Too much tool detail.** The extraction prompt doesn't matter; the trade and the ownership do.

## 10. Follow-ups an interviewer might ask

**What if the VP Catalog had said no a third time?**
I'd have shipped the Search-side fix for the top 50,000 SKUs as a stopgap. I'd have told Catalog it was temporary, and taken the data and the ticket count back to the next planning cycle. Influence can fail; the strong answer has a fallback that doesn't burn the relationship.

**Why didn't you escalate?**
My VP wouldn't, and even if they had, an ordered fix gets compliance. Catalog would have done the minimum and left the portal's SKUs on the old path.

**How did you know the 45% was right?**
It came from a sample of 2,000 rejections. The 95% margin of error at 45% is about ±2.2 points, which was tight enough for a planning decision.

**What did your team think about losing personalization for a quarter?**
Two engineers pushed back. I told them before anyone else knew, put the new date in writing, and picked volunteers for the Catalog work.

**How would this story change at director level?**
The ask would be a budget line or a headcount transfer, not three engineers for a quarter. The give-up would be one of your org's commitments to the exec team.
