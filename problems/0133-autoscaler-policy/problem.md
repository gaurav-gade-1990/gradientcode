Your vLLM fleet scales on in-flight requests. Last week it flapped between 3 and 9 replicas every few minutes, and each GPU pod takes two minutes to load weights. Write the scaling policy, modelled on the Kubernetes HPA algorithm with its stabilization windows, plus per-direction cooldowns and a cap on the scale-up step.

`autoscale(samples, config)` takes

- `samples`: `[{"t", "load"}]`, metric samples in increasing `t` (seconds). `load` is an integer: in-flight requests across the fleet.
- `config`: `{"initial_replicas", "min_replicas", "max_replicas", "capacity_per_replica", "target_pct", "tolerance_pct", "scale_up_window_s", "scale_down_window_s", "scale_up_cooldown_s", "scale_down_cooldown_s", "max_scale_up_step"}`. All values are integers.

Start with `R = initial_replicas` and `last_up = last_down = -infinity`. For each sample, in order:

1. **Raw recommendation**, in integer arithmetic so that there's no rounding ambiguity. Let `C = capacity_per_replica * target_pct`.
   - If `abs(load * 100 - R * C) * 100 <= tolerance_pct * R * C`, the fleet is within tolerance of its target, and `raw = R`.
   - Otherwise `raw = ceil(load * 100 / C)`.
   - Clamp `raw` to `[min_replicas, max_replicas]` and append `(t, raw)` to the recommendation history.
2. **Stabilize.** `up_rec` is the **minimum** `raw` over history entries with `t' >= t - scale_up_window_s`. `down_rec` is the **maximum** `raw` over entries with `t' >= t - scale_down_window_s`.
3. **Decide.**

| condition | if the cooldown allows | otherwise |
|---|---|---|
| `up_rec > R` | `t - last_up >= scale_up_cooldown_s`: set `R = min(up_rec, R + max_scale_up_step)`, `last_up = t`, event `"scale_up"` | event `"blocked_up"`, no change |
| else `down_rec < R` | `t - last_down >= scale_down_cooldown_s`: set `R = down_rec`, `last_down = t`, event `"scale_down"` | event `"blocked_down"`, no change |
| otherwise | nothing | |

An event is `{"t", "action", "from", "to"}`. `from` is `R` before the decision. `to` is the new `R`, or for a blocked event, the value it would have moved to.

4. **Record.** The sample is **overloaded** if `load > R_before * capacity_per_replica`, where `R_before` is the replica count when the sample arrived.

Return

```
{"replicas": [R after each sample],
 "events": [event, ...],
 "replica_seconds": sum over i of replicas[i] * (t[i+1] - t[i])   (the last sample adds nothing),
 "overloaded_samples": int}
```

**Constraints**

- `1 <= min_replicas <= initial_replicas <= max_replicas`
- `load >= 0`; `1 <= target_pct <= 100`; `0 <= tolerance_pct < 100`
- At most 2,000 samples
