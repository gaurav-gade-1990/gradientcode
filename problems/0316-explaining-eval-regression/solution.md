# Explaining an Eval Regression to Non-technical Leaders: model answer

## 1. Situation

The executives are asking three plain questions: is the AI broken, how much is it costing us, and what are we doing? Two reports seem to give opposite answers, and the obvious fix is illegal. The job is to explain what the numbers measure, how sure we are, and what happens this week.

| What | Number | What it forces |
|---|---|---|
| Fraud a month | 50,000 × 4% = 2,000 claims | Each recall point is 20 frauds a month |
| Cost per recall point | 20 × $6,500 = $130k a month | A 10-point drop would be $1.3M a month |
| Evidence | 40 frauds; the versions disagree on 8; old wins 6–2 | The gap rests on 4 net claims |
| Accuracy | Old (33 + 933) / 1,000 = 96.6%; new (29 + 943) / 1,000 = 97.2% | A model that flags nothing scores 960 / 1,000 = 96% |
| SIU capacity | 3,000 a month; receiving 2,300 | 700 spare investigations to spend |

**How:**
1. Separate what is known (a privacy-required change shipped; the new version flags fewer claims) from what isn't (the true size of the recall drop).
2. Out of scope: whether the privacy rule is right. It's law, and rollback isn't on the table.

**Decision.** Frame Thursday as "what we know, what we don't yet, what we're doing this week, and when we'll know", not as a verdict on the model.

**Trap.** Picking a side: declaring "accuracy is up, all fine" or "recall is down 10 points" as fact. Both reports are arithmetically true, and neither answers the question on its own.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| COO | A clear answer and no fraud leak | One slide, a dollar range, a date when the range narrows |
| SIU director | Frauds caught, and to be taken seriously | Agree the explanation with them before Thursday; give them the 700 spare investigations through a lower threshold |
| CFO | What it costs, at worst | $130k a month per recall point; the range in dollars |
| Chief claims officer | Honest claims paid quickly | False alarms held at the old level, not raised |
| Chief compliance officer | The rule respected, no rollback | Say early and plainly that rollback is off the table, and why |
| Claims AI team | Not blamed for a required change | Present it as a known cost of compliance that we are now measuring |

**The one idea to hold:** everyone at the table is reacting to a different number, so the explanation has to put all of them on one scale: frauds caught out of 40, and dollars a month.

## 3. Options

The options are the messages you could take into the room.

| | A. "Accuracy is up" | B. "It regressed; roll back" | C. "Probably a small loss; here's the range and the plan" | D. "Send everything to SIU" |
|---|---|---|---|---|
| True? | Yes, but misleading | Overstated, and illegal | Yes | n/a |
| What it does | Ignores 4 net missed frauds | Breaks the privacy rule | Acts now and measures within a week | Needs 50,000 reviews against capacity of 3,000 |
| Trust after Thursday | Lost when the SIU director objects | Lost with compliance | Kept by both | — |

**How:**
1. Explain why A misleads: 960 of 1,000 claims are honest, so accuracy mostly counts honest claims left alone. The new version flags fewer honest claims (17 false alarms against 27) and fewer frauds (29 against 33).
2. Explain why B overstates: on 40 frauds the true gap could be anywhere from a small gain to a large loss (section 5).

**Decision.** C: say the loss is probably real but small-to-moderate, act now to recover part of it, and narrow the range within a week.

**Trap.** Defending the team by citing accuracy. It's the fastest way to lose the SIU director and the room.

## 4. Decision and Trade-offs

Recommend three steps. This week, lower the flag threshold. This week, re-test on 400 historical frauds to narrow the range. Over the next six weeks, build in-house link signals that restore the lost information without sending personal data.

| We give up | Why it's worth it |
|---|---|
| The 500 fewer false alarms the redacted version gave SIU | Spending them buys back an estimated 5 recall points: 31 / 40 = 77.5% |
| 2 engineers for 6 weeks | It targets the most likely cause of the gap: phone and address links |
| A clean verdict on Thursday | An honest range and a date |

**How:**
1. **Lower threshold:** flags 58 / 1,000 × 50,000 = 2,900 a month, inside SIU's 3,000. False alarms return to the old 27 per 1,000.
2. **Reversibility:** the threshold is reversible in a day; the redaction is not reversible in production.
3. **Revisit:** next week, after the replay. If it shows a gap under 3 points, raise the threshold back and return SIU's capacity; if over 10 points, ask for contract investigators and bring the fix forward.

**Decision.** Lower the threshold now, measure in a week and fix in six, because SIU's spare capacity makes the first step close to free.

**Trap.** Waiting for certainty before acting. On the old evidence alone, certainty takes years; the threshold costs nothing SIU can't absorb.

## 5. Economics

Put the uncertainty in dollars, then compare the cost of knowing with the cost of not knowing.

| | Old | Redacted | Redacted, lower threshold |
|---|---|---|---|
| Recall (frauds caught of 40) | 33 = 82.5% | 29 = 72.5% | 31 = 77.5% |
| 95% range (Wilson) | 68%–91% | 57%–84% | 62%–88% |
| Precision (frauds per flag) | 33 / 60 = 55% | 29 / 46 = 63% | 31 / 58 = 53% |
| Frauds caught a month | 1,650 | 1,450 | 1,550 |
| Leakage vs old, point estimate | — | 200 × $6,500 = $1.3M | 100 × $6,500 = $650k |
| False alarms a month | 1,350 | 850 | 1,350 |

