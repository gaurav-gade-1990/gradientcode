## 1. What the problem is really asking

A chat reply streams over a WebSocket, one token event at a time. Mobile networks drop sockets constantly. When that happens the client has to reconnect, ask the server to resume where it left off, and still show the user **every token exactly once**: no repeats ("Your order order #1182") and no holes ("Your order shipped").

Under the story this is a **reconnect loop around a cursor**. The one piece of state that matters is `last_id`, the id of the last event the user actually saw. Every rule hangs off it:

- an event with `id <= last_id` is a replay, so skip it (that gives *at most once*);
- an event with `id > last_id + 1` means the server lost some, so fetch the hole over HTTP (that gives *at least once*);
- a reconnect always asks for `connect(last_id)`, never from the start;
- backoff counts **consecutive** failures and resets only when a *new* event is delivered.

The judge records everything observable: every id passed to `connect`, every `clock.sleep` duration, every `backfill` call, the ids passed to `on_event`, how many times `rand()` was called, the return value, and the final virtual time `t`. So the exact delays and the exact reconnect ids are graded, not just the final text.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `connect(last_event_id)` | opens a socket that resumes after that id | call with `last_id`; may raise `ServerError` (refused) |
| `sock.recv()` | the next event | raises `ServerError` when the socket drops |
| `backfill(after_id, before_id)` | HTTP fetch of ids strictly between the two | called once per gap, before the event that revealed it |
| `on_event(ev)` | render a `delta` | never called with the `done` event |
| `clock` | virtual clock | `clock.sleep(delay)` is the only way to wait |
| `rand()` | jitter source in `[0, 1)` | exactly one call per sleep |
| `max_failures`, `base`, `cap` | backoff settings | `delay = rand() * min(cap, base * 2**(failures-1))` |

Three details are easy to miss:

- **`backfill`'s range is exclusive at both ends.** `backfill(2, 5)` returns ids 3 and 4. You still have to process event 5 yourself, after them.
- **A refused `connect` and a dropped `recv` are the same failure.** Both raise `ServerError`, so one `try` around both handles them alike.
- **The give-up check comes before the sleep.** When `failures` reaches `max_failures` you return `"gave_up"` immediately, with no last sleep and no extra `rand()` call. With `max_failures=1`, the first drop ends the call with `rand_calls = 0`.

The judge's fake server explains the test plans. A plan is consumed per `connect`: `{"refuse": True}` raises, otherwise the socket starts at `last_event_id + 1 - overlap + skip` and sends `send` events before dropping. Each `connect` advances the clock 0.1 s, each `recv` 0.05 s, each `backfill` 0.2 s.

## 3. Trace Example 3 by hand

Six deltas (ids 1–6), then `done` (id 7). Plans: `{"send": 2}`, then `{"skip": 2}`. Jitter draws start `0.5, 0.25, ...`.

| t | call | result | `last_id` | `failures` |
|---|---|---|---|---|
| 0.10 | `connect(0)` | socket from id 1, will send 2 | 0 | 0 |
| 0.15 | `recv()` | id 1, new: render | 1 | 0 |
| 0.20 | `recv()` | id 2, new: render | 2 | 0 |
| 0.25 | `recv()` | raises `ServerError` (drop) | 2 | 1 |
| 0.50 | `clock.sleep(0.5 * min(8, 0.5 * 2**0))` = 0.25 | | 2 | 1 |
| 0.60 | `connect(2)` | buffer lost 3 and 4: socket starts at 2 + 1 + 2 = 5 | 2 | 1 |
| 0.65 | `recv()` | id 5 > 2 + 1: **gap** | 2 | 1 |
| 0.85 | `backfill(2, 5)` | returns ids 3, 4; render 3, render 4, then render 5 | 5 | 0 |
| 0.90 | `recv()` | id 6: render | 6 | 0 |
| 0.95 | `recv()` | id 7, `done`: return `"done"` | 6 | 0 |

The judge's output: `connect_ids = [0, 2]`, `sleeps = [0.25]`, `backfills = [[2, 5]]`, `delivered_ids = [1, 2, 3, 4, 5, 6]`, `rand_calls = 1`, `t = 0.95`.

