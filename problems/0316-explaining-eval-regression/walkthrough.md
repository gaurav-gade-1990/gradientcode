## 1. What the problem is really asking

On the surface this is a model-quality incident: recall fell 10 points. Underneath, it's a translation problem. Five executives are reacting to three different numbers (recall down, accuracy up, "1 in 10 more frauds missed") and none of them can tell which one matters. The interviewer wants to see whether you can explain precision, recall and sample size in plain words, put real dollars on the uncertainty, and still act before you're certain.

Three facts in the brief carry the case:

1. **The two reports are both true.** Accuracy counts every claim, and 96% of claims are honest, so a model that flags fewer claims looks more "accurate" even while it catches fewer frauds. Explaining that one sentence well defuses half the meeting.
2. **The gap is 4 claims.** The versions were tested on 40 frauds. They disagree on 8, and the old one wins 6–2. That isn't proof of anything yet, and the range it allows runs from a gain to a large loss.
3. **The obvious fix is illegal, but there's spare capacity.** Rollback breaks the privacy rule. SIU, though, is working 2,300 flags against a capacity of 3,000, so a lower threshold can recover part of the gap from today at almost no cost.

## 2. The numbers that drive the decision

Work these out first, slowly. This case is graded on getting them right and saying them simply.

**Volume and money.**
- Frauds a month: 50,000 × 4% = **2,000**.
- One recall point is 1% of 2,000 = 20 frauds, × $6,500 = **$130k a month**.
- One fraud out of 40 in the test is 2.5 points, about **$325k a month**.

**Precision, recall and accuracy for each version.**

| | Flags | Frauds caught | Recall | Precision | False alarms | Accuracy |
|---|---|---|---|---|---|---|
| Old | 60 | 33 | 82.5% | 55% | 27 | (33 + 933) / 1,000 = 96.6% |
| Redacted | 46 | 29 | 72.5% | 63% | 17 | (29 + 943) / 1,000 = 97.2% |
| Lower threshold | 58 | 31 | 77.5% | 53% | 27 | 96.4% |

- Recall is "of the 40 frauds, how many did we flag". Precision is "of the claims we sent SIU, how many were fraud". Accuracy is "how many of all 1,000 did we get right", and flagging nothing scores 960 / 1,000 = **96%**.
- Honest claims left alone are 960 minus the false alarms: 933 and 943.

**How sure are we?**
- 95% Wilson ranges on recall: old 33/40 → **68%–91%**; redacted 29/40 → **57%–84%**; lower threshold 31/40 → **62%–88%**. Each is about ±12 points wide, because 40 is a small number.
- The gap, treating the runs as independent (conservative): from an **8-point gain to a 28-point loss**. In money, 8 × $130k = **$1.1M a month gained** to 28 × $130k = **$3.6M a month lost**.
- The disagreement test: 8 frauds where the versions disagree. A fair coin gives a 6–2 split or worse in either direction 2 × (1 + 8 + 28) / 256 = **29%** of the time. That's the plain-language version of "not significant".

**What knowing would cost.**
- For ±5 points at about 75% recall: 1.96² × 0.75 × 0.25 / 0.05² = **288 frauds**.
- Random audit: 288 / 4% = **7,200 claims**, at 1,000 a quarter that's about 7 quarters, or 7,200 × $45 (assumed) = **$324k** of contract auditors.
- Replay 400 of the 1,200 historical frauds through both versions: ±1.96 × √(0.75 × 0.25 / 400) = **±4 points**. Model cost per claim is 20,000 × $2/1M + 400 × $10/1M = $0.044, so 800 runs cost **$35**.

**Production effect.**
- Flags a month: old 6% × 50,000 = **3,000**; redacted 4.6% = **2,300**; lower threshold 5.8% = **2,900**, inside SIU's 3,000.
- Frauds caught: 2,000 × recall = **1,650**, **1,450**, **1,550**. Point-estimate leakage against the old version: 200 × $6,500 = **$1.3M** a month; with the lower threshold, 100 × $6,500 = **$650k**.
- False alarms a month: 27 / 1,000 × 50,000 = **1,350** old and lower; 17 / 1,000 × 50,000 = **850** redacted.
- The fix: 2 × $240k (assumed) × 6 / 52 = **$55k** of payroll time.

## 3. How to spend your time

Forty-five minutes, with extra time on the numbers, because this case lives or dies on them.

| Minutes | What you do |
|---|---|
| 0–8 | Read the brief. Build the version table above. Write down $130k per point, 4 claims, 6–2, 29%, the ranges and 2,900 flags. |
| 8–15 | **Pillar A.** The three plain questions, and the stakeholders, each reacting to a different number. |
| 15–28 | **Pillar B.** Four messages, the three-step decision, and the economics of uncertainty. |
| 28–36 | **Pillar C.** Owners, a two-week plan, and the bias in the replay. |
| 36–43 | **Pillar D.** Metrics with ranges; the opening line, the slide and two answers, out loud. |
| 43–45 | Check every percentage has its count next to it. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what are the executives really asking, and which numbers frame the answer?

