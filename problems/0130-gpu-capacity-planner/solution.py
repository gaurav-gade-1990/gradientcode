import math


def plan_capacity(model, gpu, workload):
    weight_bytes = model["params"] * model["weight_bytes_per_param"]
    kv_per_token = 2 * model["layers"] * model["kv_heads"] * model["head_dim"] * model["kv_bytes_per_elem"]
    bs = workload["block_size"]
    block_bytes = kv_per_token * bs
    usable = gpu["memory_bytes"] * gpu["memory_utilization_pct"] // 100 - gpu["reserve_bytes"]
    min_blocks = -(-workload["max_model_len"] // bs)
    blocks_per_seq = -(-(workload["avg_prompt_tokens"] + workload["avg_output_tokens"]) // bs)
    latency = workload["ttft_s"] + (workload["avg_output_tokens"] - 1) * workload["tpot_s"]

    options = []
    for tp in (1, 2, 4, 8):
        if tp > gpu["max_tp"] or model["kv_heads"] % tp:
            continue
        budget = tp * usable - weight_bytes
        num_blocks = budget // block_bytes if budget > 0 else 0
        if num_blocks < min_blocks:
            continue
        conc = min(workload["max_num_seqs"], num_blocks // blocks_per_seq)
        opt = {"tp": tp, "kv_budget_bytes": budget, "num_blocks": num_blocks, "max_concurrent_seqs": conc,
               "replica_qps": 0.0, "replicas": None, "gpus": None}
        if conc > 0:
            qps = conc / latency
            replicas = max(1, math.ceil(workload["target_qps"] / (qps * workload["target_utilization_pct"] / 100) - 1e-9))
            opt.update(replica_qps=qps, replicas=replicas, gpus=replicas * tp)
        options.append(opt)
    usable_opts = [o for o in options if o["gpus"] is not None]
    chosen = min(usable_opts, key=lambda o: (o["gpus"], o["tp"])) if usable_opts else None
    return {"weight_bytes": weight_bytes, "kv_bytes_per_token": kv_per_token, "options": options, "chosen": chosen}
