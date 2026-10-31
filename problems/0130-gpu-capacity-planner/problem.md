A customer wants to self-host a 70B open-weights model behind their VPC and asks how many H100s to order for their peak traffic. Write the planner your forward-deployed team runs in the first meeting.

`plan_capacity(model, gpu, workload)` takes

- `model`: `{"params", "layers", "attention_heads", "kv_heads", "head_dim", "weight_bytes_per_param", "kv_bytes_per_elem"}`
- `gpu`: `{"memory_bytes", "memory_utilization_pct", "reserve_bytes", "max_tp"}`. `reserve_bytes` is held back on every GPU for activations, the CUDA graphs and the NCCL buffers.
- `workload`: `{"target_qps", "avg_prompt_tokens", "avg_output_tokens", "max_model_len", "ttft_s", "tpot_s", "max_num_seqs", "block_size", "target_utilization_pct"}`

**Model-level numbers** (integers):

- `weight_bytes = params * weight_bytes_per_param`
- `kv_bytes_per_token = 2 * layers * kv_heads * head_dim * kv_bytes_per_elem` (the 2 is K and V)

**One replica at tensor-parallel degree `tp`.** Consider `tp` in `1, 2, 4, 8` with `tp <= max_tp` and `kv_heads % tp == 0`. One replica spans `tp` GPUs:

| quantity | formula |
|---|---|
| `usable` (per GPU) | `memory_bytes * memory_utilization_pct // 100 - reserve_bytes` |
| `kv_budget_bytes` | `tp * usable - weight_bytes` |
| `num_blocks` | `kv_budget_bytes // (kv_bytes_per_token * block_size)`, or `0` if the budget is negative |
| feasible | `num_blocks >= ceil(max_model_len / block_size)`: one full-length sequence must fit |
| `blocks_per_seq` | `ceil((avg_prompt_tokens + avg_output_tokens) / block_size)` |
| `max_concurrent_seqs` | `min(max_num_seqs, num_blocks // blocks_per_seq)` |
| `request_latency_s` | `ttft_s + (avg_output_tokens - 1) * tpot_s` |
| `replica_qps` | `max_concurrent_seqs / request_latency_s` (Little's law) |
| `replicas` | `max(1, ceil(target_qps / (replica_qps * target_utilization_pct / 100) - 1e-9))` |
| `gpus` | `replicas * tp` |

`replicas` is `None` when `max_concurrent_seqs == 0`, and that option is skipped when choosing.

**Choose** the feasible option with the fewest `gpus`, breaking ties by the smaller `tp`. Assume `ttft_s` and `tpot_s` were measured and don't change with `tp`.

Return

```
{"weight_bytes", "kv_bytes_per_token",
 "options": [{"tp", "kv_budget_bytes", "num_blocks", "max_concurrent_seqs", "replica_qps", "replicas", "gpus"}, ...],
 "chosen": {same fields} or None}
```

`options` lists only the feasible `tp` values, in increasing order. When `replicas` is `None`, `replica_qps` is `0.0` and `gpus` is `None`. `chosen` is `None` if no option has a `replicas` value.

**Constraints**

- All sizes are integers in bytes; `memory_utilization_pct` and `target_utilization_pct` are integers in `[1, 100]`
- `avg_output_tokens >= 1`, `request_latency_s > 0`
