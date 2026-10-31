from gc_runtime import tokenize


def summarize_docs(loop, summarize, docs, chunk_tokens, max_concurrency, batch_size):
    # Bug: work is pre-split round-robin (chunk i goes to slot i % c). A slot stuck on long chunks keeps its
    # queue while other slots sit idle, so the job takes longer than the limit allows.
    chunks = []
    for d in docs:
        toks = tokenize(d["text"])
        for i in range(0, len(toks), chunk_tokens):
            chunks.append(" ".join(toks[i:i + chunk_tokens]))

    def pool(texts):
        out = [None] * len(texts)

        def lane(k):
            for i in range(k, len(texts), max_concurrency):
                out[i] = yield loop.spawn(summarize(texts[i]))

        lanes = [loop.spawn(lane(k)) for k in range(min(max_concurrency, len(texts)))]
        for t in lanes:
            yield t
        return out

    def main():
        if not chunks:
            return ""
        level = yield from pool(chunks)
        while len(level) > 1:
            batches = [level[i:i + batch_size] for i in range(0, len(level), batch_size)]
            joined = [("\n".join(b) if len(b) > 1 else None) for b in batches]
            done = yield from pool([j for j in joined if j is not None])
            it = iter(done)
            level = [next(it) if j is not None else b[0] for j, b in zip(joined, batches)]
        return level[0]

    task = loop.spawn(main())
    loop.run()
    return task.result
