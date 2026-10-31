## 1. What the problem is really asking

A tenant pays a monthly plan fee plus metered usage: agent tasks, tool calls, tokens. The usage arrives as events from a stream that delivers **at least once**, so some events show up twice. And customers change plans in the middle of the month. You're turning one tenant's month into invoice lines.

Under the story it's three small, exact computations, done in a fixed order:

1. **Dedupe by id**, then drop events outside the period. A set of seen ids, nothing more.
2. **Split the month into half-open intervals** `[day_k, day_{k+1})`, one per plan, and bucket each event by its day.
3. **Price each interval.** Prorate the base fee and the free allowance with integer floor division, then run **graduated tiers** over what's left.

The judge compares every line exactly (`rtol` and `atol` are both 0), plus `total`, `duplicates` and `out_of_period`. Money is integer cents, so a single cent off anywhere is a Wrong Answer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `plans[name]["base_fee"]` | the monthly fee in cents | prorated per segment |
| `plans[name]["meters"][m]["included"]` | free units per month | prorated per segment |
| `plans[name]["meters"][m]["tiers"]` | `[{"up_to", "unit_price"}, ...]`, last `up_to` is `None` | graduated pricing |
| `plan_changes` | `[{"day", "plan"}]`, first at day 0, strictly increasing | segment boundaries |
| `events` | `[{"id", "day", "meter", "qty"}]` in arrival order | dedupe, filter, bucket |
| `period_days` | days in the month, 1 to 31 | proration denominator and the period's end |

Three details are easy to miss:

- **Dedupe runs before the period filter.** The first copy of an id decides everything. A redelivered copy of an out-of-period event counts as a duplicate, not as a second out-of-period event.
- **Multiply first, then floor-divide.** `base_fee * days // period_days`, never `base_fee // period_days * days`. The second throws away the remainder before multiplying: growth's 90000 over a 31-day month becomes `90000 // 31 * 31 = 89993`, seven cents short even with no plan change.
- **Meter lines come from the segment's plan**, in sorted meter-name order, including meters with zero usage. Every plan here has `agent_tasks` and `tool_calls`, so every segment has exactly three lines.

## 3. Trace Example 2 by hand

Starter on day 0, growth from day 10, `period_days = 30`. Four events, no duplicates.

**Dedupe and filter.** All four ids are distinct. `evt_00004` is on day 30, and the period is days 0 to 29, so it's dropped: `out_of_period = 1`.

**Segments.**

| segment | plan | days | events |
|---|---|---|---|
| 0 | starter | `[0, 10)` = 10 | `evt_00001` (day 4, 400 tasks) |
| 1 | growth | `[10, 30)` = 20 | `evt_00002` (day 10, 1200 tasks), `evt_00003` (day 29, 25000 tool calls) |

The day-10 event belongs to growth. The interval is half-open: the change day starts the new plan.

**Lines.**

| segment | item | used | included | billable | amount |
|---|---|---|---|---|---|
| 0 | base | | | | `30000 * 10 // 30 = 10000` |
| 0 | agent_tasks | 400 | `300 * 10 // 30 = 100` | 300 | `300 × 10 = 3000` |
| 0 | tool_calls | 0 | `3000 * 10 // 30 = 1000` | 0 | 0 |
| 1 | base | | | | `90000 * 20 // 30 = 60000` |
| 1 | agent_tasks | 1200 | `1500 * 20 // 30 = 1000` | 200 | `200 × 8 = 1600` |
| 1 | tool_calls | 25000 | `20000 * 20 // 30 = 13333` | 11667 | `11667 × 1 = 11667` |

`total` is 10000 + 3000 + 0 + 60000 + 1600 + 11667 = **86267**. Note the floor in `13333`: `400000 / 30` is 13333.33, and the customer gets the floor.

**The trickiest hidden case, "duplicate of an out-of-period event".** The events are `evt_00001` on day 31 twice and `evt_00002` on day 5 twice, with a 30-day period. Dedupe first: the second copy of each id is a duplicate, so `duplicates = 2`. Then filter: the one remaining `evt_00001` is outside the period, so `out_of_period = 1`. One 500-task event is billed: 500 − 300 included = 200 billable × 10 = 2000, total 32000. If you filter first you get `duplicates: 1, out_of_period: 2`, with the same total, and the case still fails.

## 4. Key idea: graduated, not volume, tiers

Graduated tiers price each unit in the tier it falls into. Starter's agent tasks are 10 cents each up to 1000, then 6 cents. For Example 1's 1250 billable tasks:

```
first 1000 units  × 10 = 10000
next   250 units  ×  6 =  1500
                         -----
                         11500
```

The tempting alternative is volume pricing: find the tier the *total* lands in and charge every unit at that rate. That gives `1250 × 6 = 7500`. It also creates a cliff, which is why contracts that say "graduated" mean it:

| billable | graduated | volume |
|---|---|---|
| 1000 | 10000 | 10000 |
| 1001 | 10006 | 6006 |

One more task lowers the volume bill by 39.94 dollars. With graduated pricing, the bill only ever goes up as usage goes up.

