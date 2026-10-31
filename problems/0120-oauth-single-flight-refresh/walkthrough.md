## 1. What the problem is really asking

An agent fans out tool calls in parallel, all using one OAuth access token. When the token expires, every in-flight call gets `401` at about the same moment. If each one refreshes on its own, you send a burst of refreshes to the identity provider, and with rotating refresh tokens only the first succeeds: the rest get `invalid_grant`, and some providers then revoke the whole token family.

Under the story, this is **single-flight**, also called request coalescing: the first caller to need a refresh starts it, and everyone else who needs one while it's running **waits on that same task** and shares its result, or its error. Two extra rules make it correct:

- **Remember which token you sent.** A slow request that left with `tok_0` may come back with a 401 after someone else already refreshed to `tok_1`. That 401 says nothing about `tok_1`, so don't refresh again; just retry.
- **Free the slot when the refresh ends, even on failure.** Otherwise one failed refresh poisons every later call.

The judge runs everything on a deterministic `EventLoop` with virtual time. It grades every send as `[t, request id, token, status]`, the start time of every refresh, each call's result or raised error with its finish time, and the final `self.token`.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `loop` | `gc_runtime.EventLoop` | `self.loop.spawn(gen, name)` returns a `Task` |
| `token` | the current access token, `"tok_0"` | keep it in `self.token`; the refresh overwrites it |
| `send(token, request)` | a generator that takes virtual time | `resp = yield from self.send(token, request)` |
| `refresh()` | a generator; returns a new token or raises `BadRequestError` | `token = yield from self.refresh()` inside the refresh task |
| `call(request)` | **your** generator | the judge runs `yield from client.call(request)` |

The concurrency model is generators, not threads. Three things to know about it:

- **`yield from gen`** runs another generator to completion inside yours and gives you its return value. While it's waiting on virtual time, other tasks run.
- **`yield task`** suspends you until that `Task` finishes, then hands you its result. If the task raised, the same exception is raised at your `yield`. Every task waiting on it gets the same outcome.
- **`return x` in a generator** is how `call` delivers its response to the judge's `yield from`.

Two details are easy to miss:

- **The judge checks each token when the request *arrives*, after its latency.** A request sent at t=1.4 with latency 0.3 is judged at t=1.7.
- **There is at most one retry.** If the new token is also rejected, return that 401. Don't loop.

## 3. Trace Example 1 by hand

The token is already expired (`expires_at=0.0`). Three requests start at t=0 with latency 0.1. The refresh takes 0.5.

| t | event | `_inflight` | `self.token` |
|---|---|---|---|
| 0.0 | r1, r2, r3 send with `tok_0` | None | `tok_0` |
| 0.1 | r1 gets 401; no task in flight, and `self.token == sent_with`, so r1 spawns the refresh and waits | refresh | `tok_0` |
| 0.1 | r2 gets 401; a task is in flight, so it waits on it | refresh | `tok_0` |
| 0.1 | r3 gets 401; waits on the same task | refresh | `tok_0` |
| 0.6 | refresh returns `tok_1`; the `finally` clears the slot; r1, r2, r3 wake | None | `tok_1` |
| 0.6 | all three retry with `self.token` (`tok_1`) | None | `tok_1` |
| 0.7 | all three get 200 and return | None | `tok_1` |

`refreshes` is `[0.1]`, a single refresh. `sends` is three `[0.1, rX, 'tok_0', 401]` rows, then three `[0.7, rX, 'tok_1', 200]` rows.

**Example 3** shows the stale 401. `tok_0` expires at 0.05. r1 (latency 0.1) gets 401 at 0.1 and refreshes, so `tok_1` is in place by 0.6. r2 left at t=0 with `tok_0` and latency 1.0, so its 401 arrives at 1.0. No refresh is in flight, but `self.token` is `tok_1`, not the `tok_0` r2 sent. So r2 just retries with `tok_1` and gets 200 at 2.0. There's still only one refresh, at 0.1.

## 4. Key idea: the refresh must be its own Task

You could write the refresh inline in the first caller: `self.token = yield from self.refresh()`. The problem is that the other callers would have nothing to wait on. A `Task` is an object anyone can `yield`, and it delivers the same result, or the same exception, to all of them. That's how Example 2 works: r1's 401 at 0.1 starts the refresh, r2's 401 at 0.15 joins it, the refresh raises `invalid_grant` at 0.6, and both calls raise `BadRequestError` at 0.6 with no retry.

