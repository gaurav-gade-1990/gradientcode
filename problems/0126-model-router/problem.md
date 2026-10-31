Your platform serves three customer tiers from a pool of models. Product wants every request on the **cheapest model that meets its tier's quality and latency bar**, with automatic fallback when a provider errors. Write the router.

`route_requests(requests, models, tiers, call)` routes the requests **in the order given** and returns a report.

- `models` is a list of `{"name", "quality", "p95_ms", "context_window", "input_per_mtok", "output_per_mtok"}`. `quality` is the model's offline eval score in `[0, 1]`, and prices are US dollars per million tokens (illustrative).
- `tiers` maps a tier name to `{"min_quality", "max_p95_ms", "max_attempts"}`.
- Each request is `{"id", "tier", "input_tokens", "max_output_tokens"}`.
- `call(model_name, request)` sends the request to a model. It returns `{"output_tokens": int}` on success, or raises `RateLimitError`, `ServerError`, `TimeoutError_` or `BadRequestError` from `gc_runtime`.

**Routing one request:**

1. **Eligible models** satisfy all of `quality >= min_quality`, `p95_ms <= max_p95_ms` and `input_tokens + max_output_tokens <= context_window`, and have not been marked rate limited (rule 4).
2. **Rank** the eligible models by estimated cost, `(input_tokens * input_per_mtok + max_output_tokens * output_per_mtok) / 1e6`, ascending. Break ties by higher `quality`, then by `name` ascending. Compute the estimate exactly as written; the test prices make tied estimates compare equal.
3. **Try** them in rank order, at most `max_attempts` calls in total for this request.

| outcome of `call` | what to do |
|---|---|
| returns | Done: status `"ok"` |
| `RateLimitError`, `ServerError`, `TimeoutError_` | Try the next ranked model |
| `BadRequestError` | Stop: status `"bad_request"`. The prompt is invalid and will fail everywhere. |

4. **Rate limits are sticky for the batch.** When a model raises `RateLimitError`, mark it rate limited. It is not eligible for any later request in this call to `route_requests`, though the current request continues down its ranked list.
5. If no model is eligible, the status is `"no_eligible_model"` and no calls are made. If attempts run out (or the ranked list does) without a success, the status is `"exhausted"`.

**Cost.** A success costs `(input_tokens * input_per_mtok + output_tokens * output_per_mtok) / 1e6`, using the `output_tokens` that `call` returned. Failed attempts cost `0`.

Return:

```
{"results": [{"id", "status", "model", "attempts", "cost"}, ...],   # one per request, in input order
 "total_cost": float}
```

`model` is the model that succeeded, or `None`. `attempts` lists every model name you called, in order. `cost` is `0.0` unless the status is `"ok"`. The judge also records every `call` you make.

**Constraints**

- At most 10 models and 100 requests
- Model names are unique
- Call `call` exactly once per attempt; don't call a model you aren't going to use