**Example 1 is the overlap case.** The socket drops after ids 1–3. The client sleeps 0.25 and calls `connect(3)`, but the plan has `overlap: 2`, so the server resumes at id 2. Ids 2 and 3 are `<= last_id` and are skipped. Ids 4 and 5 are rendered, and id 6 is `done`. The output shows `connect_ids = [0, 3]` and `delivered_ids = [1, 2, 3, 4, 5]`, with each id exactly once.

**The trickiest hidden case, "gap then drop then overlap".** Ten deltas, and four bad connections in a row:

| connect | plan | what arrives | effect |
|---|---|---|---|
| `connect(0)` | send 3 | 1, 2, 3, then drop | `failures` 1, sleep 0.5 × 0.5 = 0.25 |
| `connect(3)` | refuse | `ServerError` | `failures` 2, sleep 0.25 × 1.0 = 0.25 |
| `connect(3)` | skip 2, send 2 | 6 (gap), 7, then drop | `backfill(3, 6)` gives 4, 5; render 4, 5, 6, 7; `failures` back to 0, then 1 on the drop; sleep 0.9 × 0.5 = 0.45 |
| `connect(7)` | overlap 4, send 6 | 4, 5, 6, 7 (skipped), 8, 9, then drop | `failures` 0, then 1; sleep 0.1 × 0.5 = 0.05 |
| `connect(9)` | clean | 10, then done | `"done"` |

The judge reports `sleeps = [0.25, 0.25, 0.45, 0.05]`. The third sleep is the one to check. Because events 4–7 were delivered, `failures` went back to 0 before the drop, so the delay uses `2**0`. A client that never resets would sleep `0.9 * min(8, 0.5 * 2**2) = 1.8` there.

## 4. Key idea: progress, not a successful connect, resets the backoff

`failures` counts *consecutive failures without progress*. Two tempting alternatives are both wrong:

- **Never reset** (`wrong_backoff_never_resets.py`). In "progress resets backoff", each of four connections delivers two new events and then drops. With `max_failures=3`, a never-reset client gives up on the third drop even though every connection was making progress. The expected result is `"done"`, with sleeps `[0.25, 0.125, 0.45, 0.05]`, all at the first backoff step.
- **Reset when `connect` succeeds.** A socket that connects and drops at once isn't healthy. In "duplicates are not progress", the second and third connections only replay ids the client already has. The expected result is `"gave_up"` after `connect_ids = [0, 3, 3]`. A client that resets on connect keeps going and returns `"done"`. "drop before first event" catches it too: the second sleep is 0.125 instead of 0.25.

That's also why the reset sits next to `last_id = e["id"]`: the two happen together, at the moment a new event is rendered.

## 5. Key idea: process the backfill before the event that revealed the gap

When event 5 arrives with `last_id = 2`, the order you process things in is the order the user reads them. Fetch 3 and 4, render them, *then* render 5. Build one list, `backfill(...) + [ev]`, and run every item through the same code: render, set `last_id`, reset `failures`, and stop on `done`.

Running the batch through the same loop matters for the `done` check too. In "gap right before done", the client has id 1, reconnects, and the server skips straight to the `done` event, id 5. `backfill(1, 5)` returns 2, 3 and 4, which get rendered, and then the `done` event ends the stream. If you rendered `ev` first and the batch after, `done` would end the stream before 2, 3 and 4 were ever shown: that version delivers only `[1]`.

## 6. Plan before you code

```
last_id = 0, failures = 0
loop forever:
    try:
        sock = connect(last_id)
        loop:
            ev = sock.recv()
            if ev.id <= last_id: skip it
            batch = backfill(last_id, ev.id) if ev.id > last_id + 1 else []
            for e in batch + [ev]:
                if e is done: return "done"
                on_event(e); last_id = e.id; failures = 0
    on ServerError:
        failures += 1
        if failures >= max_failures: return "gave_up"
        sleep rand() * min(cap, base * 2**(failures - 1))
```

| event id vs `last_id` | action |
|---|---|
| `id <= last_id` | duplicate, skip |
| `id == last_id + 1` | render it |
| `id > last_id + 1` | `backfill(last_id, id)`, render those, then render it |

