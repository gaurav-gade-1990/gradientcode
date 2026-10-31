Your agent calls a model provider that sometimes fails. Write the retry wrapper that every model call in your gateway goes through.

`call_with_retry(fn, clock, rand, max_attempts=5, base=0.5, cap=8.0)` calls `fn()` and returns its result. If `fn` raises, apply these rules:

| error (from `gc_runtime`) | what to do |
|---|---|
| `RateLimitError` (429), `ServerError` (5xx), `TimeoutError_` | retry |
| `BadRequestError` (400) or anything else | re-raise immediately |

Before retry number `k` (`k = 0` for the first retry), sleep with **full jitter**:

$$
\text{delay}_k = \text{rand}() \times \min(\text{cap},\ \text{base} \cdot 2^k)
$$

If the error is a `RateLimitError` with a `retry_after` value, sleep `max(delay_k, retry_after)` instead. Call `rand()` exactly once per retry, even when `retry_after` wins, so the jitter sequence stays aligned.

Sleep only with `clock.sleep(seconds)`, which uses virtual time. After `max_attempts` total calls to `fn` have failed with retryable errors, re-raise the **last** error.

The judge records every `fn` call, every sleep, and what you return or raise.

**Constraints**

- `1 <= max_attempts <= 10`
- `rand()` returns floats in `[0, 1)`
- Don't import `time` or `random`. Use only `clock` and `rand`.
