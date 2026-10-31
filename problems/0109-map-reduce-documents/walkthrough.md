## 1. What the problem is really asking

A contract folder is far bigger than one context window, so you can't summarize it in one call. The standard answer is **map-reduce summarization**:

> cut every document into chunks, summarize each chunk (map), then summarize groups of summaries, and keep going until one summary is left (reduce).

Under the story there are two separate pieces of engineering:

1. **A tree reduction over a list.** Each level replaces consecutive groups of `batch_size` items with one item, until the list has length 1. That's pure list slicing.
2. **A bounded worker pool on an event loop.** Every level is a batch of independent LLM calls that you run with at most `max_concurrency` in flight, start the next one the moment a slot frees, and collect the results **in input order**, not completion order.

The judge's fake `summarize` records every call's `start`, `end` and `input`, plus the peak concurrency and the makespan. So it grades *how* you ran the calls, not just the final string. The fake's latency is `0.5 + 0.02 × tokens(input)`, so longer chunks finish later and completion order really does differ from chunk order. Its output is `"sum_%04d"`, a stable hash of the input, so any change in a reduce input changes the final summary.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `loop` | `gc_runtime.EventLoop` with virtual time | `loop.spawn(gen)`, then `loop.run()` once |
| `summarize(text)` | returns a **generator** for one LLM call | `s = yield loop.spawn(summarize(text))` inside your own task |
| `docs` | `[{"id", "text"}]` | chunk each doc separately, in order |
| `chunk_tokens` | the slice length for chunking | `range(0, len(toks), chunk_tokens)` |
| `max_concurrency` | most calls in flight within a level | the number of pool workers |
| `batch_size` | how many summaries one reduce call combines | the slice length for each reduce level |

On the `EventLoop` itself (from `gc_runtime.py`): inside a task, `yield task` waits for that task and gives you its result, and `yield 1.5` sleeps. Nothing runs until you call `loop.run()`, which returns when no task is runnable.

Three details are easy to miss:

- **Chunk each document on its own.** Chunks never span two documents. In Example 1 the refund policy gives chunks of 12, 12 and 2 tokens, and the SLA then starts a fresh chunk.
- **`tokenize` splits punctuation into its own tokens**, and the chunk text is `" ".join(slice)`. That's why inputs look like `"delivery . Items"` with a space before the period, and `"card - vault"`.
- **A batch of one is passed through, not summarized.** It can happen at several levels in a row. In Example 1 the fifth map summary is carried through two levels untouched.

## 3. Trace Example 1 by hand

`docs = [POLICY, SLA]`, `chunk_tokens=12`, `max_concurrency=2`, `batch_size=2`.

**Chunk.** Five chunks. Their latencies follow from `0.5 + 0.02 × tokens`:

| chunk | text (start) | tokens | latency |
|---|---|---|---|
| c1 | "Refunds are accepted within 30 days..." | 12 | 0.74 |
| c2 | "unused and in the original packaging..." | 12 | 0.74 |
| c3 | "refunded ." | 2 | 0.54 |
| c4 | "Premium customers get a reply..." | 12 | 0.74 |
| c5 | "get a reply within 2 business days ." | 8 | 0.66 |

**Map, two slots.**

| time | event | running |
|---|---|---|
| 0 | start c1, c2 | c1, c2 |
| 0.74 | c1 and c2 finish; start c3, c4 | c3, c4 |
| 1.28 | c3 finishes; start c5 immediately | c4, c5 |
| 1.48 | c4 finishes; nothing left to start | c5 |
| 1.94 | c5 finishes; the map level is done | none |

At 1.28 a slot frees while c4 is still running, and c5 takes it straight away. That's the "start the next pending call the moment any running call finishes" rule.

**Reduce.** The map summaries, in chunk order, are `[sum_8027, sum_2853, sum_4801, sum_6034, sum_3210]`.

