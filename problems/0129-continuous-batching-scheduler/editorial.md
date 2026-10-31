## Approach

Continuous batching re-forms the batch at every step (iteration-level scheduling, from the Orca paper), and PagedAttention makes KV memory a pool of fixed-size blocks instead of one contiguous buffer per sequence (vLLM). The simulator is a loop over steps with three phases in a fixed order.

```python
# 1. Running sequences come first: each needs room for one more token.
for s in list(running):
    if s not in running: continue
    if blocks(L(s) + 1) > blocks(L(s)):
        while free == 0:
            victim = running.pop()            # newest admitted (LIFO)
            free += victim.blocks; victim.blocks = 0
            waiting.insert(0, victim)         # it resumes before new arrivals
            if victim is s: break
        if s in running: free -= 1; s.blocks += 1

# 2. Every remaining running sequence decodes 1 token.
# 3. Admit prefills from the head of the queue only (FCFS),
#    needing blocks(P + 1) blocks and P tokens of the step budget, where P = prompt + generated.
# 4. step time = base + prefill_ms * sum(P) + decode_ms * n_decode
# 5. Emit one token each; finished sequences release their blocks.
```

**Why running sequences go first.** They already hold KV memory and a user is watching their stream. Admitting new work while running sequences can't grow only creates more preemption later. You don't need a separate "no admission after a preemption" rule here. The victim goes to the head of the queue and needs at least as many blocks as it just released, one of which the running sequence took, so FCFS keeps everything else out for that step.

**Why preempt the newest.** It has the least sunk work, so recomputing it is cheapest. It is also the one the FCFS policy promised the least.

**Recompute means prompt + generated.** vLLM's default preemption mode (recompute) throws the KV away and later re-runs a prefill over every token the sequence has so far, both the prompt and the generated tokens. The user's stream doesn't restart, so the TTFT doesn't change either. The stall shows up as a gap between tokens, not as a new first token.

**The step cost model.** Prefill is compute-bound, so it costs time per token. Decode is memory-bound, so its cost depends on the batch size and barely on the context length. A prefill-heavy step slows every decoding sequence in it, which is why there is a per-step token budget.

## Common mistakes

- **Preempting the oldest.** Long requests get evicted over and over, and their p99 latency explodes.
- **Re-prefilling only the prompt.** This undercounts both blocks and compute for resumed sequences.
- **Resetting TTFT on resume.** This misreports what users saw, and hides the real problem, the mid-stream stall.
- **Skipping a blocked head.** It looks like better utilization, but long prompts starve under steady short traffic.
- **No token budget.** One huge prefill freezes every stream in the batch.
- **Sending the victim to the back of the queue.** It then waits behind every new arrival, after it has already streamed tokens to a user.

## Production notes

- vLLM's V0 scheduler is close to this model: `waiting` / `running` / `swapped` queues, `max_num_seqs`, `max_num_batched_tokens`, a block manager with `block_size` 16, and recompute or swap preemption. The V1 engine schedules prefill and decode together under a single token budget with **chunked prefill**, which splits a long prompt across steps so that decodes never stall. That is the next thing to add here.
- Sizing: a Llama-3-70B-class GQA model (80 layers, 8 KV heads, head dim 128, fp16) uses 2 × 80 × 8 × 128 × 2 B = 320 KiB of KV per token. On 4×H100 80 GB with tensor parallelism, after about 141 GB of weights and `gpu_memory_utilization=0.9`, that leaves on the order of 140 GB of KV, about 430k tokens or 27k blocks of 16. Problem 130 turns this into a capacity plan.
- Prefix caching (sharing blocks for identical prompt prefixes via a block hash) and fp8 KV both raise effective capacity a lot, and both change the preemption rate this simulator predicts.
- TGI, TensorRT-LLM (in-flight batching) and SGLang (RadixAttention) all make the same trade-offs with different defaults. Use a simulator like this to compare TTFT and inter-token latency SLOs before you change `max_num_seqs` in production. Then pair it with an autoscaler (problem 133) and a load balancer that sees the queue depth (problem 132).
