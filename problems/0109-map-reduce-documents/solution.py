from gc_runtime import tokenize


def summarize_docs(loop, summarize, docs, chunk_tokens, max_concurrency, batch_size):
    chunks = []
    for d in docs:
        toks = tokenize(d["text"])
        for i in range(0, len(toks), chunk_tokens):
            chunks.append(" ".join(toks[i:i + chunk_tokens]))

    def pool(texts):
        out, nxt = [None] * len(texts), [0]

        def worker():
            while nxt[0] < len(texts):
                i = nxt[0]
                nxt[0] += 1
                out[i] = yield loop.spawn(summarize(texts[i]))

        workers = [loop.spawn(worker()) for _ in range(min(max_concurrency, len(texts)))]
        for w in workers:
            yield w
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
