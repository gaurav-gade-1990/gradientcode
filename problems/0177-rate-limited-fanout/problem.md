When an agent run finishes, your platform notifies every subscriber over their channel (Slack, email, webhook). Each channel has its own rate limit, and some sends fail. Write the fan-out so that one slow or failing subscriber never holds up the rest of its channel, and no channel waits on another.

`fanout(loop, subscribers, channels, send)` runs on a `gc_runtime.EventLoop` and returns after every subscriber is delivered or given up on.

- `subscribers`: a list of `{"id": str, "channel": str}` in subscription order. Ids are unique.
- `channels`: `{name: {"interval": float, "max_attempts": int, "retry_delay": float}}`.
- `send(subscriber_id, channel)` returns a generator. Run it inside a task with `yield from send(sid, ch)`. It takes the channel's latency in virtual time, then returns, or raises `gc_runtime.ToolError` (transient) or `gc_runtime.BadRequestError` (permanent, for example an unknown Slack user).

**Scheduling rules**

| rule | detail |
|---|---|
| workers | Spawn exactly one task per channel that has subscribers, in sorted channel-name order. A worker sends one message at a time. |
| queue | Each channel keeps a queue of `(ready_time, seq, subscriber_id, attempt)`. Initially every subscriber is queued with `ready_time = 0`, `attempt = 1` and `seq` equal to its index in `subscribers`. |
| pick | When the worker is free, it takes the item with the smallest `(ready_time, seq)`. |
| rate limit | The attempt starts at `max(now, ready_time, last_start + interval)`, where `last_start` is when the previous attempt **on this channel** started (none before the first one). Wait with `yield <seconds>`. |
| success | The subscriber is delivered at the time `send` finished. |
| `BadRequestError` | Give up at once: failed with reason `"rejected"`. |
| `ToolError` | If `attempt == max_attempts`, failed with reason `"exhausted"`. Otherwise queue `(finish + retry_delay * 2**(attempt - 1), next_seq, id, attempt + 1)`, where `next_seq` counts up from `len(subscribers)` across all channels in the order retries are queued. Do not sleep in the worker; move on to the next item. |

Call `loop.run()` yourself, then return:

```python
{"delivered": {subscriber_id: finish_time}, "failed": {subscriber_id: "rejected" | "exhausted"}}
```

The judge also records every `send` call (its start time, channel, subscriber and outcome) and the final virtual time, and grades those too.

**Constraints**

- `1 <= len(subscribers) <= 40`, at most 4 channels.
- `0 <= interval <= 5`, `1 <= max_attempts <= 5`, `0 <= retry_delay <= 5`.
- Don't import `time`, threads or asyncio. Time moves only through `yield`.
