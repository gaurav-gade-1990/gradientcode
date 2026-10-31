## 1. What the problem is really asking

Strip away the vLLM vocabulary and this is a **discrete-time simulation with two queues and a memory pool**:

> every step: make room for the sequences already running (evicting the newest if memory runs out) → admit new work from the head of a FIFO queue while it fits → advance the clock by a cost formula → hand out one token each and release finished sequences.

There is no randomness and nothing to optimize. Every rule is spelled out in `problem.md`. The difficulty is doing the rules **in the right order** and keeping three counters straight for each sequence: tokens generated, KV blocks held, and preemptions.

The judge compares the whole return value: the per-request `ttft_ms`, `latency_ms` and `preemptions`, **and** the full `steps` log (start time, who prefilled, who decoded, who was preempted, free blocks at the end). So a scheduler that gets the final latencies right by luck but schedules a different sequence in some middle step still fails. The `steps` log is the best debugging tool you have: compare yours with the expected one and find the first step that differs.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `requests` | `[{"id", "arrival_ms", "prompt_tokens", "output_tokens"}]`, sorted by arrival | becomes one sequence object each; output is in this order |
| `block_size` | tokens per KV block | `blocks(L) = ceil(L / block_size)` |
| `num_blocks` | size of the KV pool | the starting value of `free` |
| `max_num_seqs` | cap on `len(running)` | stops admission |
| `max_batched_tokens` | per-step token budget | each decode uses 1, each prefill uses `P` |
| `max_model_len` | longest allowed `prompt + output` | longer requests are rejected on arrival |
| `step_base_ms`, `prefill_ms_per_token`, `decode_ms_per_seq` | the cost model | `base + prefill_ms * sum(P) + decode_ms * n_decode` |

Three details are easy to miss:

- **A prefill emits a token.** A prefill of `P` tokens produces token number `P + 1`, so it needs `blocks(P + 1)` blocks, not `blocks(P)`. With `block_size` 4, a 12-token prompt needs `blocks(13) = 4` blocks.
- **`P` is `prompt + generated`, not just `prompt`.** A preempted sequence lost its KV but kept its tokens. To resume, it recomputes everything it had. Its TTFT does not change, because the user already saw that first token.
- **Arrivals are checked only at step boundaries.** A request that arrives in the middle of a step joins the queue at the start of the next one. In Example 1, `chat-b` arrives at 1 ms, while `chat-a`'s first step runs from 0 to 3.5 ms, so `chat-b` first appears at t = 3.5.

## 3. Trace Example 2 by hand

Config: `block_size` 4, `num_blocks` 4, two identical requests, `doc-a` and `doc-b`, each with a 7-token prompt and 6 output tokens.

| step | t_ms | phase 1 (reserve) | decode | prefill | step time | after emit: L (blocks) | free |
|---|---|---|---|---|---|---|---|
| 1 | 0 | nothing running | - | doc-a, doc-b (P=7 each, `blocks(8)` = 2 each) | 2 + 0.25·14 = 5.5 | a 8 (2), b 8 (2) | 0 |
| 2 | 5.5 | doc-a has L=8 and needs `blocks(9)` = 3 > 2. free is 0, so pop the newest, **doc-b**: free becomes 2, and doc-a takes one | doc-a | none (doc-b at the head needs 3, free is 1) | 2 + 0.5 = 2.5 | a 9 (3), b 8 (0) | 1 |
| 3–5 | 8, 10.5, 13 | no new block needed (L 9→12 fits in 3 blocks) | doc-a | blocked | 2.5 each | a 12 (3) | 1 |
| 6 | 15.5 | doc-a has L=12 and needs `blocks(13)` = 4. free is 1, so it takes it | doc-a | blocked | 2.5 | doc-a finishes at 18, releases 4 | 4 |
| 7 | 18 | nothing running | - | doc-b: P = 7 + 1 = **8**, needs `blocks(9)` = 3 | 2 + 0.25·8 = 4 | b 9 (3) | 1 |
| 8–11 | 22 … 29.5 | | doc-b | | 2.5 each | doc-b finishes at 32 | 4 |

Result: `doc-a` has `ttft_ms` 5.5 and `latency_ms` 18. `doc-b` has `ttft_ms` **5.5** (its first token came out at the end of step 1, before the preemption), `latency_ms` 32 and `preemptions` 1. The re-prefill in step 7 costs 4 ms because it covers 8 tokens: the prompt plus the one token doc-b had already generated.

