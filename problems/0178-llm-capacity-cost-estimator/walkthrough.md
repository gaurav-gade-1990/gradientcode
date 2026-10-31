## 1. What the problem is really asking

A customer wants to know whether their support assistant should stay on a hosted API or move to their own GPUs. You answer with a back-of-envelope estimate, done carefully enough to defend in a design review.

Under the story this is **a chain of arithmetic in four layers**:

1. **One session:** how many input, cacheable and output tokens one conversation uses.
2. **Traffic:** sessions per day, turns per day, average and peak requests per second.
3. **API cost:** tokens per month times the price per million, split across models by share.
4. **Self-host cost:** enough GPUs for the *peak* decode load at a target utilization, rounded up, times the hourly price.

There's no algorithm to find. The difficulty is getting three modelling details right, each of which real estimates often get wrong: chat **resends its history** every turn, **only the prefix can be cached**, and GPUs are sized for the **peak, with headroom, rounded up**.

The judge compares every field of the returned dict with a relative tolerance of `1e-9`, so a formula that is "close" fails. It checks the intermediate values too (`peak_qps`, `monthly_cached_tokens`, the per-model breakdown), so an error shows up at the first field it affects.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `dau`, `sessions_per_user` | daily active users and sessions each | `daily_sessions = dau * sessions_per_user` |
| `turns_per_session` ($T$) | user messages per session | drives both the turn count and the history growth |
| `system_tokens` ($S$), `user_tokens` ($U$), `output_tokens` ($O$) | tokens per system prompt, user message, reply | the per-session formulas |
| `cache_hit_rate` | fraction of the cacheable prefix read from cache | `cached = rate * prefix` |
| `peak_to_avg` | peak QPS over average QPS | `peak_qps = avg_qps * peak_to_avg` |
| `days_per_month` | 30 or 31 | monthly tokens, GPU hours, `cost_per_turn` |
| `models` | `[{name, share, input, cached_input, output}]` | prices in $ per **million** tokens; shares sum to 1 |
| `self_host` | `{output_tokens_per_sec_per_gpu, target_utilization, gpu_hourly_cost}` | GPU count and monthly cost |

Three details are easy to miss:

- **Prices are per million tokens.** Divide by `1e6` once, at the cost step. Example 1 costs $1,483.20; forgetting the divide makes it $1.48 billion.
- **`by_model` token counts are multiplied by the share.** The top-level `monthly_input_tokens` is the whole fleet; each model's entry is its slice.
- **`cost_per_turn` is over the month's turns,** `api / (daily_turns * days_per_month)`, not over one day's.

## 3. Trace Example 2 by hand

The default design: `dau = 20000`, `sessions_per_user = 1.5`, $T = 4$, $S = 800$, $U = 60$, $O = 240$, `cache_hit_rate = 0.7`, `peak_to_avg = 3`, 30 days. Two models, small (share 0.8) and large (share 0.2), and an H100 profile at 1,500 tok/s, 60% utilization, $2.50/hour.

**Per session.** Turn $k$ resends $k - 1$ earlier exchanges of $U + O = 300$ tokens. Summed over $k = 1..4$ that is $0 + 1 + 2 + 3 = 6$ exchanges:

| quantity | formula | value |
|---|---|---|
| history | $(U + O)\,T(T-1)/2 = 300 \times 6$ | 1,800 |
| input | $T(S + U) + \text{history} = 3{,}440 + 1{,}800$ | 5,240 |
| prefix | $T \cdot S + \text{history} = 3{,}200 + 1{,}800$ | 5,000 |
| cached | $0.7 \times 5{,}000$ | 3,500 |
| uncached | $5{,}240 - 3{,}500$ | 1,740 |
| output | $T \cdot O = 4 \times 240$ | 960 |

**Traffic.** `daily_sessions = 30,000`, so `daily_turns = 120,000`, `avg_qps = 120,000 / 86,400 = 1.38889` and `peak_qps = 4.16667`. A month is 900,000 sessions, so `monthly_input_tokens = 4.716e9`, `monthly_cached_tokens = 3.15e9` and `monthly_output_tokens = 8.64e8`.

