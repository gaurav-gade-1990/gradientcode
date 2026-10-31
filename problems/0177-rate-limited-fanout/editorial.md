## Approach

Fan-out has two independent axes of isolation: **channels** must not wait on each other, and within a channel a **failing subscriber** must not block the healthy ones. One worker per channel gives the first. A ready-time queue gives the second.

```python
def worker(name):
    cfg, q, last_start = channels[name], queues[name], None
    while q:
        q.sort()                                   # smallest (ready_time, seq)
        ready, _, sid, attempt = q.pop(0)
        start = max(loop.now(), ready)
        if last_start is not None:
            start = max(start, last_start + cfg["interval"])
        if start > loop.now():
            yield start - loop.now()
        last_start = loop.now()                    # spacing is between starts
        try:
            yield from send(sid, name)
            delivered[sid] = loop.now()
        except BadRequestError:
            failed[sid] = "rejected"               # permanent: never retry
        except ToolError:
            if attempt >= cfg["max_attempts"]:
                failed[sid] = "exhausted"
            else:
                q.append((loop.now() + cfg["retry_delay"] * 2 ** (attempt - 1), next_seq(), sid, attempt + 1))
```

A failed send goes back into the queue with a future `ready_time`, so the worker immediately moves on to the next subscriber. The retry comes up again once its backoff has passed and it has the smallest ready time. Every attempt, retries included, consumes a rate-limit slot, because the provider counts requests, not distinct recipients.

## Common mistakes

- **Head-of-line blocking.** Sleeping the backoff inside the worker means one dead webhook delays every subscriber queued behind it by the full backoff ladder.
- **Retrying permanent errors.** A 400 or "unknown user" fails the same way every time. Retrying it burns rate-limit slots that healthy subscribers need.
- **Spacing from the finish.** The limit is on request starts. Measuring from the end of the previous send adds the latency to every gap and quietly halves throughput on slow channels.
- **One limiter for everything.** Sharing a single "last send" across channels serializes Slack behind email, even though each provider has its own quota.

## Production notes

- Real fan-out services (SNS, Knock, Courier, Novu) put each channel behind its own queue and worker pool, often with a token bucket per provider and per workspace. See **token-bucket-rate-limiter** for the bucket itself.
- Honor the provider's own signals: Slack returns `429` with `Retry-After`, and SES has a per-second send rate in the account. Use **retry-with-backoff** for jittered delays when many workers retry together.
- Failed deliveries go to a dead-letter queue with the reason, and they show up in the run's audit trail so a user can see why they were never notified.
- At scale the queue lives in Kafka, SQS or Redis Streams, and the per-channel ordering here becomes a partition key. Pair with **bounded-queue-backpressure** so a burst of notifications cannot grow the queue without bound.
