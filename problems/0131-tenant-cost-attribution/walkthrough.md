## 1. What the problem is really asking

Strip away the finance story and this is **one pass of grouped sums, plus a lookup and a set of "already fired" flags**:

> for each event: look up the price that was in force on its date → compute its cost → add it to three running totals (tenant, tenant+feature, model) → check the tenant's budget thresholds, firing each one only once. After the loop: spread the shared costs over tenants in proportion to their direct spend.

None of the steps is hard on its own. The problem tests whether you get four billing rules right at once: the point-in-time price, cached tokens counted once, alerts that fire once, and a pro-rata split. Each rule has a matching `wrong_*.py` file, because each is a real billing incident.

The judge compares the whole returned dict, including the `alerts` list (in the order they fired, with the running `spent` value) and `unpriced` (in input order). Costs are compared with a relative tolerance of `1e-9`, so the order you add floats in doesn't matter, but every dollar has to be there.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `events` | usage records in time order | one pass, in order (alerts depend on the order) |
| `e["input_tokens"]` | **all** input tokens, cached ones included | uncached = `input_tokens - cached_input_tokens` |
| `e["cached_input_tokens"]` | the part of the input served from the prompt cache | billed at the cached rate |
| `prices[model]` | a list of `{"effective", "input", "cached_input", "output"}`, any order | find the latest `effective <= date` |
| `shared_costs` | `[{"name", "amount"}]` | only the sum `S` matters |
| `budgets` | `{tenant: dollars}`, possibly missing some tenants | alerts only for tenants with a budget |

Three details are easy to miss:

- **Prices are per million tokens.** Divide by `1e6` once, at the end of the cost formula.
- **`effective` dates compare as strings.** ISO `"YYYY-MM-DD"` sorts the same way as the dates it names, so `p["effective"] <= e["date"]` works without parsing.
- **The price list is not sorted.** "price entries out of order" puts the newest entry first, and "price entries oldest first" reverses the list. Don't take `prices[model][0]` or `[-1]`, or the first entry that applies. Scan for the best match.

## 3. Trace Example 1 by hand

Two events on 2026-10-03, $200 of shared cost (`vector-db` 120 + `eval-cluster` 80), no budgets.

**u-1, acme, mid-model.** The price cut is effective 2026-10-15, so on 10-03 the 2026-09-01 entry applies: $3.00 input, $0.30 cached, $15.00 output.

| part | tokens | rate | dollars |
|---|---|---|---|
| uncached input | 1,000,000 − 800,000 = 200,000 | 3.00 | 0.60 |
| cached input | 800,000 | 0.30 | 0.24 |
| output | 100,000 | 15.00 | 1.50 |
| **total** | | | **2.34** |

**u-2, globex, small-model.** One price entry (2026-09-01): 2,000,000 × 0.80 + 50,000 × 4.00, divided by a million, is 1.60 + 0.20 = **1.80**.

**Shared.** `S = 200`, `D = 2.34 + 1.80 = 4.14`.

- acme gets 200 × 2.34 / 4.14 = **113.043**, total 115.383.
- globex gets 200 × 1.80 / 4.14 = **86.9565**, total 88.7565.

`by_feature` is `{"acme": {"support-bot": 2.34}, "globex": {"doc-search": 1.8}}`, `by_model` is `{"mid-model": 2.34, "small-model": 1.8}`, and `unallocated_shared` is `0.0`.

### The alert trace: Example 3

Six small-model events of 1M input tokens each, at $0.80 each, against a $3.90 budget. The thresholds are $1.95 (50%), $3.12 (80%) and $3.90 (100%).

| event | running spent | 50% fires? | 80% fires? | 100% fires? |
|---|---|---|---|---|
| u-0 | 0.80 | no | no | no |
| u-1 | 1.60 | no | no | no |
| u-2 | 2.40 | **yes** | no | no |
| u-3 | 3.20 | already fired | **yes** | no |
| u-4 | 4.00 | already fired | already fired | **yes** |
| u-5 | 4.80 | already fired | already fired | already fired |