| level | list in | batches | calls | list out |
|---|---|---|---|---|
| 1 | 5 summaries | `[s1,s2] [s3,s4] [s5]` | 2 (both 1.94 → 2.48) | `[sum_6192, sum_5603, sum_3210]` |
| 2 | 3 | `[sum_6192,sum_5603] [sum_3210]` | 1 (2.48 → 3.02) | `[sum_5879, sum_3210]` |
| 3 | 2 | `[sum_5879,sum_3210]` | 1 (3.02 → 3.56) | `[sum_5080]` |

Final: `"sum_5080"`, 9 calls, peak concurrency 2, makespan 3.56. `sum_3210` passed through levels 1 and 2 with no call.

**The tricky one, "completion order differs from chunk order".** With `chunk_tokens=15` and three slots, the outage doc's third chunk (`"the certificate and add expiry alerts..."`) is shorter and finishes at 0.74, before the first two finish at 0.8. If you append results as calls finish, the first reduce input becomes `"sum_0984\nsum_2329\nsum_2094"` instead of `"sum_2329\nsum_2094\nsum_0984"`, and the final summary is `sum_6556` instead of `sum_4301`. Every start and end time is still correct. Only the order of the inputs is wrong.

## 4. Key idea: a pool of workers pulling from a shared counter

You need three properties at once: at most `c` calls running, the next call starts the moment *any* call finishes, and results land by index. A small pool gives all three:

```python
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
```

- **Concurrency.** There are `c` workers, each running one call at a time, so at most `c` calls are in flight.
- **Greedy refill.** When a worker's call returns, it immediately takes the next index. No coordinator, no semaphore.
- **Order.** `out[i] = ...` stores by input position, so the order calls finish in doesn't matter.

`nxt` is a one-element list so the inner function can change it. A plain `int` would need `nonlocal`. Because the event loop is single-threaded and a task only gives up control at a `yield`, reading and incrementing `nxt[0]` can't race.

The tempting alternative, pre-assigning chunk `i` to lane `i % c`, is a trap. In "completion order differs from chunk order", lane 0 holds chunks 0, 3 and 6. At 0.74 lane 2 is free, but its next chunk is chunk 5, and chunk 3 must wait for lane 0 until 0.8. The makespan becomes 3.34 instead of 3.28.

## 5. Key idea: `yield from` makes the pool a function call

`pool` is a generator. Calling `level = yield from pool(texts)` from inside another generator runs it inline: its `yield w` statements wait on the loop for you, and its `return out` becomes the value of the `yield from` expression. That lets the main pipeline read like ordinary sequential code:

```python
level = yield from pool(chunks)        # map: returns only when every chunk is done
while len(level) > 1:
    ...
    done = yield from pool(texts)      # one reduce level, also fully finished
```

Because `pool` waits for all its workers before returning, a level never starts before the previous one has finished. That's the "each level starts only after every call of the previous level" rule, and you get it for free.

## 6. Plan before you code

```
chunks = for each doc: tokenize, slice by chunk_tokens (keep the short tail), join with " "
main():
    if no chunks: return ""
    level = pool(chunks)
    while len(level) > 1:
        batches = consecutive slices of batch_size
        texts to summarize = "\n".join(b) for batches with 2+ items
        results = pool(those texts)
        level = for each batch: its result if it was summarized, else its single item
    return level[0]
spawn main, loop.run(), return its result
```

| batch | call? | goes into the next level as |
|---|---|---|
| 2 or more summaries | yes, on `"\n".join(batch)` | the call's result |
| exactly 1 summary | no | that summary, unchanged |

## 7. Build it one piece at a time

**Step 1: chunk, keeping the partial tail.**

```python
chunks = []
for d in docs:
    toks = tokenize(d["text"])
    for i in range(0, len(toks), chunk_tokens):
        chunks.append(" ".join(toks[i:i + chunk_tokens]))
```

`range(0, len(toks), chunk_tokens)` visits every start position, including one whose slice runs off the end. Python slicing clips it, so the last chunk is just shorter. An empty doc gives `toks = []` and an empty range, so no chunks.

