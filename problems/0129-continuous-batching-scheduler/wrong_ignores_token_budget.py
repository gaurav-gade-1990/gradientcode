# Incident: prefills were admitted on KV space alone. One step took on 30k prompt tokens and
# every decoding user saw a two-second stall in the middle of their stream.
class _Seq:
    def __init__(self, r):
        self.id = r["id"]
        self.arrival = r["arrival_ms"]
        self.prompt = r["prompt_tokens"]
        self.out = r["output_tokens"]
        self.gen = 0                  # tokens generated so far (kept across preemption)
        self.blocks = 0               # KV blocks currently held
        self.preemptions = 0
        self.first = None
        self.finish = None
        self.rejected = False


def simulate_server(requests, config):
    bs = config["block_size"]

    def blocks(n):
        return -(-n // bs)

    seqs = [_Seq(r) for r in requests]
    pending = list(seqs)              # not yet arrived
    waiting, running = [], []
    free = config["num_blocks"]
    now, end, steps = 0.0, 0.0, []

    while True:
        while pending and pending[0].arrival <= now:
            s = pending.pop(0)
            if s.prompt + s.out > config["max_model_len"]:
                s.rejected = True
            else:
                waiting.append(s)
        if not waiting and not running:
            if not pending:
                break
            now = float(pending[0].arrival)
            continue

        # 1. reserve the next slot for every running sequence; preempt the newest while out of blocks
        preempted = []
        for s in list(running):
            if s not in running:              # preempted earlier in this loop
                continue
            L = s.prompt + s.gen
            if blocks(L + 1) == blocks(L):
                continue
            while free == 0:
                victim = running.pop()
                free += victim.blocks
                victim.blocks = 0
                victim.preemptions += 1
                waiting.insert(0, victim)
                preempted.append(victim.id)
                if victim is s:
                    break
            if s in running:
                free -= 1
                s.blocks += 1

        # 2. everything still running decodes one token
        decode = list(running)
        budget = config["max_batched_tokens"] - len(decode)

        # 3. strict FCFS prefill admission
        prefill, prefill_tokens = [], 0
        while waiting and len(running) < config["max_num_seqs"]:
            h = waiting[0]
            P = h.prompt + h.gen              # recompute: prompt plus whatever it already generated
            need = blocks(P + 1)
            if need > free:
                break
            waiting.pop(0)
            running.append(h)
            free -= need
            h.blocks = need
            budget -= P
            prefill_tokens += P
            prefill.append(h)

        if not decode and not prefill:
            if waiting:
                continue
            if pending:
                now = float(pending[0].arrival)
                continue
            break

        # 4. run the step
        t0 = now
        now = t0 + config["step_base_ms"] + config["prefill_ms_per_token"] * prefill_tokens + config["decode_ms_per_seq"] * len(decode)
        end = now

        # 5. emit one token per scheduled sequence; finished ones free their blocks
        for s in decode + prefill:
            s.gen += 1
            if s.first is None:
                s.first = now
            if s.gen == s.out:
                s.finish = now
                free += s.blocks
                s.blocks = 0
                running.remove(s)
        steps.append({"t_ms": t0, "prefill": [s.id for s in prefill], "decode": [s.id for s in decode],
                      "preempted": preempted, "free_blocks": free})

    out = []
    for s in seqs:
        if s.rejected:
            out.append({"id": s.id, "status": "rejected", "ttft_ms": None, "latency_ms": None, "preemptions": 0})
        else:
            out.append({"id": s.id, "status": "finished", "ttft_ms": s.first - s.arrival,
                        "latency_ms": s.finish - s.arrival, "preemptions": s.preemptions})
    return {"requests": out, "steps": steps, "makespan_ms": end}