The loop walks the tiers with a running `floor`, the previous tier's `up_to`. In each tier the units are `min(units, cap) - floor`, or `units - floor` for the open last tier. Stop as soon as a tier gets no units. "three tiers" exercises all of growth's three tiers: 14500 billable tasks are `2000 × 8 + 8000 × 5 + 4500 × 3 = 16000 + 40000 + 13500 = 69500`. Volume would charge `14500 × 3 = 43500`.

## 5. Key idea: prorate the allowance, not just the fee

A customer who upgrades on day 10 shouldn't get a full month of free starter tasks *and* a full month of free growth tasks. Each segment gets `included * days_k // period_days`. In Example 2, giving the full allowance to each segment would make starter include 300 tasks (only 100 billable) and growth include 1500 tasks (none billable) and 20000 tool calls (5000 billable), for a total of 76000 instead of 86267.

The proration uses floor division for both the fee and the allowance. That's the rule the problem fixes. The point is to pick one rounding rule and apply it everywhere, so every invoice can be reproduced exactly from the raw events.

## 6. Plan before you code

```
seen = set()
for e in events (arrival order):
    id seen before            -> duplicates += 1, skip
    mark id seen
    0 <= day < period_days    -> keep
    else                      -> out_of_period += 1
starts = change days; ends = starts[1:] + [period_days]
for each segment k:
    days = ends[k] - starts[k]
    base line: base_fee * days // period_days
    for meter in sorted(plan meters):
        used = sum qty of kept events for meter with start <= day < end
        included = meter included * days // period_days
        billable = max(0, used - included)
        amount = graduated(billable, tiers)
total = sum of line amounts
```

## 7. Build it one piece at a time

**Step 1: graduated pricing.** A standalone function you can test on its own with the numbers above:

```python
def graduated(units, tiers):
    total, floor = 0, 0
    for tier in tiers:
        cap = tier["up_to"]
        in_tier = units - floor if cap is None else min(units, cap) - floor
        if in_tier <= 0:
            break
        total += in_tier * tier["unit_price"]
        if cap is None:
            break
        floor = cap
    return total
```

`up_to` is inclusive. "exactly at quota and tier edge" has 1000 billable tasks, which fill tier 1 exactly: `min(1000, 1000) - 0 = 1000` units at 10 is 10000, and then tier 2 gets `1000 - 1000 = 0` and the loop stops.

**Step 2: dedupe, then filter.** Mark the id as seen *before* the period check, so a later copy of an out-of-period event is still a duplicate:

```python
    for e in events:
        if e["id"] in seen:
            duplicates += 1
            continue
        seen.add(e["id"])
        if 0 <= e["day"] < period_days:
            kept.append(e)
        else:
            out_of_period += 1
```

"three segments, 31 days" has an event on day `-1`, so the lower bound matters too.

**Step 3: segment boundaries.** Shifting the start list by one gives each segment's end, and the last one ends at `period_days`:

```python
    starts = [c["day"] for c in plan_changes]
    ends = starts[1:] + [period_days]
```

The bucket test is `lo <= e["day"] < hi`. Using `<` on the right is what puts a change-day event in the new plan and keeps any day from being counted twice.

**Step 4: the lines.** Keep everything an `int`. `/` would give floats like `6774.19` for starter's 7-day base fee in a 31-day month, where the expected value is `6774`.

## 8. Full solution

