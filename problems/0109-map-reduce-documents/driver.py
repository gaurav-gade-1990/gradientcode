from gc_runtime import EventLoop, count_tokens, stable_hash


def run(ns, docs, chunk_tokens, max_concurrency, batch_size):
    """A fake summarizer: latency grows with input length; the summary is a stable id of the input."""
    loop = EventLoop()
    calls = []
    live = [0, 0]

    def summarize(text):
        def gen():
            rec = {"start": round(loop.now(), 9), "end": None, "input": text}
            calls.append(rec)
            live[0] += 1
            live[1] = max(live[1], live[0])
            yield 0.5 + 0.02 * count_tokens(text)
            live[0] -= 1
            rec["end"] = round(loop.now(), 9)
            return "sum_%04d" % stable_hash(text, 10000)
        return gen()

    final = ns["summarize_docs"](loop, summarize, docs, chunk_tokens, max_concurrency, batch_size)
    return {"final": final, "calls": calls, "llm_calls": len(calls), "peak_concurrency": live[1], "makespan": round(loop.now(), 9)}
