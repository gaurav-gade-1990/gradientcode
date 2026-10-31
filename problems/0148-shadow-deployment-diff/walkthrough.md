## 1. What the problem is really asking

In a shadow deployment, the new model gets a copy of every request, but its answer is only logged. Before you switch traffic over, you diff the two logs: how often does the shadow say the same thing as the primary, and is that true in every customer segment?

Under the story, this is **a five-way classifier per record, then grouped counts and a short list of gate rules**. The classifier is the interesting part, because "the same answer" has layers:

| class | meaning |
|---|---|
| `shadow_error` | the shadow never answered; that's a capacity or infra problem, not a disagreement |
| `exact` | identical as JSON, types included |
| `normalized` | two strings that differ only in case, spacing or trailing punctuation |
| `numeric` | two real numbers within a tolerance |
| `mismatch` | a real disagreement |

The judge compares every field: each request's class, the overall and per-segment counts and agreement, the ordered mismatch list, the ordered blocking list, and `ready`. Most of the hidden cases are type traps, where Python's own equality gives the wrong class.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `records` | `{request_id, segment, primary, shadow}`, maybe `shadow_error` | classify each one |
| `primary`, `shadow` | any JSON value | compared by the class rules, first match wins |
| `shadow_error` | an error string, or absent, or `None` | only a non-`None` value counts |
| `abs_tol`, `rel_tol` | numeric tolerance `abs_tol + rel_tol * abs(primary)` | the `numeric` rule |
| `min_agreement` | agreement floor, overall and per segment | blocking rules 1 and 3 |
| `max_error_rate` | allowed share of shadow errors over **all** records | blocking rule 2 |
| `min_segment` | the smallest `compared` count that lets a segment block | blocking rule 3 |

Three details are easy to miss:

- **The agreement denominator is `compared`, which excludes shadow errors.** The error-rate denominator is `total`, which includes them.
- **`rec.get("shadow_error") is not None`.** A key that's present but set to `None` is not an error.
- **`bool` is a subclass of `int` in Python.** `isinstance(True, int)` is `True`, so a naive number check accepts booleans.

## 3. Key idea: Python's `==` is the wrong "exact"

Python is generous about equality: `True == 1`, `1 == 1.0`, and `[1, 2] == [1, 2.0]` are all `True`. But a client written in TypeScript or Go that receives `1` where it used to get `true` may break. That's a real schema change. Canonical JSON keeps the types:

```python
json.dumps(True)      # 'true'
json.dumps(1)         # '1'
json.dumps(1.0)       # '1.0'
json.dumps({"priority": 2, "intent": "refund"}, sort_keys=True)
# '{"intent": "refund", "priority": 2}'
```

`sort_keys=True` makes dict key order irrelevant (req-105 in Example 1 is `exact` despite reordered keys), while every type difference still shows. The "type traps" case is built on this:

| id | primary | shadow | class | why |
|---|---|---|---|---|
| t1 | `True` | `1` | mismatch | JSON differs; a bool is not a number |
| t2 | `1` | `True` | mismatch | same, reversed |
| t3 | `0` | `False` | mismatch | same |
| t4 | `2` | `2.0` | numeric | JSON differs, but both are real numbers within tolerance |
| t5 | `None` | `0` | mismatch | `null` is not a number |
| t6 | `[1, 2]` | `[1, 2.0]` | mismatch | lists aren't numbers, and their JSON differs |
| t7 | `"1"` | `1` | mismatch | a string and a number |

With Python `==`, five of those seven become `exact`.

## 4. Trace Example 1 by hand

Policy: `abs_tol = 0.01`, `rel_tol = 0.001`, `min_agreement = 0.9`, `max_error_rate = 0.05`, `min_segment = 3`.

