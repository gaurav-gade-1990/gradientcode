Your team is moving from a static-batching server to **continuous batching** and wants to predict TTFT and latency under load before it buys GPUs. Write the simulator. It follows the scheduling ideas in vLLM: sequences join and leave the batch every step, prefill and decode share a step under a token budget, the KV cache is paged into fixed-size blocks, and when blocks run out the newest sequence is **preempted** and recomputed later.

`simulate_server(requests, config)` takes

- `requests`: `[{"id", "arrival_ms", "prompt_tokens", "output_tokens"}]`, sorted by `arrival_ms`, with `output_tokens >= 1`.
- `config`: `{"block_size", "num_blocks", "max_num_seqs", "max_batched_tokens", "max_model_len", "step_base_ms", "prefill_ms_per_token", "decode_ms_per_seq"}`.

**The KV cache.** A sequence's length is `L = prompt_tokens + generated`, and it holds `blocks(L) = ceil(L / block_size)` blocks. The pool has `num_blocks` blocks in total. (For scale: a 70B GQA model with 80 layers, 8 KV heads, head dim 128 and fp16 KV uses 320 KiB per token, so a 16-token block is 5 MiB. The tests use small pools so that you can trace them by hand.)

**Arrivals.** At the start of every step, each request with `arrival_ms <= now` joins the tail of the `waiting` queue, in input order. If `prompt_tokens + output_tokens > max_model_len`, it is rejected instead and never scheduled.

**One step at time `now`**, in this order:

1. **Reserve decode slots.** Go through `running` in order (the order sequences were admitted or re-admitted). If a sequence needs a new block for its next token (`blocks(L + 1) > blocks(L)`) and none is free, **preempt** the last sequence in `running` (the most recently admitted): free all its blocks, add 1 to its preemption count, keep its `generated` count, and insert it at the **front** of `waiting`. Repeat until a block is free or the sequence has preempted itself. Then take the block.
2. **Decode set.** Every sequence still in `running` decodes one token this step and uses 1 token of the step's budget.
3. **Admit prefills.** While `waiting` is non-empty and `len(running) < max_num_seqs`, look at the head `h`. Its prefill recomputes `P = prompt_tokens + generated` tokens and emits one token, so it needs `blocks(P + 1)` blocks. Admit it if those blocks are free **and** `P` fits in what is left of `max_batched_tokens` after the decode set. Otherwise stop: the queue is first come, first served, and nothing jumps the head.
4. **Run the step.** If nothing was scheduled, don't advance time. Start the next step at the same `now` if anything is waiting, otherwise jump to the next arrival, and finish when no requests remain. Otherwise the step takes `step_base_ms + prefill_ms_per_token * (sum of P) + decode_ms_per_seq * (decode count)` and `now` moves to its end.
5. **Emit.** Every scheduled sequence (decode or prefill) gains one generated token at the step's end time. A request's first-ever token sets its TTFT. A re-prefill after preemption does not reset it. A sequence that reaches `output_tokens` finishes, frees its blocks and leaves `running`.

Return

```
{"requests": [{"id", "status", "ttft_ms", "latency_ms", "preemptions"}, ...],   # input order
 "steps": [{"t_ms", "prefill", "decode", "preempted", "free_blocks"}, ...],
 "makespan_ms": float}
```

- `status` is `"finished"` or `"rejected"`. `ttft_ms` is first-token time minus arrival and `latency_ms` is finish time minus arrival, both `None` when rejected.
- `steps` has one entry per step that ran, in order. `t_ms` is the start time. `prefill`, `decode` and `preempted` are lists of ids in the order they were scheduled or preempted. `free_blocks` is the number free at the end of the step, after finished sequences release theirs.
- `makespan_ms` is the end time of the last step, or `0.0` if none ran.

**Constraints**

- `max_model_len <= max_batched_tokens` and `ceil(max_model_len / block_size) <= num_blocks`, so every accepted request fits on an empty server
- At most 60 requests and 2,000 steps
