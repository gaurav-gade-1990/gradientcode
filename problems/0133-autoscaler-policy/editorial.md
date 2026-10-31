## Approach

The HPA's core formula is `desired = ceil(current * metric / target)`. With a fleet-wide load and a per-replica target that becomes `ceil(load / (capacity * target))`. Around it sit three guards against flapping and one against overshoot.

```python
raw = R if within_tolerance else ceil(load * 100 / (cap * pct))
raw = clamp(raw, min, max); history.append((t, raw))
up_rec   = min(raw over the up window)      # only scale up if the need is sustained
down_rec = max(raw over the down window)    # only scale down if every recent sample agrees
if up_rec > R and cooldown_up_ok:     R = min(up_rec, R + max_step)
elif down_rec < R and cooldown_down_ok: R = down_rec
```

**The asymmetry is the point.** Scaling up too late costs latency, while scaling down too early costs a cold start, and for LLM serving that means minutes of weight loading plus a cold KV and prefix cache. So scale-ups react to the current sample (a short or zero up window) and scale-downs wait for the max over a long window. The Kubernetes default is a 300 s down window and 0 s up.

**Integers on purpose.** `ceil(60 / 12.0)` is safe, but `ceil(load / (16 * 0.75))` with other numbers can land a hair above an integer and add a replica. Doing the comparison as `load * 100` against `R * cap * pct` removes the ambiguity, and real controllers face the same problem.

## Common mistakes

- **No down stabilization.** Bursty traffic flaps the fleet.
- **One shared cooldown.** A scale-down blocks the next scale-up exactly when a spike arrives.
- **No tolerance band.** Load near the target causes ±1 churn forever.
- **Rounding instead of ceiling.** The fleet runs above target all the time.
- **No step cap.** A flash crowd asks for more nodes than the cloud quota or the cluster autoscaler can deliver.

## Production notes

- Kubernetes HPA v2 `behavior` has exactly these knobs: `stabilizationWindowSeconds` per direction and `policies` (pods or percent per period) for step limits. The default tolerance is 10%. KEDA adds scale-to-zero and external metrics (a Prometheus query on vLLM's `vllm:num_requests_running` and `vllm:num_requests_waiting`).
- For LLM servers, GPU utilization is a poor signal because it reads high even when the batch is tiny. Scale on queue depth, KV-cache utilization, or a TTFT SLO. Load balancers that route on the same signals (problem 132) make the scaling smoother.
- Cold start dominates. Keep warm spares (`min_replicas` above the trough), pre-pull images, stream weights from local NVMe or with fast loaders (Run:ai Model Streamer, safetensors on a shared filesystem), and consider predictive scaling from the diurnal curve.
- Scaling pods is half the story: the cluster autoscaler (or Karpenter) has to find GPU nodes. The step cap keeps requests within what the node layer can supply. Size the ceiling with the capacity planner (problem 130).
