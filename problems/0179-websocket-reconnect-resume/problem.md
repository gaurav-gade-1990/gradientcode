Your chat UI streams the assistant's reply over a WebSocket. Mobile networks drop the socket mid-answer all the time. Write the client loop that reconnects with backoff and resumes from the last event it rendered, so the user sees every token exactly once.

`stream_chat(connect, backfill, on_event, clock, rand, max_failures=5, base=0.5, cap=8.0)` returns `"done"` or `"gave_up"`.

**The stream.** Events have consecutive integer ids starting at 1. Every event is `{"id": int, "type": "delta", "text": str}` except the last, which is `{"id": int, "type": "done", "text": ""}`.

**The API** (all from the judge):

| call | behavior |
|---|---|
| `sock = connect(last_event_id)` | Opens a socket that resumes after `last_event_id` (use `0` before anything was delivered). May raise `gc_runtime.ServerError` (refused). |
| `ev = sock.recv()` | The next event. Raises `gc_runtime.ServerError` when the connection drops. |
| `backfill(after_id, before_id)` | An HTTP fetch of the events with `after_id < id < before_id`, in order. Never fails. |
| `on_event(ev)` | Render a `delta` event in the UI. |

The server's resume is imperfect. It may **replay** events you already have (overlap), and its buffer may have lost some, so the first event can **jump ahead** of what you asked for.

**Rules**

| situation | what to do |
|---|---|
| `ev["id"] <= last_id` | duplicate: skip it |
| `ev["id"] > last_id + 1` | gap: call `backfill(last_id, ev["id"])` once, process each returned event in order, then process `ev` |
| a new `delta` event | `on_event(ev)`, set `last_id = ev["id"]`, set `failures = 0` |
| a new `done` event | return `"done"` (do not pass it to `on_event`) |
| `connect` or `recv` raises `ServerError` | `failures += 1`. If `failures == max_failures`, return `"gave_up"` immediately. Otherwise sleep and reconnect with `connect(last_id)`. |

Before reconnecting, sleep with full jitter using `clock.sleep`:

$$
\text{delay} = \text{rand}() \times \min(\text{cap},\ \text{base} \cdot 2^{\,\text{failures} - 1})
$$

Call `rand()` exactly once per sleep. `failures` counts consecutive failures, and it only resets when a new event is delivered (a duplicate does not count as progress).

The judge records every `connect` id, every sleep, every `backfill` call, the ids passed to `on_event`, the return value and the virtual time.

**Constraints**

- At most 40 events per stream and 15 connection attempts per case.
- `1 <= max_failures <= 8`; `rand()` returns floats in `[0, 1)`.
- Don't import `time` or `random`.