Three alerts, one per threshold. u-5 puts acme further over budget but fires nothing, because each (tenant, threshold) pair fires at most once.

## 4. Key idea: point-in-time pricing

A price is a fact about a date range, not a constant. When the provider cuts the price on 2026-10-15, events from before that date still owe the old price. Re-pricing history with today's list changes invoices you already sent. In Example 2, u-1 on 10-14 costs $3.00 and u-2 on 10-15 costs $2.50 (the cut applies on its effective date, since the test is `<=`). u-3 is dated 2026-08-30, before the first price entry, so it has no price and goes to `unpriced`. So does u-4, whose model `big-model` isn't in `prices` at all.

The lookup is a single scan that keeps the best candidate:

```python
best = None
for p in prices.get(model, []):
    if p["effective"] <= date and (best is None or p["effective"] > best["effective"]):
        best = p
```

`prices.get(model, [])` handles the unknown model, and `best` staying `None` handles the date before the first entry. Both become "unpriced" through the same `if p is None` check.

## 5. Key idea: cached tokens are a subset

Provider usage blocks (OpenAI's `prompt_tokens_details.cached_tokens`, Anthropic's cache-read count) report the cached tokens **inside** the input count. If you bill `input_tokens` at the full rate and then also add `cached_input_tokens` at the cached rate, every cached token is billed twice. In "cached tokens are billed once", the correct total is $14.50. Double-billing gives $34.50 and fires all three alerts against a $30 budget that the tenant never reached.

## 6. Plan before you code

```
direct, by_feature, by_model = {}, {}, {}
alerts, unpriced, fired = [], [], set()
for each event in order:
    p = price in force on its date for its model
    if none: record its id in unpriced; skip it
    cost = ((input - cached) * p.input + cached * p.cached_input + output * p.output) / 1e6
    add cost to direct[t], by_feature[t][feature], by_model[model]
    if t has a budget:
        for pct in 50, 80, 100:
            if (t, pct) not fired and direct[t] * 100 >= pct * budget: fire it
S = sum of shared amounts; D = sum of direct
for each tenant: shared = S * d / D (or 0 if D == 0); total = d + shared
unallocated_shared = S if D == 0 else 0.0
```

| situation | effect |
|---|---|
| model not in `prices` | unpriced |
| date before every `effective` | unpriced |
| tenant has no budget | costs counted, no alerts |
| `D == 0` (nothing priced) | no tenants, `unallocated_shared = S` |

## 7. Build it one piece at a time

**Step 1: the price lookup** (section 4). Keep it in its own function, so the main loop reads like the plan.

**Step 2: the cost and the three totals.** `dict.get(key, 0.0) + cost` is the simplest accumulator. `setdefault` creates the inner per-tenant dict for `by_feature` the first time a tenant appears:

```python
cached = e["cached_input_tokens"]
cost = ((e["input_tokens"] - cached) * p["input"] + cached * p["cached_input"] + e["output_tokens"] * p["output"]) / 1e6
direct[t] = direct.get(t, 0.0) + cost
feats = by_feature.setdefault(t, {})
feats[e["feature"]] = feats.get(e["feature"], 0.0) + cost
```

**Step 3: the alerts.** Check after adding the cost, so that `spent` is the running total right after this event. Loop over all three thresholds every time, because one large event can cross several at once ("one event crosses several thresholds" fires 50, 80 and 100 on the same event, `big`). Compare `spent * 100 >= pct * budget` instead of `spent >= pct / 100 * budget`, so that the result doesn't depend on how `0.8 * budget` rounds.

```python
if t in budgets:
    for pct in (50, 80, 100):
        if (t, pct) not in fired and direct[t] * 100 >= pct * budgets[t]:
            fired.add((t, pct))
            alerts.append({"tenant": t, "threshold": pct, "event_id": e["id"], "spent": direct[t]})
```

