# Conflict and Failure: Story Bank: model answer

## 1. Situation

The primary story is the failure: I skipped a staged rollout to catch the holiday peak, and the assistant rebooked 2,480 travelers wrongly in 9 days. The conflict, with the VP of Customer Operations over whether to switch it off, sits inside it and is retold on its own in section 10. A failure story that contains a conflict shows both skills at once.

| What | Number | What it forces |
|---|---|---|
| Rebookings, days 1–9 | 40,000, or 4,444 a day | Every day of delay is expensive |
| Wrong, single-passenger | 28,000 × 0.8% = 224 | This segment works |
| Wrong, multi-passenger or multi-leg | 12,000 × 18.8% = 2,256, including 610 split families | This segment doesn't |
| Wrong in total | 2,480 = 6.2%, × $310 = $768.8k | The failure, in money |
| Rest of the peak | 42 − 9 = 33 days | The horizon for every option |
| Program at stake | 14M × 7% = 980k disruptions × 80% × $9.80 = $7.68M a year | The CFO's January review |

**How:**
1. Own the cause in one sentence. The eval predicted it: its single-passenger cases scored (98.3% × 2,000 − 81) / 1,900 = 1,885/1,900 = 99.2%. Reweighted to the live mix, that's 70% × 99.2% + 30% × 81% = 93.7%, or 6.3% wrong. I launched on the 98.3% headline without reweighting it.
2. Check the scope against the level you're interviewing for, using the table below.

**Scope check per level:** the same kind of story, sized for each level.

| Level | Size of the failure or conflict | Money at stake | Orgs involved | What "I" owned |
|---|---|---|---|---|
| Senior engineer | A bad deploy; a design dispute with a peer engineer | $10k–$100k | 1 team | The code, the rollback, the fix |
| Staff | A launch slipped across teams; a dispute with another team's tech lead | $100k–$1M | 2–3 teams | The technical call across teams |
| Principal | A technical direction that cost an org a quarter; a dispute with a director | $1M–$10M | 2 orgs or more | The direction and its trade-offs |
| Director | A launch call that harmed customers; a conflict with a peer VP | $1M–$10M, from your own budget | 3–5 orgs | The call, the budget, the people |
| Executive | A strategic bet that missed; a conflict with another exec or the board | $10M or more, or regulatory | Company-wide | The strategy and the public story |

This story is director-sized: about $1.2M lost, $2.8M of further exposure, four orgs (AI, Customer Operations, Finance, Communications), and the fix paid from my own budget.

**Decision.** Tell the failure as the primary story, because it carries the conflict inside it and shows judgment under pressure, not just a mistake.

**Trap.** A fake failure, like "I worked too hard", or one where the cause was someone else. If the interviewer can't find your decision in the cause, it isn't your failure.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| VP Customer Operations (the conflict) | Keep 4,400 calls a day off a floor already at 48-minute holds | One-to-one before any announcement; switch off only the broken segment; I fund the 42 extra agents |
| CFO | Stop the losses; decide the program's future in January | Per-day cost of each option; I say plainly the skipped rollout was my call |
| My engineering lead | Hot-fix and stay on, to prove the system works | Show that 21 days at $85.4k a day is $1.79M before the fix lands; the fix goes in after the peak, with gates |
| VP Engineering (my manager) | No repeat, and a credible owner | Written decision within 24 hours; a governance change they can enforce |
| Travelers on wrong rebookings | Get home together, and be made whole | Proactive outreach to all 2,480, with the 610 families first |
| Communications | No surprise on social media | A holding statement and the outreach script on day 10 |

**The one idea to hold:** everyone was protecting something real — hold times, money, pride in the system or customers — and the call had to switch off only what was broken, with me paying for the gap.

## 3. Options

On day 9, four options, each priced over the 33 days left in the peak.

| | A. Leave fully on | B. Hot-fix while on | C. Full rollback | D. Segment rollback |
|---|---|---|---|---|
| Who wanted it | VP Customer Operations | My engineering lead | CFO | Me |
| Wrong rebookings a day | 2,480 / 9 = 275.6 | 275.6 until the fix | 0 | 224 / 9 = 24.9 |
| Calls back to the floor a day | 0 | 0 | 4,444 | 4,444 × 30% = 1,333 |
| Extra agents needed (32 calls a shift) | 0 | 0 | 139 | 42 |
| Feasible | Yes | Risky: fix not regression-tested mid-peak | No: limit is 50 agents | Yes |
| 33-day cost | 275.6 × $310 = $85.4k × 33 = $2.82M | $85.4k × 21 = $1.79M before the fix | $43.6k × 33 = $1.44M, if it could be staffed | $13.1k + $7.7k = $20.8k × 33 = $686k |

