### Context
A mid-size online apparel retailer handles every "where is my return?" and "can I get a refund?" message with a 22-person support team. Median first response is 9 hours, and 40% of tickets are questions the returns policy already answers. Refund mistakes cost money in both directions: agents sometimes refund outside the policy window, and sometimes deny refunds the policy allows, which turns into chargebacks. Leadership wants a customer-facing agent in the web chat that answers policy questions and issues routine refunds on its own.

### Requirements
- Answer returns, exchange and refund questions from the current written policy, with a link to the section it used.
- Look up the signed-in customer's orders, shipments and return status.
- Issue refunds and prepaid return labels for eligible orders without a human, inside fixed limits.
- Hand off to a human in Zendesk with a summary when the request is out of policy, over a limit, or the customer asks for a person.
- Never show one customer's order to another, and never refund the same item twice.

### Scale and constraints
- 60,000 chat conversations a month, about 4 turns each; traffic triples during the two weeks after Black Friday.
- About 15% of conversations need an action (refund or label); average refund is $68.
- Policy: 420 help-center pages and a 30-page internal returns playbook, edited about 10 times a week.
- Orders live in Shopify Plus; payments in Stripe; tickets in Zendesk.
- Time to first token under 1.5 s at p95; a full refund flow under 20 s.
- Auto-refund limit: $200 per order and $400 per customer per 30 days. Anything above goes to a person.
- LLM budget: $3,000 a month. Team: three backend engineers, no GPUs, no ML platform.
- Card data never enters the model; transcripts kept 90 days.

### What a strong answer covers
- Where the refund limits and eligibility rules live, and what stops the model from going around them.
- How live order data and slow-changing policy text reach the model differently.
- What happens when a refund call times out and the client retries.
- How the agent decides it should stop and hand off, and what the human receives.
- A cost and latency estimate that fits the budget, with the prompt-cache effect shown.
- How you would prove the agent is better than the current team before turning it on for everyone.