**Step 2: the pool** (section 4). Use `min(max_concurrency, len(texts))` workers so you don't spawn idle ones.

**Step 3: one reduce level.**

```python
batches = [level[i:i + batch_size] for i in range(0, len(level), batch_size)]
joined = [("\n".join(b) if len(b) > 1 else None) for b in batches]
done = yield from pool([j for j in joined if j is not None])
it = iter(done)
level = [next(it) if j is not None else b[0] for j, b in zip(joined, batches)]
```

`joined` marks pass-through batches with `None`. Only real texts go to the pool, and `next(it)` hands the results back out in the same order. The pool can never be empty here: the loop runs only when `len(level) > 1`, and `batch_size >= 2`, so the first batch always has at least two items.

**Step 4: wrap, run, return.**

```python
task = loop.spawn(main())
loop.run()
return task.result
```

`summarize_docs` itself isn't a generator, so it can't `yield`. Spawn the pipeline as a task, run the loop to completion, then read `task.result`. The empty-input case returns `""` from inside `main`, before any call.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# The judge's tokenizer: words and single punctuation marks.
from gc_runtime import tokenize


# summarize(text) returns a generator for one LLM call; everything runs on the virtual-time loop.
def summarize_docs(loop, summarize, docs, chunk_tokens, max_concurrency, batch_size):
    chunks = []  # every chunk of every doc, in doc order then chunk order
    # Chunk each document on its own, so no chunk spans two docs.
    for d in docs:
        toks = tokenize(d["text"])  # an empty doc gives [] and so no chunks
        # Step by chunk_tokens; the last start may run past the end, which keeps the short tail.
        for i in range(0, len(toks), chunk_tokens):
            chunks.append(" ".join(toks[i:i + chunk_tokens]))  # the chunk text the problem defines

    # Run summarize over texts with at most max_concurrency in flight; results come back by index.
    def pool(texts):
        out, nxt = [None] * len(texts), [0]  # results slot per input, and the next index to hand out

        # One worker = one concurrency slot; it keeps pulling work until none is left.
        def worker():
            # Take the next unclaimed text the moment this worker is free.
            while nxt[0] < len(texts):
                i = nxt[0]  # claim index i; no race, the loop only switches tasks at a yield
                nxt[0] += 1  # the next worker gets the next text
                out[i] = yield loop.spawn(summarize(texts[i]))  # store by position, not finish order

        # Never spawn more workers than there are texts.
        workers = [loop.spawn(worker()) for _ in range(min(max_concurrency, len(texts)))]
        # Wait for every worker, so the whole level is finished before we return.
        for w in workers:
            yield w  # waiting on a Task resumes us when it's done
        return out  # becomes the value of `yield from pool(...)`

    # The whole pipeline as one task: map, then reduce levels until one summary is left.
    def main():
        # No chunks means nothing to summarize and no calls at all.
        if not chunks:
            return ""  # the required result for empty input
        level = yield from pool(chunks)  # map level, in chunk order
        # Keep reducing until a single summary remains.
        while len(level) > 1:
            # Consecutive groups of batch_size; the last group may be smaller.
            batches = [level[i:i + batch_size] for i in range(0, len(level), batch_size)]
            # A batch of one passes through with no call (None marks it); others become one text.
            joined = [("\n".join(b) if len(b) > 1 else None) for b in batches]
            done = yield from pool([j for j in joined if j is not None])  # this level's calls
            it = iter(done)  # results for the batches that were summarized, in batch order
            # Rebuild the level in batch order: a call's result, or the untouched single summary.
            level = [next(it) if j is not None else b[0] for j, b in zip(joined, batches)]
        return level[0]  # the one remaining summary

    task = loop.spawn(main())  # we can't yield here, so run the pipeline as a task
    loop.run()  # run virtual time until every task has finished
    return task.result  # main's return value
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `sum_5080`, 9 calls, peak 2, makespan 3.56 | greedy refill at 1.28; a batch of one carried through two levels |
| Example 2 | `sum_5371`, 1 call | one chunk means no reduce at all |
| empty input | `""`, 0 calls | the early return in `main` |
| partial last chunk kept | 3 map calls, the last on `"days ."`; 5 calls | `range(0, len(toks), chunk_tokens)` keeps the tail |
| completion order differs from chunk order | `sum_4301`, makespan 3.28 | results stored by index; dynamic refill beats static lanes |
| serial | `sum_5080`, peak 1, makespan 5.58 | `max_concurrency=1`; same final as Example 1 |
| wide concurrency | 17 calls, peak 6, makespan 2.82 | six slots used, 13 chunks across three docs |
| batch of everything | 9 calls, one reduce call over 8 summaries | `batch_size` larger than the level |
| tiny chunks deep tree | 17 calls over four reduce levels | many levels, pool reused at every level |
| exact multiple of chunk size | 3 calls, two 4-token chunks | no empty trailing chunk |

