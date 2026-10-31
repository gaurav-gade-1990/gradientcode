import bisect


def _index(snapshots, features):
    """(entity, feature) -> its snapshots sorted by (ts, version)."""
    groups = {}
    for s in snapshots:
        if s["feature"] in features:
            groups.setdefault((s["entity_id"], s["feature"]), []).append(s)
    for rows in groups.values():
        rows.sort(key=lambda s: (s["ts"], s["version"]))
    return groups


def _choose(rows, as_of):
    """Newest visible row: walk back from the last row with ts <= as_of, skipping rows written after as_of."""
    if not rows:
        return None
    keys = [s["ts"] for s in rows]
    i = bisect.bisect_right(keys, as_of) - 1
    while i >= 0:
        if rows[i]["created_at"] <= as_of:
            return rows[i]
        i -= 1
    return None


def point_in_time_join(labels, snapshots, feature_specs):
    groups = _index(snapshots, feature_specs)
    stats = {f: {"ok": 0, "missing": 0, "expired": 0} for f in feature_specs}
    out = []
    for lab in labels:
        row = {"label_id": lab["label_id"], "label": lab["label"], "features": {}, "sources": {}, "status": {}}
        for f, spec in feature_specs.items():
            as_of = lab["event_ts"] - spec["lag"]
            snap = _choose(groups.get((lab["entity_id"], f), []), as_of)
            if snap is None:
                status = "missing"
            elif as_of - snap["ts"] > spec["ttl"]:
                status = "expired"
            else:
                status = "ok"
            ok = status == "ok"
            row["features"][f] = snap["value"] if ok else spec["default"]
            row["sources"][f] = snap["snapshot_id"] if ok else None
            row["status"][f] = status
            stats[f][status] += 1
        out.append(row)
    return {"rows": out, "stats": stats}
