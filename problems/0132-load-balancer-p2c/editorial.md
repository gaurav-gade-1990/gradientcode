## Approach

This is a discrete-event simulation with two event types and one rule about ties.

```python
heap of (time, kind, seq, payload)    # kind 0 = completion sorts before kind 1 = arrival
on completion: outstanding[rep] -= 1; start the next queued request on rep, if any
on arrival:    rep = policy(...); outstanding[rep] += 1
               start now if busy[rep] < slots else enqueue
```

The policies differ only in what they look at:

- **Round-robin** looks at nothing. It is fair in *count*, but a replica at 25% speed gets 25% of the traffic and its queue grows without bound.
- **Least outstanding** looks at every replica's in-flight count. Slow replicas hold requests longer, so their count stays high and they get fewer new requests. The balancer adapts to speed without ever measuring it.
- **P2C** looks at two random replicas. Mitzenmacher's result is that two choices give an exponential improvement in the maximum load over one random choice, and they get most of the benefit of the full scan at O(1) cost and with no global state. Many balancers can then share the load without coordinating.

## Common mistakes

- **Counting only the queue.** Requests in service are load too, so a replica with full slots and an empty queue looks idle.
- **Never decrementing.** If the "done" hook doesn't fire on every path (streams, errors, client cancels), the counter turns into "requests ever assigned".
- **Arrivals before completions.** At the same instant, a slot being released should be visible to the arriving request.
- **An off-by-one in nearest-rank percentiles.** `int(0.99 * n)` reads past the rank for small n.
- **Breaking P2C ties by index.** This skews load toward low indices.

## Production notes

- Envoy's `LEAST_REQUEST` load balancer is P2C over active requests by default (`choice_count: 2`). NGINX has `least_conn` and `random two least_conn`. Finagle and linkerd use P2C with peak-EWMA latency. For LLM serving, Kubernetes' Gateway API Inference Extension and llm-d route on model-server metrics (queue depth, KV-cache utilization, LoRA adapters loaded) scraped from vLLM, because "outstanding requests" ignores how long each generation will run.
- Prefix-aware routing (send requests that share a prompt prefix to the replica that already has it cached) often beats pure load balancing for chat and agents. It trades balance for prefix-cache hit rate, so add a load cap.
- Slow replicas still need to be **ejected**, not just avoided. Pair this with outlier detection or a breaker per host (problem 125). Then scale on queue depth (problem 133), and model the server itself with the batching simulator (problem 129).
