## 1. What the problem is really asking

Strip the Kubernetes wording and this is a **state machine driven by a sliding window**. The state is the replica count `R` plus two timestamps, `last_up` and `last_down`. Each sample turns into one number, the *raw* recommendation. The decision doesn't use that raw number directly. It uses the **minimum** of recent raws to go up and the **maximum** of recent raws to go down. Then a cooldown per direction and a cap on the step decide whether the move happens now.

Every rule is there to stop the fleet from flapping:

- the **tolerance band** ignores small differences from the target,
- the **windows** require a need to persist before acting on it,
- the **cooldowns** space out moves in the same direction,
- the **step cap** limits how many cold GPU pods you ask for at once.

The judge compares your whole return dict: `R` after every sample, the full event list (including `blocked_up` and `blocked_down`, with their would-be `to`), `replica_seconds` and the overload count. A missed blocked event is a Wrong Answer even when the replica counts are right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `samples` | `[{"t", "load"}]`, increasing `t`, integer `load` | one decision per sample |
| `capacity_per_replica`, `target_pct` | how many in-flight requests one replica should carry | `C = capacity * target_pct`, the target scaled by 100 |
| `tolerance_pct` | dead band around the target | within it, `raw = R` |
| `min_replicas`, `max_replicas` | bounds | clamp `raw` before it enters the history |
| `scale_up_window_s`, `scale_down_window_s` | how far back each window looks | `up_rec = min`, `down_rec = max` over entries with `t' >= t - window` |
| `scale_up_cooldown_s`, `scale_down_cooldown_s` | minimum gap between moves in each direction | compare with `last_up` or `last_down` only |
| `max_scale_up_step` | largest single increase | `min(up_rec, R + step)` |

Details that are easy to miss:

- **Stay in integers.** `C` is `capacity * target_pct`, so `load * 100 / C` is the same ratio as `load / (capacity * target_pct / 100)` without the float. With floats the two can disagree: for capacity 16, target 57% and load 228, `228 / (16 * 0.57)` is `25.000000000000004`, so `math.ceil` gives 26, while `-(-(228 * 100) // (16 * 57))` gives 25.
- **Both windows include the current sample.** With `scale_up_window_s = 0`, `up_rec` is just this sample's raw.
- **Overload uses `R_before`**, the count when the sample arrived, not after the decision.
- **A blocked event still records `to`**, and for a blocked scale-up that `to` is already capped by the step.
- **The window edge is inclusive.** `t' >= t - window`, so an entry exactly `window` seconds old still counts.

## 3. Trace Example 1 by hand

`CFG`: capacity 16, target 75%, so one replica targets 12 in flight and `C = 1200`. Tolerance 10%, up window 0, down window 120, up cooldown 30 s, step cap 4. Start at `R = 2`. Samples every 15 s with loads `[24, 25, 60, 120, 120, 120, 120]`.

The tolerance test is `abs(load*100 - R*C) * 100 <= tolerance_pct * R * C`.

| t | load | R before | tolerance test | raw | up_rec | decision | R after |
|---|---|---|---|---|---|---|---|
| 0 | 24 | 2 | 0 ≤ 24000, within | 2 | 2 | none | 2 |
| 15 | 25 | 2 | 10000 ≤ 24000, within | 2 | 2 | none | 2 |
| 30 | 60 | 2 | 360000 > 24000 | ceil(6000/1200) = 5 | 5 | **scale_up** 2 → 5 | 5 |
| 45 | 120 | 5 | 600000 > 60000 | 10 | 10 | 45 − 30 = 15 < 30: **blocked_up** 5 → 9 | 5 |
| 60 | 120 | 5 | out | 10 | 10 | cooldown ok, capped: **scale_up** 5 → 9 | 9 |
| 75 | 120 | 9 | 120000 > 108000 | 10 | 10 | 15 < 30: **blocked_up** 9 → 10 | 9 |
| 90 | 120 | 9 | out | 10 | 10 | **scale_up** 9 → 10 | 10 |

Expected output: `replicas [2, 2, 5, 5, 9, 9, 10]`, five events, `replica_seconds` 480 (`(2+2+5+5+9+9) * 15`; the last sample adds nothing) and `overloaded_samples` 3. The overloaded samples are t=30 (60 > 2·16), t=45 and t=60 (120 > 5·16). At t=75, `R_before` is 9 and 120 ≤ 144.

