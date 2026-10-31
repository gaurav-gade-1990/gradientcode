## Approach

The client keeps one piece of state that matters: `last_id`, the id of the last event the user actually saw. Everything else follows from it.

```python
def stream_chat(connect, backfill, on_event, clock, rand, max_failures=5, base=0.5, cap=8.0):
    last_id, failures = 0, 0
    while True:
        try:
            sock = connect(last_id)                      # resume, never restart
            while True:
                ev = sock.recv()
                if ev["id"] <= last_id:
                    continue                             # replay overlap
                batch = backfill(last_id, ev["id"]) if ev["id"] > last_id + 1 else []
                for e in batch + [ev]:
                    if e["type"] == "done":
                        return "done"
                    on_event(e)
                    last_id, failures = e["id"], 0       # progress resets backoff
        except ServerError:
            failures += 1
            if failures >= max_failures:
                return "gave_up"
            clock.sleep(rand() * min(cap, base * 2 ** (failures - 1)))
```

Ids make the stream idempotent on the client side. A replayed event is recognizable (`id <= last_id`), and a missing one is recognizable too (`id > last_id + 1`). Dedupe gives "at most once", the backfill gives "at least once", and together the user sees exactly once.

Resetting `failures` on progress, not on a successful `connect`, matters on flaky links. A socket that connects and immediately drops is not healthy, but one that delivered new tokens is.

## Common mistakes

- **Reconnecting from zero.** The server replays the whole answer each time. With dedupe the UI looks right, but you pay for the full replay on every drop, and on a long answer you can drop before you catch up.
- **No dedupe.** Servers resume at-least-once. Without the `id <= last_id` check the user sees "Your order order #1182".
- **Trusting the first event after resume.** If the replay buffer evicted events, rendering what arrives leaves a hole in the middle of the sentence. Detect the jump and backfill over HTTP.
- **Backoff that never resets.** After a few drops on a long stream, the client waits the full cap or gives up, even though every connection was making progress.

## Production notes

- SSE has this built in: the browser's `EventSource` reconnects on its own and sends `Last-Event-ID`, and the server's `retry:` field sets the delay. WebSockets have nothing, so you build exactly this loop (Socket.IO's connection-state recovery and Phoenix channels do the same).
- The server side needs a short replay buffer per stream (a Redis Stream or a ring buffer keyed by run id), and a durable store for the backfill path once the buffer has rolled over. OpenAI's and Anthropic's streaming APIs do not resume, so chat products put their own event log between the model and the browser.
- Ack the id back to the server once rendered if the server trims its buffer by acks, and emit a `resync` or full-reload event when even the backfill store cannot cover the gap.
- Jitter is essential: after a regional blip, every open chat reconnects at once. Pair with **sse-stream-parser** for the wire format and **retry-with-backoff** for the delay policy.
