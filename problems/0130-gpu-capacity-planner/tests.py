GiB = 1024 ** 3

# A Llama-3-70B-class GQA model: 80 layers, 64 query heads, 8 KV heads, head_dim 128.
LLAMA70 = {"params": 70_553_706_496, "layers": 80, "attention_heads": 64, "kv_heads": 8, "head_dim": 128,
           "weight_bytes_per_param": 2, "kv_bytes_per_elem": 2}
LLAMA70_FP8 = dict(LLAMA70, weight_bytes_per_param=1, kv_bytes_per_elem=1)
LLAMA8 = {"params": 8_030_261_248, "layers": 32, "attention_heads": 32, "kv_heads": 8, "head_dim": 128,
          "weight_bytes_per_param": 2, "kv_bytes_per_elem": 2}
MHA13 = {"params": 13_015_864_320, "layers": 40, "attention_heads": 40, "kv_heads": 40, "head_dim": 128,
         "weight_bytes_per_param": 2, "kv_bytes_per_elem": 2}
QWEN_LIKE = {"params": 32_763_876_352, "layers": 64, "attention_heads": 40, "kv_heads": 4, "head_dim": 128,
             "weight_bytes_per_param": 2, "kv_bytes_per_elem": 2}

H100 = {"memory_bytes": 80 * GiB, "memory_utilization_pct": 90, "reserve_bytes": 4 * GiB, "max_tp": 8}
L40S = {"memory_bytes": 48 * GiB, "memory_utilization_pct": 90, "reserve_bytes": 3 * GiB, "max_tp": 4}

CHAT = {"target_qps": 50, "avg_prompt_tokens": 2000, "avg_output_tokens": 500, "max_model_len": 8192,
        "ttft_s": 0.4, "tpot_s": 0.03, "max_num_seqs": 256, "block_size": 16, "target_utilization_pct": 70}


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"model": LLAMA70, "gpu": H100, "workload": CHAT},
         "explanation": "KV per token is 2 * 80 * 8 * 128 * 2 = 327,680 bytes (320 KiB). The fp16 weights are about 141 GB. TP=1 can't hold them. TP=2 leaves only about 5 GB for KV: 938 blocks, 5 concurrent sequences, 220 replicas. TP=4 fits 183 sequences per replica, so 6 replicas and 24 GPUs. TP=8 hits max_num_seqs=256 and needs 40 GPUs. The planner picks TP=4."},
        {"name": "Example 2", "hidden": False, "args": {"model": LLAMA70_FP8, "gpu": H100, "workload": CHAT},
         "explanation": "fp8 halves both the weights and the KV per token (163,840 bytes). TP=1 now loads, but with 938 blocks it holds only 5 sequences. TP=2 holds 183 sequences per replica, so 6 replicas and 12 GPUs: half of the fp16 plan."},
        {"name": "Example 3", "hidden": False, "args": {"model": LLAMA8, "gpu": L40S, "workload": dict(CHAT, target_qps=8, max_num_seqs=64)},
         "explanation": "An 8B model fits on one 48 GB L40S with room for KV, and max_num_seqs=64 is what limits each replica. TP=1 wins: more TP just multiplies GPUs that are capped at the same concurrency."},
        {"name": "MHA model, tie on gpus prefers smaller tp", "args": {"model": MHA13, "gpu": H100, "workload": dict(CHAT, target_qps=10)}},
        {"name": "kv_heads must divide tp", "args": {"model": QWEN_LIKE, "gpu": H100, "workload": dict(CHAT, target_qps=20)}},
        {"name": "nothing feasible", "args": {"model": LLAMA70, "gpu": dict(L40S, max_tp=2), "workload": CHAT}},
        {"name": "long context forces higher tp", "args": {"model": LLAMA70, "gpu": H100, "workload": dict(CHAT, max_model_len=131072, avg_prompt_tokens=60000, avg_output_tokens=800, target_qps=2)}},
        {"name": "feasible but zero concurrency", "args": {"model": LLAMA70, "gpu": H100,
                                                            "workload": dict(CHAT, max_model_len=4096, avg_prompt_tokens=30000, avg_output_tokens=1000, target_qps=1)}},
        {"name": "tiny load still needs one replica", "args": {"model": LLAMA8, "gpu": H100, "workload": dict(CHAT, target_qps=0.01)}},
        {"name": "full utilization target", "args": {"model": LLAMA70, "gpu": H100, "workload": dict(CHAT, target_utilization_pct=100, target_qps=120)}},
        {"name": "scheduler cap dominates", "args": {"model": LLAMA8, "gpu": H100, "workload": dict(CHAT, target_qps=1, max_num_seqs=8)}},
    ]
