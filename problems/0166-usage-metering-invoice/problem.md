Your platform bills each tenant monthly for its AI coworkers: a base fee for the plan plus metered usage (agent tasks, thousands of tokens, tool calls). Usage events arrive from Kafka with at-least-once delivery, and customers upgrade mid-month. Write the function that turns one tenant's month into invoice lines.

`build_invoice(plans, plan_changes, events, period_days)` returns

```
{"lines": [...], "total": int, "duplicates": int, "out_of_period": int}
```

All money is in **integer cents**. Use integer arithmetic throughout.

**Inputs**

- `plans`: `{plan_name: {"base_fee": cents, "meters": {meter: {"included": units, "tiers": [{"up_to": int or None, "unit_price": cents}, ...]}}}}`. Tiers are in increasing `up_to` order and the last has `up_to: None`. Every plan prices every meter that appears in `events`.
- `plan_changes`: `[{"day": d, "plan": name}, ...]` with strictly increasing days. The first entry has `day == 0`. Every day is `< period_days`.
- `events`: `[{"id": str, "day": int, "meter": str, "qty": int}, ...]` in arrival order.

**Rules**, applied in this order:

1. **Dedupe.** Keep the first event with each `id`. Count every later event with an already-seen `id` in `duplicates` and ignore it.
2. **Period.** Of the kept events, ignore those with `day < 0` or `day >= period_days`, and count them in `out_of_period`.
3. **Segments.** Plan change `k` starts segment `k`, covering days `[day_k, day_{k+1})`. The last segment ends at `period_days`. Let `days_k` be its length. An event belongs to the segment that contains its `day`.
4. **Base line.** `base_fee * days_k // period_days`.
5. **Meter lines.** For each meter of the segment's plan, in sorted meter-name order:
   - `used` = total `qty` of that segment's events for the meter
   - `included` = `meter_included * days_k // period_days`
   - `billable` = `max(0, used - included)`
   - `amount` = graduated pricing of the `billable` units: tier `i` prices the units above the previous tier's `up_to` (0 for the first tier) up to and including its own `up_to`, at its `unit_price`.

**Lines**, in segment order, each segment's base line first and then its meter lines:

```
{"segment": k, "plan": name, "item": "base", "days": days_k, "amount": cents}
{"segment": k, "plan": name, "item": meter, "used": u, "included": i, "billable": b, "amount": cents}
```

`total` is the sum of every line's `amount`.

**Constraints**

- `1 <= period_days <= 31`, `1 <= len(plan_changes) <= 5`
- `0 <= len(events) <= 2000`, `0 <= qty <= 10^6`
