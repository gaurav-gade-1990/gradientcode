# Pushing Back on a CEO Deadline: model answer

## 1. Situation

The CEO isn't really asking for a technology. She's asking for a story on stage in 8 weeks that wins the two anchor renewals. "All shippers, autonomous" is her guess at that story. The job is to give her a better one that is true, without becoming the person who said no.

| What | Number | What it forces |
|---|---|---|
| Average load | $900M / 12 / 45,000 = $1,667, so $233 of margin at 14% | Every pricing error is priced in margin |
| Under-quotes if autonomous everywhere | 45,000 × 9% = 4,050 loads × ($1,667 × 8% = $133) = $540k a month | Unsupervised pricing gives away about 5% of the $10.5M monthly margin |
| Fraud without vetting | 45,000 × 0.4% = 180 suspect offers a month; 1 in 10 becomes a loss (assumed) × $2.09M / 38 = $55k, so $990k a month | The big risk is cargo theft, not pricing |
| Anchors at stake | $60M × 14% = $8.4M net revenue, 6.7% of $126M; renewal in 18 weeks | The real deadline is week 18, not week 8 |
| Earliest safe autonomy | Vetting 10 weeks + integration 3 + shadow run 4 = 17 weeks | Week 8 is impossible for "all shippers" at any price |

**How:**
1. Restate her goal: the anchors renew, and the summit shows a product that works.
2. Out of scope: changing the summit date. It's public and fixed.

**Decision.** Frame the conversation around her goal (renewals and a credible stage moment) and two dates, week 8 and week 18, not around your estimate.

**Trap.** Opening with "20 weeks". It answers her plan with yours, and she'll hear a no before she hears the risk.

## 2. Stakeholders

| Stakeholder | What they want | How you bring them along |
|---|---|---|
| CEO | A strong summit announcement and the anchors kept | A one-to-one, not the staff meeting; a counter-offer with stage words, not a list of risks |
| CRO | Something to sell at the summit and in renewals | Anchors get autonomous booking at the summit; a written list of what sales may and may not claim |
| COO (brokerage ops) | Brokers kept in control of margin | Co-pilot keeps a broker on every non-anchor load until vetting is live |
| Head of carrier compliance | No new route for cargo theft | Autonomous booking only with trusted carriers; any change to a carrier's bank details removes it from the list |
| CFO | No margin leak, a clear price for the $400k | Exposure of each option in dollars a month; the $400k buys 3 weeks |
| Anchor shippers | Faster booking, at least as good as the competitor | Live autonomous booking on their lanes at the summit |
| Brokers | Their jobs, and not cleaning up the agent's mistakes | The co-pilot saves 19 minutes a load; they approve, the agent drafts |

**The one idea to hold:** everyone wants the anchors to renew; they disagree only on how much risk to take getting there, so the counter-offer has to show each of them the risk they care about, priced.

## 3. Options

The options are the answers you could give her on Friday. Each is scored on what's true on stage, what it risks, and the anchors.

| | A. Yes, as asked | B. No, 20 weeks | C. Yes to the date, different scope | D. Announce a vision only |
|---|---|---|---|---|
| On stage at week 8 | "Autonomous for all" | Nothing new | Autonomous for anchors on trusted carriers; co-pilot for everyone | A slide, no product |
| Monthly exposure | $540k + $990k = $1.53M until vetting is live | $0 | Up to $22k (anchor under-quotes, before the price guard) | $0 |
| All-shipper autonomy | Week 8, unsafe | Week 20, after the renewal | Week 17, before the renewal | Week 20 |
| The CEO's promise | Kept, at risk | Broken | Kept for the two she told | Bent |

**How:**
1. A from week 8 to week 17: $1.53M × 9 / 4.33 weeks a month = about $3.2M of exposure, plus up to $525k a month of margin at risk on over-quoted loads (2,250 × $233).
2. C's autonomous slice: anchors book 3,000 loads a month ($60M / $1,667 / 12); 62% on trusted carriers is 1,860 loads. Under-quotes there: 1,860 × 9% × $133 = $22.3k a month at most.

