### Context

You are the engineering manager of the leasing technology team at a mid-size apartment property-management company: 300 properties, 38,100 units, average rent $1,650 a month. Five months ago your team launched an AI leasing assistant at 40 properties. It answers prospective renters' web-chat and text inquiries and books tours straight into the property-management system (PMS). The pilot's stated goal was to cut leasing-agent overtime by 30 percent; overtime fell 2 percent, and the sponsor has gone quiet. Your manager, the VP of Engineering, wants your call in two weeks: kill it, scale it, or something in between.

### What you have

- **Pilot design.** 40 pilot properties against 40 matched control properties, for 5 months. 45,000 inquiries at pilot properties (9,000 a month) and 43,000 at control. 40 percent arrive after hours (6 pm to 8 am, and weekends), when no leasing agent is on duty; at control properties those inquiries wait until morning.
- **Results.** The assistant finished 62 percent of conversations without a human.
  - Tour-booking rate within 48 hours, business hours: 19.2 percent pilot against 18.8 percent control. Analytics calls this within noise (p ≈ 0.24).
  - Tour-booking rate within 48 hours, after hours: 17.5 percent pilot against 11.0 percent control. Analytics calls this significant.
  - Days vacant per unit turnover: 26.8 pilot against 29.1 control. Analytics puts the standard error of that difference at 0.8 days.
- **Operations feedback.** Leasing agents say 7 percent of handoffs from the assistant arrive without the conversation attached, so they start over with the renter.
- **Portfolio.** Annual unit turnover is 45 percent. Properties run on three PMS products: PMS-A at 120 properties (the only one the pilot integrates with), PMS-B at 110 and PMS-C at 70. The team estimates each new PMS integration at 2 engineers for 3 months.
- **Team.** 4 engineers and a PM. Fully loaded engineer cost is assumed at $250k a year. All 4 engineers have worked on the pilot for the full 5 months.
- **Model.** Every call goes to Opus 5.5. A conversation averages 6 model calls, each with 5,000 input tokens (4,000 of them a fixed prefix of property facts and leasing policy, served from the prompt cache) and 300 output tokens. Per million tokens, Opus 5.5 costs $4 input, $20 output and $0.20 for cache reads; Sonnet 5.5 costs $2, $10 and $0.20.
- **Legal review.** In 500 sampled transcripts, legal found 4 fair-housing problems: the assistant described who a building "suits", and answered a question about a neighborhood's demographics. The general counsel estimates one fair-housing complaint costs $50k to $150k to defend.

### The constraint

In 8 weeks, 2 of your 4 engineers move to the rent-payments migration for 6 months. The payment processor shuts down its old API on a fixed date, and that move is not negotiable. Whatever you keep running has to be built before then and run by the 2 engineers who stay.

### What a strong answer covers

- Whether the pilot failed, or measured the wrong thing.
- What the value really is in dollars, and how sure you are of it.
- What 2 engineers can actually run, and what scaling to all 300 properties would take.
- The fair-housing risk at a larger volume, and what controls it.
- What you tell your VP, the leasing operations director, legal and your team.