### The trickiest hidden case: "preempted victims resume in order"

`num_blocks` 3. `a` and `b` each have a 3-token prompt and 6 output tokens. `c` (1 token in, 1 out) arrives at 4 ms.

- **Step 1, t=0.** Both prefill `P=3` and take `blocks(4) = 1` block each, so free is 1. The step takes 2 + 0.25·6 = 3.5.
- **Step 2, t=3.5.** `a` has L=4 and needs `blocks(5) = 2`. free is 1, so `a` takes it and free is 0. Now `b` also has L=4 and needs a block. free is 0, so the scheduler pops the newest running sequence, which is **`b` itself**. This is self-preemption: `b` frees its block, goes to the front of `waiting`, and the inner loop stops. `steps[1]` is `{"decode": ["a"], "preempted": ["b"], "free_blocks": 1}`.
- `c` arrived at 4 ms, during step 2, so it joins at t=6, **behind** `b`.
- **Step 7, t=16.** `a` finished at 16 and released its blocks, so free is 3. `b` resumes with `P = 3 + 1 = 4` and needs `blocks(5) = 2`. `c` needs `blocks(2) = 1`. Both fit, so prefill is `["b", "c"]`.

`c` finishes with `ttft_ms` 15.25. It waited behind `b` the whole time, which is the FCFS rule doing its job.

## 4. Key idea: why the three phases go in this order

**Running sequences reserve first.** They already hold memory, and a user is watching each of their streams. If you admitted new prefills first, they would take the free blocks, and a running sequence would then have to be preempted to grow, which wastes the work it has done. Doing reservation first also means that a sequence preempted in phase 1 is at the head of `waiting` during phase 3. It needs at least as many blocks as it just freed, and the running sequence took one of those, so it can't fit and FCFS keeps everyone behind it out for that step. You get "no admission right after a preemption" for free, without writing a special rule.

**The victim is the newest.** `running.pop()` takes the last-admitted sequence. It has the least sunk work, so recomputing it is cheapest, and under FCFS it is the one with the weakest claim.

**The victim goes to the front.** `waiting.insert(0, victim)`. It has already streamed tokens to a user. Sending it to the back would freeze that half-finished answer behind every new arrival.

## 5. Key idea: FCFS means stop, not skip

When the head of `waiting` doesn't fit (not enough blocks, or `P` is bigger than the budget left), you **break**. You don't look further down the queue for a smaller request. In "head of line blocking is FCFS", `big` needs 6 blocks while `small-1` holds 2 of the 7, so `big` waits 20.5 ms, and `small-2` (which would fit in one block) waits behind it. Skipping the head looks like better utilization, but under steady short traffic a long prompt would never run at all.

## 6. Plan before you code

```
make a sequence object per request (gen=0, blocks=0, preemptions=0, first=None, finish=None)
pending = all sequences; waiting = []; running = []; free = num_blocks; now = 0
loop:
    move arrived requests from pending to waiting (or mark them rejected)
    if nothing waiting or running: jump to next arrival, or stop if none
    phase 1: for each running s in order: if it needs a block and none is free,
             pop the newest running (repeat while free == 0, stop if it was s); take a block
    phase 2: decode = everything still running; budget = max_batched_tokens - len(decode)
    phase 3: while waiting and room in max_num_seqs:
                 head needs blocks(P+1) and P tokens; if either doesn't fit: break; else admit
    if nothing scheduled: continue at the same now (or jump to next arrival)
    step time from the cost formula; now = end
    every scheduled sequence gains a token; set first token once; finished ones release blocks
    log the step
build the per-request results
```

Decision table for one running sequence in phase 1:

| `blocks(L+1) > blocks(L)`? | free > 0? | action |
|---|---|---|
| no | any | nothing, it already has room |
| yes | yes | take one block |
| yes | no | pop the newest until a block is free; if `s` itself was popped, it doesn't decode |

## 7. Build it one piece at a time

**Step 1: the sequence state and the block helper.** `-(-n // bs)` is ceiling division in integers. Use it rather than `math.ceil(n / bs)` to stay out of floats.

```python
class _Seq:
    def __init__(self, r):
        self.id, self.arrival = r["id"], r["arrival_ms"]
        self.prompt, self.out = r["prompt_tokens"], r["output_tokens"]
        self.gen = self.blocks = self.preemptions = 0
        self.first = self.finish = None
        self.rejected = False
```