```python
def graduated(units, tiers):  # price units tier by tier, each unit at the rate of the tier it falls in
    total, floor = 0, 0  # cents so far, and the previous tier's upper bound
    for tier in tiers:  # tiers come in increasing up_to order
        cap = tier["up_to"]  # this tier's inclusive upper bound, or None for the open last tier
        in_tier = units - floor if cap is None else min(units, cap) - floor  # units that land in this tier
        if in_tier <= 0:  # every unit was priced by an earlier tier
            break  # nothing left to charge
        total += in_tier * tier["unit_price"]  # charge this tier's units at its own price
        if cap is None:  # the open tier takes everything that remains
            break  # so there is no later tier
        floor = cap  # the next tier starts above this bound
    return total  # integer cents


def build_invoice(plans, plan_changes, events, period_days):  # one tenant's month as invoice lines
    seen, kept = set(), []  # ids already delivered, and the events we will bill
    duplicates = out_of_period = 0  # counters for the report
    for e in events:  # arrival order, so the first copy of an id wins
        if e["id"] in seen:  # at-least-once delivery sent this one again
            duplicates += 1  # count the redelivery
            continue  # and never bill it twice
        seen.add(e["id"])  # mark it before the period check, so its copies are duplicates
        if 0 <= e["day"] < period_days:  # inside this billing period
            kept.append(e)  # it will be billed
        else:  # late or early: belongs to another month
            out_of_period += 1  # count it, don't bill it

    starts = [c["day"] for c in plan_changes]  # each plan change opens a segment
    ends = starts[1:] + [period_days]  # each segment ends where the next begins; the last at month end
    lines = []  # invoice lines in segment order
    for k, change in enumerate(plan_changes):  # one segment per plan change
        plan = plans[change["plan"]]  # the rate card in force for this segment
        lo, hi = starts[k], ends[k]  # the half-open day range [lo, hi)
        days = hi - lo  # the segment's length, the proration numerator
        # base fee prorated by days; multiply before floor-dividing so no cents are lost early
        lines.append({"segment": k, "plan": change["plan"], "item": "base", "days": days,
                      "amount": plan["base_fee"] * days // period_days})
        for meter in sorted(plan["meters"]):  # every meter of this plan, in name order
            spec = plan["meters"][meter]  # its allowance and tiers
            used = sum(e["qty"] for e in kept if e["meter"] == meter and lo <= e["day"] < hi)  # usage in [lo, hi)
            included = spec["included"] * days // period_days  # allowance prorated like the fee
            billable = max(0, used - included)  # only usage above the allowance is charged
            # the meter line, priced with graduated tiers
            lines.append({"segment": k, "plan": change["plan"], "item": meter, "used": used, "included": included,
                          "billable": billable, "amount": graduated(billable, spec["tiers"])})
    # the total is the sum of the lines, so lines and total always agree
    return {"lines": lines, "total": sum(l["amount"] for l in lines), "duplicates": duplicates, "out_of_period": out_of_period}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | total 41500, `duplicates: 1`; tasks 1250 billable = 11500 | dedupe by id, graduated tiers across one boundary |
| Example 2 | total 86267, `out_of_period: 1` | proration of fee and allowance, the change-day event goes to growth |
| no usage | total 90000, three lines | zero-usage meter lines still appear; floor of a full month is the full fee |
| exactly at quota and tier edge | tasks 1000 billable = 10000; tool calls 3000 used, 0 billable | `up_to` is inclusive; usage equal to the allowance costs nothing |
| three tiers | tasks 69500, tool calls 50000, total 209500 | all three of growth's tiers, and a 0-cent last tier |
| downgrade mid month | total 205500; enterprise 21 days, starter 7 | plan changes go down as well as up |
| three segments, 31 days | total 184195; base lines 6774, 34838, 96774 | floor division with a 31-day denominator; a day `-1` event |
| duplicate of an out-of-period event | `duplicates: 2`, `out_of_period: 1`, total 32000 | dedupe runs before the period filter |
| redelivery storm, long stream | totals 281953 and 342009 | everything at once over hundreds of events with redeliveries |

## 10. Complexity

Dedupe is O(n) with a set. The straightforward `used` sum scans every kept event once per (segment, meter), so it's O(s · m · n) for s segments and m meters. With at most 5 segments, 2 meters and 2000 events that's 20000 comparisons. Grouping events by (segment, meter) in one pass would make it O(n), which is what you'd do for a big tenant.

In production, the expensive part is dedupe at ingest: you need every event id for the period, which is a unique index in the warehouse or a set with a TTL. Keep the raw events, too. When a customer disputes an invoice months later, you must be able to rebuild it exactly, and integer cents with one fixed rounding rule is what makes that possible.

## 11. If you got Wrong Answer

- **Example 1's total is 45400 and `duplicates` is 0.** You're billing redelivered events. Track seen ids and skip repeats.
- **Example 1's tasks line is 7500, or "three tiers" gives 43500.** Volume pricing: every unit at the rate of the tier the total lands in. Price each tier's units separately.
- **Example 2 bills the 1200 day-10 tasks to starter (total 94667).** The change day went to the old plan. Segments are `[day_k, day_{k+1})`.
- **Example 2's `included` shows 300 and 1500 (total 76000).** You gave each segment the full monthly allowance. Prorate it with `* days // period_days`.
- **"duplicate of an out-of-period event" shows `duplicates: 1, out_of_period: 2`.** You filtered by period before deduping. Mark the id seen first.
- **"no usage" gives a base of 89993.** You divided before multiplying. Use `base_fee * days // period_days`.
- **Amounts like 6774.19 or 34839 in "three segments, 31 days".** You used `/`, or `round()`. The rule is integer floor division.

## 12. Follow-ups an interviewer might ask

- *Events can arrive after the month closes. What do you do?* Close the period after a grace window, and put anything later into an adjustment line or credit on the next invoice. Silently dropping it under-bills; reopening a sent invoice confuses the customer.
- *Why integer cents and not floats?* Floats drift, and the sum of the rounded lines must equal the total. For token pricing, use smaller integer units (micro-dollars) and round once, at the line.
- *How do you dedupe at scale?* A unique constraint on the event id in the usage store, or a windowed set keyed by id (a Redis set with a TTL a little longer than the redelivery window). Make the producer idempotent too, so retries reuse the same id (problem 119, idempotent-tool-execution).
- *How would you prorate to the second instead of the day?* Same formula with seconds instead of days. Stripe Billing prorates to the second by default; Metronome, Orb and Lago have the same graduated vs volume and proration options.
- *This is what the customer pays. What does it cost you?* That's attribution of model and tool spend to tenants, which problem 131 (tenant-cost-attribution) covers.
