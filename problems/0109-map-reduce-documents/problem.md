Your legal-ops agent summarizes whole contract folders, which are far bigger than one context window. Write the map-reduce pipeline, with a concurrency limit so you don't trip the provider's rate limit.

`summarize_docs(loop, summarize, docs, chunk_tokens, max_concurrency, batch_size)` gets:

- `loop`, a `gc_runtime.EventLoop`.
- `summarize(text)`, which returns a **generator** for one LLM call. Run it with `s = yield loop.spawn(summarize(text))` (or `yield from summarize(text)`) inside your own task. It takes virtual time and returns the summary string.
- `docs`, a list of `{"id": str, "text": str}`, and the three limits.

**1. Chunk.** For each doc, in order, take `toks = gc_runtime.tokenize(text)` and cut it into consecutive slices of `chunk_tokens` tokens. The last slice may be shorter. Each chunk's text is `" ".join(slice)`. An empty doc has no chunks.

**2. Map.** Summarize every chunk, in doc order and then chunk order.

**3. Reduce.** Starting from the map summaries in **chunk order** (not completion order), and while more than one summary is left:

- Split the list into consecutive batches of `batch_size`. The last batch may be smaller.
- A batch with one summary passes through unchanged, with no call. Any other batch is summarized as `"\n".join(batch)`.
- The new list holds the batch results in batch order. Each level starts only after every call of the previous level, the map level included, has finished.

**Concurrency.** Within a level, never run more than `max_concurrency` calls at once. Start calls in list order, and start the next pending call the moment any running call finishes.

Return the single remaining summary. Return `""` when there are no chunks. Spawn your tasks on `loop` and call `loop.run()` yourself.

The judge records every call's start time, end time and input, the peak concurrency, and the makespan.

**Constraints**

- At most 10 docs and 40 chunks
- `1 <= chunk_tokens`, `1 <= max_concurrency <= 8`, `2 <= batch_size <= 10`