**Step 2: arrivals and idle jumps.** Pop from the front of `pending` while `arrival <= now`. When nothing is waiting or running, set `now` to the next arrival and loop. Don't create a step: the log only has steps that ran, which is why "idle gaps and a late rejection" has three steps and a `makespan_ms` of 55.75, not 200.

**Step 3: phase 1.** Iterate over a **copy** (`list(running)`), because you pop from `running` inside the loop. Then skip any `s` that is no longer in `running`, since it was preempted earlier in the same loop.

```python
for s in list(running):
    if s not in running:
        continue
    L = s.prompt + s.gen
    if blocks(L + 1) == blocks(L):
        continue
    while free == 0:
        victim = running.pop()
        free += victim.blocks; victim.blocks = 0
        victim.preemptions += 1
        waiting.insert(0, victim); preempted.append(victim.id)
        if victim is s:
            break
    if s in running:
        free -= 1; s.blocks += 1
```

**Step 4: phase 3 admission.** The budget starts at `max_batched_tokens - len(decode)`, because each decode uses one token. Both conditions go in one `if ... break`.

```python
while waiting and len(running) < config["max_num_seqs"]:
    h = waiting[0]
    P = h.prompt + h.gen
    need = blocks(P + 1)
    if need > free or P > budget:
        break
    ...
```

**Step 5: emit.** Loop over `decode + prefill`. Set `first` only when it is `None`, so a re-prefill doesn't reset TTFT. Free blocks *before* you log `free_blocks`, because the log records the value after finished sequences release theirs.

## 8. Full solution

