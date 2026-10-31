def graduated(units, tiers):
    # every unit is priced at the rate of the tier the total lands in
    for tier in tiers:
        if tier["up_to"] is None or units <= tier["up_to"]:
            return units * tier["unit_price"]
    return 0


def build_invoice(plans, plan_changes, events, period_days):
    seen, kept = set(), []
    duplicates = out_of_period = 0
    for e in events:
        if e["id"] in seen:
            duplicates += 1
            continue
        seen.add(e["id"])
        if 0 <= e["day"] < period_days:
            kept.append(e)
        else:
            out_of_period += 1

    starts = [c["day"] for c in plan_changes]
    ends = starts[1:] + [period_days]
    lines = []
    for k, change in enumerate(plan_changes):
        plan = plans[change["plan"]]
        lo, hi = starts[k], ends[k]
        days = hi - lo
        lines.append({"segment": k, "plan": change["plan"], "item": "base", "days": days,
                      "amount": plan["base_fee"] * days // period_days})
        for meter in sorted(plan["meters"]):
            spec = plan["meters"][meter]
            used = sum(e["qty"] for e in kept if e["meter"] == meter and lo <= e["day"] < hi)
            included = spec["included"] * days // period_days
            billable = max(0, used - included)
            lines.append({"segment": k, "plan": change["plan"], "item": meter, "used": used, "included": included,
                          "billable": billable, "amount": graduated(billable, spec["tiers"])})
    return {"lines": lines, "total": sum(l["amount"] for l in lines), "duplicates": duplicates, "out_of_period": out_of_period}