**How to reason.** Strip the jargon. They want to know three things: is it broken, what is it costing, and what are we doing? Build a frame table that answers in their units: 2,000 frauds a month, $130k a recall point, 4 net claims of evidence, accuracy dominated by honest claims, and 700 spare investigations.

Say what is out of scope: whether the privacy rule is wise. It's law.

**The trap.** Picking a side early. Both reports are true; neither is enough.

**Rubric criteria earned:** frauds a month and cost per point; 4 claims and the 6–2 split; the 96% do-nothing accuracy; rollback ruled out.

### Stakeholders

**The question it answers:** who is reacting to which number, and how do you bring each along?

**How to reason.** Map each person to their number. The SIU director saw recall and fears missed fraud. The ops dashboard owner saw accuracy. The CFO wants the worst case in dollars. The chief claims officer cares about honest customers getting paid, so fewer false alarms is good news to them. Compliance needs to hear early that rollback is off the table.

The most important move is the SIU director: agree the explanation with them before Thursday, and give them the lever, the 600 extra flags from a lower threshold. An expert who raised an alarm and gets a role becomes your best witness in the room.

Close with one idea: everyone is reacting to a different number, so put them all on one scale: frauds out of 40, and dollars a month.

**The trap.** Letting the SIU director's email stand as the opposing view in the meeting.

**Rubric criteria earned:** pre-briefs; the CFO's dollars; the claims officer's false-alarm view; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** what message could you take in, and how does each fare?

**How to reason.** Four messages. "Accuracy is up" is true and misleading: it counts 960 honest claims and hides 4 missed frauds. "Roll back" overstates the evidence and is illegal. "Send everything to SIU" needs 50,000 investigations against capacity for 3,000. The honest message is the useful one: probably a small-to-moderate loss, here's the range, here's what we're doing today, here's when we'll know.

The plain-words explanation of the disagreement: the new version flags fewer claims. That means fewer honest customers bothered (17 false alarms against 27) and somewhat fewer frauds caught (29 against 33). Accuracy rewards the first; recall punishes the second.

**The trap.** Defending the team with accuracy. The SIU director will take it apart.

**Rubric criteria earned:** the two bad messages shown to fail; the plain-words explanation; one table.

### Decision and Trade-offs

**The question it answers:** what do you do now, and what does it cost?

**How to reason.** Three steps on three clocks. Today: lower the threshold. It flags 2,900 a month, inside capacity, and the test suggests it recovers 2 of the 4 lost frauds in 40 (31 against 29). This week: replay 400 historical frauds for a ±4-point answer. Six weeks: in-house link signals that give the model "this phone is on 3 other claims" without the number.

What you give up: the 500 fewer false alarms a month the redacted version had given SIU, and 2 engineers for 6 weeks. What's reversible: the threshold, in a day. What's not: the redaction. The revisit is next week: under 3 points of gap, raise the threshold back; over 10, add contract investigators and bring the fix forward.

**The trap.** Waiting for certainty. On the audit alone, certainty takes 7 quarters.

**Rubric criteria earned:** threshold and 2,900 flags; the give-ups; reversibility; replay-based triggers.

### Economics

**The question it answers:** how uncertain is the gap, and what does knowing cost?

**How to reason.** Put a range on each recall: 68–91% old, 57–84% redacted. Then on the gap: from an 8-point gain to a 28-point loss, which is $1.1M a month gained to $3.6M lost. Always say the range next to the $1.3M point estimate.

Then compare the cost of knowing. Random audit: 288 frauds needed, 7,200 claims, 7 quarters or $324k. Replay: $35 and two days for ±4 points. That comparison is the strongest argument in the room.

Show precision and false alarms too, so the claims officer sees the other side: 1,350 false alarms a month before, 850 now, 1,350 again with the lower threshold.

**The trap.** Saying "$1.3M a month" alone. It's 4 claims multiplied by a big number.

**Rubric criteria earned:** recall ranges; the gap in dollars; 288 frauds and the replay comparison; precision and false alarms.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owns the threshold, the replay and the fix?

**How to reason.** You're accountable. The SIU director co-owns the threshold because it sets their team's workload. Two engineers own the fix, compliance signs off on every signal, and claims analytics rebuilds the dashboard to show recall and precision with ranges.

**The trap.** Owning the threshold alone, so every missed fraud becomes "the AI team's model".

**Rubric criteria earned:** one owner; SIU co-ownership; compliance sign-off.

### Plan and Milestones

**The question it answers:** what happens between now and the fix?

