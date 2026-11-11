## 1. What the problem is really asking

"Tell me about a time you failed" and "tell me about a conflict with a peer" are the two behavioral questions candidates prepare worst. They're also the two that interviewers trust most. Anyone can tell a success story. A failure story shows whether you can see your own part in what went wrong, and a conflict story shows whether you can disagree with someone at your level and still both come out ahead.

Both are graded on level. The same shape of story ("I pushed a launch, it broke, I rolled it back") is a senior engineer story when it's one service and a $20k incident. It's a director story when it's four orgs, $1.2M, a peer VP and your own budget. So the case asks for two things beyond a good story:

1. **A failure that is really yours.** The cause has to include a decision you made. Here: you argued to skip the staged rollout, and the eval you launched on had already predicted the error rate.
2. **A scope check.** Hold the story up against the level you're interviewing for, and either resize it or pick a different one.

The background is built so one story answers both questions. The failure is primary, and the conflict with the VP of Customer Operations happens inside it, so you can retell it on its own in 30 seconds. Use your own stories if you have them; the structure is the same.

## 2. The numbers that drive the decision

Derive these before you tell the story. Vague numbers make a failure story sound minimized.

**The failure.**
- 40,000 rebookings in 9 days = **4,444 a day**.
- Single-passenger: 28,000 × 0.8% = **224** wrong. Multi-passenger or multi-leg: 12,000 × 18.8% = **2,256** wrong.
- Total: **2,480**, which is 6.2%, × $310 = **$768.8k**.
- Concentration: 2,256 / 2,480 = **91%** of errors in 30% of volume. This is the way out.

**The cause, in the eval you already had.**
- Single-passenger cases scored (98.3% × 2,000 − 81) / 1,900 = **99.2%**.
- Reweighted to live traffic: 70% × 99.2% + 30% × 81% = **93.7% correct, 6.3% wrong**. That's within a tenth of a point of what happened.

**The options over the 33 days left.**
- Leave on: 275.6 wrong a day × $310 = **$85.4k a day**, $2.82M.
- Full rollback: 4,444 calls ÷ 32 per agent = **139 agents**, against a limit of 50. Not feasible.
- Segment rollback: 1,333 calls ÷ 32 = **42 agents**. 1,333 × $9.80 = $13.1k, plus 24.9 wrong × $310 = $7.7k, so **$20.8k a day**, $686k.
- Saved against leaving it on: **$2.13M**.

**The counterfactual.** The staged plan's first week at 10%: 3,111 rebookings, 193 wrong, **$59.8k**. Skipping it cost about **$709k** more.

**What's at stake for the program.** 980k disruptions × 80% × $9.80 = **$7.68M a year**.

## 3. How to spend your time

Forty-five minutes of practice for a story you'll tell in about two minutes, plus follow-ups.

| Minutes | What you do |
|---|---|
| 0–5 | Pick the primary story (failure or conflict). Write your role, the decision that caused it, and the cost. |
| 5–12 | **Pillar A.** The situation with the cause in one sentence, the scope check against your level, the stakeholders in conflict. |
| 12–24 | **Pillar B.** The options when it surfaced, priced over the same period; your call and what you paid; the counterfactual. |
| 24–34 | **Pillar C.** Ownership of the response, the timeline from discovery to relaunch, and the governance change. |
| 34–42 | **Pillar D.** The result with a guard. Then say the 2-minute STAR version out loud, timed, and the 30-second retelling of the other story. |
| 42–45 | Find every "we" in your Action and every sentence that blames something outside you. Fix both. |

## 4. Pillar A: Frame

### Situation

**The question it answers:** what happened, what was your part in it, and is the story the right size?

**How to reason.** Open with your role and one number for scale: director of applied AI, 22 engineers, at a $520M travel agency. Then state the failure as your decision: "I argued to skip the staged rollout." Put the damage in a small table: 2,480 wrong rebookings, $768.8k, 610 split families, 33 days of peak still to go, $7.68M a year of program value at risk.

Then do the scope check. The model answer's table runs from senior engineer to executive, across four dimensions: size of the failure or conflict, money at stake, orgs involved, and what "I" owned. This story is director-sized: four orgs, about $1.2M lost, a peer VP, and the fix paid from your budget. If you're interviewing for staff, a director story told as staff undersells you only if you claim the director's decisions; tell it from your own seat. If you're interviewing for director with a staff-sized story, pick another one.

**The trap.** A failure caused by someone else, or a "weakness" dressed up as a strength.

**Rubric criteria earned:** company, role and scale; the failure as your decision; damage quantified; scope checked against the level.

### Stakeholders

**The question it answers:** who was in conflict, what was each protecting, and how did you bring them along?

