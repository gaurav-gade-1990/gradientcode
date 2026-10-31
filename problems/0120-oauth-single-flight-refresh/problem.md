Your agent's tools call a customer's Salesforce, Jira and Google APIs with one shared OAuth access token. When the token expires, a burst of parallel tool calls all get `401` at once, and today each one refreshes on its own. The identity provider rate-limits you, and some providers rotate refresh tokens so only the first refresh succeeds. Make the refresh single-flight.

Implement `class AuthClient(loop, token, refresh, send)`:

- `loop` is a `gc_runtime.EventLoop`. `token` is the current access token (a string); keep it in `self.token`.
- `send(token, request)` returns a generator. Run it with `resp = yield from self.send(token, request)`. It takes virtual time and returns `{"status": 200 | 401, "body": str}`.
- `refresh()` returns a generator. Run it with `yield from self.refresh()`. It takes virtual time and returns the new token string, or raises `gc_runtime.BadRequestError` (`invalid_grant`).

`call(request)` is a **generator** (the judge runs it with `yield from client.call(request)` inside an `EventLoop` task) that returns the final response dict. Follow these rules exactly:

| step | rule |
|---|---|
| 1 | Remember `sent_with = self.token`, then `resp = yield from self.send(sent_with, request)`. If `resp["status"] != 401`, return `resp`. |
| 2a | On a 401, if a refresh Task is **in flight**, wait for it with `yield task`. |
| 2b | Otherwise, if `self.token != sent_with`, another call already refreshed while this request was on the wire. Do **not** refresh. |
| 2c | Otherwise, start exactly one refresh: `task = self.loop.spawn(...)` on a generator that runs `refresh()`, stores the new token in `self.token`, and returns it. Mark it in flight and wait for it with `yield task`. |
| 3 | Send once more with the **current** `self.token` and return that response, whatever its status. Never retry more than once. |

When the refresh raises, `yield task` re-raises the error in every waiting call. Let it propagate out of `call` without a retry. A refresh is **in flight** from the moment it is spawned until it finishes, successfully or not. A finished refresh, including a failed one, must not be waited on again, so a later 401 can start a fresh refresh.

The judge expires `tok_0` at `expires_at` and checks each token when the request arrives (after its latency). Refreshes issue `tok_1`, `tok_2`, … in order. It grades every send `[t, request id, token, status]`, the start time of every refresh, each call's response or raised error with its finish time, and the final `self.token`.

**Constraints**

- `1 <= len(requests) <= 10`; requests start at given virtual times and run concurrently
- Do not import `time`, `threading` or `asyncio`; wait only by yielding a Task
- Do not catch the refresh error inside `call`