## 7. Build it one piece at a time

**Step 1: the happy path.** One connect, read until `done`. This alone passes "clean stream".

```python
def stream_chat(connect, backfill, on_event, clock, rand, max_failures=5, base=0.5, cap=8.0):
    last_id = 0
    sock = connect(last_id)
    while True:
        ev = sock.recv()
        if ev["type"] == "done":
            return "done"
        on_event(ev)
        last_id = ev["id"]
```

**Step 2: the reconnect loop with backoff.** Wrap connect and recv in one `try`, so a refusal and a drop are both a failure.

```python
    last_id, failures = 0, 0
    while True:
        try:
            sock = connect(last_id)
            ...  # the read loop
        except ServerError:
            failures += 1
            if failures >= max_failures:
                return "gave_up"
            clock.sleep(rand() * min(cap, base * 2 ** (failures - 1)))
```

The exponent is `failures - 1`, so the first retry waits up to `base`, not `2 * base`. Multiplying by `rand()` is *full jitter*: after a regional outage every client draws a different delay, instead of all reconnecting in the same instant.

**Step 3: dedupe and gap fill inside the read loop.**

```python
            while True:
                ev = sock.recv()
                if ev["id"] <= last_id:
                    continue
                batch = backfill(last_id, ev["id"]) if ev["id"] > last_id + 1 else []
                for e in list(batch) + [ev]:
                    if e["type"] == "done":
                        return "done"
                    on_event(e)
                    last_id = e["id"]
                    failures = 0
```

The `done` check comes before `on_event`. The problem says the `done` event is never rendered. A version that renders it first adds one extra id to `delivered_ids` in nine of the twelve cases.

## 8. Full solution

```python
# connect refusals and socket drops both arrive as ServerError
from gc_runtime import ServerError


# stream a chat reply, reconnecting with backoff and resuming from the last rendered event
def stream_chat(connect, backfill, on_event, clock, rand, max_failures=5, base=0.5, cap=8.0):
    last_id = 0  # id of the last event the user saw; 0 means nothing yet
    failures = 0  # consecutive failures since the last new event
    while True:  # one pass per connection attempt
        try:  # a refused connect and a dropped recv are handled the same way
            sock = connect(last_id)  # resume after what we have, never from the start
            while True:  # read until done or until the socket drops
                ev = sock.recv()  # the next event, or ServerError on a drop
                if ev["id"] <= last_id:  # the server replayed something we already rendered
                    continue  # skip duplicates, and don't count them as progress
                # a jump past last_id + 1 means the server lost events: fetch the hole first
                batch = backfill(last_id, ev["id"]) if ev["id"] > last_id + 1 else []
                for e in list(batch) + [ev]:  # missing events in order, then the one that revealed the gap
                    if e["type"] == "done":  # the reply is complete
                        return "done"  # done is never rendered
                    on_event(e)  # show this token to the user
                    last_id = e["id"]  # move the resume cursor
                    failures = 0  # new data is progress, so the backoff starts over
        except ServerError:  # the connection was refused or dropped
            failures += 1  # one more failure in a row
            if failures >= max_failures:  # out of attempts
                return "gave_up"  # stop now, with no final sleep
            # full jitter: a random fraction of the capped exponential delay
            clock.sleep(rand() * min(cap, base * 2 ** (failures - 1)))
```

## 9. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | `connect_ids [0, 3]`; ids 2, 3 replayed and skipped | reconnect with `last_id`, and dedupe with `id <= last_id` |
| Example 2 | `connect_ids [0, 0, 0]`, `sleeps [0.25, 0.25]` | refused connects count as failures; nothing delivered, so `connect(0)` |
| Example 3 | `backfills [[2, 5]]`, ids 1–6 | gap detection and backfill before the jumping event |
| clean stream | one connect, no sleeps, `t = 0.65` | the happy path |
| give up | `gave_up` after `connect_ids [0, 1, 1, 1]`, `sleeps [0.25, 0.25, 1.8]` | the backoff grows, and the give-up check comes before the sleep |
| progress resets backoff | `done`, `sleeps [0.25, 0.125, 0.45, 0.05]` | `failures = 0` on every new event |
| duplicates are not progress | `gave_up` after `connect_ids [0, 3, 3]` | a replay-only connection doesn't reset `failures` |
| gap right before done | `backfills [[1, 5]]`, ids 1–4 | the backfill is rendered before the `done` event ends the stream |
| gap then drop then overlap | `backfills [[3, 6]]`, `sleeps [0.25, 0.25, 0.45, 0.05]` | gap, refusal and overlap together |
| drop before first event | `connect_ids [0, 0, 0]`, `sleeps [0.25, 0.25]` | connecting isn't progress |
| cap reached | `sleeps [0.99, 1.98, 3.96, 3.96, 3.96, 3.96]` | `min(cap, ...)` with `base 1.0`, `cap 4.0` |
| max_failures one | `gave_up`, `rand_calls 0` | the first failure ends the call with no sleep |

