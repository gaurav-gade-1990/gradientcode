## Approach

Reduce every proposed call to one canonical string, keep the history, and inspect only its tail.

```python
def check(self, name, arguments):
    h = self.history
    h.append(name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":")))
    n = self.n_repeat
    if len(h) >= n and len(set(h[-n:])) == 1:
        return {"reason": "repeat", "block": [h[-1]]}
    for L in range(2, self.max_cycle + 1):
        if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:] and len(set(h[-L:])) >= 2:
            return {"reason": "cycle", "block": h[-L:]}
    return None
```

The new call is appended **before** checking, so the guard blocks the call that would complete the loop instead of letting it run first. A block of identical calls is excluded from the cycle rule so that `n_repeat` stays the only knob for plain repeats.

## Common mistakes

- **Comparing raw JSON.** Models emit the same arguments with keys in a different order. Without `sort_keys` the loop is invisible.
- **Comparing only the arguments.** `get_order(id=A-1)` and `get_invoice(id=A-1)` are different actions.
- **Checking before appending.** The guard fires one call late, after the wasteful call already executed.
- **Only detecting A-B-A-B.** Agents that alternate search, read, re-plan form length-3 cycles just as often.
- **Treating `[A, A]` as a cycle.** That silently overrides the `n_repeat` setting.

## Production notes

- Every agent framework ships a hard cap (LangGraph's `recursion_limit`, the OpenAI Agents SDK's `max_turns`). A cap catches loops only after spending the whole budget; a guard like this one stops them in a few steps.
- On a verdict, don't just kill the run. Common responses: inject a message ("you've called search_tickets with the same query three times; try something else"), switch to a stronger model, or escalate to a human.
- Signatures make good metrics. Counting repeats per tool tells you which tool descriptions confuse the model.
- Pair with the basic loop in problem 101 (react-tool-loop) and with replanning in problem 106 (plan-and-execute-replan).