```python
# Per-request state for the simulation.
class _Seq:
    # Copy the request fields and start every counter at zero.
    def __init__(self, r):
        self.id = r["id"]  # reported back in the output and in the step log
        self.arrival = r["arrival_ms"]  # TTFT and latency are measured from here
        self.prompt = r["prompt_tokens"]  # part of the KV length and of every prefill
        self.out = r["output_tokens"]  # the sequence finishes when gen reaches this
        self.gen = 0  # tokens generated so far; survives preemption
        self.blocks = 0  # KV blocks currently held; dropped to 0 on preemption
        self.preemptions = 0  # how many times it was evicted
        self.first = None  # time of the first-ever token; set once
        self.finish = None  # time of the last token
        self.rejected = False  # too long for max_model_len, never scheduled


# Run the scheduler step by step and return per-request results plus the step log.
def simulate_server(requests, config):
    bs = config["block_size"]  # tokens per KV block

    # Number of blocks needed to hold n tokens.
    def blocks(n):
        return -(-n // bs)  # integer ceiling division, no floats

    seqs = [_Seq(r) for r in requests]  # one state object per request, in input order
    pending = list(seqs)  # requests that haven't arrived yet, still sorted by arrival
    waiting, running = [], []  # the FCFS queue and the current batch, in admission order
    free = config["num_blocks"]  # the KV pool starts empty
    now, end, steps = 0.0, 0.0, []  # clock, end of the last step that ran, and the log

    # One iteration per step, plus iterations that only move the clock.
    while True:
        # Requests that have arrived by now join the queue, in input order.
        while pending and pending[0].arrival <= now:
            s = pending.pop(0)  # the earliest request that hasn't been seen yet
            # A request longer than the model allows can never run.
            if s.prompt + s.out > config["max_model_len"]:
                s.rejected = True  # reported as rejected, never scheduled
            else:  # it fits, so it waits its turn
                waiting.append(s)  # new arrivals go to the tail
        # Nothing to schedule right now.
        if not waiting and not running:
            # No future arrivals either: the simulation is over.
            if not pending:
                break  # leave the main loop
            now = float(pending[0].arrival)  # idle: jump the clock to the next arrival
            continue  # go back and admit it

        # Phase 1: every running sequence reserves room for its next token.
        preempted = []  # ids evicted this step, in eviction order
        # Iterate over a copy because preemption removes items from running.
        for s in list(running):
            # It was evicted earlier in this same loop, so it has nothing to reserve.
            if s not in running:
                continue  # skip it
            L = s.prompt + s.gen  # current KV length
            # The next token still fits in the blocks it holds.
            if blocks(L + 1) == blocks(L):
                continue  # no new block needed
            # Out of blocks: evict the newest sequence until one is free.
            while free == 0:
                victim = running.pop()  # newest admitted, the least sunk work
                free += victim.blocks  # its whole KV goes back to the pool
                victim.blocks = 0  # it holds nothing now
                victim.preemptions += 1  # count the eviction
                waiting.insert(0, victim)  # front of the queue, so it resumes first
                preempted.append(victim.id)  # record it in this step's log
                # It evicted itself, so there is no one left to give the block to.
                if victim is s:
                    break  # stop evicting
            # Still running, so take the block it needed.
            if s in running:
                free -= 1  # one block leaves the pool
                s.blocks += 1  # and is now held by s

        # Phase 2: everything still running decodes one token.
        decode = list(running)  # snapshot before admissions add prefills
        budget = config["max_batched_tokens"] - len(decode)  # each decode uses one token

        # Phase 3: admit prefills from the head of the queue only.
        prefill, prefill_tokens = [], 0  # admitted sequences and their total recompute tokens
        # Keep admitting while there's a head and room in the batch.
        while waiting and len(running) < config["max_num_seqs"]:
            h = waiting[0]  # FCFS: only the head may be admitted
            P = h.prompt + h.gen  # recompute the prompt plus anything already generated
            need = blocks(P + 1)  # the prefill also emits one token, so room for P + 1
            # Not enough memory or budget: nothing may jump the head.
            if need > free or P > budget:
                break  # stop admitting for this step
            waiting.pop(0)  # take it off the queue
            running.append(h)  # it is now the newest running sequence
            free -= need  # reserve its blocks
            h.blocks = need  # it holds exactly these
            budget -= P  # its prefill uses P tokens of the step
            prefill_tokens += P  # feeds the step cost
            prefill.append(h)  # record it in this step's log

        # Nothing could be scheduled this step.
        if not decode and not prefill:
            # Something is queued, so retry at the same time.
            if waiting:
                continue  # back to the top without advancing time
            # Otherwise wait for the next arrival.
            if pending:
                now = float(pending[0].arrival)  # jump the clock
                continue  # and try again
            break  # nothing left at all

        # Phase 4: run the step.
        t0 = now  # the step's start time, for the log
        # Base cost, plus compute-bound prefill per token, plus memory-bound decode per sequence.
        now = t0 + config["step_base_ms"] + config["prefill_ms_per_token"] * prefill_tokens + config["decode_ms_per_seq"] * len(decode)
        end = now  # makespan is the end of the last step that ran

        # Phase 5: every scheduled sequence emits one token at the step's end.
        for s in decode + prefill:
            s.gen += 1  # one more output token
            # Only the first-ever token counts for TTFT; re-prefills don't reset it.
            if s.first is None:
                s.first = now  # the user sees their first token now
            # It has produced everything it asked for.
            if s.gen == s.out:
                s.finish = now  # latency ends here
                free += s.blocks  # release its KV before the step is logged
                s.blocks = 0  # it holds nothing now
                running.remove(s)  # it leaves the batch
        # Log the step; free_blocks is the value after finished sequences released theirs.
        steps.append({"t_ms": t0, "prefill": [s.id for s in prefill], "decode": [s.id for s in decode],
                      "preempted": preempted, "free_blocks": free})

    out = []  # one result per request, in input order
    # Turn each sequence's timestamps into the reported metrics.
    for s in seqs:
        # Rejected requests have no timings.
        if s.rejected:
            # Report it with no timings and no preemptions.
            out.append({"id": s.id, "status": "rejected", "ttft_ms": None, "latency_ms": None, "preemptions": 0})
        else:  # it ran to completion
            # Both times are measured from arrival.
            out.append({"id": s.id, "status": "finished", "ttft_ms": s.first - s.arrival,
                        "latency_ms": s.finish - s.arrival, "preemptions": s.preemptions})
    return {"requests": out, "steps": steps, "makespan_ms": end}  # the full simulation report
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 3 steps, chat-a ttft 3.5, chat-b ttft 7.5 | a mid-step arrival joins at the next boundary; prefill and decode share a step |
| Example 2 | doc-b preempted at t=5.5, ttft 5.5, latency 32 | newest is preempted; re-prefill is 7 + 1 = 8 tokens; TTFT is kept |
| Example 3 | too-long rejected; rag-b ttft 10.5 | `max_model_len` rejection; the token budget delays a prefill even with blocks free |
| preempt newest of three | c preempted (1 time), a and b keep running | `running.pop()` takes the last admitted, not the one that needs the block |
| self preemption | b preempted at t=13, latency 24.5 | a block shortage late in the stream; resume re-prefills 4 + 4 = 8 tokens |
| repeated preemption keeps first ttft | y then x preempted; y ttft 7.5, latency 38.25 | victims stack at the front, so x (preempted last) resumes before y |
| head of line blocking is FCFS | big ttft 28.25; small-2 waits behind it and is later preempted | `break`, not skip, when the head doesn't fit |
| token budget caps prefill | p0, p1 at t=0; p2, p3 at t=7 | 10 + 10 fits a 24 budget, a third 10 doesn't |
| max_num_seqs caps the batch | s0, s1, then s2, s3, then s4 | `len(running) < max_num_seqs` |
| idle gaps and a late rejection | 3 steps, makespan 55.75 | idle jumps create no steps; makespan uses the last step, not the clock |
| single output token | cls-1, cls-2 finish in their prefill step at 6.5 | a prefill's token can be the last one |
| preempted victims resume in order | b preempts itself at t=3.5; prefill `["b", "c"]` at t=16 | self-preemption, and the victim stays ahead of a later arrival |
| empty | `{"requests": [], "steps": [], "makespan_ms": 0.0}` | the loop ends immediately |
| load test, load test tight memory | 40 and 30 random requests | every rule interacting at once |

## 10. Complexity

Let `n` be the number of requests (≤ 60) and `S` the number of steps (≤ 2,000). Each step walks `running` (at most `max_num_seqs` long) and pops from the front of short lists, and `s in running` is a linear scan of that small list. The total is O(S · max_num_seqs) with tiny constants, well under the time limit. Memory is O(n + S) for the sequences and the log.

At production scale the shape changes but the logic doesn't. vLLM runs this scheduler once per forward pass (tens of milliseconds), with thousands of blocks and hundreds of sequences. That's why real schedulers keep `running` and `waiting` as deques and track blocks in a block table instead of scanning lists. The cost model is the useful part: a prefill-heavy step slows every stream in it, which is exactly what `max_batched_tokens` protects against.

## 11. If you got Wrong Answer

Diff your `steps` with the expected ones and find the first step that differs:

- **Example 2 has doc-a with `preemptions` 1 and latency 32, and doc-b finishing at 18.** You evicted the oldest (`running.pop(0)`). Evict the newest with `running.pop()`.
- **doc-b's `ttft_ms` is 22 instead of 5.5.** You stamp the first token on every prefill. Set it only when `s.first is None`.
- **doc-b's latency is 31.75 instead of 32.** The re-prefill used only `prompt_tokens` (7 tokens, 3.75 ms instead of 4 ms). Use `P = prompt + gen`.
- **In "head of line blocking is FCFS", small-2 has `ttft_ms` 3.75 and no preemption.** You skipped a head that didn't fit and admitted the request behind it. Break instead.
- **In Example 3, both rag requests prefill at t=0 with `ttft_ms` 8.** You only check blocks. Add `P > budget` to the admission test.
- **In "repeated preemption keeps first ttft", y finishes with latency 25.75 and long with 31.75.** Victims are appended to the back of `waiting`. Insert them at index 0.
- **`free_blocks` in the last step is too low.** You logged the step before releasing finished sequences' blocks.
- **`makespan_ms` is 200 in "idle gaps and a late rejection".** You returned the clock instead of the end of the last step that ran.

## 12. Follow-ups an interviewer might ask

- *How would chunked prefill change this?* Split a long prompt across steps so that each step's prefill tokens fit the budget left after decodes. Decodes never stall behind a 20k-token prompt, at the cost of a slightly later TTFT for that prompt. vLLM's V1 engine schedules this way by default.
- *Recompute or swap?* Swapping copies the victim's KV to CPU memory and back, which costs PCIe bandwidth but no compute. Recompute is cheaper for short sequences and is vLLM's default. Swap wins when sequences are long and the GPU is compute-bound.
- *How many GPUs does this workload need?* Turn KV bytes per token and the traffic into a block budget and a replica count. That's problem 130 (gpu-capacity-planner).
- *How would prefix caching change the preemption rate?* Requests that share a system prompt share its blocks through a block hash, so each new request needs fewer free blocks and preemption happens less. Freed blocks must be reference-counted, not simply returned to the pool.
- *What metric would you autoscale on?* Queue depth and KV utilization predict TTFT better than GPU utilization, which reads near 100% whenever anything is running. See problem 133 (autoscaler-policy).
