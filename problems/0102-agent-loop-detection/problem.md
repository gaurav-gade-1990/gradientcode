Your research agent sometimes gets stuck: it calls `search_tickets` with the same query again and again, or bounces between `get_order` and `get_customer` forever, burning tokens until the step limit. Write the guard the agent loop consults **before** it runs each tool call.

Implement `class LoopGuard` with:

- `LoopGuard(n_repeat=3, max_cycle=3)`
- `check(name, arguments)`, called once per proposed tool call, in order. Return `None` to let the call run, or a verdict dict to stop the agent. The call you're checking counts as part of the history.

Two calls are the same when their **signatures** match:

```
signature = name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":"))
```

so key order inside `arguments` (at any depth) doesn't matter.

After adding the new call to the history, apply the rules in this order:

| rule | fires when | verdict |
|---|---|---|
| repeat | the last `n_repeat` signatures are all equal | `{"reason": "repeat", "block": [sig]}` |
| cycle | for some `L` in `2 .. max_cycle`, the last `2L` signatures are one block of length `L` twice in a row (`h[-2L:-L] == h[-L:]`), and that block has at least 2 distinct signatures | `{"reason": "cycle", "block": h[-L:]}` |

If several cycle lengths fire, report the smallest `L`. If repeat fires, don't check cycles. The judge stops the agent at the first verdict, so the guard never sees another call after one.

The judge feeds a proposed call sequence through your guard and records which calls ran, the step (1-based) where you stopped the agent, and your verdict.

**Constraints**

- `2 <= n_repeat <= 6`, `2 <= max_cycle <= 4`
- At most 40 calls per run
- `arguments` is a JSON object (nested dicts and lists allowed)
