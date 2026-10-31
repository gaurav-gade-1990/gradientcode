## Approach

Index children by parent, walk from the root, and use one helper for both the self-time and kind-time questions: the length of a union of intervals.

```python
def union_length(intervals):              # sort, then merge
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(intervals):
        if e <= s: continue
        if cur_e is None or s > cur_e:
            if cur_e is not None: total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    return total + (cur_e - cur_s if cur_e is not None else 0.0)

self_time[s] = (s.end - s.start) - union_length(
    [(max(c.start, s.start), min(c.end, s.end)) for c in children[s]])

cur = root
while children[cur]:
    cur = min(children[cur], key=lambda c: (-c.end, -c.start, c.id))
```

The child that ends last is the one the parent was waiting on when it finished, so following it repeatedly gives the chain that set the total latency.

## Common mistakes

- **Summing overlapping children.** With three parallel tool calls the parent gets negative self time.
- **Not clipping.** A fire-and-forget email that outlives the request isn't time the parent spent waiting, and without clipping it drives the parent's self time negative. Clipping is for self time only: the latest-end rule still puts that email on the critical path, and `time_by_kind` uses the raw intervals.
- **Following the longest child.** A long LLM call that finished early isn't what the user waited on at the end.
- **Summing durations by kind.** Three parallel LLM calls of 500 ms are 500 ms of waiting, not 1500. (The sum is still the right number for *cost*; report both in practice.)
- **Re-parenting orphans to the root.** It mixes in spans from other requests or a sampled-away subtree.

## Production notes

- Jaeger's critical-path view and Honeycomb's trace waterfall compute the same thing. Jaeger's version also walks backwards through gaps between sequential children; the latest-end rule is the common simplification.
- Instrument LLM and tool calls with the OpenTelemetry GenAI semantic conventions (`gen_ai.operation.name`, `gen_ai.usage.input_tokens`) so `kind` and cost come for free. Langfuse, LangSmith and Arize consume the same spans.
- Tail-based sampling (in the OTel Collector) keeps whole slow traces; head sampling is what creates orphans.
- Pair with problem 103 (parallel-tool-dag), whose start and end events are these spans, and with problems 138 and 139 for turning per-trace latency into percentiles and SLO alerts.
