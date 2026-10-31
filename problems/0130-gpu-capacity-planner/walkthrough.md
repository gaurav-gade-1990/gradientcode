## 1. What the problem is really asking

Strip away the sales meeting and this is a **small enumeration with a formula per option**:

> for each allowed tensor-parallel degree, work out how much KV memory is left after the weights, turn that into concurrent sequences, turn that into throughput with Little's law, and count the GPUs needed for the target load → pick the option with the fewest GPUs.

There are at most four options (`tp` = 1, 2, 4, 8). Every formula is given in `problem.md`. What makes the problem worth doing is that the cheapest answer is **not** at either end. The smallest `tp` that holds the weights has almost no memory left for KV, so each replica serves very few users. The largest `tp` has plenty of KV, but the scheduler cap `max_num_seqs` stops it from using it. The winner is usually in the middle, and the only way to find it is to evaluate every option.

The judge compares the whole dict: `weight_bytes`, `kv_bytes_per_token`, the full `options` list (only feasible `tp` values, in order) and `chosen`. So an intermediate value that is off by one block shows up even when the final pick is right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `model["params"]`, `weight_bytes_per_param` | model size and precision | `weight_bytes = params * bytes` |
| `layers`, `kv_heads`, `head_dim`, `kv_bytes_per_elem` | the shape of the KV cache | `2 * layers * kv_heads * head_dim * bytes` per token |
| `attention_heads` | query heads | **not used** for KV; a distractor that matters for GQA models |
| `gpu["memory_bytes"]`, `memory_utilization_pct`, `reserve_bytes` | per-GPU memory and what's held back | `usable = mem * pct // 100 - reserve` |
| `gpu["max_tp"]` | the largest TP degree the box supports | skip larger `tp` |
| `max_model_len`, `block_size` | feasibility: one full-length sequence must fit | `num_blocks >= ceil(max_model_len / block_size)` |
| `avg_prompt_tokens + avg_output_tokens` | the size of a typical sequence | `blocks_per_seq` |
| `ttft_s`, `tpot_s` | measured latencies | `request_latency_s = ttft + (out - 1) * tpot` |
| `max_num_seqs` | the scheduler's batch cap | caps concurrency |
| `target_qps`, `target_utilization_pct` | the load and the headroom | how many replicas |

Three details are easy to miss:

- **Use `kv_heads`, not `attention_heads`.** Llama-3-70B has 64 query heads but only 8 KV heads (grouped-query attention). The KV cache stores only the 8, so using 64 overstates KV memory 8×.
- **`kv_heads % tp == 0`.** Tensor parallelism splits KV heads across GPUs, so the head count must divide evenly. A model with 4 KV heads can't run at `tp` 8.
- **Integer math for memory, float math for throughput.** `usable`, `kv_budget_bytes` and `num_blocks` are integers, using `//`. A negative budget means the weights don't fit, and `num_blocks` is then 0 (not a negative number from floor division).

## 3. Trace Example 1 by hand

Llama-3-70B in fp16 on H100s (80 GiB), 50 QPS target, 70% utilization.

**Model numbers.**

- `weight_bytes = 70,553,706,496 * 2 = 141,107,412,992` (about 141 GB).
- `kv_bytes_per_token = 2 * 80 * 8 * 128 * 2 = 327,680` bytes (320 KiB).

**Per-GPU and workload numbers.**

- `usable = 85,899,345,920 * 90 // 100 - 4,294,967,296 = 73,014,444,032` (about 73 GB per GPU).
- One full-length sequence needs `ceil(8192 / 16) = 512` blocks.
- A typical sequence (2,000 + 500 tokens) needs `blocks_per_seq = ceil(2500 / 16) = 157` blocks.
- `request_latency_s = 0.4 + 499 * 0.03 = 15.37` seconds.

**Each option.** A block is `327,680 * 16` bytes.

