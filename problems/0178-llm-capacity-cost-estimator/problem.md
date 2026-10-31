A customer asks your forward-deployed team whether their support assistant should stay on a hosted API or move to self-hosted GPUs. Turn their design numbers into the breakdown the decision needs.

`estimate(design)` takes a dict and returns a dict. All token prices are in dollars per **million** tokens.

```python
design = {
    "dau": 20000, "sessions_per_user": 1.5, "turns_per_session": 4,
    "system_tokens": 800, "user_tokens": 60, "output_tokens": 240,
    "cache_hit_rate": 0.7, "peak_to_avg": 3.0, "days_per_month": 30,
    "models": [{"name": "small", "share": 0.8, "input": 0.8, "cached_input": 0.08, "output": 4.0}, ...],
    "self_host": {"output_tokens_per_sec_per_gpu": 1500.0, "target_utilization": 0.6, "gpu_hourly_cost": 2.5},
}
```

**Per session.** Write $T$ = `turns_per_session`, $S$ = `system_tokens`, $U$ = `user_tokens`, $O$ = `output_tokens`. Turn $k$ sends the system prompt, the $k-1$ earlier user and assistant messages, and the new user message, so:

$$
\text{input} = T(S + U) + (U + O)\,\frac{T(T-1)}{2}, \qquad
\text{prefix} = T\,S + (U + O)\,\frac{T(T-1)}{2}, \qquad
\text{output} = T\,O
$$

Only the prefix is cacheable: $\text{cached} = \text{cache\_hit\_rate} \times \text{prefix}$, and $\text{uncached} = \text{input} - \text{cached}$.

**Traffic.** `daily_sessions = dau * sessions_per_user`, `daily_turns = daily_sessions * T`, `avg_qps = daily_turns / 86400`, `peak_qps = avg_qps * peak_to_avg`. Monthly token totals are the per-session numbers times `daily_sessions * days_per_month`.

**API cost.** Each model serves its `share` of all traffic (the shares sum to 1). For a model,

$$
\text{cost} = \frac{\text{share}\,(\text{uncached}_m \cdot p_\text{input} + \text{cached}_m \cdot p_\text{cached} + \text{output}_m \cdot p_\text{output})}{10^6}
$$

using the monthly totals. `api_monthly_cost` is the sum over models.

**Self-hosting.** It must carry the peak decode load: `peak_output_tps = peak_qps * O`. Then `gpus = max(1, ceil(peak_output_tps / (output_tokens_per_sec_per_gpu * target_utilization) - 1e-9))`, and `self_host_monthly_cost = gpus * gpu_hourly_cost * 24 * days_per_month`.

**Return** this dict (no rounding; floats are compared with a tolerance):

| key | value |
|---|---|
| `daily_turns`, `avg_qps`, `peak_qps`, `peak_output_tps` | floats |
| `monthly_input_tokens`, `monthly_cached_tokens`, `monthly_output_tokens` | floats |
| `by_model` | `{name: {"monthly_cost": float, "monthly_input_tokens": float, "monthly_output_tokens": float}}`, with tokens multiplied by the share |
| `api_monthly_cost`, `cost_per_dau` (`api_monthly_cost / dau`), `cost_per_turn` (API cost over the month's turns) | floats |
| `self_host_gpus` | int |
| `self_host_monthly_cost` | float |
| `recommendation` | `"api"` if `api_monthly_cost <= self_host_monthly_cost`, else `"self_host"` |

**Constraints**

- `1 <= dau <= 10**8`, `1 <= turns_per_session <= 50`, `0 <= cache_hit_rate <= 1`.
- `peak_to_avg >= 1`, `0 < target_utilization <= 1`.
- 1 to 5 models with unique names.
