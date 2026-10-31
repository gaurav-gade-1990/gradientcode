## Approach

This is the back-of-envelope every LLM design review needs, done carefully enough to defend. Work from one session outward.

**One session.** A chat API is stateless, so turn $k$ resends everything before it: the system prompt, $k-1$ exchanges and the new message. Summing $k-1$ over the session gives the triangular term:

$$
\text{input} = T(S+U) + (U+O)\frac{T(T-1)}{2}
$$

With $T = 4$, $S = 800$, $U = 60$, $O = 240$, that is $3440 + 1800 = 5240$ tokens, not $4 \times 860 = 3440$. History dominates long sessions: at 25 turns it is most of the bill.

**Caching.** Prefix caching can serve the stable prefix (the system prompt plus earlier turns) but never the message that just arrived, and output is never cached. So `cached = hit_rate * (T*S + history)`.

**Traffic and capacity.** Daily turns over 86,400 s gives the average QPS. Capacity is sized for the peak, and each GPU only runs at its target utilization so latency stays flat:

```python
peak_output_tps = daily_turns / 86400 * peak_to_avg * O
gpus = max(1, math.ceil(peak_output_tps / (tps_per_gpu * utilization) - 1e-9))
```

The `- 1e-9` keeps an exact fit (900.0000000001 from float error) from buying a GPU you do not need. Monthly API cost is tokens times price per million, split by the model shares.

## Common mistakes

- **Ignoring history growth.** Multiplying per-turn tokens by turns underestimates long chats by 2-10x. This is the most common error in real cost estimates.
- **Caching the whole input.** The new user message is never a cache hit, so applying the hit rate to all input overstates the savings.
- **Sizing for the average.** Traffic peaks at 3-8x the daily average. A fleet sized for the mean falls over every weekday morning.
- **No utilization headroom.** Running GPUs at 100% means queueing, and TTFT goes up sharply well before you reach the theoretical throughput.
- **Rounding GPUs down.** `int()` buys 222 GPUs for a 222.2-GPU load. You cannot buy 0.2 of a GPU, and missing capacity is an outage.

## Production notes

- Real prices have more tiers: Anthropic charges a premium for cache writes (1.25x for a 5-minute TTL) and 0.1x for cache reads, and OpenAI discounts cached input automatically. See **prompt-caching-cost** for the write and read accounting.
- Self-hosting is not just decode. Prefill throughput, KV-cache memory (**gpu-capacity-planner**), replicas across zones, idle overnight capacity and on-call engineers usually add 30-100% to the GPU line.
- Measure the peak from real traffic (the p99 of 1-minute QPS over a week) rather than assuming a peak factor, and redo the estimate after launch with real token counts from your gateway logs (**tenant-cost-attribution**).
- The usual answer is hybrid: an API for the long tail and spiky traffic, and self-hosted small models for the high-volume, latency-tolerant paths.