## 5. Key idea: clear the slot in `finally`

The slot must be empty again as soon as the refresh ends, whichever way it ends. If you clear it only after a successful refresh, a failure leaves `_inflight` pointing at a finished, failed task. Every later 401 then does `yield self._inflight`, gets the same old `BadRequestError` immediately, and the client never recovers.

"failure then recovery" tests this. The first refresh (t=0.1) fails, and r1 and r2 raise at 0.6. At t=2.1, r3 and r4 get 401s. With the slot cleared, r3 starts a second refresh at 2.1, r4 joins it, and both succeed at 2.7 with `tok_1`.

Putting the `finally` inside the refresh task, rather than in `call`, also gets the timing right. The task clears the slot before any waiter resumes, so no waiter can see a stale slot.

## 6. Plan before you code

```
call(request):
    sent_with = self.token
    resp = send(sent_with)
    if not 401: return resp
    if a refresh is in flight:      wait for it
    elif self.token == sent_with:   spawn one refresh, mark it in flight, wait for it
    else:                           someone already refreshed; don't refresh
    return send(self.token)         exactly one retry, with the CURRENT token

refresh task:
    try: token = refresh(); self.token = token; return token
    finally: clear the in-flight slot
```

| on a 401 | in flight? | `self.token == sent_with`? | action |
|---|---|---|---|
| first to notice | no | yes | spawn and wait |
| during a refresh | yes | either | wait |
| after a refresh finished | no | no | retry now |
| after a refresh failed | no | yes | spawn a new one |

The last row is "stale 401s after a failed refresh": b's 401 at 1.5 comes after the failed refresh ended at 0.6, the token is still `tok_0`, so b starts a second refresh at 1.5, which succeeds.

## 7. Build it one piece at a time

**Step 1: state.** One slot for the task.

```python
    def __init__(self, loop, token, refresh, send):
        self.loop = loop
        self.token = token
        self.refresh = refresh
        self.send = send
        self._inflight = None
```

**Step 2: the refresh task.** A generator that runs `refresh()`, stores the token, and always frees the slot. On failure the exception leaves the generator, and the event loop records it on the `Task`, so every waiter re-raises it.

```python
    def _refresh_task(self):
        try:
            token = yield from self.refresh()
            self.token = token
            return token
        finally:
            self._inflight = None
```

**Step 3: the first send.** Capture the token *before* sending. By the time the response arrives, `self.token` may have changed.

```python
    def call(self, request):
        sent_with = self.token
        resp = yield from self.send(sent_with, request)
        if resp["status"] != 401:
            return resp
```

**Step 4: join, start, or skip the refresh, then retry once.** Spawn with `self._refresh_task()`, with the parentheses: `spawn` takes a generator object, not the method.

```python
        if self._inflight is not None:
            yield self._inflight
        elif self.token == sent_with:
            self._inflight = self.loop.spawn(self._refresh_task(), "refresh")
            yield self._inflight
        return (yield from self.send(self.token, request))
```

The retry reads `self.token` at the moment of the retry. Using `sent_with` would resend the dead token.

## 8. Full solution