**How:**
1. **The range on the gap:** treating the two runs as independent (conservative), the true drop lies somewhere between an 8-point gain and a 28-point loss. In money, from a gain of about $1.1M to a loss of about $3.6M a month.
2. **The disagreement test:** of 8 frauds where the versions disagree, the old one wins 6. A fair coin is that lopsided 2 × (1 + 8 + 28) / 256 = 29% of the time.
3. **Cost of knowing:** to pin recall to ±5 points needs 1.96² × 0.75 × 0.25 / 0.05² = 288 frauds. From random audits that's 288 / 4% = 7,200 claims: 7 quarters, or $324k of contract auditors. Replaying 400 historical frauds through both versions gives ±4 points for 800 × (20,000 × $2 + 400 × $10) / 1M = $35 of model cost and two days of work.
4. **Cost of the fix:** 2 × $240k × 6 / 52 = $55k of payroll time.

**Decision.** The replay is the cheapest information we'll ever buy, and the threshold change costs nothing new. Do both this week.

**Trap.** Quoting "$1.3M a month" as the loss. It's the point estimate from 4 claims; say the range with it.

## 6. Org and Ownership

One owner for the explanation and the fix, and the person who raised the alarm given part of the answer.

| Role | Who | Owns |
|---|---|---|
| Accountable | You | The explanation, the replay and the fix |
| Threshold | SIU director with you | Flag volume within capacity |
| Fix | 2 engineers from the claims AI team | Link signals in 6 weeks |
| Rule | Chief compliance officer | Sign-off on each signal sent |
| Reporting | Claims analytics | Dashboard showing recall and precision with ranges |

**How:**
1. The SIU director co-owns the threshold, so the person who raised the alarm controls part of the answer.
2. Compliance approves every new signal before it ships.

**Decision.** Make SIU a co-owner of the threshold rather than a critic of the model.

**Trap.** Owning the threshold alone. Then every missed fraud is "the AI team's model".

## 7. Plan and Milestones

Three days to Thursday, one week to a narrower range, six weeks to the fix.

| When | Milestone | Gate |
|---|---|---|
| Day 1–2 | Pre-brief SIU director and compliance; lower threshold | Flags ≤ 3,000 a month |
| Day 3 (Thursday) | Exec review | — |
| Week 1 | Replay 400 historical frauds | Range on the gap ≤ ±5 points |
| Week 2 | Second exec update with the narrowed range | — |
| Weeks 1–6 | Build link signals | Compliance sign-off |
| Week 7 | Ship fix | Replay recall within 3 points of old |
| Next quarter | Audit sample doubled to 2,000 | — |

**Decision.** Promise the executives one date: a narrowed range in two weeks.

**Trap.** Promising the fix will "restore recall". It's the likely cause, not a proven one.

## 8. Risk and Governance

The biggest risk now is false confidence, in either direction, from a test that is too small.

| Risk | Control |
|---|---|
| Replay flatters the old version: past frauds were mostly found by its flags | Report replay recall separately for frauds found by audit or tips |
| Lower threshold overloads SIU | Weekly flag count; raise threshold if over 3,000 |
| Link signals leak personal data | Counts only, computed in-house, compliance-approved |
| Next change regresses silently | Release gate on the replay set; no change ships if recall drops more than 3 points |
| Dashboards contradict again | Retire accuracy as a headline metric |

**Decision.** Add a recall gate on the replay set to every future release, so the next drop is caught before it ships.

**Trap.** Treating the replay as unbiased. Historical frauds are the ones someone caught.

## 9. Metrics

Recall and precision are reported together, always with a range, and accuracy stops being a headline.

| Success metric | Target | Guard metric |
|---|---|---|
| Recall on replay set | ≥ 80% after fix | Precision ≥ 53% (the lower threshold's level) |
| Frauds caught a month | ≥ 1,600 | SIU flags ≤ 3,000 a month |
| Leakage avoided | Within $650k of old by week 2; gap closed after fix | Honest claims' days-to-pay unchanged |

**Decision.** Report every eval figure as "x of n, range a–b", so nobody reads a 4-claim gap as a 10-point fact again.

**Trap.** Replacing accuracy with recall alone. Recall rises by flagging everything.

## 10. Communication

**Opening line:** "The AI isn't broken, and we can't roll back. The privacy change we were required to make probably costs us some fraud catches. Our best estimate is 4 frauds in 40, but the test is too small to be sure. We're using spare investigator capacity to cover it from today, and we'll have a firm number in two weeks."

**The one slide:** "Out of every 40 frauds: old version caught 33, new caught 29, new with a lower threshold catches 31. When it flags a claim, it's right 55%, 63% and 53% of the time. Each fraud in 40 is 2.5 points, about $325k a month. Range today: from a $1.1M gain to a $3.6M loss a month. Range in two weeks: about ±4 points."

**Hardest question 1:** "Is the AI broken?" "No. It flags fewer claims, so it bothers fewer honest customers and catches somewhat fewer frauds. Accuracy went up because 96% of claims are honest, which is why we're dropping accuracy as a headline."

**Hardest question 2:** "Why can't we just roll back?" "The old version sends phone numbers and addresses that the rule now forbids. What we can do is give the model the useful part, such as 'this phone appears on 3 other claims', without the number itself. That's six weeks away."

| Audience | One line |
|---|---|
| SIU director | "You were right to raise it; you'll get 600 more flags from today." |
| CFO | "Each recall point is $130k a month; firm number in two weeks." |
| Compliance | "No rollback; every new signal comes to you first." |

**Decision.** Use counts of claims and dollars, never percentages alone, and send the narrowed range in writing in two weeks, whatever it shows.

**Trap.** Explaining confidence intervals. Say "the test is too small to be sure" and give the range in dollars.
