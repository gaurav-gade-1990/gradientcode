## 1. What the problem is really asking

Agents get stuck. A model that doesn't like a search result will often search again with the same query. Or it bounces between two lookups forever. Each wasted step costs a full model call, and the transcript gets resent every time (problem 101), so the cost grows fast.

You're writing a **guard** that the agent loop asks before every tool call: "should I let this run?" It answers `None` (go ahead) or a verdict dict (stop). There are only two patterns to catch:

- **Repeat:** the same call N times in a row. `A A A`
- **Cycle:** a block of 2 to `max_cycle` calls, then that same block again. `A B A B` or `A B C A B C`

Under the story, this is a **string-matching problem on the tail of a list**.

## 2. Understand the inputs before writing anything

| piece | what it is |
|---|---|
| `LoopGuard(n_repeat=3, max_cycle=3)` | constructed once per agent run, so it keeps state between calls |
| `check(name, arguments)` | called once per proposed call, in order |
| `name` | a tool name, like `"get_order"` |
| `arguments` | a dict, possibly nested, like `{"order_id": "A-1182"}` |
| return value | `None`, or `{"reason": "repeat" or "cycle", "block": [...]}` |

The judge's driver is tiny, and reading it tells you exactly how you're graded:

```python
for step, c in enumerate(calls, start=1):
    verdict = guard.check(c["name"], c["arguments"])
    if verdict is not None:
        return {"executed": executed, "stopped_at": step, "verdict": verdict}
    executed.append(c["name"])
```

So a call **runs only if you return `None` for it**. A verdict for call 4 means call 4 never runs.

## 3. Key idea 1: make calls comparable

Models aren't consistent about key order. These are the same action:

```python
{"query": "refund delayed", "status": "open"}
{"status": "open", "query": "refund delayed"}
```

Comparing the dicts with `==` would work for this pair, but you also need to store history and put calls in the verdict, so you want a **string**. Turn each call into a canonical signature:

```python
sig = name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":"))
# 'search_tickets {"query":"refund delayed","status":"open"}'
```

- `sort_keys=True` sorts keys at **every depth**, so nested dicts are handled too.
- The `name` is included because `get_order(id="A-1")` and `get_invoice(id="A-1")` are different actions.
- `separators` just fixes the exact format the verdict must contain.

## 4. Key idea 2: append first, then look at the tail

The problem says "the call you're checking counts as part of the history." So:

```python
self.history.append(sig)      # first
# then inspect self.history[-k:]
```

If you checked first and appended after, you'd notice `A A A` only when the *fourth* call arrives. The third identical call would already have run. That's the classic off-by-one here, and a test catches it.

## 5. Trace the examples by hand

**Example 1:** `[ORD, S1, S1, S1, CUS]` with `n_repeat=3`.

| step | history tail | repeat? (last 3 equal) | cycle? | result |
|---|---|---|---|---|
| 1 | ORD | too short | too short | run |
| 2 | ORD S1 | too short | L=2 needs 4 | run |
| 3 | ORD S1 S1 | no | no | run |
| 4 | S1 S1 S1 | **yes** | — | **stop: repeat** |

The third S1 never runs. That's the point of appending first.

**Example 2:** `[S1, ORD, CUS, ORD, CUS, INV]`

At step 5 the history is `S1 ORD CUS ORD CUS`. Try `L=2`: `h[-4:-2] = [ORD, CUS]` and `h[-2:] = [ORD, CUS]`. They're equal, and they hold 2 distinct calls, so the verdict is a cycle with `block = [ORD, CUS]`.

**The subtle one, "aabaab cycle of 3":** `[ORD, ORD, CUS, ORD, ORD, CUS, INV]`

- At step 2, `ORD ORD` is only 2 in a row (n=3), so it's not a repeat. A cycle with L=2 needs 4 items. The call runs.
- At step 6 the history is `ORD ORD CUS ORD ORD CUS`. L=2 compares `[CUS, ORD]` with `[ORD, CUS]`: no match. L=3 compares `[ORD, ORD, CUS]` with `[ORD, ORD, CUS]`: match, and the block has 2 distinct signatures. **Cycle of 3.**

A block may contain duplicates. It just can't be *all* duplicates.

## 6. Key idea 3: why "at least 2 distinct" matters

Take five identical calls with `n_repeat=5`, `max_cycle=2`. At step 4 the history is `A A A A`. Does L=2 fire? `[A, A] == [A, A]`, so it looks like a cycle. If you allowed that, the guard would stop at step 4, and the user's `n_repeat=5` setting would be silently ignored. The rule "the block has at least 2 distinct signatures" (`len(set(block)) >= 2`) leaves plain repeats to the repeat rule alone. The expected result is **repeat at step 5**.

## 7. Plan before you code

