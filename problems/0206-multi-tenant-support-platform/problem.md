### Context
A help-desk software company sells an AI support agent as an add-on to its B2B customers. Two hundred tenants have signed, from a 40-person bike shop to an airline, and each wants the agent to speak in its brand voice, answer from its own help center and act in its own Shopify, Salesforce or custom systems. Today each tenant is a hand-tuned deployment: prompt changes are copied by hand, one tenant's holiday spike slowed everyone last December, and finance cannot say what any tenant costs to serve. Leadership wants one shared platform where onboarding a tenant is configuration, not code.

### Requirements
- One agent runtime serving all tenants, with per-tenant prompts, knowledge, tools, limits and model tier.
- Tenants edit their own configuration in an admin console; a change goes live only after it passes that tenant's evals.
- Actions (refunds, cancellations, returns) can take minutes or days and must survive deploys and restarts.
- No tenant can ever see another tenant's data, prompts or tool credentials.
- Per-tenant quotas, cost attribution and usage billing.

### Scale and constraints
- 3 million conversations a month, about 5 turns each; business-hours peak is 4 times the average.
- Tiers: 20 Enterprise tenants carry 50% of traffic, 60 Growth carry 35%, 120 Starter carry 15%.
- The largest tenant is 8% of traffic and runs flash sales that send 10 times its normal load.
- Knowledge bases from 200 to 400,000 articles per tenant; 10 million chunks in total.
- Time to first token under 1.5 s at p95 for Enterprise, 2.5 s for Starter.
- Priced at $0.80 per resolved conversation; model spend must stay under $120,000 a month.
- Team: eight engineers. SOC 2 Type II; Enterprise tenants may require their own encryption keys.

### What a strong answer covers
- How one tenant's surge is kept from hurting the other 199, and what happens to the overflow.
- Where tenant isolation is enforced, at each layer, and how you would prove it.
- How a tenant's prompt or tool change is tested and rolled out without risk to the rest.
- Where long-running actions live, separate from the chat turn.
- Monthly model cost by tier, and the one lever that moves it most.
- How cost and usage are attributed to each tenant.