| tp | kv_budget_bytes | num_blocks | feasible (≥ 512)? | conc = min(256, blocks // 157) | replica_qps = conc / 15.37 | replicas | gpus |
|---|---|---|---|---|---|---|---|
| 1 | −68,092,968,960 | 0 | no, weights don't fit | | | | |
| 2 | 4,921,475,072 | 938 | yes | 5 | 0.325309 | ceil(50 / (0.325309·0.7)) = ceil(219.57) = 220 | 440 |
| 4 | 150,950,363,136 | 28,791 | yes | 183 | 11.9063 | ceil(5.9992) = 6 | **24** |
| 8 | 443,008,139,264 | 84,497 | yes | 256 (capped; memory alone allows 538) | 16.6558 | ceil(4.2885) = 5 | 40 |

`options` holds `tp` 2, 4 and 8. `tp` 1 is left out because it isn't feasible. The chosen option is **`tp` 4 with 24 GPUs**.

Look at what each end got wrong. `tp` 2 "fits", but after 141 GB of weights it has 4.9 GB of KV, which is room for 5 conversations, so it needs 220 replicas. `tp` 8 has enough KV for 538 sequences, but the scheduler runs at most 256 at once, so half of each 8-GPU box is wasted.

### A trickier case: "feasible but zero concurrency"

Same model, but `max_model_len` is 15,000 and the average request is 14,200 + 900 = 15,100 tokens, slightly longer than the cap (the averages describe the traffic, not one request the server must accept). Feasibility needs `ceil(15000/16) = 938` blocks, so `tp` 2 (exactly 938 blocks) is feasible. But one average request needs `ceil(15100/16) = 944` blocks, so `938 // 944 = 0`. The option stays in `options` with `max_concurrent_seqs` 0, `replica_qps` 0.0 and `replicas` and `gpus` both `None`. It is skipped when choosing. `tp` 4 (30 sequences, 2 replicas) and `tp` 8 (89 sequences, 1 replica) both come out at 8 GPUs, and the tie goes to the smaller `tp`, 4.

## 4. Key idea: Little's law turns memory into throughput

A replica holds `conc` sequences at once, and each takes `request_latency_s` seconds from arrival to last token. In steady state, Little's law says `concurrency = throughput × time in system`, so

```
replica_qps = max_concurrent_seqs / request_latency_s
```

With 183 sequences and 15.37 s each, one `tp` 4 replica finishes 11.9 requests per second. That's the bridge from bytes to users. Then you divide the target by **70%** of that, not 100%, because a fleet planned to run at full load has no room for a traffic spike, and queueing delay grows sharply as utilization approaches 1. That's the difference between 6 and 5 replicas in Example 1.

## 5. Plan before you code

```
weight_bytes, kv_per_token from the model
usable per GPU; min_blocks for one full-length sequence; blocks_per_seq; latency
for tp in 1, 2, 4, 8:
    skip if tp > max_tp or kv_heads % tp != 0
    budget = tp * usable - weight_bytes
    num_blocks = budget // (kv_per_token * block_size), or 0 if budget <= 0
    skip if num_blocks < min_blocks            # not feasible: not listed at all
    conc = min(max_num_seqs, num_blocks // blocks_per_seq)
    if conc > 0: qps, replicas, gpus
    else: replica_qps 0.0, replicas None, gpus None
chosen = min over options with gpus, by (gpus, tp)
```

| situation | in `options`? | can be `chosen`? |
|---|---|---|
| `tp > max_tp` or `kv_heads % tp != 0` | no | no |
| `num_blocks < ceil(max_model_len / block_size)` | no | no |
| feasible, `conc == 0` | yes, with `None`s | no |
| feasible, `conc > 0` | yes | yes |

## 6. Build it one piece at a time

**Step 1: the constants that don't depend on `tp`.** Compute them once, outside the loop. `-(-a // b)` is integer ceiling division.

```python
weight_bytes = model["params"] * model["weight_bytes_per_param"]
kv_per_token = 2 * model["layers"] * model["kv_heads"] * model["head_dim"] * model["kv_bytes_per_elem"]
usable = gpu["memory_bytes"] * gpu["memory_utilization_pct"] // 100 - gpu["reserve_bytes"]
```

Multiply before dividing in `usable`. `memory_bytes * (pct // 100)` would be `memory_bytes * 0`.

**Step 2: the filter and the budget.** Both skip conditions go first, before any arithmetic:

```python
if tp > gpu["max_tp"] or model["kv_heads"] % tp:
    continue
budget = tp * usable - weight_bytes
num_blocks = budget // block_bytes if budget > 0 else 0
if num_blocks < min_blocks:
    continue
```

The `if budget > 0` guard matters: in Python, `-68,092,968,960 // 5,242,880` is a large negative number, not 0. The feasibility check would reject it either way, but `num_blocks` should be what the spec says.

**Step 3: concurrency and replicas.** `max(1, ...)` makes sure even a tiny load gets one replica. The `- 1e-9` stops floating-point noise from turning an exact 6.0 into 7.

```python
conc = min(workload["max_num_seqs"], num_blocks // blocks_per_seq)
if conc > 0:
    qps = conc / latency
    replicas = max(1, math.ceil(workload["target_qps"] / (qps * workload["target_utilization_pct"] / 100) - 1e-9))
```

**Step 4: choose.** A tuple key sorts by GPUs first, then by `tp`, which gives the tie-break for free.

```python
chosen = min(usable_opts, key=lambda o: (o["gpus"], o["tp"])) if usable_opts else None
```

## 7. Full solution

```python
import math  # for ceil when rounding replicas up


# Evaluate every allowed TP degree and pick the cheapest one that serves the target load.
def plan_capacity(model, gpu, workload):
    weight_bytes = model["params"] * model["weight_bytes_per_param"]  # the weights every replica must hold
    # K and V tensors, per layer, per KV head (not query head), per head dimension.
    kv_per_token = 2 * model["layers"] * model["kv_heads"] * model["head_dim"] * model["kv_bytes_per_elem"]
    bs = workload["block_size"]  # tokens per KV block
    block_bytes = kv_per_token * bs  # bytes in one KV block
    # Memory the server may use on each GPU, after the utilization cap and the fixed reserve.
    usable = gpu["memory_bytes"] * gpu["memory_utilization_pct"] // 100 - gpu["reserve_bytes"]
    min_blocks = -(-workload["max_model_len"] // bs)  # one full-length sequence must fit
    # Blocks used by a typical request.
    blocks_per_seq = -(-(workload["avg_prompt_tokens"] + workload["avg_output_tokens"]) // bs)
    # Time a request spends in the system: first token, then one TPOT per remaining token.
    latency = workload["ttft_s"] + (workload["avg_output_tokens"] - 1) * workload["tpot_s"]

    options = []  # feasible TP degrees, in increasing order
    # Try each TP degree a single node supports.
    for tp in (1, 2, 4, 8):
        # The box can't go this wide, or the KV heads can't be split evenly.
        if tp > gpu["max_tp"] or model["kv_heads"] % tp:
            continue  # not a valid configuration
        budget = tp * usable - weight_bytes  # KV memory left across the replica's GPUs
        num_blocks = budget // block_bytes if budget > 0 else 0  # a negative budget holds no blocks
        # Can't hold even one max-length sequence.
        if num_blocks < min_blocks:
            continue  # not feasible, so not listed
        conc = min(workload["max_num_seqs"], num_blocks // blocks_per_seq)  # memory limit, capped by the scheduler
        # Defaults for an option that can't serve anyone.
        opt = {"tp": tp, "kv_budget_bytes": budget, "num_blocks": num_blocks, "max_concurrent_seqs": conc,
               "replica_qps": 0.0, "replicas": None, "gpus": None}
        # At least one typical request fits, so this option can serve traffic.
        if conc > 0:
            qps = conc / latency  # Little's law: throughput = concurrency / time in system
            # Size for the utilization target, round up, and never go below one replica.
            replicas = max(1, math.ceil(workload["target_qps"] / (qps * workload["target_utilization_pct"] / 100) - 1e-9))
            opt.update(replica_qps=qps, replicas=replicas, gpus=replicas * tp)  # fill in the sizing
        options.append(opt)  # every feasible option is reported
    usable_opts = [o for o in options if o["gpus"] is not None]  # only options that can serve load
    # Fewest GPUs wins; on a tie, the smaller TP degree.
    chosen = min(usable_opts, key=lambda o: (o["gpus"], o["tp"])) if usable_opts else None
    # The model-level numbers, every feasible option, and the pick.
    return {"weight_bytes": weight_bytes, "kv_bytes_per_token": kv_per_token, "options": options, "chosen": chosen}
```

## 8. How the test cases map to the code

| test case | expected chosen | what it checks |
|---|---|---|
| Example 1 | tp 4, 6 replicas, 24 GPUs | the middle option beats both ends; tp 1 isn't listed |
| Example 2 | tp 2, 6 replicas, 12 GPUs | fp8 halves weights and KV (163,840 bytes per token); tp 1 now loads but holds 5 sequences |
| Example 3 | tp 1, 3 replicas, 3 GPUs | an 8B model on L40S; `max_num_seqs` 64 caps every tp, so more GPUs per replica buy nothing |
| MHA model, tie on gpus prefers smaller tp | tp 2, 8 GPUs | tp 2, 4 and 8 all need 8 GPUs; the tie goes to the smaller tp |
| kv_heads must divide tp | tp 2, 4 GPUs | 4 KV heads, so tp 8 is skipped even though `max_tp` is 8 |
| nothing feasible | `options` `[]`, `chosen` `None` | a 70B model on two L40S: the budget is negative at every tp |
| long context forces higher tp | tp 8, 4 replicas, 32 GPUs | 131,072-token context needs 8,192 blocks, so tp 2 is infeasible; tp 8 beats tp 4 (40 GPUs) |
| feasible but zero concurrency | tp 4, 2 replicas, 8 GPUs | tp 2 is listed with `None`s and skipped; the 8-GPU tie goes to tp 4 |
| tiny load still needs one replica | tp 1, 1 replica | `max(1, ...)` at 0.01 QPS |
| full utilization target | tp 4, 11 replicas, 44 GPUs | `target_utilization_pct` 100 divides by the full replica QPS |
| exact replica count is not rounded up | tp 1, 4 replicas, 4 GPUs | 5 / (1.78571 · 0.7) is exactly 4 but computes as 4.000000000000001; the `- 1e-9` keeps it at 4 |
| scheduler cap dominates | tp 1, 3 GPUs | `max_num_seqs` 8 makes every option 3 replicas, so tp 1 wins on GPUs |

## 9. Complexity

At most four options, each a handful of arithmetic operations: O(1) time and memory. The work is trivial. The value of the planner is in the model it encodes, not in the computation.

In production, the inputs are the weak point. `reserve_bytes` covers activations, CUDA graphs and NCCL buffers, and you only know it for sure from vLLM's startup log ("# GPU blocks: N"). `ttft_s` and `tpot_s` are not constant across `tp` or batch size: more TP speeds up each token but adds all-reduce time. A real planner runs a benchmark per (tp, batch size) and plugs in the measured numbers. The structure of this function stays the same.

## 10. If you got Wrong Answer

Compare `kv_bytes_per_token` first, then each option's `num_blocks`, then `replicas`.

- **`kv_bytes_per_token` is 2,621,440 in Example 1, and the plan is 136 GPUs at tp 8.** You used `attention_heads` (64) instead of `kv_heads` (8). The MHA test still passes, because there the two are equal.
- **`kv_bytes_per_token` is half the expected value (163,840 for fp16).** You forgot the factor 2 for K and V.
- **`chosen` is tp 2 with 440 GPUs in Example 1.** You stopped at the first feasible option. Evaluate them all and take the minimum.
- **Example 1 picks 5 replicas and 20 GPUs.** You sized at 100% utilization. Divide by `qps * target_utilization_pct / 100`.
- **The tp 8 option in Example 1 shows 538 concurrent sequences.** You forgot `min(max_num_seqs, ...)`. The pick happens to survive here (538 sequences gives 3 replicas, 24 GPUs, a tie lost to tp 4), but the `options` list doesn't.
- **"kv_heads must divide tp" lists a tp 8 option.** You're missing `kv_heads % tp`.
- **"exact replica count is not rounded up" gives 5 replicas instead of 4.** You dropped the `- 1e-9`, so float noise above an exact integer rounds up. Keep the epsilon inside the `ceil`.
- **`nothing feasible` crashes, or `chosen` is a dict with `None` GPUs.** You called `min` on an empty list, or didn't filter out options whose `gpus` is `None`.

## 11. Follow-ups an interviewer might ask

- *How do you validate the plan before the hardware arrives?* Rent one node, start vLLM with the planned `tp`, and read the "# GPU blocks" and maximum-concurrency lines it logs. Then run a load test at the target QPS and check TTFT and TPOT against the SLO.
- *What if the traffic is bursty, not steady?* Little's law gives the average. Simulate the arrival pattern through a batching scheduler (problem 129, continuous-batching-scheduler) to see TTFT under bursts, and let an autoscaler (problem 133, autoscaler-policy) handle the peaks above the planned base.
- *What would you change to cut the GPU count?* fp8 weights and KV halve both terms (Example 2: 24 → 12 GPUs). Prefix caching shares the KV of a common system prompt. Raising `max_num_seqs` helps only if compute isn't already the bottleneck.
- *Why not use pipeline parallelism across nodes?* It adds pipeline bubbles and cross-node latency, and the spec limits `tp` to one node. For a 70B model one 8-GPU node is enough. Pipeline parallelism earns its place for models that don't fit on one node at all.
- *Self-host or call an API?* Multiply the chosen GPUs by an hourly price and compare it with per-token API pricing at the same traffic. The break-even depends on utilization, which is why the 70% target matters.
