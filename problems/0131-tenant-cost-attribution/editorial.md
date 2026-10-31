## Approach

This is one pass over the events to get the direct costs and alerts, then one pass over the tenants to allocate the shared costs.

```python
p = latest entry with effective <= date          # point-in-time price
cost = ((inp - cached) * p.input + cached * p.cached_input + out * p.output) / 1e6
direct[t] += cost
for pct in (50, 80, 100):
    if (t, pct) not in fired and direct[t] * 100 >= pct * budget[t]:
        fire once
...
share_t = S * direct_t / D                       # pro rata
```

Two details carry the problem:

- **Point-in-time prices.** A price is a fact about a date range, not a constant. Re-pricing history with today's list breaks every past invoice.
- **Cached tokens are a subset of input tokens.** The usage block reports `input_tokens` (or `prompt_tokens`) together with a cached count *inside* it. Bill the uncached remainder at the full rate and the cached part at the discount.

The threshold test uses `spent * 100 >= pct * budget` so that the comparison doesn't depend on how `0.8 * budget` rounds.

## Common mistakes

- **Using today's prices for last month.** After a price cut you under-bill, and after an increase you over-bill.
- **Double-billing cached tokens.** You charge full price plus the cached price on the same tokens.
- **Alert storms.** Alerting on every event over the line trains people to ignore the channel.
- **Splitting shared costs evenly.** A trial tenant ends up paying the same infrastructure cost as your biggest customer. Pro rata to usage is the usual default.

## Production notes

- Tag every model call at the gateway with tenant, feature, model and a request id, and emit the provider's usage block, not your own token estimate. Store these as immutable events (in Kafka, then the warehouse), so that a price change re-runs the job instead of mutating rows.
- Provider invoices are the ground truth. Reconcile the monthly totals per model against the provider's usage and cost APIs (the Anthropic Admin API usage reports, the OpenAI usage and costs endpoints) and investigate drift above about 1%.
- Real price tables have more dimensions: batch-API discounts, cache-write premiums (problem 128), long-context tiers, and regional or provisioned-throughput pricing. Keep them as data with effective dates, like here.
- Budgets need enforcement as well as alerts. At 100%, many platforms switch the tenant to a cheaper model (problem 126) or a hard limit (problem 123) rather than only sending an email.
- For shared costs, "pro rata to direct spend" is simple and defensible. Other allocation keys (requests, storage GB, seats) suit costs that don't scale with tokens, such as the vector DB.
