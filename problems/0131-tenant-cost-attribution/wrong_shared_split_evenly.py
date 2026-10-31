# Incident: shared infrastructure was split evenly across tenants, so a trial tenant with $3 of
# usage was billed $66 of vector DB cost and churned.
def _price(prices, model, date):
    best = None
    for p in prices.get(model, []):
        if p["effective"] <= date and (best is None or p["effective"] > best["effective"]):
            best = p
    return best


def attribute_costs(events, prices, shared_costs, budgets):
    direct, by_feature, by_model = {}, {}, {}
    alerts, unpriced, fired = [], [], set()
    for e in events:
        p = _price(prices, e["model"], e["date"])
        if p is None:
            unpriced.append(e["id"])
            continue
        cached = e["cached_input_tokens"]
        cost = ((e["input_tokens"] - cached) * p["input"] + cached * p["cached_input"] + e["output_tokens"] * p["output"]) / 1e6
        t = e["tenant"]
        direct[t] = direct.get(t, 0.0) + cost
        feats = by_feature.setdefault(t, {})
        feats[e["feature"]] = feats.get(e["feature"], 0.0) + cost
        by_model[e["model"]] = by_model.get(e["model"], 0.0) + cost
        if t in budgets:
            for pct in (50, 80, 100):
                if (t, pct) not in fired and direct[t] * 100 >= pct * budgets[t]:
                    fired.add((t, pct))
                    alerts.append({"tenant": t, "threshold": pct, "event_id": e["id"], "spent": direct[t]})
    S = sum(c["amount"] for c in shared_costs)
    D = sum(direct.values())
    by_tenant = {}
    for t, d in direct.items():
        share = S / len(direct) if D > 0 else 0.0
        by_tenant[t] = {"direct": d, "shared": share, "total": d + share}
    return {"by_tenant": by_tenant, "by_feature": by_feature, "by_model": by_model, "alerts": alerts,
            "unpriced": unpriced, "unallocated_shared": 0.0 if D > 0 else float(S)}
