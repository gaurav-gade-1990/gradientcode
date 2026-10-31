## Approach

Everything hangs on a small `pool` that runs a list of texts with at most `c` in flight and returns the results **by index**:

```python
def pool(texts):
    out, nxt = [None] * len(texts), [0]
    def worker():
        while nxt[0] < len(texts):
            i = nxt[0]; nxt[0] += 1
            out[i] = yield loop.spawn(summarize(texts[i]))
    workers = [loop.spawn(worker()) for _ in range(min(max_concurrency, len(texts)))]
    for w in workers:
        yield w
    return out

def main():
    if not chunks:
        return ""
    level = yield from pool(chunks)                       # map
    while len(level) > 1:                                 # reduce levels
        batches = [level[i:i + batch_size] for i in range(0, len(level), batch_size)]
        joined = ["\n".join(b) if len(b) > 1 else None for b in batches]
        done = iter((yield from pool([j for j in joined if j])))
        level = [next(done) if j else b[0] for j, b in zip(joined, batches)]
    return level[0]
```

Workers that pull from a shared counter are a semaphore without the semaphore: a fast worker takes the next chunk as soon as it's free. Storing results by index keeps the reduce in document order no matter which call finishes first.

## Common mistakes

- **Collecting in completion order.** `as_completed` returns whichever call finished first. The final summary then tells the story out of order.
- **No concurrency limit.** Fine for 5 chunks; 500 simultaneous calls get rate limited and retried, and the job ends up slower.
- **Static round-robin lanes.** Pre-assigning chunk `i` to lane `i % c` leaves lanes idle while one lane works through long chunks.
- **Dropping the partial chunk.** `range(0, n - size + 1, size)` loses the end of every document, which is often where the conclusion is.
- **Summarizing a batch of one.** That's a paid call that rewrites a summary into a slightly worse summary.

## Production notes

- LangChain's `MapReduceDocumentsChain` and LlamaIndex's tree summarize implement exactly this. The production knobs are the same three: chunk size, concurrency and batch size.
- Base concurrency on the provider's limits (RPM and TPM, problem 123) and wrap each call with retries (problem 124). One failed chunk shouldn't restart the whole job; checkpoint the map results.
- Chunk on structure (sections, paragraphs) rather than raw token counts; problem 153 (recursive-chunker) does that. Overlap between chunks helps when sentences straddle a boundary.
- For long batch jobs, the Message Batches APIs from Anthropic and OpenAI cut the price roughly in half in exchange for latency. The map level is a perfect fit.
