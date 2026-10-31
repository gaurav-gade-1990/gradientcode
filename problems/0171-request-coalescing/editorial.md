## Approach

Single flight is a map from key to the in-progress call. In an async runtime the in-progress call is a task (a future), and every caller awaits it.

```python
def call(self, request):
    if request["temperature"] > 0:
        return (yield from self.upstream(request))
    k = self.key(request)                      # canonical JSON of (tenant, model, messages)
    task = self.inflight.get(k)
    if task is None:
        task = self.loop.spawn(self._flight(k, request))
        self.inflight[k] = task
    return (yield task)

def _flight(self, k, request):
    try:
        return (yield from self.upstream(request))
    finally:
        del self.inflight[k]
```

Two details carry the correctness. First, the **flight owns its own eviction**. The `finally` runs when the upstream call settles, before any waiter resumes, on success and on failure alike. If the first caller evicts after it wakes up, or only on success, the map holds a finished task that later callers silently reuse. Second, the **key is the full identity of the answer**: tenant, model and the canonical messages. Anything that can change the response belongs in the key.

## Common mistakes

- **No tenant in the key.** Two customers paste the same prompt, and one gets the other's completion. This is a cross-tenant data leak, not a cache miss. It is the same incident class as a semantic cache keyed without the tenant.
- **Never evicting.** Without eviction the coalescer is an unbounded cache with no TTL. Requests an hour later get the old answer, and memory grows without limit.
- **Evicting only on success.** A single 503 from the provider gets cached as the permanent answer for that prompt, and every retry fails instantly until the process restarts.
- **Coalescing sampled requests.** With `temperature > 0` the user wants a different draw, and "regenerate" must actually regenerate. Sharing one sample also skews any A/B test that counts responses.

## Production notes

- Go's `golang.org/x/sync/singleflight` is the reference design (`Do`, `DoChan`, `Forget`). Envoy and Varnish call it request collapsing, CDNs call it origin shielding, and Nginx has `proxy_cache_lock`.
- Coalescing is not caching. It removes duplicate work only while the call is in flight. Put a semantic or exact cache (**semantic-cache**, 127) behind it, so a request that arrives just after a flight settles hits the cache instead of the provider.
- In a cluster, an in-process coalescer only collapses requests on the same replica. Use consistent hashing on the key (**consistent-hashing-sessions**, 175) to route identical requests to one replica, or a Redis lock to share flights across replicas.
- Streaming responses complicate it. Late joiners need the tokens already sent, so you have to buffer the stream and replay it, or not coalesce streams at all.
- Cancellation: if the first caller disconnects, keep the flight alive for the other waiters, and cancel it only when the waiter count drops to zero. **oauth-single-flight-refresh** (120) applies the same pattern to token refreshes.
