# Treats an is_premium flag as numeric because bool subclasses int.
import math


def _missing(row, f):
    return row["features"].get(f) is None


def _is_num(v):
    return isinstance(v, (int, float))


def _distance(kind, t_vals, s_vals):
    if not t_vals or not s_vals:
        return None
    if kind == "numeric":
        mu_t, mu_s = sum(t_vals) / len(t_vals), sum(s_vals) / len(s_vals)
        sd = math.sqrt(sum((x - mu_t) ** 2 for x in t_vals) / len(t_vals))
        if sd == 0:
            return 0.0 if mu_s == mu_t else float("inf")
        return abs(mu_s - mu_t) / sd
    pt, ps = {}, {}
    for v in t_vals:
        pt[v] = pt.get(v, 0) + 1
    for v in s_vals:
        ps[v] = ps.get(v, 0) + 1
    keys = set(pt) | set(ps)
    return 0.5 * sum(abs(pt.get(k, 0) / len(t_vals) - ps.get(k, 0) / len(s_vals)) for k in keys)


def train_serve_skew(train_rows, serve_rows, features, policy):
    latest = {}
    for row in serve_rows:
        cur = latest.get(row["entity_id"])
        if cur is None or row["ts"] >= cur["ts"]:
            latest[row["entity_id"]] = row
    serve = list(latest.values())
    train_ids = {r["entity_id"] for r in train_rows}
    joined = [(r, latest[r["entity_id"]]) for r in train_rows if r["entity_id"] in latest]

    report = {}
    for f in features:
        t_vals = [r["features"][f] for r in train_rows if not _missing(r, f)]
        s_vals = [r["features"][f] for r in serve if not _missing(r, f)]
        values = t_vals + s_vals
        kind = "numeric" if values and all(_is_num(v) for v in values) else "categorical"

        bad = 0
        for t, s in joined:
            mt, ms = _missing(t, f), _missing(s, f)
            if mt and ms:
                continue
            if mt != ms:
                bad += 1
            elif kind == "numeric":
                bad += abs(t["features"][f] - s["features"][f]) > policy["abs_tol"]
            else:
                bad += t["features"][f] != s["features"][f]
        mismatch = bad / len(joined) if joined else None
        dist = _distance(kind, t_vals, s_vals)
        tm = sum(_missing(r, f) for r in train_rows) / len(train_rows)
        sm = sum(_missing(r, f) for r in serve) / len(serve)
        skewed = ((mismatch is not None and mismatch > policy["max_mismatch_rate"])
                  or (dist is not None and dist > policy["max_distance"])
                  or abs(sm - tm) > policy["max_missing_delta"])
        report[f] = {"kind": kind, "mismatch_rate": mismatch, "distance": dist,
                     "train_missing_rate": tm, "serve_missing_rate": sm, "skewed": bool(skewed)}

    offenders = sorted((f for f in features if report[f]["mismatch_rate"]), key=lambda f: (-report[f]["mismatch_rate"], f))
    skewed = sorted(f for f in features if report[f]["skewed"])
    return {
        "joined": len(joined),
        "train_only": len(train_ids - set(latest)),
        "serve_only": len(set(latest) - train_ids),
        "features": report,
        "top_offenders": offenders[:policy["top_k"]],
        "skewed": skewed,
        "decision": "block" if skewed else "pass",
    }