```python
class AuthClient:  # one shared OAuth token for many concurrent tool calls
    def __init__(self, loop, token, refresh, send):  # the event loop and the two I/O generators
        self.loop = loop  # used to spawn the single refresh Task
        self.token = token  # the current access token; the refresh replaces it
        self.refresh = refresh  # generator factory: new token, or raises BadRequestError
        self.send = send  # generator factory: the API call, judged when it arrives
        self._inflight = None  # the one refresh Task currently running, if any

    def _refresh_task(self):  # body of the shared refresh; every waiting call sees its result or error
        try:  # whatever happens, the slot must be freed
            token = yield from self.refresh()  # takes virtual time; may raise invalid_grant
            self.token = token  # publish the new token for every later send
            return token  # the Task's result
        finally:  # runs on success and on failure
            self._inflight = None  # free the slot, so a failed refresh can't poison later calls

    def call(self, request):  # generator: send, maybe refresh once, retry once
        sent_with = self.token  # a 401 only proves THIS token is bad
        resp = yield from self.send(sent_with, request)  # the first attempt
        if resp["status"] != 401:  # success, or any non-auth status
            return resp  # nothing to fix
        if self._inflight is not None:  # someone is already refreshing
            yield self._inflight  # wait for it; re-raises its error if it failed
        elif self.token == sent_with:  # nobody has refreshed since we sent: we're first
            self._inflight = self.loop.spawn(self._refresh_task(), "refresh")  # start the only refresh
            yield self._inflight  # wait like everyone else
        # else: someone refreshed while our request was on the wire; just retry
        return (yield from self.send(self.token, request))  # one retry with the CURRENT token, whatever comes back
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 1 refresh at 0.1; all three 200 at 0.7 | single-flight: one spawn, two joins |
| Example 2 | 1 refresh; both raise `BadRequestError` at 0.6 | the refresh error reaches every waiter; no retry |
| Example 3 | 1 refresh; r2 retries with `tok_1`, 200 at 2.0 | the `self.token == sent_with` test on a stale 401 |
| token never expires | no refreshes; both 200 | the non-401 fast path |
| failure then recovery | refreshes at 0.1 and 2.1; r3 and r4 200 at 2.7 | the `finally` frees the slot after a failure |
| expires mid-traffic | 1 refresh at 1.3; c, d, e join; e finishes at 2.1 | joins at different times; f sent after the refresh never sees a 401 |
| new token also rejected | both return 401 at 0.7 | exactly one retry, even when it fails |
| two expiry cycles | refreshes at 0.1, 1.6, 3.1; final token `tok_3` | a finished refresh isn't waited on again; each cycle refreshes once |
| slow 401 for old token while second refresh runs | refreshes at 0.1 and 1.1; b returns 401 at 4.0 | b's stale `tok_0` 401 at 2.0 retries with `tok_2` instead of refreshing a third time |
| stale 401s after a failed refresh | refreshes at 0.1 and 1.5; b 200 at 3.5 | after a failure, a 401 with an unchanged token starts a new refresh |

In "slow 401 for old token while second refresh runs", b's retry still fails: `tok_2` was issued at 1.6 with `token_ttl=0.5`, so it expired at 2.1, and the retry arrives at 4.0. The rule is one retry, so the 401 is returned.

## 10. Complexity

Each call does at most two sends and at most one refresh wait. For `N` concurrent calls during one expiry, the number of refreshes drops from `N` to 1, and every waiter's extra delay is one refresh latency plus one send. Memory is one slot.

At scale, the slot has to be shared across processes. Each pod would otherwise do its own refresh, and with rotating refresh tokens the second pod's refresh fails. The usual design is a short lock per connection in Redis (`SET key NX PX`), and after acquiring it, re-read the stored token: if it changed, skip the refresh. That re-read is the same check as `self.token != sent_with`. Most clients also refresh **proactively** a little before `expires_in` runs out, so this reactive path is the backstop.

## 11. If you got Wrong Answer

- **`refreshes` has three entries in Example 1.** You refresh on every 401. Check the in-flight slot first, and join it.
- **Example 3 has a second refresh at 1.0.** You refresh on a stale 401. Compare `self.token` with `sent_with` before refreshing.
- **The retry shows `tok_0` again and gets 401.** You retried with `sent_with`. Retry with `self.token`.
- **"failure then recovery" raises for r3 and r4 at 2.1 with no second refresh.** The slot is cleared only on success. Put the clear in `finally`.
- **"new token also rejected" never finishes.** You retry in a loop: each new token is rejected too, so the loop refreshes forever. One retry, then return.
- **Runtime Error mentioning `BadRequestError` handling.** Don't catch the refresh error in `call`. Let it propagate; the driver records it.

## 12. Follow-ups an interviewer might ask

- *How is this different from request coalescing in general?* It's the same pattern applied to credentials. Problem 171 (request-coalescing) does it for identical cache misses: one origin fetch, many waiters.
- *What should happen on `invalid_grant`?* Treat it as terminal. Mark the connection as needing re-consent, tell the user, and stop retrying. Retrying a revoked refresh token never helps.
- *How would you avoid most 401s in the first place?* Refresh early: when `expires_in` is within a minute or so, with jitter so many clients don't refresh at the same instant.
- *What about non-auth failures from `send`?* A 429 or 5xx needs retry with backoff (problem 124, retry-with-backoff), not a token refresh. Keep the two paths separate so a rate limit never triggers a refresh.
- *Where does this matter for MCP?* MCP's authorization spec uses OAuth 2.1 with refresh-token rotation for public clients, so an MCP client that fans tool calls out to a remote server needs exactly this guard.
