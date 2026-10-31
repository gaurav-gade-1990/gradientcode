## Approach

Capacity planning for LLM serving is memory first, then Little's law.

```python
kv_per_token = 2 * layers * kv_heads * head_dim * kv_bytes        # K and V
usable = memory_bytes * pct // 100 - reserve                       # per GPU
for tp in (1, 2, 4, 8):
    budget = tp * usable - weight_bytes                            # KV left after weights
    num_blocks = budget // (kv_per_token * block_size)
    conc = min(max_num_seqs, num_blocks // blocks_per_seq)
    qps = conc / (ttft + (out - 1) * tpot)                         # Little's law
    replicas = ceil(target_qps / (qps * util))
pick min(gpus = replicas * tp)
```

**The 70B numbers.** 2 × 80 × 8 × 128 × 2 B = **320 KiB per token**. An average 2,500-token conversation is about 800 MB of KV. At TP=2 on 80 GB H100s, the 141 GB of fp16 weights leave about 5 GB, so only five such conversations fit at once. At TP=4 there's about 150 GB of KV and 183 conversations fit. The KV budget grows faster than the GPU count, because the weights are a fixed cost that more GPUs share.

**Why search over TP.** Smaller TP is not cheaper when the weights eat almost all the memory. Larger TP is not better once `max_num_seqs` (or compute) caps the batch. Evaluate each option and compare total GPUs.

## Common mistakes

- **Attention heads instead of KV heads.** GQA exists to cut KV by `heads / kv_heads` (8× for Llama-3-70B). Using the query heads quotes the MHA cost.
- **Forgetting the factor 2.** There are two cached tensors, K and V.
- **Sizing at 100% utilization.** Queueing delay grows sharply near saturation. Plan for 60–75% and let the autoscaler (problem 133) absorb the peaks.
- **Stopping at the smallest TP that fits.** "It loads" is not the same as "it serves".
- **Ignoring the scheduler cap.** `max_num_seqs` limits concurrency even when memory doesn't.
- **GB vs GiB.** An "80 GB" H100 has 80 GiB (85.9e9 bytes). Mixing units moves the answer by 7%.

## Production notes

- vLLM logs exactly this at startup ("# GPU blocks: N" and the maximum concurrency for `max_model_len`). Confirm the plan against that line on real hardware, because CUDA graphs, the sampler and the NCCL buffers eat into `reserve_bytes`.
- `ttft_s` and `tpot_s` do change with TP and batch size. Higher TP speeds up each token but adds all-reduce overhead. A real planner measures a throughput curve per (TP, batch size) with a benchmark such as `vllm bench serve` and plugs the measurement in here.
- Levers that change the answer a lot: fp8 weights and KV (H100 has native FP8), prefix caching for shared system prompts, chunked prefill for TTFT under load, and speculative decoding for TPOT. Grouped or latent attention (MLA in DeepSeek) shrinks the KV per token much further.
- Prefill and decode have different bottlenecks. Large deployments increasingly split them across separate GPU pools (disaggregated serving, as in DistServe or NVIDIA Dynamo) and plan each pool separately.
- Pair this with the batching simulator (problem 129) to check TTFT and inter-token latency under bursty arrivals, and with the cost estimator (problem 178) to compare self-hosting against API pricing.