**Decision.** C. It keeps the date, keeps the promise to the two anchors, and is true on stage.

**Trap.** Treating it as yes or no. Leaders who only offer those two get overruled; the counter-offer is the pushback.

## 4. Decision and Trade-offs

Recommend C: at the summit, autonomous booking for the two anchors on trusted carriers within each lane's price band, and the broker co-pilot for every shipper. Autonomous booking for all shippers at week 17, before the anchors renew.

| We give up | Why it's worth it |
|---|---|
| "All shippers" on stage | It avoids about $1.5M a month of exposure |
| $400k for contractors | It moves all-shipper autonomy from week 20, after the renewal, to week 17, before it |
| Some autonomous volume: only 62% of anchor loads | Trusted carriers have 2 years with no claims |
| The CEO's original wording | She keeps the promise to the two customers she made it to |

**How:**
1. **What the $400k buys:** the 17-week vetting path can't be shortened. Contractors take the parallel work so the team's 20 weeks fits inside it (assumed: the 3 weeks of non-critical work can be handed over). Money buys 3 weeks, not 12.
2. **Sign the vetting contract this week.** Every week of delay moves week 17 by a week.
3. **Reversibility:** C is reversible (a feature flag per shipper). An announced capability that then causes a theft is not.
4. **Revisit:** if the week-6 shadow gate fails, ship co-pilot only; if vetting onboarding slips past week 10, tell the anchors before the summit.

**Decision.** C with the $400k, because it is the only option where the date, the promise and the risk all hold.

**Trap.** Taking the money as if it bought the date. Saying exactly what it buys is what makes the rest of the pushback credible.

## 5. Economics

The money behind the message is exposure per month against revenue at stake, over the 18 weeks to renewal.

| | A. Yes, as asked | B. No | C. Re-scope |
|---|---|---|---|
| New spend | Vetting $18k a month | Vetting $18k a month | Vetting $18k a month + $400k contractors |
| Pricing exposure | $540k a month | $0 | ≤ $22.3k a month on anchors |
| Fraud exposure | $990k a month (assumed rate) | $0 | Near zero: trusted carriers only |
| Exposure, week 8 to 17 | About $3.2M | $0 | ≤ $46k (9 weeks × $22.3k / 4.33) |
| Anchors ($8.4M net revenue) | Kept unless an incident hits them | At risk | Kept, with autonomy on their lanes |

**How:**
1. **People:** 7 engineers × $230k (assumed) = $1.61M a year, already on payroll in every option.
2. **Value of the co-pilot:** 45,000 × 19 minutes = 14,250 broker hours a month, 76% of the 18,750 hours spent on loads today. That is capacity to grow without hiring, not cash this quarter.
3. **Opportunity cost of C:** the team builds two products at once, so nothing else ships for 17 weeks.

**Decision.** C costs $400k plus $18k a month and caps exposure under $50k before full autonomy; A risks about $3.2M to say "all" eight weeks early.

**Trap.** Weighing $400k against the $8.4M anchors and stopping there. The real comparison is the $3.2M of exposure A carries to get the same anchors.

## 6. Org and Ownership

One owner for the counter-offer, and the risky decisions given to people who own the risk.

| Role | Who | Owns |
|---|---|---|
| Accountable | You, head of AI | The counter-offer, the gates, week 17 |
| Delivery | EM, 7 engineers, contractors | Co-pilot by week 6; anchor autonomy; vetting integration |
| Trusted-carrier list | Head of carrier compliance | Who is on it, and removal on any bank-detail change |
| Price band | COO's pricing lead | The lane bands the agent can book inside |
| Stage words | CEO, CRO, you | Exactly what is announced |

**How:**
1. Compliance, not engineering, controls the trusted list.
2. The agent can't book outside a band the COO's team set.

**Decision.** Give the two risk levers, carriers and prices, to the people who already own those risks.

**Trap.** Owning everything yourself. It makes the agent look like an AI-team experiment rather than a brokerage product.

## 7. Plan and Milestones

Work back from two dates: the summit at week 8 and the renewal at week 18.

