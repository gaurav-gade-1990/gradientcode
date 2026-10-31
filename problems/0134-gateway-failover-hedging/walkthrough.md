## 1. What the problem is really asking

Under the gateway story this is an **event loop with a single question at its centre**: what is the earliest moment something could change? Only three things can change the plan:

- an attempt **finishes** (success or error),
- the single attempt in flight reaches its **hedge timer** (`start + hedge_delay`),
- the request reaches its **deadline**.

Your handler is a generator. Each time round the loop it either **sends** (because a rule says to, right now) or **waits** with `client.wait_any(inflight, timeout)`, where the timeout is exactly the time until the earliest timer. When the wait returns, you react: an attempt (success or failure) or `None` (a timer fired).

The judge grades much more than the answer. It records every attempt (provider, start, end, outcome), the total cost and the virtual time you returned. So *when* you sent each attempt, and whether you cancelled the loser, are graded as strictly as which provider won.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `client.now()` | virtual time in seconds; the request starts at 0 | timer arithmetic |
| `client.is_open(name)` | is that provider's breaker open *right now* | checked at the moment you pick a provider |
| `client.send(name, request)` | starts an attempt now, returns an `Attempt` | the only way to start work |
| `yield from client.wait_any(attempts, timeout)` | first attempt to finish, or `None` after `timeout` | the only way to wait |
| `client.cancel(a)` | stops an attempt still in flight | every loser, every time |
| `Attempt` | `.provider`, `.start`; after it is returned also `.ok`, `.error`, `.text` | `.start` drives the hedge timer |
| `providers` | names in priority order | a queue you pop from |
| `hedge_delay`, `deadline` | seconds | the two timers |

Details that are easy to miss:

- **`wait_any` keeps returning a finished attempt.** If you don't remove it from `inflight`, the next call returns it again at once.
- **A completion on a timer instant wins.** If an attempt finishes exactly when the timeout expires, `wait_any` returns the attempt, not `None`. That is what rule 3 means by "completions at an instant are handled before the hedge timer or the deadline".
- **Skipped means skipped for good.** A provider whose breaker is open when you reach it is popped from the queue and never reconsidered, even if its breaker closes a second later.
- **Billing is by outcome.** Success: input + output tokens. Cancelled: input tokens only. Failed: nothing. Left running after you return: it finishes in the background and bills in full.
- **Your function must be a generator** even on paths that never wait. Any `yield` in the body makes it one, and a `return {...}` in a generator becomes its result.

## 3. Trace Example 2 by hand

Providers `primary` ($3 / $15 per million input / output tokens), `secondary` ($2.50 / $10), `selfhosted` ($0.90 / $0.90). The request has 2,000 input tokens. `hedge_delay = 1.0`, `deadline = 8.0`. Script: primary answers after 3.0 s, secondary after 1.0 s with 380 output tokens.

| t | in flight | queue | wake (min of deadline and hedge timer) | what happens |
|---|---|---|---|---|
| 0 | — | primary, secondary, selfhosted | — | send primary |
| 0 | primary (start 0) | secondary, selfhosted | min(8, 0 + 1) = 1 | wait 1.0 s; nothing finishes |
| 1 | primary | secondary, selfhosted | — | `wait_any` returned `None` before the deadline: hedge, send secondary |
| 1 | primary, secondary | selfhosted | 8 (two in flight, no hedge) | wait 7.0 s |
| 2 | primary | selfhosted | — | secondary returns ok: cancel primary, return |

Expected output:

```python
{'result': {'status': 'ok', 'provider': 'secondary', 'text': 'secondary: answer'},
 'attempts': [{'provider': 'primary', 'start': 0, 'end': 2, 'outcome': 'cancelled'},
              {'provider': 'secondary', 'start': 1, 'end': 2, 'outcome': 'ok'}],
 'cost': 0.0148, 't': 2}
```

The cost is primary's input only, `2000 × 3 / 1e6 = 0.006`, plus secondary's full bill, `(2000 × 2.5 + 380 × 10) / 1e6 = 0.0088`. If you forget to cancel primary, it keeps running, finishes at t=3 with outcome `ok` and bills in full, and the total becomes 0.0208.