Notice the blocked event at t=45: its `to` is 9, not 10. The step cap is applied before the cooldown check.

**Example 2: why the down window takes the max.** `R = 8`, samples every 30 s. Load 96 sits exactly on target (8 × 12), then drops to 30 from t=60, which needs `ceil(3000/1200) = 3`. But `down_rec` is the max raw over the last 120 s:

| t | raws in the window (t' ≥ t − 120) | down_rec | R after |
|---|---|---|---|
| 60 | 8, 8, 3 | 8 | 8 |
| 150 | 8 (t=30), 3, 3, 3, 3 | 8 | 8 |
| 180 | 3 (t=60 to 180) | 3 | **3** |

At t=150 the window starts at t=30, and that entry's 8 is still in (the edge is inclusive). At t=180 the window starts at t=60, the last 8 falls out, and the fleet drops straight to 3 in one move.

## 4. Key idea: up takes the minimum, down takes the maximum

This asymmetry is what keeps the fleet stable. To scale **up** to `k`, every raw in the up window must be at least `k`: the need has to persist for the whole window. To scale **down** to `k`, every raw in the down window must be at most `k`: every recent sample has to agree that fewer replicas are enough.

Example 3 shows what that buys. Load alternates 12 and 40 every 30 s, which means raws of 1 and 4. The up window is 0, so the first 40 scales to 4 immediately. After that, every low sample has a 4 within the last 120 s, so `down_rec` stays 4 and the fleet holds at 4: `replicas [1, 4, 4, 4, 4, 4, 4, 4, 4, 4]`. If you scale down on the current raw instead, it flaps `1, 4, 1, 4, ...` with nine events.

Production picks a short or zero up window and a long down window for the same reason. A late scale-up costs latency for a minute. An early scale-down costs a two-minute cold start, a cold KV cache, and probably a scale-up right after.

## 5. Key idea: cooldowns are per direction

`last_up` and `last_down` are separate clocks. In "cooldowns are per direction" (samples every 40 s, up cooldown 200 s, down cooldown 100 s, down window 0), the fleet scales down 8 → 2 at t=40, then a spike at t=200 asks for 9 raw, capped to 6. The up clock has never fired, so the scale-up goes through. At t=240 the spike is gone, and the down clock last fired at t=40, 200 s ago, so the fleet drops back to 2.

With one shared timer, the t=40 scale-down would make the t=200 scale-up wait (200 − 40 = 160 < 200), giving a `blocked_up` event and an overloaded fleet. That is the incident in `wrong_shared_cooldown.py`.

## 6. Plan before you code

```
R = initial; C = capacity * target_pct; last_up = last_down = -inf
for each sample (t, load):
    if load > R * capacity: overloaded += 1          # uses R before the decision
    raw = R if within tolerance else ceil(load*100 / C)
    raw = clamp(raw, min, max); history.append((t, raw))
    up_rec   = min raw with t' >= t - up_window
    down_rec = max raw with t' >= t - down_window
    if up_rec > R:
        target = min(up_rec, R + step)
        up cooldown ok?   scale_up to target        : blocked_up with to = target
    elif down_rec < R:
        down cooldown ok? scale_down to down_rec    : blocked_down with to = down_rec
    replicas.append(R)
replica_seconds = sum replicas[i] * (t[i+1] - t[i])
```

The `elif` matters. If `up_rec > R` you never consider a scale-down in the same sample, even when the up move is blocked.

## 7. Build it one piece at a time

**Step 1: the raw recommendation.** Ceiling division in integers is `-(-a // b)`. Do the tolerance check first, against the *current* `R`.

```python
        if abs(load * 100 - R * C) * 100 <= config["tolerance_pct"] * R * C:
            raw = R
        else:
            raw = -(-(load * 100) // C)
        raw = max(lo, min(hi, raw))
```

The "tolerance boundary" case pins the `<=`. With `R = 10` and target 120, load 132 is exactly 10% over: `120000 <= 120000`, so `raw = 10`. Load 133 is not: raw 12.

**Step 2: the windows.** A plain scan of the history is fine at 2,000 samples. Clamp *before* appending, so the windows only ever see legal counts.

```python
        history.append((t, raw))
        up_rec = min(r for ht, r in history if ht >= t - config["scale_up_window_s"])
        down_rec = max(r for ht, r in history if ht >= t - config["scale_down_window_s"])
```

**Step 3: the decision.** Compute the capped target before the cooldown test, so a blocked event reports the capped value.

```python
        if up_rec > R:
            target = min(up_rec, R + config["max_scale_up_step"])
            if t - last_up >= config["scale_up_cooldown_s"]:
                events.append({"t": t, "action": "scale_up", "from": R, "to": target})
                R, last_up = target, t
            else:
                events.append({"t": t, "action": "blocked_up", "from": R, "to": target})
```

Starting `last_up` at `float("-inf")` makes the first move in each direction always allowed, even at `t = 0`.

**Step 4: the cost.** Each sample's replica count is paid for until the next sample, so the last sample adds nothing. With uneven spacing ("uneven sample spacing" has gaps of 7, 43, 1, 119, 2 and 228 s) you have to use the real gaps.

```python
    replica_seconds = 0
    for i in range(len(samples) - 1):
        replica_seconds += replicas[i] * (samples[i + 1]["t"] - samples[i]["t"])
```

## 8. Full solution

```python
def autoscale(samples, config):                            # replay the scaling policy over a metric trace
    R = config["initial_replicas"]                         # current replica count, the controller's state
    C = config["capacity_per_replica"] * config["target_pct"]   # per-replica target scaled by 100, kept integer
    lo, hi = config["min_replicas"], config["max_replicas"]     # bounds every recommendation is clamped to
    last_up = last_down = float("-inf")                    # separate clocks, so the first move each way is allowed
    history, replicas, events, overloaded = [], [], [], 0  # raw history, outputs, and the overload counter

    for s in samples:                                      # one decision per metric sample, in time order
        t, load = s["t"], s["load"]                        # sample time and fleet-wide in-flight requests
        if load > R * config["capacity_per_replica"]:      # judged against R before this sample's decision
            overloaded += 1                                # the fleet was over raw capacity at this moment
        if abs(load * 100 - R * C) * 100 <= config["tolerance_pct"] * R * C:   # close enough to target
            raw = R                                        # inside the dead band: recommend no change
        else:                                              # outside the band
            raw = -(-(load * 100) // C)                    # integer ceil: enough replicas to meet the target
        raw = max(lo, min(hi, raw))                        # never recommend outside [min, max]
        history.append((t, raw))                           # the windows include the current sample
        # scale up only to what every sample in the up window needed (a sustained need)
        up_rec = min(r for ht, r in history if ht >= t - config["scale_up_window_s"])
        # scale down only to what every sample in the down window allows
        down_rec = max(r for ht, r in history if ht >= t - config["scale_down_window_s"])

        if up_rec > R:                                     # the up window wants more replicas
            target = min(up_rec, R + config["max_scale_up_step"])   # cap the jump; blocked events report this too
            if t - last_up >= config["scale_up_cooldown_s"]:        # only the up clock gates a scale-up
                events.append({"t": t, "action": "scale_up", "from": R, "to": target})   # record the move
                R, last_up = target, t                     # apply it and restart the up cooldown
            else:                                          # too soon after the last scale-up
                events.append({"t": t, "action": "blocked_up", "from": R, "to": target})  # record what was held back
        elif down_rec < R:                                 # no up pressure, and the down window allows fewer
            if t - last_down >= config["scale_down_cooldown_s"]:   # only the down clock gates a scale-down
                events.append({"t": t, "action": "scale_down", "from": R, "to": down_rec})  # record the move
                R, last_down = down_rec, t                 # apply it and restart the down cooldown
            else:                                          # too soon after the last scale-down
                events.append({"t": t, "action": "blocked_down", "from": R, "to": down_rec})  # record the hold
        replicas.append(R)                                 # the count after this sample's decision

    replica_seconds = 0                                    # total cost of the replicas we ran
    for i in range(len(samples) - 1):                      # each count is paid until the next sample
        replica_seconds += replicas[i] * (samples[i + 1]["t"] - samples[i]["t"])   # count times the real gap
    # the last sample adds no cost; every field is graded
    return {"replicas": replicas, "events": events, "replica_seconds": replica_seconds, "overloaded_samples": overloaded}
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `[2, 2, 5, 5, 9, 9, 10]`, two `blocked_up` events | tolerance band, up cooldown, step cap, capped `to` on a blocked event |
| Example 2 | holds at 8 until t=180, then 8 → 3 | the down window takes the max, edge inclusive |
| Example 3 | 1 → 4 at t=30, then holds at 4 | min/max windows stop flapping on oscillating load |
| up stabilization window | 1 → 5 only at t=75 | a 30 s up window: one low sample at t=30 delays the scale-up |
| cooldowns are per direction | down at 40, up at 200, down at 240 | separate `last_up` and `last_down` clocks |
| clamped to min and max | 3 → 2 at t=0, 2 → 10 at t=30 | clamping, including a scale-down at the very first sample |
| tolerance boundary | `[10, 12, 9, 9, 10]` | `<=` at exactly 10%; load 133 is just outside |
| zero tolerance, exact ceil | `[2, 2, 3, 3, 4, 1]` | exact ceiling: 24 needs 2, 25 needs 3 |
| step cap during a flash crowd | 2 → 5 → 8 → 11, `blocked_up` in between | step cap of 3 together with a 60 s cooldown |
| uneven sample spacing | `replica_seconds` 1110 | real gaps between samples, and the inclusive window edge at t=170 |
| diurnal day with a spike | 300 samples | everything together on a realistic trace |

## 10. Complexity

Each sample scans the history for both windows, so the reference is O(N²) for N samples, at most 4 million comparisons for 2,000 samples. Memory is O(N).

A real controller runs forever, so it can't keep the whole history. Drop entries older than the longer window, or keep a **monotonic deque** per window (the classic sliding-window minimum), which makes each sample amortized O(1). Kubernetes stores the recommendations it has made with their timestamps and drops the stale ones, which comes to the same thing.

## 11. If you got Wrong Answer

- **The fleet alternates `1, 4, 1, 4, ...` on Example 3.** You scale down on the current raw instead of the max over the down window.
- **Example 1 scales up at t=15 (2 → 3).** You have no tolerance band. Load 25 against a target of 24 is within 10%.
- **"cooldowns are per direction" ends with `blocked_up` at t=200 and stays at 2.** You use one cooldown timer for both directions.
- **"tolerance boundary" goes 10 → 11 at t=15 instead of 12**, or "zero tolerance, exact ceil" starts at 1. You round to nearest. Load 133 needs 11.08 replicas, and that rounds to 11 but ceils to 12.
- **"step cap during a flash crowd" jumps 2 → 25 in one event.** You never apply `max_scale_up_step`.
- **A `blocked_up` event's `to` is the uncapped `up_rec`.** Compute `min(up_rec, R + step)` before the cooldown check.
- **Off by one replica on some loads, but only with float math.** Use `-(-(load * 100) // C)`, not `math.ceil(load / (cap * pct / 100))`.

## 12. Follow-ups an interviewer might ask

- *What metric should an LLM fleet scale on?* Not GPU utilization, which reads high even with a tiny batch. Use queue depth (waiting requests), KV-cache utilization or a TTFT SLO. Problem 129 (continuous-batching-scheduler) shows where those numbers come from, and problem 132 (load-balancer-p2c) routes on the same signal.
- *How do you handle the two-minute cold start?* Keep warm spares (`min_replicas` above the trough), pre-pull images, stream weights from local NVMe, or scale predictively from yesterday's diurnal curve so the pods are ready before the peak.
- *What sets `max_replicas` and the step cap?* GPU quota and how fast the node layer (cluster autoscaler or Karpenter) can supply GPUs. Size the ceiling with the capacity planner in problem 130 (gpu-capacity-planner).
- *How would you alert when scaling can't keep up?* Count `blocked_up` events and overloaded samples, and alert on the SLO itself with burn rates (problem 139, slo-burn-rate-alerts).
- *How does this map to Kubernetes?* HPA v2's `behavior` block has `stabilizationWindowSeconds` per direction and `policies` (pods or percent per period) for the step cap. The default tolerance is 10% and the default down window is 300 s. KEDA adds scale to zero on external metrics, such as a Prometheus query on vLLM's waiting-request gauge.