| request | segment | primary → shadow | first matching rule | class |
|---|---|---|---|---|
| req-101 | enterprise | `"refund"` → `"refund"` | same JSON | exact |
| req-102 | enterprise | `"Shipping status"` → `"shipping status."` | both normalize to `shipping status` | normalized |
| req-103 | smb | `129.99` → `130.0` | diff 0.01 ≤ 0.01 + 0.001 · 129.99 = 0.13999 | numeric |
| req-104 | smb | `"cancel"` → `"billing_question"` | nothing matches | mismatch |
| req-105 | smb | dict with keys reordered | same canonical JSON | exact |

Overall: `total = 5`, `compared = 5`, agreement `= (2 + 1 + 1) / 5 = 0.8`. The segments: enterprise is 2 of 2 (1.0), smb is 2 of 3 (0.666667).

Blocking, in order:

1. `0.8 < 0.9`, so `"overall_agreement"`.
2. 0 errors out of 5, so no `"shadow_errors"`.
3. Segments sorted by name: enterprise agrees fully. smb has `compared = 3 >= 3` and `0.666667 < 0.9`, so `"segment:smb"`.

`blocking = ["overall_agreement", "segment:smb"]`, `ready = False`, `mismatches = ["req-104"]`.

**Example 2 adds errors and types.** req-201 timed out in shadow, so it's `shadow_error`, and it leaves the agreement denominator: `compared = 4 - 1 = 3`. req-203 (`True` vs `1`) is a mismatch. req-204 (`3` vs `3.0`) is numeric, not exact. Agreement is `2/3`, and the error rate is `1/4 = 0.25 > 0.05`. Both overall rules block. `min_segment = 5` keeps the two-record segments out of it.

## 5. Key idea: tolerance has to scale

An absolute tolerance alone treats a 1-cent difference on a $12,400 invoice like a 1-cent difference on a $0.50 fee. Float arithmetic makes it worse: `12400.01 - 12400.0` is `0.010000000000218`, which is *more* than `abs_tol = 0.01`. The combined rule, the same shape as `math.isclose`, is

```
abs(primary - shadow) <= abs_tol + rel_tol * abs(primary)
```

In "relative tolerance on large totals", the tolerance on 12,400 is `0.01 + 12.4 = 12.41`. A 12.0 difference passes, a 12.5 difference is a mismatch, and on an 80.0 total the tolerance shrinks to 0.09. Five of six are numeric. With `abs_tol` alone, all six are mismatches.

## 6. Plan before you code

```
classify(rec):
    shadow_error not None        -> shadow_error
    canonical JSON equal         -> exact
    both str and norm equal      -> normalized
    both real numbers and close  -> numeric
    else                         -> mismatch
summary(classes): counts of each, compared = total - shadow_error, agreement or None
overall = summary(all); segments = summary per segment
blocking: overall agreement None or low; error rate high; each large-enough low segment, sorted
```

| blocking rule | denominator | small groups? |
|---|---|---|
| `overall_agreement` | `compared` | `None` agreement blocks |
| `shadow_errors` | `total` | n/a |
| `segment:<name>` | `compared` | only if `compared >= min_segment` |

## 7. Build it one piece at a time

**Step 1: the helpers.** `rstrip(".!?")` strips any run of trailing `.`, `!` and `?`, and `split()` with no argument collapses every run of whitespace:

```python
def _norm(s):
    return " ".join(s.lower().strip().rstrip(".!?").split())


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)
```

The order inside `_norm` matters. `strip()` before `rstrip` means `"hi  there ..."` loses the trailing space first, then the dots, giving `hi there`. Only trailing punctuation goes: `"a. b"` vs `"a b"` is still a mismatch in "normalization rules".

**Step 2: the classifier.** Each `return` is one row of the class table, in order:

```python
def _classify(rec, policy):
    if rec.get("shadow_error") is not None:
        return "shadow_error"
    p, s = rec["primary"], rec["shadow"]
    if json.dumps(p, sort_keys=True) == json.dumps(s, sort_keys=True):
        return "exact"
    if isinstance(p, str) and isinstance(s, str) and _norm(p) == _norm(s):
        return "normalized"
    if _is_number(p) and _is_number(s) and abs(p - s) <= policy["abs_tol"] + policy["rel_tol"] * abs(p):
        return "numeric"
    return "mismatch"
```

