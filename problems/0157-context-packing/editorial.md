## Approach

Retrieval returns *candidates*. Packing decides what the model actually reads, and it is where most RAG quality and cost is won or lost. There are three passes.

**1. Dedupe by Jaccard on lowercase token sets.** Re-imported wiki pages and overlapping chunks (problem 153) produce near-copies. Visit by score, so the best copy survives and the rest point at it:

```python
for c in sorted(chunks, key=lambda c: (-c["score"], c["chunk_id"])):
    toks = {t.lower() for t in tokenize(c["text"])}
    dup = next((k["chunk_id"] for k, s in zip(kept, kept_sets)
                if len(toks & s) / len(toks | s) >= dedupe_threshold), None)
```

**2. Greedy knapsack by value density.** `score / cost` is the classic greedy for a fractional knapsack. It is not optimal for 0/1, but it is fast, predictable and close enough. Two details matter:

- the cost includes the wrapper tags, because the model is billed for them and they count against the window;
- an item that doesn't fit is **skipped, not a stop**. A short, high-value chunk later in the order can still use the leftover space.

The per-doc cap runs before the budget check, so one long policy can't take every slot.

**3. Reorder for reading.** Score order is right for choosing and wrong for reading. Runbook step 4 before step 1 confuses the model as much as a person. Group by doc (best doc first) and restore `position` order within each.

## Common mistakes

- **Greedy by raw score.** One long, high-scoring chunk evicts three short ones that together answer more.
- **`break` on the first overflow.** It leaves a third of the window empty on most queries.
- **Budgeting only the text.** The `<source>` tags, ids and separators add up, and the prompt goes over the limit in production while passing in tests.
- **Case-sensitive dedupe.** "PARENTAL LEAVE is 16 weeks!" and "Parental leave is 16 weeks." both get in, wasting tokens and over-weighting one claim.
- **Context in score order.** Procedures and clauses read out of order, and the model stitches them together wrongly.

## Production notes

- LangChain's `EmbeddingsRedundantFilter` and `LongContextReorder` and LlamaIndex's node postprocessors (`SimilarityPostprocessor`, `LongContextReorder`) are the off-the-shelf versions of these passes. MinHash/LSH replaces pairwise Jaccard once you have hundreds of candidates.
- "Lost in the middle" (Liu et al., 2023): models use the start and end of a long context best. Some teams put the top doc first and the second-best last. Whatever you choose, keep it deterministic so evals are comparable.
- Count tokens with the target model's tokenizer (Anthropic's `count_tokens` endpoint, `tiktoken`) and keep headroom for the system prompt, the conversation and the answer. Pair this with memory budgeting (problem 107).
- Wrap each source in tags with a stable id. Citations ("[hr/expense-policy#2]") and grounded-answer checks (problem 158) depend on it, and so does treating retrieved text as data rather than instructions (problem 118).