| Week | Milestone | Gate |
|---|---|---|
| 0 | Friday one-to-one; vetting signed; contractors start | CEO agrees the stage words |
| 1–6 | Co-pilot for all; anchor autonomy behind a flag | — |
| 6–8 | Anchor autonomy in shadow: agent decides, broker books | ≥ 90% of in-band bookings within 5% of the broker's rate, and zero non-trusted carriers chosen |
| 8 | Summit: anchors live, co-pilot for all | Gate passed, or co-pilot only |
| 10–13 | Vetting live; integration | — |
| 13–17 | Shadow run on all lanes | Same thresholds, all lanes |
| 17 | Autonomous for all shippers | — |
| 18 | Anchor renewals | — |

**Decision.** The week-6 gate decides what goes on stage, and the CEO hears its result the same day.

**Trap.** No gate before the summit. You'd find out on stage that the anchors' lanes price worse than the backtest.

## 8. Risk and Governance

The biggest risk is a theft on an autonomously booked load in the first month, after a public announcement.

| Risk | Control |
|---|---|
| Fraudulent carrier books autonomously | Trusted list only until vetting is live; any change to a carrier's bank details removes it |
| Under-quoting | Lane price band; outside it, the load goes to a broker |
| Week-6 gate fails | Co-pilot only on stage; anchors told before the summit |
| Vetting onboarding slips | Week 17 slips one-for-one; the CEO hears the same week |
| Sales over-claims on stage | Written list of permitted claims, agreed with the CRO |

**Decision.** Encode the trusted list and the price band in the booking path, so the agent can't book outside them.

**Trap.** Relying on the 86% backtest. 9% of loads under-quoted is 4,050 a month at full scale.

## 9. Metrics

The counter-offer worked if the anchors renew and autonomy doesn't cost margin or cargo. Each success metric gets a guard that would catch the harm it could hide.

| Success metric | Target | Guard metric |
|---|---|---|
| Anchor loads booked autonomously | 1,860 a month (62%) | Margin per autonomous load vs broker-booked |
| Broker minutes per load | 6 with co-pilot | Over-quote rate (loads lost) |
| All-shipper autonomy date | Week 17 | Fraud incidents on autonomous loads: zero |
| Anchor renewals | Both renewed | Anchor complaints about wrong bookings |

**Decision.** Report autonomous volume only alongside margin per load and fraud incidents.

**Trap.** Counting bookings. Volume rises fastest when the agent under-quotes.

## 10. Communication

**Opening line (Friday):** "I can get you a true story on stage in 8 weeks and both anchors live on it. What I can't do is 'all shippers' by then without about $1.5M a month of fraud and pricing risk, so here's what I'd announce instead."

**The one paragraph she keeps:** "At the summit we announce autonomous booking, live, for our two largest shippers on carriers we've vetted over two years, and an AI co-pilot that quotes every other shipper in seconds. Autonomous booking for everyone follows in 17 weeks, before the anchors renew, once automated carrier vetting is in. We sign the vetting contract this week and use your $400k to bring the date in from week 20."

**Hardest question 1:** "The competitor says it's fully autonomous. Why can't we be?" "We can, at week 17. Booking with unvetted carriers is how cargo gets stolen, and we priced that at about $1M a month. On stage we'll be the one showing it live with customers."

**Hardest question 2:** "I told the anchors. Are you making me walk it back?" "No. The two you told get exactly what you promised, at the summit. Only 'all shippers' moves, and it lands before their renewal."

| Audience | One line |
|---|---|
| CRO | "Anchors live at the summit; say 'live for our largest customers', never 'all'." |
| COO | "Brokers stay on every other load until week 17, and the agent books inside your bands." |
| Compliance | "Trusted carriers only, and you own the list." |
| CFO | "$400k buys 3 weeks; it caps exposure under $50k before week 17." |

**Decision.** Push back in private, with a counter-offer and stage words, then back her decision in public. Weekly update to the CEO until week 17.

**Trap.** Pushing back in the staff meeting, or with a risk list and no alternative. Both make her choose between you and her promise.
