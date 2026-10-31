## Approach

For each request: filter, rank, then walk the ranked list.

```python
eligible = [m for m in models
            if m["quality"] >= tier["min_quality"]
            and m["p95_ms"] <= tier["max_p95_ms"]
            and need <= m["context_window"]
            and m["name"] not in limited]
eligible.sort(key=lambda m: (estimate(m, req), -m["quality"], m["name"]))
for m in eligible[:tier["max_attempts"]]:
    try:
        usage = call(m["name"], req)
    except BadRequestError:
        status = "bad_request"; break        # same prompt fails everywhere
    except (RateLimitError, ServerError, TimeoutError_) as e:
        if isinstance(e, RateLimitError):
            limited.add(m["name"])           # skip it for the rest of the batch
        continue
    cost = (inp * m["input_per_mtok"] + usage["output_tokens"] * m["output_per_mtok"]) / 1e6
    break
```

**Rank by this request's cost, not by a price column.** A chat completion is two meters. Summaries and code generation are output-heavy, so a model with cheap input and expensive output loses on exactly the traffic that matters. Estimate with `max_output_tokens`, because that's what you know before the call, and then bill the actual usage.

**Fallbacks come from the same eligible list.** The tier is a contract (quality floor, latency SLO). Falling back to an ineligible model breaks it silently, which is worse than failing loudly.

## Common mistakes

- **Sorting by input price only.** This is cheap for RAG traffic and very expensive for long answers.
- **Falling back to anything.** An enterprise request that ends up on an 8B model passes every health check and fails the customer.
- **Retrying 400s on other models.** A prompt that is too long or blocked by policy fails the same way everywhere, and you pay the latency three times.
- **Billing `max_tokens`.** Budgets and dashboards then overstate spend by 3–10×.
- **Forgetting the 429.** Hitting the same throttled model first for every later request doubles latency and deepens the hole.

## Production notes

- Real routers (OpenRouter, LiteLLM's router, Martian, internal gateways) use the same shape: a static eligibility filter from policy, a dynamic ranking from cost and live health, and a fallback chain. The live part replaces the static `p95_ms` with a rolling measurement and feeds circuit state (problem 125) into eligibility.
- Quality per tier normally comes from an offline eval harness, per task type, not one global score. Many teams route by task (classification goes to small models, reasoning to large ones) before cost even enters.
- The rate-limit cooldown here is batch-scoped. In production it's time-based and driven by `retry-after` and the provider's `x-ratelimit-reset-*` headers.
- Learned routers (RouteLLM and similar) predict whether the small model will be good enough for this prompt and escalate only when needed. They sit in front of exactly this cost-ranking step.
- Pair this with tenant cost attribution (problem 131) to bill what you routed, and with hedging and failover (problem 134) when latency matters more than cost.
