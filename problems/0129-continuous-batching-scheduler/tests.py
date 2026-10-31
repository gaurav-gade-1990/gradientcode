import numpy as np

BASE = {"block_size": 4, "num_blocks": 8, "max_num_seqs": 4, "max_batched_tokens": 32, "max_model_len": 32,
        "step_base_ms": 2.0, "prefill_ms_per_token": 0.25, "decode_ms_per_seq": 0.5}


def r(rid, arrival, prompt, out):
    return {"id": rid, "arrival_ms": arrival, "prompt_tokens": prompt, "output_tokens": out}


def load(n, seed):
    rng = np.random.default_rng(seed)
    t, out = 0.0, []
    for i in range(n):
        t += float(rng.integers(0, 6))
        out.append(r("req-%02d" % i, t, int(rng.integers(3, 20)), int(rng.integers(1, 12))))
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"requests": [r("chat-a", 0, 6, 3), r("chat-b", 1, 10, 2)], "config": BASE},
         "explanation": "chat-a prefills alone (2 + 0.25*6 = 3.5 ms) and holds blocks(7) = 2 blocks. chat-b arrives during that step and joins the next one as a prefill, while chat-a decodes in the same step. At t=8.5 chat-a needs a third block for its 9th token. Both finish at t=11.5 and free all 8 blocks."},
        {"name": "Example 2", "hidden": False,
         "args": {"requests": [r("doc-a", 0, 7, 6), r("doc-b", 0, 7, 6)], "config": dict(BASE, num_blocks=4, max_model_len=16)},
         "explanation": "Both prefill at t=0 and take all 4 blocks. At t=5.5 doc-a needs a third block and none is free, so the newest sequence, doc-b, is preempted: its blocks are freed and it goes to the front of the queue. It can't come back until doc-a finishes at t=18. Then it re-prefills 7 + 1 = 8 tokens (prompt plus the token it already generated). Its TTFT stays 5.5 ms."},
        {"name": "Example 3", "hidden": False,
         "args": {"requests": [r("rag-a", 0, 12, 2), r("rag-b", 0, 12, 2), r("too-long", 0, 4, 40)],
                  "config": dict(BASE, max_batched_tokens=20, max_model_len=20)},
         "explanation": "too-long needs 44 tokens, which is more than max_model_len 20, so it is rejected on arrival. rag-a's 12-token prefill leaves 8 of the 20-token budget, which is not enough for rag-b's 12, so rag-b waits a step even though blocks are free. Next step, rag-a's decode uses 1 token of the budget and rag-b's prefill fits."},
        {"name": "preempt newest of three",
         "args": {"requests": [r("a", 0, 7, 5), r("b", 0, 3, 6), r("c", 0, 3, 6)], "config": dict(BASE, num_blocks=5, max_model_len=16)}},
        {"name": "self preemption",
         "args": {"requests": [r("a", 0, 4, 6), r("b", 0, 4, 6)], "config": dict(BASE, num_blocks=4, max_model_len=12)}},
        {"name": "repeated preemption keeps first ttft",
         "args": {"requests": [r("long", 0, 6, 10), r("x", 0, 6, 10), r("y", 1, 2, 3)], "config": dict(BASE, num_blocks=6, max_model_len=24)}},
        {"name": "head of line blocking is FCFS",
         "args": {"requests": [r("small-1", 0, 4, 8), r("big", 0, 20, 4), r("small-2", 0, 3, 2)], "config": dict(BASE, num_blocks=7, max_model_len=24)}},
        {"name": "token budget caps prefill",
         "args": {"requests": [r("p%d" % i, 0, 10, 2) for i in range(4)], "config": dict(BASE, max_batched_tokens=24, max_model_len=24, num_blocks=16)}},
        {"name": "max_num_seqs caps the batch",
         "args": {"requests": [r("s%d" % i, 0, 2, 3) for i in range(5)], "config": dict(BASE, max_num_seqs=2)}},
        {"name": "idle gaps and a late rejection",
         "args": {"requests": [r("a", 0, 5, 1), r("b", 50, 5, 2), r("c", 200, 30, 30)], "config": BASE}},
        {"name": "single output token", "args": {"requests": [r("cls-1", 0, 9, 1), r("cls-2", 0, 9, 1), r("cls-3", 0.5, 9, 1)], "config": BASE}},
        {"name": "preempted victims resume in order",
         "args": {"requests": [r("a", 0, 3, 6), r("b", 0, 3, 6), r("c", 4, 1, 1)], "config": dict(BASE, num_blocks=3, max_model_len=12)}},
        {"name": "empty", "args": {"requests": [], "config": BASE}},
        {"name": "load test", "args": {"requests": load(40, 129), "config": dict(BASE, num_blocks=10)}},
        {"name": "load test tight memory", "args": {"requests": load(30, 1290), "config": dict(BASE, num_blocks=8, max_num_seqs=6, max_batched_tokens=40)}},
    ]
