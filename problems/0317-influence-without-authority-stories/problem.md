### Context

The interviewer asks: **"Tell me about a time you got another org to change direction when you had no authority over them."** This is a behavioral question, and it is graded on level: the scope you moved, the money involved, the people you brought along and the risk you took on. If you have a real story of your own, use it, and use this case to give it structure. If you don't, build your answer from the background below; the model answer does.

The background: you were the principal ML engineer for search and substitutions at a national online grocery delivery platform with $2.4B of gross merchandise value (GMV) a year and 2.5M orders a month. When an item is out of stock, a substitution model picks a replacement, and customers rejected 22 percent of those picks. Most of the cause sat in product data owned by the Catalog org: a different VP, 40 engineers, and the next two quarters already committed to a seller portal. Quarterly planning locked in 5 weeks.

### What you have

- **Volume.** An average order has 40 items, and 8 percent of items are substituted. Revenue is 15 percent of GMV.
- **Cost of a rejection.** Finance puts each rejected substitution at $1.50 (refund handling, wasted picking, support contacts).
- **Root cause.** You sampled 2,000 rejected substitutions: 45 percent traced to a wrong or missing catalog attribute, such as size, a dietary flag or brand tier.
- **Catalog.** 1.2M SKUs, 18 percent with at least one wrong or missing attribute, and 60,000 new SKUs a month. Catalog's 6-person data-ops team fixes attributes by hand: 2,000 tickets a month at about 20 minutes each, with an assumed 140 working hours per person a month.
- **Your pilot.** Over two weeks you ran a pilot on 5,000 high-volume SKUs. Haiku 5.5 extracted attributes from supplier spec sheets, at about 2,000 input and 200 output tokens per SKU, and the least confident 10 percent went on to Sonnet 5.5. Reviewers checked the 15 percent of SKUs with low-confidence fields, at about 40 seconds each and an assumed $32 an hour. Attribute-driven rejections on those SKUs fell 60 percent.
- **Catalog's commitment.** Seller portal v1 by the end of Q2, a date the CEO gave the board. It onboards 300 regional sellers worth $18M a year of GMV, bringing 90,000 new SKUs. 120 of those sellers need portal phase 2 (bulk upload).
- **People.** Catalog can free 4 engineers for one quarter, but only if bulk upload slips 6 weeks. Your director can lend 3 of your team's 12 engineers for a quarter, which delays your personalization ranking launch by one quarter; that launch was projected to lift revenue 0.6 percent. Fully loaded engineer cost is assumed at $240k a year.
- **Prices.** Haiku 5.5 costs $0.10 input and $0.50 output per million tokens; Sonnet 5.5 costs $2 and $10.

### The constraint

The Catalog VP owns a board-level date and has already said no to "a data cleanup project" twice. Your own VP will not escalate it to the CTO this quarter. So persuasion is the only route, and whatever you ask for has to fit beside a portal date that cannot move, paid for partly out of your own roadmap.

### What a strong answer covers

- A story told with "I": what you personally did, separate from what your team or the other org did.
- The number that changed the other org's mind, and why it mattered to them, not just to you.
- The options you weighed, including escalating, and why you didn't take them.
- What you gave up yourself to make it happen, and who ended up owning the result.
- A quantified result, a guard that shows nothing else broke, and what you'd do differently.
