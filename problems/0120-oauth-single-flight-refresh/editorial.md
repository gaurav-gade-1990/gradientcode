## Approach

This is **single-flight** (request coalescing) applied to credentials. Keep a slot for the one refresh Task in flight, and let every 401 that arrives while it runs wait on that same Task.

```python
def _refresh_task(self):
    try:
        token = yield from self.refresh()
        self.token = token
        return token
    finally:
        self._inflight = None              # success or failure, the slot is free again

def call(self, request):
    sent_with = self.token
    resp = yield from self.send(sent_with, request)
    if resp["status"] != 401:
        return resp
    if self._inflight is not None:
        yield self._inflight               # join the refresh already running
    elif self.token == sent_with:
        self._inflight = self.loop.spawn(self._refresh_task(), "refresh")
        yield self._inflight
    return (yield from self.send(self.token, request))
```

There are three details to get right:

1. **Remember the token you sent.** A 401 proves only that `sent_with` is bad. A slow request sent with `tok_0` can come back after the refresh already finished. At that point the client holds `tok_1`, so the right move is to retry, not to refresh again.
2. **Spawn the refresh as its own Task.** If the first caller ran `refresh()` inline, there would be nothing for the others to wait on. A Task gives every waiter the same result, or the same exception.
3. **Clear the slot in `finally`.** Then a failed refresh frees the slot, and the next 401 can try again.

## Common mistakes

- **A refresh per 401.** Fifty parallel tool calls make fifty refreshes. With rotating refresh tokens (Auth0, Okta, Google with rotation enabled) only the first one succeeds, the other 49 get `invalid_grant`, and some providers then revoke the whole token family as a suspected replay.
- **Refreshing on a stale 401.** If you don't compare against the token you sent, a slow request that left before the refresh triggers a second, needless refresh.
- **A poisoned slot.** When the slot is cleared only on success, one failed refresh means every later 401 re-raises the old error forever, even after the user re-authorizes.
- **Retrying with the captured token.** If you retry with `sent_with` instead of `self.token`, you send the dead token again and get a guaranteed second 401.
- **Retrying in a loop.** If the new token is also rejected (it's revoked, or the clock is skewed), stop after one retry and surface the 401. Don't spin.

## Production notes

- Refresh **proactively**. Real clients refresh when `expires_in` is close (often 60 s early, with jitter), so most calls never see the 401 at all. This reactive path is the backstop.
- Across processes or pods, the in-flight slot lives in Redis or the database: a short lock keyed per connection (`SET key NX PX`), then a re-read of the token after the lock. That's the same "did someone else already refresh?" check as `self.token != sent_with`.
- MCP's authorization spec uses OAuth 2.1, with PKCE and refresh-token rotation for public clients, so an MCP client that fans tool calls out to a remote server needs exactly this guard.
- Treat `invalid_grant` as **terminal**. Mark the connection as needing re-consent, tell the user, and stop retrying. The Google, Microsoft and Salesforce SDKs all raise a distinct error for it.
- Pairs with **request-coalescing** (171), the general single-flight pattern, and **retry-with-backoff** (124) for the non-auth failures.
