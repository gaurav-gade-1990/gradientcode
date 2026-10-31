Your gateway's p99 is set by the slowest provider responses, and outages of a single provider still reach users. Implement **hedged requests with failover**: if the primary hasn't answered within the hedge delay, also send to the next provider and take whichever succeeds first. Fail over immediately on errors, skip providers whose circuit breaker is open, and never leave a losing request running to be billed.

`handle_request(client, request, providers, hedge_delay, deadline)` is a **generator** that runs on `gc_runtime.EventLoop` and returns a result dict. `providers` is a list of names in priority order. Times are seconds of virtual time, and the request starts at `t = 0`.

**The client** (built by the judge):

| call | does |
|---|---|
| `client.now()` | the current virtual time |
| `client.is_open(name)` | `True` if that provider's circuit breaker is open right now |
| `client.send(name, request)` | starts an attempt now and returns an `Attempt` |
| `a = yield from client.wait_any(attempts, timeout)` | waits for the first of `attempts` (ignoring cancelled ones) to finish and returns it, or returns `None` once `timeout` seconds pass first. `timeout=None` waits without limit. If two finish at the same instant, the one sent first is returned. An attempt that finishes exactly when the timeout expires is returned rather than `None`. An already-finished attempt is returned immediately, so remove the ones you've handled. |
| `client.cancel(a)` | cancels an attempt still in flight; a no-op if it has finished |

An `Attempt` has `.provider` and `.start`. Once `wait_any` has returned it, it also has `.ok`, `.error` (`"server"`, `"rate_limit"`, `"timeout"` or `"circuit_open"`) and `.text`.

**Rules**

1. **Choosing whom to send to.** Take the next provider in priority order. If `client.is_open(name)` is `True` at that moment, skip it for good and take the one after. Sending to an open provider fails instantly with `"circuit_open"` and is graded as a bug.
2. Send the first attempt at `t = 0`. If every provider is skipped, return status `"unavailable"`.
3. **Hedge.** Whenever exactly one attempt is in flight, providers remain, and that attempt has been in flight for `hedge_delay` (`now >= attempt.start + hedge_delay`), send to the next provider. At most two attempts are ever in flight. An attempt that has finished is not in flight: completions at an instant are handled before the hedge timer or the deadline at that same instant.
4. **Fail over.** When an attempt fails, drop it. If nothing else is in flight, send to the next provider right away. If one attempt is still in flight, rule 3 continues to apply to it.
5. **Win.** On the first success, cancel every other attempt in flight and return `{"status": "ok", "provider": a.provider, "text": a.text}`.
6. **Give up.** If nothing is in flight and no providers remain, return status `"failed"`. If `now` reaches `deadline` first, cancel everything in flight and return status `"timeout"`. A response arriving exactly at the deadline still counts, but never send a new attempt at or after the deadline.

Every non-ok result is `{"status", "provider": None, "text": None}`.

**Billing (applied by the judge).** A successful attempt bills its input and output tokens. A **cancelled** attempt bills its input tokens, because the prompt was already processed. A failed attempt bills nothing. An attempt you leave running after you return keeps going in the background and is billed when it finishes. The judge grades your result, every attempt (provider, start, end, outcome), the total cost and the time you returned.

**Constraints**

- 1 to 4 providers; `0 < hedge_delay`; `0 < deadline`
- Don't import `time` or `asyncio`; wait only through `client.wait_any`
