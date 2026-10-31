# Incident: only the second occurrence of a duplicated request_id was flagged, so the dedupe job kept the wrong copy and billing double-counted retried requests.
import re
from collections import Counter


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _type_ok(v, t):
    if t == "bool":
        return isinstance(v, bool)
    if t == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "float":
        return _is_number(v)
    if t == "str":
        return isinstance(v, str)
    raise ValueError("unknown type %r" % t)


def _row_checker(exp, refs, values):
    check = exp["check"]
    if check == "type":
        return lambda v: _type_ok(v, exp["type"])
    if check == "range":
        lo, hi = exp.get("min"), exp.get("max")
        return lambda v: _is_number(v) and (lo is None or v >= lo) and (hi is None or v <= hi)
    if check == "regex":
        pat = re.compile(exp["pattern"])
        return lambda v: isinstance(v, str) and pat.fullmatch(v) is not None
    if check == "in_set":
        allowed = exp["values"]
        return lambda v: v in allowed
    if check == "foreign_key":
        keys = (refs or {})[exp["ref"]]
        return lambda v: v in keys
    if check == "unique":
        seen = set()

        def first(v):
            k = (type(v).__name__, _freeze(v))
            if k in seen:
                return False
            seen.add(k)
            return True
        return first
    raise ValueError("unknown check %r" % check)


def _freeze(v):
    if isinstance(v, list):
        return tuple(_freeze(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _freeze(x)) for k, x in v.items()))
    return v


def validate(records, expectations, refs=None, id_column="request_id", sample_size=3):
    results, failed_rows = [], set()
    for exp in expectations:
        col = exp["column"]
        if exp["check"] == "not_null":
            rows = list(range(len(records)))
            bad = [i for i in rows if records[i].get(col) is None]
        else:
            rows = [i for i, r in enumerate(records) if r.get(col) is not None]
            ok = _row_checker(exp, refs, [records[i][col] for i in rows])
            bad = [i for i in rows if not ok(records[i][col])]
        evaluated, failed = len(rows), len(bad)
        passed = evaluated == 0 or (evaluated - failed) / evaluated >= exp.get("mostly", 1.0)
        failed_rows.update(bad)
        results.append({
            "column": col,
            "check": exp["check"],
            "evaluated": evaluated,
            "failed": failed,
            "fail_rate": failed / evaluated if evaluated else 0.0,
            "passed": passed,
            "sample": [records[i].get(id_column) for i in bad[:sample_size]],
        })
    return {"success": all(r["passed"] for r in results), "results": results, "failed_rows": sorted(failed_rows)}