**Step 3: one summary function for every group.** Writing it once guarantees the overall and segment numbers use the same rules:

```python
def _summary(classes):
    out = {"total": len(classes)}
    for c in CLASSES:
        out[c] = classes.count(c)
    out["compared"] = out["total"] - out["shadow_error"]
    agree = out["exact"] + out["normalized"] + out["numeric"]
    out["agreement"] = agree / out["compared"] if out["compared"] else None
    return out
```

**Step 4: blocking.** In the segment rule, check `compared >= min_segment` first. Python's `and` short-circuits, so a segment with `compared == 0` never reaches the `None < float` comparison, which would raise a `TypeError`.

## 8. Full solution

```python
import json  # canonical JSON is the type-aware equality test

CLASSES = ("exact", "normalized", "numeric", "mismatch", "shadow_error")  # every class gets a count


def _norm(s):  # string comparison that ignores case, spacing and trailing punctuation
    return " ".join(s.lower().strip().rstrip(".!?").split())  # lowercase, trim, drop trailing .!?, collapse spaces


def _is_number(x):  # a real number, the way JSON clients see it
    return isinstance(x, (int, float)) and not isinstance(x, bool)  # bool subclasses int, so exclude it


def _classify(rec, policy):  # first matching rule wins
    if rec.get("shadow_error") is not None:  # the shadow failed to answer at all
        return "shadow_error"  # infra problem, kept out of agreement
    p, s = rec["primary"], rec["shadow"]  # the two answers to compare
    if json.dumps(p, sort_keys=True) == json.dumps(s, sort_keys=True):  # same value and same types; key order ignored
        return "exact"  # byte-identical once serialized
    if isinstance(p, str) and isinstance(s, str) and _norm(p) == _norm(s):  # cosmetic string differences only
        return "normalized"  # same text for a reader
    # both real numbers and within absolute plus relative tolerance
    if _is_number(p) and _is_number(s) and abs(p - s) <= policy["abs_tol"] + policy["rel_tol"] * abs(p):
        return "numeric"  # float noise, not a disagreement
    return "mismatch"  # a real difference


def _summary(classes):  # counts and agreement for one group of records
    out = {"total": len(classes)}  # every record in the group
    for c in CLASSES:  # count each class, zeros included
        out[c] = classes.count(c)  # how many records fell in this class
    out["compared"] = out["total"] - out["shadow_error"]  # only records where the shadow answered
    agree = out["exact"] + out["normalized"] + out["numeric"]  # the three kinds of agreement
    out["agreement"] = agree / out["compared"] if out["compared"] else None  # undefined with nothing to compare
    return out  # same shape for overall and every segment


def shadow_diff(records, policy):  # the shadow readiness report
    per_request = {r["request_id"]: _classify(r, policy) for r in records}  # one class per request
    overall = _summary([per_request[r["request_id"]] for r in records])  # the whole log
    by_seg = {}  # segment -> list of classes
    for r in records:  # group in input order
        by_seg.setdefault(r["segment"], []).append(per_request[r["request_id"]])  # reuse the classes already computed
    segments = {seg: _summary(cls) for seg, cls in by_seg.items()}  # per-segment summaries

    blocking = []  # reasons not to switch traffic, in spec order
    if overall["agreement"] is None or overall["agreement"] < policy["min_agreement"]:  # nothing compared, or too low
        blocking.append("overall_agreement")  # the shadow disagrees too often overall
    if overall["shadow_error"] / overall["total"] > policy["max_error_rate"]:  # errors over all records, not compared
        blocking.append("shadow_errors")  # the shadow can't serve reliably yet
    for seg in sorted(segments):  # deterministic order by segment name
        s = segments[seg]  # this segment's numbers
        # only segments big enough to be meaningful can block; short-circuit avoids None < float
        if s["compared"] >= policy["min_segment"] and s["agreement"] < policy["min_agreement"]:
            blocking.append("segment:%s" % seg)  # a real customer group would see worse answers

    return {  # the full report
        "per_request": per_request,  # class of every request
        "overall": overall,  # whole-log summary
        "segments": segments,  # per-segment summaries
        "mismatches": [r["request_id"] for r in records if per_request[r["request_id"]] == "mismatch"],  # for review
        "blocking": blocking,  # why not, if not
        "ready": not blocking,  # ready only with no blocking reasons
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | agreement 0.8; blocks on overall and `segment:smb` | all four agreement classes and one segment block |
| Example 2 | agreement 0.666667; blocks on overall and `shadow_errors` | errors leave `compared`; `True` vs `1`; `3` vs `3.0` |
| type traps | one numeric, six mismatches | canonical JSON and the bool exclusion |
| relative tolerance on large totals | five numeric, `inv-2` mismatch | `abs_tol + rel_tol * abs(primary)` |
| errors excluded from agreement | agreement 1.0, ready | 3 errors in 12 is 0.25, under `max_error_rate = 0.3` |
| tiny segment cannot block | ready, `pilot` at 0.5 ignored | `compared >= min_segment` |
| normalization rules | six normalized, `n6` mismatch | trailing punctuation only; `""` vs `"."` normalize equal |
| all shadow errors | agreement `None`, blocks on overall | the `None` agreement rule |
| week of traffic | agreement 0.943782, ready | 600 mixed records over three segments |

## 10. Complexity

Classifying is O(size of the JSON values) per record, dominated by `json.dumps`. Summaries use `list.count` five times per group, O(5·n) total. With 2,000 records that's instant. Memory is O(n) for the per-request map.

In production this runs as a batch job over a week of mirrored traffic, often millions of records. The same logic works as a streaming aggregation: classify each pair as it arrives, keep counters per segment, and store only the mismatches with their inputs for review.

## 11. If you got Wrong Answer

- **"type traps" shows `t1`, `t2`, `t3`, `t4` and `t6` as `exact`.** You're using `p == s`. Compare canonical JSON.
- **Example 2's `req-203` (`True` vs `1`) is `numeric`.** Your number check accepts `bool`.
- **Example 2's `req-201` is a `mismatch` and agreement is 0.5.** You're counting shadow errors as disagreements. In "errors excluded from agreement" that wrongly blocks on overall agreement and `segment:free`.
- **All six records in "relative tolerance on large totals" are mismatches.** You dropped `rel_tol`.
- **"tiny segment cannot block" blocks on `segment:pilot`.** You're missing the `min_segment` check.
- **A `TypeError` comparing `None` and a float.** A segment with zero compared records reached the agreement comparison; check `compared` first.

## 12. Follow-ups an interviewer might ask

- *How do you mirror traffic in the first place?* At the proxy: Envoy's `request_mirror_policies`, Istio's `mirror`, or a Kafka tap feeding a shadow consumer. Mirrored calls must never have side effects, so strip write tools from a shadow agent or point them at a sandbox.
- *These rules work for intents and amounts. What about free-text answers?* Exact and normalized matching only fit structured fields. For free text, add an embedding-similarity or LLM-judge class (problem 145, llm-judge-position-swap) and sample mismatches for human review.
- *What do you do with the mismatch list?* Bucket it by type: type changes, rounding and real disagreements. The first two are serialization bugs you fix directly. Only the third needs a modeling discussion.
- *Shadow agrees. Are you done?* No. Shadow shows the outputs match; it doesn't show users are fine with the new latency or the new edge cases. Follow it with a canary (problem 147, canary-analysis).
- *Why not just raise `min_agreement` to 1.0?* A better model is supposed to disagree sometimes. The shadow diff tells you where; a human-labeled sample of the mismatches tells you whether shadow or primary was right.