## 10. Complexity

With `n` chunks and batch size `b`, the reduce tree has about `log_b(n)` levels, and the total number of calls is about `n + n/(b-1)`: every reduce call turns `b` items into one. Tokenizing and chunking is O(total tokens). The makespan is roughly the sum, over levels, of `ceil(calls_in_level / c)` call latencies, because each level waits for its slowest call.

At scale the trade-offs are cost against latency. A larger `batch_size` means fewer levels and fewer calls, but each reduce input is longer and the model may lose detail. Higher concurrency cuts wall time until you hit the provider's requests-per-minute or tokens-per-minute limit (problem 123, token-bucket-rate-limiter), after which 429s and retries make the job slower. For overnight jobs, the map level is ideal for a batch API at roughly half the price.

## 11. If you got Wrong Answer

- **The final summary is different but every start and end time matches.** You collected results in completion order. Store them as `out[i]`.
- **The calls are right but some start a little late, and the makespan is 3.34 instead of 3.28 in "completion order differs from chunk order".** You pre-assigned chunks to lanes (`i % c`). Workers must pull the next index from a shared counter.
- **`peak_concurrency` is above `max_concurrency` (Example 1 shows more than 2).** You spawned one task per chunk with no limit.
- **"partial last chunk kept" has no call on `"days ."`, and Example 2 makes no calls at all and returns `""`.** Your chunk loop stops at the last full chunk (`range(0, len(toks) - chunk_tokens + 1, chunk_tokens)`).
- **Example 1 makes 11 calls instead of 9.** You summarize batches of one. Pass a single summary through unchanged.
- **"empty input" returns `None` instead of `""`.** Without the early return, `level` is `[]` and `level[0]` raises inside the task. The event loop stores the exception on the task, so `task.result` is just `None`. Return `""` before running the pool when there are no chunks.

## 12. Follow-ups an interviewer might ask

- *One chunk's call fails. What happens?* Here the exception would propagate and kill the job. In production, wrap each call with retries and backoff (problem 124), and checkpoint map results so a rerun only redoes the failed chunks.
- *Why not start a reduce call as soon as its batch is ready, instead of waiting for the whole level?* You can: batch `[s1, s2]` doesn't depend on `s5`. That's a DAG schedule, not a level barrier, and it's exactly problem 103 (parallel-tool-dag). It lowers makespan; the level barrier is simpler to reason about and retry.
- *Chunking by raw token count splits sentences. What's better?* Split on structure: sections, then paragraphs, then sentences, falling back to tokens only when needed (problem 153, recursive-chunker). Add a small overlap so a clause that straddles a boundary appears in both chunks.
- *How do you pick `max_concurrency`?* From the provider's limits, not a guess: requests per minute and tokens per minute, divided across the jobs sharing the key. A token bucket enforces it (problem 123).
- *Map-reduce loses cross-chunk detail. Any alternative?* Refine (summarize chunk 1, then "update this summary with chunk 2", and so on) keeps more continuity but is fully sequential. With long-context models, sending whole documents per call and reducing only across documents is often both cheaper and better.