**How:**
1. **C** fails on a hard limit: 139 agents against 50 leaves 89 × 32 = 2,848 calls a day unanswered at the peak.
2. **B** keeps the harm running for three weeks, then ships an untested change at the busiest time of year.
3. **D** works because the failure is concentrated: 30% of volume carries 91% of the errors (2,256 / 2,480).

**Decision.** D: switch off multi-passenger and multi-leg itineraries, and keep single-passenger on.

**Trap.** Presenting it as a binary, on or off. The segment data was the way out of the conflict, and most candidates never look for it.

## 4. Decision and Trade-offs

I decided within 24 hours: segment rollback on day 10, 42 temporary agents funded from my budget, and the multi-passenger relaunch only after the peak, with gates.

| I gave up | Why it was worth it |
|---|---|
| $431.2k of my $600k (72%): the Q1 contractor team | It made the rollback acceptable to Customer Operations, and saved $2.13M against leaving it on |
| 30% of the automation during the peak | Those itineraries were 18.8% wrong |
| My credibility with the CFO, by saying it was my call | Owning it early kept the January review about the fix, not about blame |
| My engineering lead's hot-fix | A mid-peak deploy without a full regression was a second failure waiting |

**How:**
1. **Reversible:** yes. The segment is a flag; it can go back on within minutes.
2. **Kill criterion, agreed with the VP of Customer Operations:** if single-passenger errors pass 1.5% on two consecutive days, everything goes off, and they get 50 agents from the outsourcer.
3. **Resolving the conflict:** the VP's real fear was hold times, not the assistant. Paying for the agents removed that fear, and the agreed kill criterion gave them a say.

**Decision.** Segment rollback, paid for by me, because it was the only option that was feasible, cut the harm by 91%, and gave each side what it was actually protecting.

**Trap.** Winning the argument instead of resolving it. If the peer leaves the room overruled, the next incident starts with less trust.

## 5. Economics

What the failure cost, what the call saved, and what following the original plan would have cost.

| Item | Derivation | Amount |
|---|---|---|
| The failure, days 1–9 | 2,480 × $310 | $768.8k |
| Extra agents, days 10–42 | 1,333 × $9.80 × 33 | $431.2k |
| Remaining single-passenger errors | 24.9 × $310 × 33 | $254.6k |
| Segment rollback, 33 days | $431.2k + $254.6k | $686k |
| Saved against leaving it on | $2.82M − $686k | $2.13M |
| Following the staged plan instead | Week 1 at 10%: 4,444 × 10% × 7 = 3,111 rebookings × 6.2% = 193 wrong × $310 | $59.8k |
| Program value at stake | 980k × 80% × $9.80 | $7.68M a year |

**How:**
1. **The counterfactual:** the staged plan would have shown the multi-passenger problem in week 1, on 933 itineraries with about 175 wrong. Skipping it cost $768.8k − $59.8k = $709k more.
2. **Assumed:** the outsourcer's agents cost the same $9.80 a call as the existing floor, and errors stay at the day 1–9 rates.

**Decision.** Lead the economics with the $709k that skipping the gate cost. It's the number that makes the failure mine and the lesson concrete.

**Trap.** Telling the failure without a number, or only with the saving. The interviewer wants the cost first.

## 6. Org and Ownership

I ran the response as the accountable owner, and I gave the peer I was in conflict with a defined role in it.

| Role | Who | Owns |
|---|---|---|
| Accountable | Me | The rollback, the budget, the review, the relaunch |
| Fix | My engineering lead | Passenger-linking fix and full regression |
| Floor capacity | VP Customer Operations | 42 agents, the kill criterion, hold-time reporting |
| Remediation | Finance with Customer Operations | Refunds and credits for the 2,480 travelers |
| Outreach | Communications | Families first, then the rest |

**How:**
1. **Lasting change:** a launch gate can be skipped only with written sign-off from the accountable director and the VP of Customer Operations.
2. **Eval rule:** the eval set's segment mix has to be within 5 points of live traffic, and every segment is scored on its own.

**Decision.** Customer Operations co-owned the kill criterion, so the next on/off argument has a pre-agreed answer.

**Trap.** Blaming the eval team or the engineers. The gate existed; I chose to skip it.

## 7. Plan and Milestones

From discovery to a decision in 24 hours, then a gated relaunch after the peak.