**The trickiest hidden case, "short hedge delay chains three providers".** `hedge_delay = 0.5`. Primary would answer at 4.0, secondary fails with a server error after 0.25 s, selfhosted takes 2.0 s.

| t | event | in flight after | next wake |
|---|---|---|---|
| 0 | send primary | primary (start 0) | 0.5 |
| 0.5 | hedge timer: send secondary | primary, secondary | 8 |
| 0.75 | secondary fails, drop it | primary (start 0) | `0 + 0.5 = 0.5`, already past, so timeout 0 |
| 0.75 | `wait_any(..., 0)` returns `None`: hedge, send selfhosted | primary, selfhosted | 8 |
| 2.75 | selfhosted ok: cancel primary | — | — |

After the failure, one attempt is still in flight and its hedge timer expired long ago, so rule 3 sends the next provider immediately. Expected: selfhosted wins at `t = 2.75`, with primary cancelled at 2.75 and cost 0.00816. The `max(0.0, wake - now)` in the wait is what turns "the timer is already overdue" into "check right now".

## 4. Key idea: the hedge timer belongs to the attempt, not the request

The hedge timer is `inflight[0].start + hedge_delay`, the start of the attempt that is in flight now. In "hedge timer runs from the attempt in flight", primary fails at 0.5 and you fail over to secondary at 0.5. Secondary's timer then expires at 1.5, so selfhosted is sent at 1.5 and wins at 2.0.

If you measure from the request start (`wake = hedge_delay`), the timer reads 1.0 for every attempt. Secondary is hedged after only 0.5 s in flight, and selfhosted goes out at 1.0. Every failover then turns into a near-instant double send, which is exactly what hedging is not meant to do.

## 5. Key idea: an error is information, not slowness

When an attempt fails and nothing else is in flight, you send the next provider **at that instant**. In "fail over immediately on error", primary returns a 5xx at 0.25, secondary is sent at 0.25 and answers at 0.75. Treating the error like a slow response and waiting for the hedge timer delays the secondary to t=1.0 and the answer to 1.5, adding the whole hedge delay to every failover.

This comes for free with the loop shape below: after you drop the failed attempt, the top of the loop sees `not inflight` and sends straight away.

## 6. Plan before you code

```
queue = providers; inflight = []
send_next(): pop providers until one is not open; send it; False if none left
if not send_next(): return unavailable
loop:
    if nothing in flight:
        if now >= deadline: return timeout          # never send at or after the deadline
        if not send_next(): return failed
        continue
    wake = deadline
    if exactly one in flight and providers remain: wake = min(wake, that.start + hedge_delay)
    a = wait_any(inflight, max(0, wake - now))
    if a is None:                                     # a timer fired, nothing finished first
        if now >= deadline: cancel all, return timeout
        send_next()                                   # the hedge
        continue
    remove a from inflight
    if a.ok: cancel the rest, return ok
    # a failed: loop again (failover or keep waiting on the other one)
```

| `wait_any` returned | and | do |
|---|---|---|
| `None` | `now >= deadline` | cancel everything, `"timeout"` |
| `None` | before the deadline | hedge: `send_next()` |
| attempt, `.ok` | — | cancel the rest, `"ok"` |
| attempt, failed | another in flight | keep going; rule 3 still applies to it |
| attempt, failed | nothing in flight | fail over at once (top of the loop) |

## 7. Build it one piece at a time

**Step 1: choosing a provider.** One helper serves the first send, the hedge and the failover, so the breaker check can't be forgotten on any of them. That was the incident in `wrong_ignores_circuit.py`: the hedge path was a second send path without the check.

```python
    def send_next():
        while queue:
            p = queue.pop(0)
            if client.is_open(p):
                continue
            inflight.append(client.send(p, request))
            return True
        return False
```

**Step 2: giving up cleanly.** Cancel before you return. An attempt left running bills in full when it finishes.

```python
    def give_up(status):
        for a in inflight:
            client.cancel(a)
        return {"status": status, "provider": None, "text": None}
```

