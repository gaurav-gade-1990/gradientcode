### Context

You are the principal AI architect at a mid-market accounting SaaS company: $180M ARR, 9,000 business customers. Every month 60M bank transactions flow in. A rules engine categorizes 72 percent of them; the other 28 percent sit in a queue until the customer's bookkeeper picks a category by hand, at about 20 seconds each. In May a competitor launched AI categorization, and sales says it is now coming up in renewals. The CTO wants your recommendation, at next week's staff meeting, on whether to buy, build or fine-tune.

### What you have

- **Revenue at stake.** 140 enterprise renewals worth $12M ARR fall in the next 12 months, and renewal season starts in 6 months. The competitor's AI was cited in 30 of this year's 80 lost-deal notes.
- **Team.** An applied AI team of 6 engineers. 4 can be moved for 6 months, but only by pausing the multi-entity consolidation feature, which then slips two quarters. The other 2 are committed to a compliance release. Fully loaded cost is assumed at $250k per engineer a year.
- **Budget.** The CFO caps new year-one spend (vendors, APIs, compute, contractors) at $1.5M. Existing salaries are not counted against it.
- **Data.** Two years of bookkeeper corrections: 400M labeled transactions.
- **Option A, buy.** A categorization vendor charges $0.004 per transaction, scored 91 percent correct on a 50,000-transaction bake-off, and needs 8 weeks to integrate. The vendor is not yet one of our listed sub-processors.
- **Option B, build on a hosted model API.** The team's prototype sends Haiku 5.5 each customer's chart of accounts and the 20 most similar past categorizations from that customer. It averages 1,500 input and 30 output tokens and scores 88 percent. Sending the least confident 10 percent on to Sonnet 5.5 raises that to 93 percent. In the prototype, the most confident 75 percent of suggestions were 98.5 percent correct. The model provider is already a listed sub-processor (it powers the support chatbot), and its contract includes zero data retention and no training on our data.
- **Option C, fine-tune.** Fine-tune an 8B open-weight model on the corrections. It scores 94 percent offline, on the data we are allowed to train on. The team estimates 9 months with all 6 engineers, then serving on 4 H100 GPUs at an assumed $2.50 per GPU-hour and a monthly retraining run at an assumed $15k.
- **Prices.** Haiku 5.5 costs $0.10 input and $0.50 output per million tokens; Sonnet 5.5 costs $2 and $10.
- **Growth.** Transaction volume grows 20 percent a year.

### The constraint

35 percent of ARR comes from enterprise contracts with two clauses. First, customer data may not be used to train any model that serves other customers. Second, we must give 90 days' notice before adding a sub-processor, and the customer may object. These are the same customers whose renewals are at stake.

### What a strong answer covers

- What each option really costs over three years, not just in year one, and what is already on payroll.
- Which option can ship by renewal season, and which ones the enterprise contracts quietly rule out or slow down.
- What happens when a categorization is wrong, at this volume.
- What you give up, and what would make you change your mind later.
- How you bring the CFO, the CPO, sales and legal along.