**API cost, per model.** Per session the small model costs $1{,}740 \times 0.8 + 3{,}500 \times 0.08 + 960 \times 4.0 = 5{,}512$ token-dollars per million, and the large one $1{,}740 \times 3 + 3{,}500 \times 0.3 + 960 \times 15 = 20{,}670$.

| model | share × sessions | cost |
|---|---|---|
| small | 0.8 × 900,000 = 720,000 | 720,000 × 5,512 / 1e6 = **$3,968.64** |
| large | 0.2 × 900,000 = 180,000 | 180,000 × 20,670 / 1e6 = **$3,720.60** |

`api_monthly_cost = $7,689.24`. Notice that the large model serves 20% of the traffic but costs almost as much as the small one.

**Self-host.** `peak_output_tps = 4.16667 × 240 = 1,000` (the judge's float is `999.9999999999999`). One GPU carries `1,500 × 0.6 = 900` tok/s, so you need `ceil(1.111) = 2` GPUs, which cost `2 × 2.5 × 24 × 30 = $3,600`. Since $7,689.24 > $3,600, the `recommendation` is `"self_host"`.

**Example 1** is the degenerate version: one turn, no cache, one model. 860 input and 240 output tokens per session, $1,483.20 a month, a 250 tok/s peak, one GPU at $1,800. The API wins. **Example 3** scales to 2M DAU with 6 turns: the peak is 833.3 QPS and 200,000 output tok/s, so `200,000 / 900 = 222.2` rounds up to **223** GPUs, $401,400 against an API bill of $1,636,948.80.

## 4. Key idea: history grows quadratically

Chat APIs are stateless. Every turn resends the whole conversation, so turn $k$ costs more than turn $k - 1$. Summing $k - 1$ for $k = 1..T$ gives the triangular number $T(T-1)/2$, multiplied by the size of one exchange, $U + O$.

At 4 turns the history is 1,800 of 5,240 input tokens. In "long sessions, three models" ($T = 25$, $U = 120$, $O = 400$) it is 156,000 of 221,500, about 70%. Drop the history term (`wrong_ignores_history_growth.py`) and that case's API bill comes out at $655,758 instead of $1,034,426. Long chats are where this mistake costs the most.

## 5. Key idea: only the prefix is cacheable

Prefix caching (Anthropic's prompt caching, OpenAI's automatic cached input) can only reuse tokens the provider has seen before in the same position: the system prompt and the earlier turns. The **new user message is never a cache hit**, and output is never discounted. So the hit rate applies to `T*S + history`, not to the whole input.

You can see this in "full cache hit". With `cache_hit_rate = 1.0` and 10 turns, `monthly_cached_tokens` is 1.935e10 out of 1.989e10 input tokens. The 5.4e8 difference is exactly the new user messages: 10 × 60 tokens × 900,000 sessions. Applying the rate to all input (`wrong_caches_whole_input.py`) reports 1.989e10 cached tokens and fails every case that has a nonzero cache rate.

## 6. Key idea: size for the peak, leave headroom, round up

Three separate rules go into the GPU count, and each has its own wrong file:

- **Peak, not average.** Traffic arrives in waves. A fleet sized for the mean falls over every weekday morning. `peak_output_tps` uses `peak_qps`. Using `avg_qps` (`wrong_sized_for_average.py`) gives Example 1 a peak of 83.3 instead of 250.
- **Headroom.** A GPU at 100% utilization queues requests, and time-to-first-token climbs well before raw throughput runs out. Each GPU is counted at `tps × target_utilization`. Without that (`wrong_no_utilization_headroom.py`), Example 3 buys 134 GPUs instead of 223.
- **Round up.** You can't buy 0.2 of a GPU, and missing capacity is an outage. `int()` (`wrong_gpus_rounded_down.py`) buys 222 in Example 3 and 1 in Example 2.

The `- 1e-9` inside the `ceil` is there for float noise. With `dau = 14,400`, `sessions_per_user = 1.1`, $T = 7$, peak 3, $O = 400$ and a 2,200 tok/s GPU at 70%, the peak load is `1540.0000000000002` against a per-GPU capacity of exactly 1,540. Without the epsilon, `ceil` would buy 2 GPUs for a load that fits on 1; that design is the "float noise on an exact fit" case. The `max(1, ...)` matters when there is no decode load at all: with `output_tokens = 0` the ratio is 0, `ceil(0 - 1e-9)` is 0, and without the floor self-hosting would cost $0 and win.

## 7. Plan before you code

```
per session:  history = (U+O) * T*(T-1)/2
              input = T*(S+U) + history;  prefix = T*S + history
              cached = rate * prefix;  uncached = input - cached;  output = T*O
traffic:      daily_sessions, daily_turns, avg_qps = daily_turns/86400, peak_qps
              monthly_sessions = daily_sessions * days
api:          for each model: cost = share * monthly_sessions * (uncached*p_in + cached*p_cached + output*p_out) / 1e6
self-host:    peak_output_tps = peak_qps * O
              gpus = max(1, ceil(peak_output_tps / (tps * util) - 1e-9))
              self_cost = gpus * hourly * 24 * days
recommend:    "api" if api <= self_cost else "self_host"
```

| output field | built from |
|---|---|
| `monthly_*_tokens` | per-session value × `monthly_sessions` |
| `by_model[name]` | the same, × `share`, plus that model's cost |
| `cost_per_dau` | `api / dau` |
| `cost_per_turn` | `api / (daily_turns * days)` |

## 8. Build it one piece at a time

**Step 1: one session.** Compute the history once and reuse it in both the input and the prefix, so the two can't drift apart.

```python
T = design["turns_per_session"]
S, U, O = design["system_tokens"], design["user_tokens"], design["output_tokens"]
history = (U + O) * T * (T - 1) / 2
input_s = T * (S + U) + history
cached_s = design["cache_hit_rate"] * (T * S + history)
uncached_s = input_s - cached_s
output_s = T * O
```

`T * (T - 1)` is always even, so `/ 2` gives a whole number. Using `/` rather than `//` keeps everything a float, which the output fields expect.

**Step 2: traffic.**

```python
days = design["days_per_month"]
daily_sessions = design["dau"] * design["sessions_per_user"]
daily_turns = daily_sessions * T
avg_qps = daily_turns / 86400
peak_qps = avg_qps * design["peak_to_avg"]
monthly_sessions = daily_sessions * days
```

**Step 3: API cost per model.** Apply the share once to both the cost and the token counts.

```python
by_model, api = {}, 0.0
for m in design["models"]:
    share = m["share"]
    cost = share * monthly_sessions * (uncached_s * m["input"] + cached_s * m["cached_input"] + output_s * m["output"]) / 1e6
    by_model[m["name"]] = {"monthly_cost": cost,
                           "monthly_input_tokens": share * monthly_sessions * input_s,
                           "monthly_output_tokens": share * monthly_sessions * output_s}
    api += cost
```

Uncached input pays the full input price and cached input the discounted one. They are disjoint, so together they cover the input exactly once.

**Step 4: GPUs and the verdict.**

```python
sh = design["self_host"]
peak_output_tps = peak_qps * O
gpus = max(1, math.ceil(peak_output_tps / (sh["output_tokens_per_sec_per_gpu"] * sh["target_utilization"]) - 1e-9))
self_cost = gpus * sh["gpu_hourly_cost"] * 24 * days
```

Only decode (output) throughput is modelled. `peak_qps * O` is output tokens per second at the peak, the number a GPU's `output_tokens_per_sec_per_gpu` is quoted in.

## 9. Full solution

```python
# math.ceil rounds the GPU count up
import math


# turn a design dict into the API vs self-host cost breakdown
def estimate(design):
    T = design["turns_per_session"]  # turns per session
    S, U, O = design["system_tokens"], design["user_tokens"], design["output_tokens"]  # per-message sizes
    history = (U + O) * T * (T - 1) / 2  # earlier exchanges resent across the session (triangular sum)
    input_s = T * (S + U) + history  # every turn sends the system prompt and its user message, plus history
    cached_s = design["cache_hit_rate"] * (T * S + history)  # only the prefix can come from cache
    uncached_s = input_s - cached_s  # the rest pays the full input price
    output_s = T * O  # one reply per turn

    days = design["days_per_month"]  # month length for tokens and GPU hours
    daily_sessions = design["dau"] * design["sessions_per_user"]  # sessions started per day
    daily_turns = daily_sessions * T  # model calls per day
    avg_qps = daily_turns / 86400  # spread over the seconds in a day
    peak_qps = avg_qps * design["peak_to_avg"]  # the rate capacity must survive
    monthly_sessions = daily_sessions * days  # sessions per month, for the bill

    by_model, api = {}, 0.0  # per-model breakdown and the running API total
    for m in design["models"]:  # each model serves its share of all traffic
        share = m["share"]  # this model's fraction of sessions
        # prices are per million tokens: uncached, cached and output each at their own rate
        cost = share * monthly_sessions * (uncached_s * m["input"] + cached_s * m["cached_input"] + output_s * m["output"]) / 1e6
        by_model[m["name"]] = {  # the breakdown the judge reads for this model
            "monthly_cost": cost,  # this model's slice of the bill
            "monthly_input_tokens": share * monthly_sessions * input_s,  # its slice of input tokens
            "monthly_output_tokens": share * monthly_sessions * output_s,  # its slice of output tokens
        }
        api += cost  # add to the fleet total

    sh = design["self_host"]  # the GPU profile
    peak_output_tps = peak_qps * O  # decode load at the peak, in output tokens per second
    # GPUs at target utilization, rounded up; the epsilon ignores float noise on an exact fit; never zero
    gpus = max(1, math.ceil(peak_output_tps / (sh["output_tokens_per_sec_per_gpu"] * sh["target_utilization"]) - 1e-9))
    self_cost = gpus * sh["gpu_hourly_cost"] * 24 * days  # GPUs run around the clock all month

    return {  # every field the judge compares
        "daily_turns": float(daily_turns),  # model calls per day
        "avg_qps": avg_qps,  # average request rate
        "peak_qps": peak_qps,  # peak request rate
        "peak_output_tps": peak_output_tps,  # peak decode load
        "monthly_input_tokens": float(monthly_sessions * input_s),  # fleet-wide input tokens
        "monthly_cached_tokens": float(monthly_sessions * cached_s),  # of which read from cache
        "monthly_output_tokens": float(monthly_sessions * output_s),  # fleet-wide output tokens
        "by_model": by_model,  # the per-model split
        "api_monthly_cost": api,  # total hosted-API bill
        "cost_per_dau": api / design["dau"],  # what each active user costs per month
        "cost_per_turn": api / (daily_turns * days),  # what each model call costs, over the month's turns
        "self_host_gpus": int(gpus),  # whole GPUs to buy
        "self_host_monthly_cost": float(self_cost),  # their monthly cost
        "recommendation": "api" if api <= self_cost else "self_host",  # cheaper option; a tie stays on the API
    }
```

## 10. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | $1,483.20 API vs $1,800 for 1 GPU: `"api"` | the basic chain with no history and no cache |
| Example 2 | $7,689.24 API vs 2 GPUs at $3,600: `"self_host"` | history, the prefix-only cache and two models |
| Example 3 | 223 GPUs, $401,400 vs $1,636,948.80 | peak sizing with headroom, rounded up |
| exact GPU boundary | 750 tok/s on 750 tok/s of capacity: 1 GPU | an exact fit doesn't buy an extra GPU |
| just over the boundary | 750.0087 tok/s: 2 GPUs | anything over capacity rounds up |
| float noise on an exact fit | `peak_output_tps` 1540.0000000000002 on 1,540 of capacity: 1 GPU | the `- 1e-9` absorbs float error |
| no decode load still needs one GPU | `output_tokens` 0, peak 0 tok/s: 1 GPU, $1,737.84 API vs $1,800: `"api"` | the `max(1, ...)` floor |
| API and self-host tie | $1,800.00 API vs $1,800 for 1 GPU: `"api"` | a tie stays on the API (`<=`) |
| full cache hit | 1.935e10 of 1.989e10 input tokens cached | the new user message is never cached, even at a 100% hit rate |
| long sessions, three models | $1,034,426.20 API, 48 GPUs, 31-day month | long-session history dominates; three model shares |
| tiny pilot | $7.44 API vs 1 GPU at $1,800: `"api"` | small traffic still needs one whole GPU |
| high peak factor | 22,222 tok/s peak, 17 GPUs at 90% utilization | a large `peak_to_avg` and a different utilization |
| fractional GPU need | 3,125 tok/s needs 3.47 GPUs: 4 | rounding a clearly fractional need up |

## 11. Complexity

O(M) time for M models, and O(M) memory for the breakdown. Everything else is a fixed number of arithmetic operations.

The interesting scale question is the formulas, not the code. Input grows as $O(T^2)$ per session because of history, while output grows as $O(T)$. That's why long agent sessions are input-dominated, why prompt caching matters so much, and why products cap or summarize history (problem 107, memory-under-token-budget). On the self-host side, cost moves in whole-GPU steps: going from 750 to 750.0087 tok/s in the boundary cases doubles the GPU bill from $1,800 to $3,600.

## 12. If you got Wrong Answer

The judge reports the first field that differs, so the field name points at the bug:

- **`monthly_input_tokens` is too low** (Example 2: 3.096e9 instead of 4.716e9). You left out the history term: `wrong_ignores_history_growth.py`.
- **`monthly_cached_tokens` is too high** (Example 2: 3.3012e9 instead of 3.15e9). You applied the hit rate to the whole input: `wrong_caches_whole_input.py`.
- **`monthly_cached_tokens` is too low** (Example 2: 2.016e9). You cached only the system prompts and forgot the history is part of the prefix.
- **`peak_output_tps` is a third of the expected value** (Example 1: 83.3 instead of 250). You sized for `avg_qps`: `wrong_sized_for_average.py`.
- **`self_host_gpus` is one short** (Example 3: 222 instead of 223). You rounded down with `int()`: `wrong_gpus_rounded_down.py`.
- **`self_host_gpus` is far too low** (Example 3: 134). You ignored `target_utilization`: `wrong_no_utilization_headroom.py`.
- **`self_host_gpus` is 2 instead of 1 in "float noise on an exact fit".** You dropped the `- 1e-9`: `wrong_gpus_no_epsilon.py`.
- **`self_host_gpus` is 0 in "no decode load still needs one GPU".** You dropped the `max(1, ...)`: `wrong_gpus_no_minimum.py`.
- **`recommendation` is `"self_host"` in "API and self-host tie".** You compared with `<`; a tie stays on the API: `wrong_tie_goes_self_host.py`.
- **`by_model[...]["monthly_input_tokens"]` equals the fleet total.** You didn't multiply the model's tokens by its share.
- **`cost_per_turn` is 30 times too big** (Example 1: 0.04944 instead of 0.001648). You divided by one day's turns, not the month's.

## 13. Follow-ups an interviewer might ask

- *What does this leave out on the self-host side?* Prefill throughput, KV-cache memory per concurrent session (problem 130, gpu-capacity-planner), replicas across zones, idle capacity overnight and the engineers on call. Together they often add 30–100% to the GPU line.
- *How would you model cache writes?* Anthropic charges a premium to write a prefix into the cache (1.25× for the 5-minute TTL) and about 0.1× to read it. The first turn of each session writes and the later turns read, so split the prefix into write and read tokens (problem 128, prompt-caching-cost).
- *Where do the real inputs come from after launch?* From gateway logs: measured tokens per turn, turns per session and the p99 of one-minute QPS over a week, attributed per tenant (problem 131, tenant-cost-attribution). Then redo the estimate.
- *Is the answer ever just one or the other?* Usually it's hybrid: the API for spiky and long-tail traffic, self-hosted small models for the high-volume, latency-tolerant paths, with a router deciding per request (problem 126, model-router).
- *How would you cut the API bill without moving?* Route easy turns to the small model, raise the cache hit rate by keeping the system prompt byte-stable, and trim history.