**Step 4: the shared split.** Do it after the loop, because it needs the month's total `D`. Guard against `D == 0`.

```python
S = sum(c["amount"] for c in shared_costs)
D = sum(direct.values())
```

When `D == 0`, `direct` is empty, so the loop over tenants does nothing and `by_tenant` is `{}`. The guard inside the loop is still worth keeping, so that the code never divides by zero.

## 8. Full solution

```python
# Find the price entry in force for a model on a given date, or None.
def _price(prices, model, date):
    best = None  # nothing found yet
    # Entries can be in any order, so look at all of them.
    for p in prices.get(model, []):
        # In force on this date, and newer than the best so far (ISO dates compare as strings).
        if p["effective"] <= date and (best is None or p["effective"] > best["effective"]):
            best = p  # the latest entry that applies so far
    return best  # None for an unknown model or a date before the first entry


# One pass for direct costs and alerts, then a pro-rata split of shared costs.
def attribute_costs(events, prices, shared_costs, budgets):
    direct, by_feature, by_model = {}, {}, {}  # the three groupings of direct cost
    alerts, unpriced, fired = [], [], set()  # alerts in firing order, skipped ids, and (tenant, pct) already fired
    # Events are in time order, which the alerts depend on.
    for e in events:
        p = _price(prices, e["model"], e["date"])  # point-in-time price
        # No price applies, so this event can't be billed.
        if p is None:
            unpriced.append(e["id"])  # report it for follow-up
            continue  # it contributes nothing else
        cached = e["cached_input_tokens"]  # a subset of input_tokens
        # Uncached input at the full rate, cached at the discount, output at the output rate; per million.
        cost = ((e["input_tokens"] - cached) * p["input"] + cached * p["cached_input"] + e["output_tokens"] * p["output"]) / 1e6
        t = e["tenant"]  # who pays for this event
        direct[t] = direct.get(t, 0.0) + cost  # the tenant's running direct cost
        feats = by_feature.setdefault(t, {})  # this tenant's per-feature totals
        feats[e["feature"]] = feats.get(e["feature"], 0.0) + cost  # add to the feature's total
        by_model[e["model"]] = by_model.get(e["model"], 0.0) + cost  # add to the model's total
        # Only tenants with a budget get alerts.
        if t in budgets:
            # Lowest threshold first, so one big event fires them in order.
            for pct in (50, 80, 100):
                # Not fired yet, and spend has reached the threshold (multiplied out to avoid rounding).
                if (t, pct) not in fired and direct[t] * 100 >= pct * budgets[t]:
                    fired.add((t, pct))  # never fire this pair again
                    # Record the alert with the running total right after this event.
                    alerts.append({"tenant": t, "threshold": pct, "event_id": e["id"], "spent": direct[t]})
    S = sum(c["amount"] for c in shared_costs)  # all shared infrastructure for the month
    D = sum(direct.values())  # all direct cost, the denominator of the split
    by_tenant = {}  # direct, shared and total per tenant
    # Every tenant with a priced event gets a row.
    for t, d in direct.items():
        share = S * d / D if D > 0 else 0.0  # pro rata to direct spend; guard the division
        by_tenant[t] = {"direct": d, "shared": share, "total": d + share}  # the tenant's bill
    # Shared cost stays unallocated only when nothing was priced.
    return {"by_tenant": by_tenant, "by_feature": by_feature, "by_model": by_model, "alerts": alerts,
            "unpriced": unpriced, "unallocated_shared": 0.0 if D > 0 else float(S)}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | acme 2.34 + 113.043 shared, globex 1.80 + 86.9565 | cached tokens billed once; shared split pro rata |
| Example 2 | acme direct 5.5; `unpriced` `["u-3", "u-4"]` | the price cut applies on its effective date; a date before the first entry and an unknown model are both unpriced |
| Example 3 | three alerts, on u-2, u-3 and u-4 | each threshold fires once; u-5 fires nothing |
| one event crosses several thresholds | 50, 80 and 100 all fire on `big` with spent 30 | loop over every threshold after each event |
| cached tokens are billed once | direct 14.5, no alerts | `(input - cached)` at the full rate |
| no priced events leaves shared unallocated | `by_tenant` `{}`, `unallocated_shared` 200 | the `D == 0` path |
| price entries out of order | a costs 15, b costs 10; 50% fires on a, 80% on b | scan every entry instead of trusting list order |
| price entries oldest first | o1 costs 2.5, not 3 | the first entry that applies (2026-09-01) is not the latest one (2026-10-15) |
| month of traffic | globex crosses 50, 80, 100 on u-0109, u-0184, u-0235 | everything at once over 240 events |

## 10. Complexity

Let `n` be the number of events and `k` the number of price entries per model. Each event scans its model's entries, so the time is O(n·k), and with `k` around 2 that's O(n). Memory is O(tenants × features + models + alerts). 5,000 events take well under a millisecond each.

At production scale (billions of events a month) the shape stays the same but moves into the warehouse: a range join of events to price rows on `effective <= date < next_effective`, then `GROUP BY tenant, feature, model`. Precompute the price ranges (each entry's end date is the next entry's start) so the join is a simple range lookup. The alerts can't wait for the month-end batch: run them in a streaming job keyed by tenant, with the `fired` set stored per tenant and month.

## 11. If you got Wrong Answer

- **Alerts repeat, for example a second `threshold` 50 alert on u-3 in Example 3.** You don't remember which thresholds fired. Keep a `fired` set of `(tenant, pct)`.
- **Example 1 has acme at 4.74 instead of 2.34, or "cached tokens are billed once" shows 34.5 instead of 14.5 with three alerts.** You billed all of `input_tokens` at the full rate and the cached tokens again. Subtract `cached` first.
- **Example 1 gives both tenants exactly 100 of shared cost.** You split `S` evenly. Use `S * d_t / D`.
- **Example 2 has acme at 7.5 and only u-4 in `unpriced`.** You used the latest price for every event, ignoring the date. Require `effective <= date`.
- **"price entries out of order" bills b at $15 instead of $10, and a 100% alert fires.** You kept the last entry in the list that applies (`effective <= date`) instead of the one with the latest `effective` date. The list is not sorted, so compare dates.
- **`ZeroDivisionError` on "no priced events leaves shared unallocated".** Guard `D > 0`, and return `unallocated_shared = S`.
- **"price entries oldest first" bills o1 at $3 instead of $2.50.** You returned the first entry with `effective <= date`. That is right only when the list is newest first. Keep scanning and take the latest `effective`.
- **Only one alert fires on `big` in "one event crosses several thresholds".** You `break` after the first threshold fires.

## 12. Follow-ups an interviewer might ask

- *How would you reconcile this with the provider's invoice?* Sum `by_model` for the month and compare it with the provider's usage and cost API (the Anthropic Admin API usage reports, the OpenAI usage and costs endpoints). Investigate anything off by more than about 1%: usually a missing tag or a price-table error.
- *What should happen at 100% of budget?* Alerting is the minimum. Many platforms then downgrade the tenant to a cheaper model (problem 126, model-router) or apply a hard rate limit (problem 123, token-bucket-rate-limiter).
- *Is pro rata to spend always the fair split?* No. It suits costs that grow with tokens. A vector database scales with stored vectors, so splitting it by storage GB per tenant is fairer. Keep the allocation key per shared cost as data.
- *What about cache writes, batch discounts and long-context tiers?* Add them as more price fields with effective dates. Cache writes cost more than plain input (problem 128, prompt-caching-cost), batch jobs cost less, and some models charge more above a context length.
- *A price change is announced late and backdated. What do you do?* Because events are immutable and prices are data with effective dates, add the new price row and re-run the job for the affected month. Never edit the stored costs in place.
