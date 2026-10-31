## Approach

Chunk on **token spans**, not on characters or `str.split()`. One regex pass gives every token's `(start, end)`, and a chunk is just a run of token indices `[a, b)`. Its offsets come straight from the spans, so they are right even when the same sentence appears twice in the document.

**Split.** A run that fits is a piece. A run that doesn't is cut at the strongest separator it contains, and each part is split again one level down. A paragraph that fits stays whole; only an oversized one falls through to lines, sentences, and finally single tokens.

```python
def split(a, b, level):
    if b - a <= max_tokens:
        return [(a, b)]
    if level == 3:
        return [(i, i + 1) for i in range(a, b)]
    cuts = [i + 1 for i in range(a, b - 1) if is_separator(i, level)]
    if not cuts:
        return split(a, b, level + 1)
    edges = [a] + cuts + [b]
    return [p for s, e in zip(edges, edges[1:]) for p in split(s, e, level + 1)]
```

**Merge.** Small pieces (a title, a one-line step) are packed greedily so you don't embed 2-token chunks. When the next piece `p` overflows, close the chunk and seed the next one with the longest suffix of whole pieces that fits the overlap budget **and** leaves room for `p`:

```python
for q in reversed(cur):
    if kept + size(q) > overlap_tokens or kept + size(q) + size(p) > max_tokens:
        break
    keep.insert(0, q); kept += size(q)
```

The second condition matters: without it the overlap plus the next piece can exceed the model limit.

## Common mistakes

- **Counting with `str.split()`.** `payments-api,` is one word and four tokens. The chunker thinks a chunk fits and the embedding API truncates or rejects it.
- **Recovering offsets with `text.find(chunk)`.** Policies repeat boilerplate ("Report lost devices to security@…"). `find` returns the first copy, so citations and highlights point at the wrong section.
- **Overlap that ignores `max_tokens`.** Overlap plus the next piece can go past the limit; check both budgets.
- **A fixed sliding window.** Cutting every N tokens splits sentences and steps of a runbook in half, which hurts retrieval and makes cited snippets unreadable.
- **Stripping or normalizing text before computing offsets.** The offsets then point into a different string than the one you store.

## Production notes

- This is LangChain's `RecursiveCharacterTextSplitter` and LlamaIndex's `SentenceSplitter`, measured in tokens. In production use the embedding model's own tokenizer (`tiktoken`, the Voyage or Cohere tokenizer) so your budget matches the API's.
- Keep `start`/`end` offsets with every chunk. You need them for citations with highlights, for grounded-answer checks (problem 158), and to re-chunk only what changed (problem 156).
- Structure-aware splitting beats any separator list: split Markdown on headings, HTML on block elements, code on functions, and carry the section path ("Security Baseline > Contractors") into each chunk's metadata or prefix.
- Overlap of 10–20% is common, but it costs index size and makes duplicates show up in retrieval. Context packing (problem 157) dedupes them at query time.
