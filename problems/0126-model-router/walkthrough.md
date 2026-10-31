## 1. What the problem is really asking

A platform with several models and several customer tiers wants each request on the **cheapest model that's good enough and fast enough for that customer**, and wants a provider failure to fall back automatically, but never to a model the customer's contract doesn't allow.

Under the story, this is **filter, sort, walk** per request:

1. **Filter** the models by the tier's quality floor, the tier's latency ceiling, the request's size against each context window, and a set of models already rate limited in this batch.
2. **Sort** what's left by this request's estimated cost, with two tie-breakers.
3. **Walk** the sorted list, up to `max_attempts` calls, reacting to each outcome: success stops, a retryable error moves on, a 400 stops for good.

One piece of state crosses requests: a model that returned 429 is skipped for the rest of the batch. The judge compares the report (status, model, attempts and cost for every request, plus `total_cost`) and also records every `call` you made, so calling an extra model, or the right models in the wrong order, is a Wrong Answer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `models` | `name`, `quality`, `p95_ms`, `context_window`, two prices per million tokens | the candidate pool |
| `tiers` | `min_quality`, `max_p95_ms`, `max_attempts` | the request's contract |
| `requests` | `id`, `tier`, `input_tokens`, `max_output_tokens` | routed in the order given |
| `call(name, request)` | the provider; returns `{"output_tokens"}` or raises | exactly once per attempt |

| outcome | action | status if it ends here |
|---|---|---|
| returns | stop | `ok` |
| `RateLimitError` | mark the model limited, try the next one | `exhausted` if nothing else succeeds |
| `ServerError`, `TimeoutError_` | try the next one | `exhausted` |
| `BadRequestError` | stop | `bad_request` |

Three details are easy to miss:

- **Estimate with `max_output_tokens`, bill with the real `output_tokens`.** You rank before the call, when only the maximum is known. You bill after it.
- **The context check is `input_tokens + max_output_tokens <= context_window`.** The output has to fit too.
- **`max_attempts` bounds calls, not the ranked list.** Slice the list to `max_attempts`.

## 3. Trace Example 1 by hand

Three requests, no scripted failures.

**`faq-1`** (free: quality ≥ 0.60, p95 ≤ 1000 ms; 600 in, 300 max out). Eligible: `edge-8b` (0.62, 450 ms) and `fast-small` (0.74, 900 ms). Estimates:

| model | estimate |
|---|---|
| edge-8b | (600 × 0.10 + 300 × 0.10) / 1e6 = $0.00009 |
| fast-small | (600 × 0.80 + 300 × 4.00) / 1e6 = $0.00168 |

`edge-8b` succeeds with 120 real output tokens: cost (600 × 0.10 + 120 × 0.10) / 1e6 = $0.000072.

**`summ-7`** (pro: quality ≥ 0.75, p95 ≤ 3000 ms; 2000 in, 1000 max out). Eligible: `reasoning-mini`, `oss-70b`, `balanced-mid`.

| model | input price | output price | estimate |
|---|---|---|---|
| oss-70b | 0.90 | 0.90 | $0.0027 |
| reasoning-mini | 0.50 | 6.00 | $0.007 |
| balanced-mid | 3.00 | 15.00 | $0.021 |

`reasoning-mini` has the cheapest input, but for this request `oss-70b` is cheaper overall. It succeeds with 640 output tokens: $0.002376.

**`legal-3`** (enterprise: quality ≥ 0.85). Only `balanced-mid` ($0.066) and `frontier-large` ($0.33) qualify. `balanced-mid` succeeds with 1,500 output tokens: $0.0585. `total_cost` is $0.060948.

**Example 3** adds the sticky rate limit. `t-1` (pro) tries `oss-70b`, gets 429, marks it limited, and falls back to `reasoning-mini`, which succeeds. `t-2` is the same tier and size, but `oss-70b` is no longer eligible, so its first and only call is `reasoning-mini`. `t-3` (free) gets a 400 from `edge-8b` and stops with `attempts: ['edge-8b']`; `fast-small` is never called.

## 4. Key idea: rank by this request's cost, not by a price column

A model call has two meters, input and output, and their ratio differs by model. `reasoning-mini` is $0.50 in and $6.00 out; `oss-70b` is $0.90 in and $0.90 out. Which is cheaper depends on the request: for a summary with 1,000 output tokens, `oss-70b` wins by more than 2×. Sorting by input price alone gets Example 1, 2 and 3 wrong.

The estimate is computed per request, so the same pool can rank differently for different requests. In "mixed batch", `m-4` (a pro request with relatively more output) ranks `reasoning-mini` ($0.003186) just ahead of `oss-70b` ($0.0032), while most other pro requests rank `oss-70b` first.