**Step 3: the wait.** Only hedge when exactly one attempt is in flight *and* a provider remains. With two in flight, or nothing left to hedge to, the only timer is the deadline.

```python
        wake = deadline
        if len(inflight) == 1 and queue:
            wake = min(wake, inflight[0].start + hedge_delay)
        a = yield from client.wait_any(inflight, max(0.0, wake - client.now()))
```

**Step 4: reacting.** `None` means a timer fired. Check the deadline first, because the deadline and the hedge timer can coincide, and you must never send at or after the deadline.

```python
        if a is None:
            if client.now() >= deadline:
                return give_up("timeout")
            send_next()
            continue
        inflight.remove(a)
        if a.ok:
            for other in inflight:
                client.cancel(other)
            return {"status": "ok", "provider": a.provider, "text": a.text}
```

"response exactly at the deadline counts" depends on the `wait_any` rule. Secondary was hedged at 1.0 with a 3.0 s latency, so it answers at exactly 4.0, the deadline. `wait_any` returns it rather than `None`, and you return `ok`.

## 8. Full solution

```python
def handle_request(client, request, providers, hedge_delay, deadline):   # a generator run on the event loop
    queue = list(providers)                    # providers not yet tried, in priority order
    inflight = []                              # attempts sent and not yet handled (at most two)

    def send_next():                           # the only send path: first send, hedge and failover
        while queue:                           # keep looking until a provider is usable
            p = queue.pop(0)                   # take the next provider; it is never reconsidered
            if client.is_open(p):              # its breaker is open right now
                continue                       # skipped for good, try the one after
            inflight.append(client.send(p, request))   # start the attempt now and track it
            return True                        # something was sent
        return False                           # no providers left to try

    def give_up(status):                       # every non-ok exit goes through here
        for a in inflight:                     # anything still running would keep billing
            client.cancel(a)                   # stop it; it bills input tokens only
        return {"status": status, "provider": None, "text": None}   # the non-ok result shape

    if not send_next():                        # the first attempt goes out at t = 0
        return {"status": "unavailable", "provider": None, "text": None}   # every breaker was open
    while True:                                # each pass either sends or waits once
        if not inflight:                       # nothing running: fail over at once
            if client.now() >= deadline:       # never send at or after the deadline
                return give_up("timeout")      # out of time
            if not send_next():                # no providers left to fail over to
                return give_up("failed")       # every provider failed
            continue                           # re-plan with the new attempt in flight
        wake = deadline                        # the deadline is always a timer
        if len(inflight) == 1 and queue:       # hedging is possible: one in flight, someone to hedge to
            wake = min(wake, inflight[0].start + hedge_delay)   # timer runs from this attempt's own start
        # wait until the earliest timer; a completion on that same instant is returned first
        a = yield from client.wait_any(inflight, max(0.0, wake - client.now()))
        if a is None:                          # a timer fired and nothing finished first
            if client.now() >= deadline:       # it was the deadline (checked first, it can coincide)
                return give_up("timeout")      # cancel everything and stop
            send_next()                        # it was the hedge timer: send the next provider
            continue                           # re-plan with two in flight
        inflight.remove(a)                     # handled; wait_any would return it again otherwise
        if a.ok:                               # first success wins
            for other in inflight:             # the loser is still running
                client.cancel(other)           # cancel it so it bills input tokens only
            return {"status": "ok", "provider": a.provider, "text": a.text}   # the winner's answer
        # a failed: loop again, which fails over at once or keeps waiting on the other attempt
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | primary ok at 0.75, cost 0.012 | no hedge when the primary answers before `hedge_delay` |
| Example 2 | secondary wins at 2, primary cancelled, cost 0.0148 | the hedge, and cancelling the loser |
| Example 3 | primary skipped, secondary 429 at 0.25, selfhosted wins at 1.5 | breaker skip at the first send, then immediate failover |
| hedge timer runs from the attempt in flight | selfhosted sent at 1.5, wins at 2 | `inflight[0].start + hedge_delay` |
| fail over immediately on error | secondary sent at 0.25, answer at 0.75 | no waiting out the hedge timer after an error |
| deadline cancels everything | `timeout` at 4, both attempts cancelled, cost 0.011 | the deadline and `give_up` cancelling |
| response exactly at the deadline counts | secondary ok at exactly 4 | a completion on the timer instant beats the timeout |
| primary fails after the hedge went out | selfhosted hedged at 2 (secondary's start 1 + 1), wins at 3 | rule 3 keeps applying to the attempt still in flight |
| everything fails | `failed` at 1.25, cost 0 | failover through the whole list; failures bill nothing |
| every circuit open | `unavailable`, no attempts, t 0 | the first `send_next()` finds nothing |
| circuit closes before the hedge | secondary (open until 0.5) is sent at 1 and wins | the breaker is checked when you reach the provider |
| circuit still open at hedge time | secondary skipped at 1, selfhosted wins at 1.75 | skipping at hedge time, for good |
| simultaneous finish, error first | primary's error and secondary's ok both at 2; secondary wins at 2 | the error is handled, then the ok returns with a zero timeout |
| simultaneous finish, both ok | primary wins (sent first); secondary finished too, cost 0.0215 | tie order; an attempt that already finished can't be cancelled |
| single provider times out | `timeout` at 2.5, cost 0.006 | deadline with no queue to hedge to |
| short hedge delay chains three providers | selfhosted sent at 0.75, wins at 2.75 | an overdue hedge timer fires at once after a failure |

## 10. Complexity

With `P ≤ 4` providers, each attempt causes at most a couple of loop passes, so the handler does O(P) work. `send_next` pops from the front of a list, which is O(P) per pop and irrelevant at this size. Memory is O(P).

What matters at scale is cost, not CPU. A hedge sends a second request, and a cancelled one still pays for its prompt. Hedge at roughly your p95 latency and only about 5% of requests hedge, while the tail shrinks a lot. Hedge too early and you pay for twice the input tokens on most requests. The `cost` field in the judge's output is there to make that trade-off visible.

## 11. If you got Wrong Answer

- **Cost is too high and the loser's outcome is `ok` instead of `cancelled`** (Example 2 costs 0.0208 instead of 0.0148). You never cancel the losing attempt.
- **The second attempt starts at `hedge_delay` exactly, even after a failover** ("hedge timer runs from the attempt in flight" sends selfhosted at 1.0 instead of 1.5). Your hedge timer runs from the request start. Use `inflight[0].start + hedge_delay`.
- **The failover starts late** ("fail over immediately on error" sends secondary at 1.0 instead of 0.25). You wait for the hedge timer after an error.
- **An attempt with outcome `circuit_open` appears in the log** (Example 3). You sent to a provider without checking `is_open`, on the first send or the hedge path.
- **"deadline cancels everything" returns `ok` at t=10.** You have no deadline: your wait has no timeout when two attempts are in flight.
- **The same attempt is handled twice or the loop never ends.** You didn't remove the returned attempt from `inflight`.

## 12. Follow-ups an interviewer might ask

- *How do you choose `hedge_delay`?* From the latency distribution, usually around p95, so only the slowest few percent hedge (Dean and Barroso, "The Tail at Scale"). Measure it with a streaming percentile sketch (problem 138, streaming-latency-percentiles). When you stream, hedge on time to first token, and stop hedging once a token arrives.
- *When must you not hedge?* When the call has side effects. An agent turn that sends an email or charges a card must not run twice, so hedge the model call, never the tool execution (problem 119).
- *What stops hedging from making an outage worse?* A hedge budget: cap hedged requests at, say, 10% of traffic, so that a provider-wide slowdown doesn't double your load on it. Feed every attempt's outcome into the per-provider breakers (problem 125), which is where `is_open` comes from.
- *How would you pick the order of `providers`?* With a router that weighs cost, latency and quality per request (problem 126) instead of a fixed list.
- *How does this map to real gateways?* Envoy's retry policy has per-try timeouts and hedging on per-try timeout; LiteLLM and Portkey expose fallback lists, per-attempt and overall timeouts. All of them need the same three rules: breaker check on every send path, timer per attempt, and cancel the loser.