| When | What happened | Gate |
|---|---|---|
| Day 9, morning | Finance flags refund spike; segment breakdown confirms 91% of errors in multi-passenger | — |
| Day 9, afternoon | One-to-one with VP Customer Operations; then CFO and my manager | Kill criterion agreed |
| Day 10 | Multi-passenger off; outreach to 2,480 travelers starts | — |
| Day 14 | 42 agents on the floor | Holds back under 50 minutes |
| Weeks 3–6 | Passenger-linking fix plus full regression | Eval scored per segment |
| Day 43 onward | Staged relaunch: 10%, 50%, 100%, a week each | Each segment under 1.5% wrong |
| January | Blameless review shared with Customer Operations and Finance; CFO funding review | — |

**Decision.** The VP of Customer Operations heard the plan from me, privately, before the CFO did.

**Trap.** Announcing the rollback in a group email first. The peer learns about it with everyone else and the conflict hardens.

## 8. Risk and Governance

After the call, some risk remained, and the governance changes were the part that outlived the incident.

| Risk | Size | Control |
|---|---|---|
| Single-passenger errors continue | 24.9 a day, $254.6k over 33 days | Kill criterion: over 1.5% for two days, everything goes off |
| Floor overloaded until day 14 | 1,333 calls a day on 4 days, before temps arrive | VP Customer Operations prioritizes same-day departures |
| Split families escalate publicly | 610 families | Called first; rebooked together; holding statement ready |
| Program cancelled in January | $7.68M a year | The review leads with what changed, not with the saving |

**How:**
1. Skipping a gate needs two written signatures, one of them outside my reporting line.
2. Launch readiness reports accuracy per segment, reweighted to the live mix.

**Decision.** The governance change put a peer outside my org in the gate, because the failure was a director overriding their own process.

**Trap.** "We added more tests." The failure was a decision, so the fix has to change who decides.

## 9. Metrics

The outcome, labelled where it is the model story's assumed result.

| Success metric | Before → after | Guard metric |
|---|---|---|
| Wrong rebookings a day | 275.6 → 24.9, down 91% | Hold time: peaked at 55 minutes on days 10–13, back to 47 by day 14 (assumed) |
| Multi-passenger error after relaunch | 18.8% → 1.2% (assumed) | Repeat contacts on automated rebookings |
| Disruptions automated by end of Q1 | 76% (assumed): 980k × 76% × $9.80 = $7.30M a year | Wrong-rebooking cost under 5% of savings |
| Program | Funded at the January review (assumed) | Customer Operations a co-signer on every launch |

**Decision.** Report the harm cut and the guard together, so nobody can say the problem was just moved to the phone queue.

**Trap.** Ending the failure story without a result. The interviewer wants evidence you recovered and changed something.

## 10. Communication

The primary story in two minutes, the conflict told with the same STAR structure, and the lines each person heard on day 9.

| Audience | One line |
|---|---|
| VP Customer Operations | "I'll switch off only the broken 30%, and pay for the 42 agents you need." |
| CFO | "The skipped rollout was my call; this cuts the loss from $85k a day to $21k." |
| My team | "The gate was right and I overrode it. We fix it properly after the peak." |

**Failure, the 2-minute STAR version:**
- **Situation.** "I led applied AI at an online travel agency: 22 engineers, $520M of revenue. My team built an assistant that rebooks travelers automatically when an airline cancels, worth about $7.7M a year in contact-center cost."
- **Task.** "The plan was a staged rollout with a gate on multi-passenger trips. To catch the holiday peak, I argued to skip it and launch at 100%, and my VP agreed on my recommendation. By day 9, 2,480 of 40,000 rebookings were wrong, about $769k, including 610 families split across flights. I had to stop the damage without collapsing a contact center already at 48-minute holds."
- **Action.** "I broke the errors down by segment and found 91% of them in multi-passenger and multi-leg trips, which were 30% of volume. Before announcing anything, I met the VP of Customer Operations one-to-one, because they wanted it left on. I offered to switch off only that segment and to fund the 42 extra agents it needed from my own budget, and we agreed a kill criterion together. Then I told the CFO the skipped rollout was my call. I held the fix until after the peak and relaunched it in stages, gated by segment."
- **Result.** "Wrong rebookings fell 91%, from 276 a day to 25, which saved about $2.1M over the rest of the peak. The program kept its funding in January."
- **Differently.** "I'd reweight the eval to live traffic before launch: it predicted 6.3% errors, and I launched on the 98.3% headline. Since then, skipping a launch gate needs two signatures, one from outside my org."

**The conflict, same STAR:** Situation: the peer wants it on, floor at 48-minute holds. Task: agree a call within 24 hours. Action: a one-to-one first, the per-day table, the segment option, my budget for agents, a shared kill criterion. Result: agreed that day; Customer Operations co-signs launches now.

**Decision.** Tell the failure as primary and keep the conflict ready as a 30-second retelling, because one well-scoped story answers both questions.

**Trap.** A "differently" that blames the timeline. The lesson has to be about your own call.