**How to reason.** Three people wanted three incompatible things on day 9. The VP of Customer Operations wanted it on, because of holds at 48 minutes. The CFO wanted it off. Your engineering lead wanted a hot-fix. Add your manager, the 2,480 travelers (families first) and Communications. For each, write what they were really protecting. The VP's fear was hold times, not the assistant, and that's what made the conflict solvable.

**The trap.** Making the conflicting peer the villain. Interviewers listen for whether you understood the other side's position well enough to meet it.

**Rubric criteria earned:** the conflict counterpart and what they protected; three incompatible wants; the harmed customers; one idea to hold.

## 5. Pillar B: Decide

### Options

**The question it answers:** when it surfaced, what could you do, and what would each option cost?

**How to reason.** Four options, one per stakeholder plus yours, priced over the same 33 days:

- **Leave fully on:** $2.82M.
- **Hot-fix while on:** $1.79M before the fix even lands, then an untested deploy at the peak.
- **Full rollback:** needs 139 agents against a limit of 50, so it's ruled out by a hard limit, not by preference.
- **Segment rollback:** $686k and 42 agents.

The segment breakdown is the key move: 91% of errors sat in 30% of volume.

**The trap.** Treating it as on or off. The binary framing is what made the conflict feel unsolvable.

**Rubric criteria earned:** three or more options including the peer's; same period; one ruled out on a hard limit; one table.

### Decision and Trade-offs

**The question it answers:** what did you decide, and what did you give up?

**How to reason.** One call, in "I": segment rollback on day 10, with 42 agents funded from your $600k. That uses $431.2k, 72% of it, and the Q1 contractor team goes. Name the other give-ups too: 30% of the automation during the peak, your engineering lead's preferred fix, and some credibility with the CFO when you said it was your call.

Say it's reversible: the segment is a flag. Then say how the conflict was resolved. You paid for the thing the VP feared, and gave them a pre-agreed kill criterion: over 1.5% single-passenger errors for two days, and everything goes off.

**The trap.** Winning the argument. A peer who leaves overruled makes the next incident harder.

**Rubric criteria earned:** one first-person call; a trade-off paid from your budget; reversibility; how the conflict was resolved.

### Economics

**The question it answers:** what did the failure cost, what did your call save, and what would the right process have cost?

**How to reason.** Three numbers carry the story:

- The failure: **$768.8k**.
- The saving from your call: **$2.13M** against leaving it on.
- The counterfactual: the staged plan's week 1 would have cost **$59.8k**. Skipping the gate cost about $709k more.

Label the assumptions: temporary agents cost the same $9.80 a call, and error rates hold at the day 1–9 levels.

**The trap.** Leading with the saving. In a failure story the cost comes first, or it sounds like spin.

**Rubric criteria earned:** failure cost derived; options compared on the same period; counterfactual priced; assumptions labelled.

## 6. Pillar C: Execute

### Org and Ownership

**The question it answers:** who owned the response, and what changed afterwards?

**How to reason.** You were accountable for the rollback, the budget, the review and the relaunch. Your engineering lead owned the fix. The VP of Customer Operations, your conflict counterpart, owned floor capacity and co-owned the kill criterion. Giving them a real role is part of resolving the conflict. Finance and Customer Operations handled remediation, and Communications handled outreach.

The lasting change: skipping a launch gate now needs written sign-off from the accountable director and the VP of Customer Operations. And the eval mix must be within 5 points of live traffic, with each segment scored separately.

**The trap.** Blaming the eval or the engineers. The gate existed; you skipped it.

**Rubric criteria earned:** you accountable; the peer given a role; a lasting ownership change.

### Plan and Milestones

**The question it answers:** what happened in what order?

**How to reason.** Day 9 morning: the refund spike and the segment breakdown. Day 9 afternoon: a one-to-one with the VP of Customer Operations, then the CFO and your manager. Day 10: segment off, outreach starts. Day 14: 42 agents on the floor. Weeks 3–6: the fix and a full regression. After the peak: a staged relaunch at 10%, 50% and 100%, gated per segment at under 1.5% wrong. In January: a blameless review shared with Customer Operations and Finance.

**The trap.** Announcing the rollback in a group message before talking to the peer.

**Rubric criteria earned:** discovery to decision in 24 hours; the conflict conversation first; a gated relaunch; a review shared beyond your team.

### Risk and Governance

**The question it answers:** what risk remained, and what rule changed?

**How to reason.** Quantify what's left:

- **Single-passenger errors:** 24.9 wrong a day, $254.6k over the rest of the peak, controlled by the kill criterion.
- **The floor:** 4 days of extra load before the agents arrive.
- **The 610 split families:** called first, with a holding statement ready.
- **The program's January review:** $7.68M a year at stake.