## 5. Key idea: fallbacks never leave the eligible list

The tier is a contract. An enterprise customer pays for quality ≥ 0.85. If `balanced-mid` returns a 5xx and you fall back to the next cheapest model in the whole catalog, the request gets answered by an 8B model, every health check passes, and the customer gets a worse product without anyone knowing. In "fallback stays inside the tier", `e-1`'s fallback after `balanced-mid` fails is `frontier-large`, the only other enterprise-eligible model, even though it's five times the price.

Failing loudly (`exhausted` or `no_eligible_model`) is better than silently breaking the contract.

## 6. Plan before you code

```
limited = set()
for each request, in order:
    tier = tiers[request.tier]
    eligible = models passing quality, latency, context, and not in limited
    sort eligible by (estimate, -quality, name)
    status = "no_eligible_model" if empty else "exhausted"
    for m in eligible[:max_attempts]:
        record the attempt; call it
        BadRequestError -> status bad_request; stop
        retryable       -> if 429, add m to limited; next model
        success         -> status ok; bill actual usage; stop
total_cost = sum of successful costs
```

Setting the default status before the loop handles both "nothing eligible" and "ran out of attempts" without extra branches.

## 7. Build it one piece at a time

**Step 1: the estimate.** Exactly as the problem writes it. The test prices are chosen so that tied estimates are equal as floats when computed this way.

```python
def _estimate(m, req):
    return (req["input_tokens"] * m["input_per_mtok"] + req["max_output_tokens"] * m["output_per_mtok"]) / 1e6
```

**Step 2: filter and sort.** The sort key is a tuple, so ties fall through to the next element. `-m["quality"]` sorts higher quality first while everything else sorts ascending.

```python
        eligible = [m for m in models
                    if m["quality"] >= tier["min_quality"] and m["p95_ms"] <= tier["max_p95_ms"]
                    and need <= m["context_window"] and m["name"] not in limited]
        eligible.sort(key=lambda m: (_estimate(m, req), -m["quality"], m["name"]))
```

In "ties by quality then name", all three models estimate $0.002 for a 1,000-in, 1,000-out request. `mid` (quality 0.9) is first, then `alpha` before `zeta` by name.

**Step 3: the attempt loop.** Append the model name before calling, so failed attempts are listed too. `break` on a 400 ends the request; `continue` on a retryable error moves to the next model.

```python
        for m in eligible[:tier["max_attempts"]]:
            res["attempts"].append(m["name"])
            try:
                usage = call(m["name"], req)
            except BadRequestError:
                res["status"] = "bad_request"
                break
            except RETRYABLE as e:
                if isinstance(e, RateLimitError):
                    limited.add(m["name"])
                continue
```

**Step 4: bill the success.** Use the returned `output_tokens`. Billing `max_output_tokens` overstates spend; in Example 1 it would bill `summ-7` at $0.0027 instead of $0.002376.

```python
            res["status"], res["model"] = "ok", m["name"]
            res["cost"] = (req["input_tokens"] * m["input_per_mtok"] + usage["output_tokens"] * m["output_per_mtok"]) / 1e6
            total += res["cost"]
            break
```

## 8. Full solution

