### Context

Two behavioral questions come up in almost every leadership loop: **"Tell me about a time you failed"** and **"Tell me about a serious conflict with a peer, and how you resolved it."** Both are graded on level: how big the failure or conflict was, what was at stake, how many orgs were involved, and what you personally owned. Prepare one primary story told in STAR form (Situation, Task, Action, Result), and know how to retell the other one using the same structure. If you have real stories of your own, use them, and use this case to give them structure and the right scope. If you don't, build your answer from the background below; the model answer does.

The background: you were director of applied AI at a mid-size online travel agency with $520M of revenue and 14M bookings a year, leading 22 engineers in three teams. Your team built an AI rebooking assistant. When an airline cancels a flight or makes a major schedule change, it picks an alternative itinerary, rebooks it and messages the traveler. You launched it at the start of the holiday peak, and it went wrong.

### What you have

- **The business case.** 7 percent of the 14M bookings a year are disrupted. The target was to automate 80 percent of disruptions, each of which otherwise costs a 14-minute contact-center call at $9.80 fully loaded.
- **The launch plan you skipped.** The plan was a staged rollout: 10 percent, then 50, then 100 percent, a week at each step, with a gate on multi-passenger and multi-leg itineraries. The offline eval used 2,000 past disruptions, 95 percent of them single-passenger and single-leg. It scored 98.3 percent correct overall; its 100 multi-passenger or multi-leg cases scored 81 percent. To catch the 42-day peak, you argued for launching at 100 percent on day 1, and your VP of Engineering agreed on your recommendation.
- **The first 9 days.** The assistant made 40,000 automated rebookings. 70 percent were single-passenger and single-leg, and 0.8 percent of those were wrong. The other 30 percent were multi-passenger or multi-leg, and 18.8 percent of those were wrong; 610 of them split a family across different flights. Finance puts the average cost of a wrong rebooking at $310 (refunds, fare differences and goodwill credits).
- **The contact center.** 1,400 agents, with hold times already at 48 minutes. An agent handles about 32 disruption calls a shift. The outsourcer can add at most 50 agents, within 5 days, and each call costs the same $9.80.
- **The fix.** The root cause is how passengers on one booking are linked. Fixing it needs about 3 weeks, plus a full regression run.
- **Budget.** Your org has $600k unspent this year, earmarked for a Q1 contractor team.
- **Timeline.** The problem surfaced on day 9 of the 42-day peak. The CFO's funding review of the program is in January.

### The constraint

On day 9 three people want three different things. The VP of Customer Operations, a peer outside your reporting line, wants the assistant left fully on, because it takes about 4,400 calls a day off a floor that is already overloaded. The CFO wants it switched off. Your engineering lead wants to keep it on and hot-fix during the peak. A full rollback needs more agents than the outsourcer can supply, and leaving it on keeps producing wrong rebookings every day. Whatever you choose, someone pays, and the failure started with your own call.

### What a strong answer covers

- A failure that was really yours, owned with "I", including the decision that caused it.
- The options on day 9, priced over the rest of the peak, and the one you chose.
- How you resolved the conflict with the peer VP, and what you gave up to do it.
- A quantified result, and what you changed so it can't happen the same way again.
- The scope of the story checked against the level you're interviewing for.