Then the governance change, stated specifically: who can skip a gate (two signatures, one outside your line), and how readiness is reported (per segment, reweighted to live traffic).

**The trap.** "We added more tests." The failure was a decision, so the fix changes who decides.

**Rubric criteria earned:** remaining risk quantified; customer outreach; a specific governance change; a pre-agreed kill criterion.

## 7. Pillar D: Land

### Metrics

**The question it answers:** what was the result, and what shows the harm wasn't just moved?

**How to reason.** Wrong rebookings fell from 275.6 a day to 24.9, a 91% cut. Pair that with hold time, the guard showing the harm didn't move to the phone queue: it peaked at 55 minutes and was back to 47 by day 14 (assumed outcome). After the relaunch, multi-passenger errors were 1.2%, and by the end of Q1 the assistant automated 76% of disruptions: 980k × 76% × $9.80 = $7.30M a year. Both are assumed outcomes. The program kept its funding.

**The trap.** Ending without a result, or with only "I learned a lot".

**Rubric criteria earned:** before and after; a guard; what happened to the program and the relationship; assumed outcomes labelled.

### Communication

**The question it answers:** how do you tell it in two minutes, and how does the other story use the same structure?

**How to reason.** STAR, with the Action longest and in "I":

- **Situation:** role, company, the program's value.
- **Task:** what you did that caused it, and the damage.
- **Action:** the segment analysis, the private one-to-one, the funded agents, owning it with the CFO, and the gated relaunch.
- **Result:** the 91% cut, the $2.1M saved, the program funded.
- **Differently:** reweight the eval to live traffic, which predicted 6.3%, and the two-signature rule.

Then the conflict in 30 seconds, using the same STAR: the peer's position, the 24-hour task, the one-to-one and the trade, and the outcome, which is that they now co-sign launches.

**The trap.** A "differently" that blames the calendar.

**Rubric criteria earned:** STAR in two minutes in first person; the other story in the same structure; a specific lesson and change; one line per audience.

## 8. The decisions that separate strong answers

**Finding your decision in the cause.** Strong candidates say "I argued to skip the gate" in the first 20 seconds. Weak ones say "the model had issues with multi-passenger bookings".

**Showing the failure was predictable, and that you see it now.** Reweighting the eval to 6.3% shows you understand exactly how you missed it. That's more convincing than general humility.

**Breaking the binary.** The segment rollback turned a three-way conflict into an agreement. Most candidates argue for on or off.

**Paying for the resolution.** Funding 42 agents from your own budget is what moved the peer. Influence and conflict stories both turn on what *you* gave up.

**Changing who decides.** The governance fix puts a peer outside your line in the gate. That's a director-level lesson; "more testing" is a senior engineer's.

## 9. Common mistakes

- **No real failure.** "I took on too much" or a project that "could have gone better".
- **Blame drift.** The eval team, the airline data, the deadline.
- **No numbers.** A failure without its cost sounds minimized.
- **The peer as villain.** The interviewer wonders what the peer would say about you.
- **Wrong scope.** A director candidate telling a one-service outage, or a staff candidate claiming budget decisions they didn't make.
- **"We" in the Action.** The interviewer can't tell what you did.
- **Too long.** Over three minutes, the result gets lost. Practise the two-minute version until it fits.

## 10. Follow-ups an interviewer might ask

**Why did you skip the gate in the first place?**
Against the staged plan (10%, then 50%, then 100%), launching at 100% automated an extra (90% + 50%) × 7 days × 4,444 = 43,555 rebookings in the first two weeks, about $427k of calls at $9.80. I weighed that against a risk I thought was small, because I believed the 98.3% headline. I didn't reweight the eval to live traffic. That's the mistake, and the two-signature rule is the fix.

**What did the VP of Customer Operations say about you afterwards?**
They co-signed the relaunch and every launch since. If you don't know how your conflict counterpart sees you now, the story isn't finished.

**What if the outsourcer could only supply 30 agents?**
Then 1,333 − 30 × 32 = 373 calls a day would have no agent. I'd keep the multi-passenger segment on only for itineraries departing more than 72 hours out, where a wrong rebooking can still be fixed by an agent before the flight, and switch it off for everything closer.

**How would you tell this at an executive interview?**
Raise the scope: the program as one of several AI bets, the board-level reputational risk of 610 split families, and the change as a company launch policy, not your org's rule.

**Your engineering lead disagreed with you too. How did that end?**
I told them the gate was right and I had overridden it, so they weren't carrying my call. Then they led the fix and the relaunch, which is the result they cared about.