**How to reason.** Days 1–2: pre-briefs and the threshold change. Thursday: the review. Week 1: the replay. Week 2: a second update with the narrowed range, sent whatever it shows. Weeks 1–6: the fix, gated on compliance sign-off and on replay recall within 3 points of the old version. Next quarter: double the audit sample to 2,000.

**The trap.** Promising the fix will restore recall. It addresses the likely cause; the replay will confirm or refute that.

**Rubric criteria earned:** threshold before Thursday; a dated narrowed range; a gate before the fix ships.

### Risk and Governance

**The question it answers:** what could still mislead, and what controls it?

**How to reason.** The replay has a bias: historical frauds were mostly found because the old version flagged them, which flatters the old version. Check it by reporting recall separately on frauds found by random audit or tips. Then make sure this doesn't happen again: a recall gate on the replay set for every future release, a weekly flag count against SIU capacity, and accuracy retired as a headline.

**The trap.** Treating the replay as clean.

**Rubric criteria earned:** the replay bias and its check; a release gate; accuracy retired.

## 7. Pillar D: Land

### Metrics

**The question it answers:** how will leaders read model quality from now on?

**How to reason.** Recall with precision as its guard, frauds caught with SIU load as its guard, and leakage in dollars with honest claims' time-to-pay. Every figure is reported as "x of n, range a–b", so nobody reads 4 claims as a 10-point fact again.

**The trap.** Swapping accuracy for recall alone. Flag everything and recall is 100%.

**Rubric criteria earned:** paired guards; counts with ranges; leakage in dollars.

### Communication

**The question it answers:** what exactly do you say on Thursday?

**How to reason.** Answer the three questions in the first breath: "The AI isn't broken, and we can't roll back. The privacy change probably costs us some fraud catches. Our best estimate is 4 frauds in 40, but the test is too small to be sure. We're using spare investigator capacity to cover it from today, and we'll have a firm number in two weeks."

Then one slide, in counts and dollars: out of every 40 frauds, 33, 29 and 31 caught; right 55%, 63% and 53% of the time when it flags; each fraud in 40 worth about $325k a month; today's range a $1.1M gain to a $3.6M loss; ±4 points in two weeks.

Rehearse the two hard questions.

- **"Is it broken?"** It flags fewer claims, so it bothers fewer honest customers and catches somewhat fewer frauds.
- **"Why not roll back?"** The rule forbids the data, and the fix gives the model the useful part without the number.

Don't explain confidence intervals by name. Say "the test is too small to be sure" and give the range in dollars.

**The trap.** Teaching statistics to a COO. They need the range, not the method.

**Rubric criteria earned:** an opening that answers both questions; a slide in counts and dollars; both hard answers.

## 8. The decisions that separate strong answers

**Reconciling the two reports.** Weak answers pick recall or accuracy. Strong answers explain in one sentence why both moved: fewer flags means fewer false alarms and fewer catches.

**Pricing uncertainty, not just loss.** Saying "$1.3M a month" is easy. Saying "somewhere between a $1.1M gain and a $3.6M loss, and $35 buys us ±4 points in a week" is what a leader brings.

**Acting before certainty.** The spare SIU capacity makes the threshold change almost free. Strong answers use it today rather than waiting for the replay.

## 9. Common mistakes

- **Quoting percentages without counts.** "10 points" hides that it's 4 claims.
- **Recommending rollback.** It's illegal under the rule.
- **Citing accuracy in the team's defence.** A model that flags nothing scores 96%.
- **Ignoring precision.** The redacted version spared 500 honest claims a month; that's real.
- **Proposing 7 quarters of audits.** The replay answers in a week for $35.
- **Forgetting the replay's bias.** Past frauds were found partly by the old version.

## 10. Follow-ups an interviewer might ask

**The replay shows a 9-point loss, ±4. What do you tell the executives?**
That the loss is real, between 5 and 13 points, so $650k to $1.7M a month. The lower threshold covers about half; the fix arrives in about 5 weeks. Ask the CFO for contract investigators if the gap stays above 5 points after the threshold change.

**The COO asks you to just say yes or no: did it get worse?**
"Probably yes, a little. I'll tell you how much in two weeks, and we're already recovering half of the likely loss."

**Why not run the old version in shadow in production to compare?**
Shadow mode still sends the stripped fields to the model, which the rule forbids in production. Historical replay is the legal version of the same test.

**How do you stop this happening on the next compliance change?**
Run the replay set as a release gate: no change ships if recall drops more than 3 points beyond its range, and compliance changes get the same gate as model changes.

**The SIU director says 31 out of 40 still isn't good enough. Are they right?**
Possibly. The old version's 33 was never the target; it was what we had. Use the fix and the doubled audit sample to set a recall target with SIU, priced at $130k a month per point against investigator capacity.
