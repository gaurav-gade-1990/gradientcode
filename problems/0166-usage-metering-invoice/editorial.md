## Approach

An invoice is a pure function of the deduplicated usage and the plan timeline. Do it in three passes.

1. **Dedupe, then filter.** Keep the first event per id. Kafka and most usage pipelines are at-least-once, so redelivery is normal, not an error.
2. **Segment the month.** Each plan change opens a half-open interval `[day_k, day_{k+1})`. Half-open intervals tile the month with no gaps and no overlap, and the change day belongs to the new plan.
3. **Price each segment.** Prorate the base fee and the included quota by `days_k / period_days` with floor division, then run graduated tiers over the billable units.

```python
def graduated(units, tiers):
    total, floor = 0, 0
    for t in tiers:
        top = units if t["up_to"] is None else min(units, t["up_to"])
        if top <= floor:
            break
        total += (top - floor) * t["unit_price"]
        if t["up_to"] is None:
            break
        floor = t["up_to"]
    return total
```

For 1250 billable tasks with tiers `≤1000 @ 10, rest @ 6`, that's `1000·10 + 250·6 = 11500`.

## Common mistakes

- **Counting redelivered events.** A consumer restart replays a batch and the customer is billed twice for the same agent tasks.
- **Volume pricing when the contract says graduated.** Pricing every unit at the rate of the tier the total lands in creates a cliff: one more task can lower the bill by thousands.
- **A full quota in every segment.** A customer who upgrades on day 29 gets two full monthly allowances.
- **Closed intervals at the change.** Billing the change day to the old plan (or to both) shifts usage between rate cards, which is exactly the kind of discrepancy finance escalates.

## Production notes

- Stripe Billing, Metronome, Orb and Lago all expose these primitives: an idempotency key per usage event, graduated vs volume tiers, and proration on plan changes. Stripe prorates to the second by default; daily granularity is a simplification.
- Deduplicate at ingest with a window keyed by event id (a Redis set with a TTL, or a unique index in the warehouse), and keep the raw events. Invoices must be reproducible months later when a customer disputes one.
- Use integer minor units (cents, or micro-dollars for token pricing) and pick the rounding rule once. Floats drift, and the sum of the lines must equal the total.
- Close the period after a grace window so late events land in the right month, and route the rest into a credit or adjustment on the next invoice instead of silently dropping them.
- Pairs with `tenant-cost-attribution` (what usage costs you) and `idempotent-tool-execution` (making the producer side idempotent too).
