Finance wants a monthly report of LLM spend by tenant, feature and model, with shared infrastructure costs spread fairly, and every account manager wants an alert when their customer crosses 50%, 80% and 100% of budget. Write the attribution job.

`attribute_costs(events, prices, shared_costs, budgets)` takes

- `events`: usage records in chronological order, `{"id", "date", "tenant", "feature", "model", "input_tokens", "cached_input_tokens", "output_tokens"}`. `date` is `"YYYY-MM-DD"`. As in the OpenAI and Anthropic usage blocks, `input_tokens` **includes** the cached tokens.
- `prices`: `{model: [{"effective", "input", "cached_input", "output"}, ...]}`. Prices are US dollars per million tokens (illustrative) and the entries can be in any order.
- `shared_costs`: `[{"name", "amount"}]`, such as the vector database or the eval cluster, in dollars for the month.
- `budgets`: `{tenant: monthly_budget_dollars}`. Not every tenant has one.

**Pricing an event.** Use the price entry for its model with the **latest `effective` date that is on or before the event's `date`**. If there is none (an unknown model, or a date before the first entry), the event is **unpriced**: add its id to `unpriced`, and it contributes nothing anywhere else. Otherwise

$$
\text{cost} = \frac{(\text{input} - \text{cached}) \cdot p_{in} + \text{cached} \cdot p_{cached} + \text{output} \cdot p_{out}}{10^6}
$$

**Shared costs.** Let `S` be the sum of all `shared_costs` amounts, `D` the total direct cost of all priced events, and `d_t` tenant `t`'s direct cost. Tenant `t` gets `S * d_t / D`. If `D == 0`, nothing is allocated, and `unallocated_shared = S`. Otherwise `unallocated_shared = 0.0`.

**Budget alerts.** Walk the priced events in order and keep each tenant's running direct cost. After adding an event's cost, for each threshold in `50, 80, 100` (in that order) that has not fired yet for that tenant, fire it if `spent * 100 >= threshold * budget`. Each (tenant, threshold) pair fires **at most once**. An alert is `{"tenant", "threshold", "event_id", "spent"}`, where `spent` is the running total right after that event. Shared costs don't count toward alerts, because they're allocated at month end.

Return

```
{"by_tenant":  {tenant: {"direct", "shared", "total"}},     # every tenant with a priced event
 "by_feature": {tenant: {feature: direct_cost}},
 "by_model":   {model: direct_cost},
 "alerts":     [alert, ...],                                 # in the order they fired
 "unpriced":   [event_id, ...],                              # in input order
 "unallocated_shared": float}
```

**Constraints**

- At most 5,000 events; token counts are non-negative integers with `cached_input_tokens <= input_tokens`
- Budgets are positive
