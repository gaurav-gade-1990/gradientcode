## Approach

Write the handler as one loop with two kinds of moves: **send** when a rule says so, otherwise **wait** with the right timeout.

```python
while True:
    if not inflight:                      # failover (or nothing left)
        if now >= deadline: return timeout
        if not send_next(): return failed
        continue
    wake = deadline
    if len(inflight) == 1 and queue:
        wake = min(wake, inflight[0].start + hedge_delay)
    a = yield from client.wait_any(inflight, max(0, wake - now))
    if a is None:                         # a timer fired, and nothing finished first
        if now >= deadline: cancel all; return timeout
        send_next(); continue             # the hedge
    inflight.remove(a)
    if a.ok: cancel the rest; return ok
```

`send_next()` takes the next provider and skips (for good) any whose circuit is open at that moment. Every rule then comes down to one question: "what is the earliest time something could change?" That is the next completion, the hedge timer of the single attempt in flight, or the deadline. Waiting for exactly that long keeps the timeline deterministic. Because `wait_any` returns a completion that lands on the timer instant, you never hedge against an attempt that has in fact just answered.

**Errors are not slowness.** A 5xx is information. Waiting out the hedge timer after an error throws away the time you just learned about.

**The hedge timer belongs to the attempt.** Measure it from the start of the attempt in flight, not from the start of the request. Otherwise every failover fans out right away.

## Common mistakes

- **Not cancelling the loser.** Your latency improves while the bill doubles. Cancelling (closing the stream) usually stops output billing, but the prompt is already paid for.
- **Hedging into an open circuit.** The hedge path is a second send path, and it needs the same breaker check.
- **Waiting out the hedge after an error.** That adds `hedge_delay` to every failover.
- **No overall deadline.** Hung providers hold workers, and the user's spinner keeps turning.
- **A hedge timer from the request start.** Failovers become instant double sends.

## Production notes

- Hedging comes from Dean and Barroso's "The Tail at Scale". Send a backup request after the p95 latency, and the extra load stays small (around 5%) while the tail shrinks a lot. For LLMs, set the hedge delay from the **TTFT** distribution when you stream, and hedge only until the first token arrives. After that, cancelling the winner's competitor matters more than racing.
- Gateways such as LiteLLM, Portkey and Envoy (`retry_policy` with hedging, `per_try_timeout`) expose these knobs: fallback order, timeouts per attempt and overall, and hedge on per-try timeout. Envoy hedges only on timeouts by default, and it is a deliberate choice.
- Hedging is only safe for **idempotent** calls. A tool-using agent turn that sends emails must not run twice, so hedge the model call, never the tool execution (problem 119).
- Budget the hedges: cap the fraction of hedged requests (for example 10%) so that a provider-wide slowdown doesn't double your traffic exactly when the provider is struggling. Feed the outcomes back into the breakers (problem 125), and pick the order with the router (problem 126).