## 10. Complexity

Each event is handled in O(1), apart from the backfill call, which returns the hole. Over a stream of `n` events with `r` reconnects, the work is O(n + replayed events + r). Memory is O(1) beyond the backfill batch: the client keeps one integer cursor and one counter, not the transcript.

The cost that matters in production is on the server and the network. Resuming from `last_id` means a drop costs only a short replay. Reconnecting from 0 replays the whole answer every time, and on a long answer over a bad link you can drop again before you even catch up. The worst-case wait before giving up is bounded too: at most `max_failures - 1` sleeps, each at most `cap`.

## 11. If you got Wrong Answer

- **`connect_ids` shows `0` on a reconnect.** You resume from the start: `wrong_resumes_from_zero.py`. It fails seven cases, and "progress resets backoff" even gives up.
- **`delivered_ids` has repeats** (7 ids instead of 5 in Example 1). You're missing the `id <= last_id` skip: `wrong_no_dedupe.py`. It also turns "duplicates are not progress" into `done`, because each replay looks like progress.
- **`backfills` is empty and the text has holes.** You don't detect the jump: `wrong_ignores_gap.py`.
- **`backfills` shows `[2, 6]` instead of `[2, 5]`.** You passed `ev["id"] + 1` as the upper bound. The range is already exclusive.
- **"gap right before done" delivers only `[1]`.** You process `ev` before the backfill batch, so `done` ends the stream first.
- **`sleeps[2]` is 1.8 instead of 0.45 in "gap then drop then overlap", or "progress resets backoff" gives up.** `failures` never resets: `wrong_backoff_never_resets.py`.
- **"duplicates are not progress" returns `done`, or the second sleep in "drop before first event" is 0.125.** You reset `failures` after `connect` succeeds instead of after a new event.
- **Every first sleep is 0.5 instead of 0.25.** Either the exponent is `failures` instead of `failures - 1`, or you forgot to multiply by `rand()`.
- **"give up" makes 5 connects, or "max_failures one" returns `done`.** You check `failures > max_failures`. Use `>=`.
- **`delivered_ids` has one extra id at the end.** You render the `done` event.

## 12. Follow-ups an interviewer might ask

- *How does SSE handle this?* It's built in. The browser's `EventSource` reconnects on its own, sends a `Last-Event-ID` header, and honours the server's `retry:` field. Parsing that wire format is problem 169 (sse-stream-parser). WebSockets have none of this, which is why you write this loop.
- *What does the server need to support resume?* A short replay buffer per stream (a Redis Stream or a ring buffer keyed by run id) for the `connect` path, and a durable event log for `backfill` once the buffer has rolled over. If even the log can't cover the gap, send a `resync` event and reload the whole message.
- *Why full jitter instead of a fixed exponential delay?* After a regional blip every open chat reconnects at once. Fixed delays keep the clients in lockstep, so the server takes the same spike at every retry step. Full jitter spreads them across `[0, delay)`. Retry policies are covered in problem 124 (retry-with-backoff).
- *What if the reply also contains tool calls streamed in pieces?* The same dedupe-by-id applies, and the client also has to stitch partial JSON arguments together by index (problem 115, streaming-tool-call-assembly).
- *How would multi-device sync reuse this?* The cursor becomes a per-device version, and the sync sends only changes after it. That's the delta-state version of problem 176 (lww-conversation-merge).