```python
from gc_runtime import BadRequestError, RateLimitError, ServerError, TimeoutError_  # provider failures

RETRYABLE = (RateLimitError, ServerError, TimeoutError_)  # another model might succeed; a 400 won't


def _estimate(m, req):  # what this request would cost on model m, before we know the real output
    return (req["input_tokens"] * m["input_per_mtok"] + req["max_output_tokens"] * m["output_per_mtok"]) / 1e6  # both meters


def route_requests(requests, models, tiers, call):  # cheapest eligible model per request, with fallback
    limited = set()  # models that returned 429 in this batch; skipped from then on
    results, total = [], 0.0  # one report row per request, and the running bill
    for req in requests:  # in the order given, because 429s carry over to later requests
        tier = tiers[req["tier"]]  # this request's contract
        need = req["input_tokens"] + req["max_output_tokens"]  # the prompt and the longest answer must fit
        # eligible = meets the quality floor, the latency ceiling, the context size, and isn't rate limited
        eligible = [m for m in models
                    if m["quality"] >= tier["min_quality"] and m["p95_ms"] <= tier["max_p95_ms"]
                    and need <= m["context_window"] and m["name"] not in limited]
        eligible.sort(key=lambda m: (_estimate(m, req), -m["quality"], m["name"]))  # cheapest, then best, then by name
        # default status: nothing to try, or (if we try and never succeed) out of attempts
        res = {"id": req["id"], "status": "no_eligible_model" if not eligible else "exhausted",
               "model": None, "attempts": [], "cost": 0.0}
        for m in eligible[:tier["max_attempts"]]:  # fallbacks come only from the eligible list, up to the cap
            res["attempts"].append(m["name"])  # every call is listed, failed or not
            try:  # one real call
                usage = call(m["name"], req)  # returns the real output token count
            except BadRequestError:  # the prompt itself is invalid
                res["status"] = "bad_request"  # it would fail on every model
                break  # so don't fall back
            except RETRYABLE as e:  # this model failed; another may not
                if isinstance(e, RateLimitError):  # throttled
                    limited.add(m["name"])  # don't send it anything else this batch
                continue  # try the next ranked model
            res["status"], res["model"] = "ok", m["name"]  # success
            # bill what was actually used, not max_output_tokens; failed attempts cost nothing
            res["cost"] = (req["input_tokens"] * m["input_per_mtok"] + usage["output_tokens"] * m["output_per_mtok"]) / 1e6
            total += res["cost"]  # add to the batch total
            break  # done with this request
        results.append(res)  # input order
    return {"results": results, "total_cost": total}  # the report
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `edge-8b`, `oss-70b`, `balanced-mid`; total $0.060948 | ranking by full estimate; billing actual output |
| Example 2 | `balanced-mid` on the third attempt, $0.0165 | fallback through two retryable errors; failures cost 0 |
| Example 3 | `t-2` skips `oss-70b`; `t-3` is `bad_request` after one call | sticky 429; stop on 400 |
| fallback stays inside the tier | `e-1` falls back to `frontier-large` | fallbacks stay in the eligible list |
| context window filters | `huge` is `no_eligible_model`; `big-2` goes to `fast-small` | `input + max_output <= context_window` |
| exhausted after max_attempts | `x-1` exhausted after 2 calls; `x-2` ok on `edge-8b` | the attempt cap; timeouts and 5xx don't mark a model limited |
| no eligible model | `n-1` makes no calls | an empty eligible list |
| bad request after a fallback | `b-1` stops at `reasoning-mini` | a 400 after a retry still stops |
| two rate limits shrink the pool | `r-2` and `r-3` go straight to `balanced-mid` | two models limited at once |
| ties by quality then name | `mid`, then `alpha`, then `zeta` | the tie-breakers |
| mixed batch | 12 requests, total $0.4054205 | everything together; `m-8` lands on `frontier-large` because `m-5` limited `balanced-mid` |

## 10. Complexity

For `R` requests and `M` models, each request filters in O(M) and sorts in O(M log M), then makes at most `max_attempts` calls. That's O(R · M log M) work, which is nothing next to the model calls themselves.

In production the inputs move. `p95_ms` is a rolling measurement rather than a constant, the rate-limit set is time-based (cleared when the provider's `retry-after` or `x-ratelimit-reset` passes, not at the end of a batch), and circuit-breaker state feeds eligibility, so a model that is down drops out of the list before anyone calls it. The quality scores come from an offline eval harness, usually per task type, and they're what makes "cheapest that's good enough" trustworthy.

## 11. If you got Wrong Answer

- **Example 1 picks `reasoning-mini` for `summ-7`.** You sorted by input price. Sort by the full estimate.
- **Every cost is too high.** You billed `max_output_tokens`. Bill `usage["output_tokens"]`.
- **Example 2 or "fallback stays inside the tier" falls back to a model outside the tier.** Fallbacks must come from the same eligible list.
- **Example 3's `t-3` calls `fast-small` after the 400.** A 400 stops the request.
- **Example 3's `t-2` calls `oss-70b` again.** You're not remembering 429s across requests.
- **"ties by quality then name" picks `alpha` or `zeta` first.** Your sort key is missing `-quality` or `name`.

## 12. Follow-ups an interviewer might ask

- *How would you use live health instead of a static p95?* Track latency and errors per model with a rolling window, and drop models whose circuit is open from the eligible list (problem 125, circuit-breaker).
- *What if latency matters more than cost?* Hedge: send to the first choice, and if it hasn't answered by a deadline, send to the second and take whichever finishes first (problem 134, gateway-failover-hedging).
- *Can the router know when a cheap model is good enough for this prompt?* Learned routers such as RouteLLM predict, per prompt, whether the small model's answer will be acceptable and escalate only when it won't. They sit in front of this cost ranking.
- *How do you bill tenants for this?* Attribute each successful call's cost to its tenant and request, including cached and failed-over calls (problem 131, tenant-cost-attribution).
- *What should a 429 really do?* Mark the model limited until its `retry-after` or reset time passes, and feed the per-tenant limiter so you stop the overload upstream (problem 123, token-bucket-rate-limiter).