```
__init__: store n_repeat, max_cycle, history = []
check(name, arguments):
    append signature to history
    if the last n_repeat entries are all equal: return repeat verdict
    for L = 2 .. max_cycle (smallest first):
        if history has 2L entries, the two halves of the last 2L match,
        and that block has >= 2 distinct entries:
            return cycle verdict with that block
    return None
```

Going smallest L first gives you the "report the smallest L" rule for free.

## 8. Build it

**The signature and the history:**

```python
import json


class LoopGuard:
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n_repeat = n_repeat
        self.max_cycle = max_cycle
        self.history = []

    @staticmethod
    def signature(name, arguments):
        return name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":"))
```

**The repeat rule.** `set()` of the last n entries has size 1 exactly when they're all equal:

```python
    def check(self, name, arguments):
        h = self.history
        h.append(self.signature(name, arguments))
        n = self.n_repeat
        if len(h) >= n and len(set(h[-n:])) == 1:
            return {"reason": "repeat", "block": [h[-1]]}
```

The `len(h) >= n` guard matters. Without it, `h[-3:]` on a 1-item list is that one item, whose set has size 1, so you'd report a "repeat" on the very first call.

**The cycle rule.** Python's negative slices read naturally. `h[-2*L:-L]` is the block before last and `h[-L:]` is the last block:

```python
        for L in range(2, self.max_cycle + 1):
            if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:] and len(set(h[-L:])) >= 2:
                return {"reason": "cycle", "block": h[-L:]}
        return None
```

## 9. Full solution

```python
import json


class LoopGuard:
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n_repeat = n_repeat
        self.max_cycle = max_cycle
        self.history = []

    @staticmethod
    def signature(name, arguments):
        return name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":"))

    def check(self, name, arguments):
        h = self.history
        h.append(self.signature(name, arguments))
        n = self.n_repeat
        if len(h) >= n and len(set(h[-n:])) == 1:
            return {"reason": "repeat", "block": [h[-1]]}
        for L in range(2, self.max_cycle + 1):
            if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:] and len(set(h[-L:])) >= 2:
                return {"reason": "cycle", "block": h[-L:]}
        return None
```

## 10. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| key order does not matter | repeat at step 3 | `sort_keys=True` |
| nested args key order | repeat at step 3 | `sort_keys` also sorts nested dicts |
| same args different tool | never stops | the tool name is part of the signature |
| repeat n=2 | repeat at step 3 | `n_repeat` is honoured, not hard-coded to 3 |
| two in a row is fine at n=3 | never stops | `A A B B C C` has no run of 3 and no 2-distinct cycle |
| repeat beats cycle length check | repeat at step 5, not cycle at 4 | the "at least 2 distinct" rule |
| cycle of 3 | cycle at step 7 | L goes beyond 2 |
| cycle of 3 not checked when max_cycle 2 | never stops | the `range` stops at `max_cycle` |
| cycle of 4 | cycle at step 8 | the largest L allowed |
| late cycle after varied prefix | cycle at step 11 | only the tail matters, wherever it starts |
| aabaab cycle of 3 | cycle at step 6 | a block can contain duplicates |

## 11. Complexity

Each `check` does O(n_repeat + max_cycle²) signature comparisons, plus the cost of `json.dumps` on the arguments. With `max_cycle ≤ 4` that's effectively constant per call. History grows by one per call; in production you'd keep only the last `max(n_repeat, 2·max_cycle)` entries (`collections.deque(maxlen=...)`).

## 12. If you got Wrong Answer

- **`stopped_at` is one later than expected.** You check before appending.
- **The key-order tests never stop.** You're missing `sort_keys=True`.
- **"same args different tool" stops.** You left `name` out of the signature.
- **"repeat beats cycle" gives a cycle at step 4.** You're missing `len(set(block)) >= 2`.
- **"cycle of 3" never stops.** You only check A-B-A-B (L=2).
- **The block strings differ only by spaces.** Use `separators=(",", ":")`. The default adds spaces after `,` and `:`.

## 13. Follow-ups an interviewer might ask

- *What do you do on a verdict?* Killing the run is the bluntest option. Better: inject a message ("you've run this search 3 times; try different terms or answer with what you have"), switch to a stronger model, or hand off to a human.
- *What about near-duplicates, like "refund delayed" vs "refund late"?* Exact signatures miss them, by design (see Example 3). You could normalize arguments (lowercase, strip whitespace) or compare embeddings, at the cost of false positives.
- *How does this relate to a step limit?* A cap like LangGraph's `recursion_limit` stops a loop only after the whole budget is spent. A guard stops it within a few calls. Use both.
- *What would you log?* Count verdicts per tool name. A tool that keeps triggering repeats usually has a confusing description or an unhelpful error message.
