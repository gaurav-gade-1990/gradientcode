## Approach

BPE builds a vocabulary bottom-up. Start from characters, then repeatedly fuse the most frequent adjacent pair into a new symbol. The learned merge list *is* the tokenizer: replaying it on any word reproduces the training segmentation and generalizes to unseen words.

Work on **distinct words with counts**, not the raw text. A word that appears 1,000 times is processed once and weighted by 1,000.

```python
freqs = Counter(corpus.split())
words = [(list(w), f) for w, f in freqs.items()]
for _ in range(num_merges):
    counts = Counter()
    for symbols, f in words:
        for pair in zip(symbols, symbols[1:]):
            counts[pair] += f
    if not counts:
        break
    best = min(counts, key=lambda p: (-counts[p], p))   # max count, then smallest tuple
    merges.append(best)
    words = [(merge_symbols(s, best), f) for s, f in words]
```

`merge_symbols` walks the list left to right. On a match it emits `a + b` and jumps two positions, so overlapping matches like `a a a` resolve to `aa a`.

Encoding replays the merges in learned order. Each merge is applied to the whole word before the next one is tried.

## Common mistakes

- **Tie-breaking by insertion order.** `Counter.most_common` returns the first pair it saw among equal counts, which depends on corpus order. The spec says smallest tuple.
- **Comparing `a + b` instead of `(a, b)`.** `("ab", "c")` and `("a", "z")` order differently as tuples and as joined strings.
- **`str.replace` on space-joined symbols.** `"xa b".replace("a b", "ab")` matches inside the symbol `xa`. Compare whole symbols, or use a regex anchored on symbol boundaries.
- **Dropping frequencies.** Counting each distinct word once picks different merges.
- **Encoding by lookup.** Reusing the training segmentation fails on any word not in the corpus.

## Complexity

- **Time:** $O(M \cdot L)$ for $M$ merges and $L$ total symbols across distinct words, since each round recounts every pair. Production tokenizers update pair counts incrementally with a priority queue to avoid the full recount.
- **Space:** $O(L)$ for the segmented words plus $O(L)$ for the pair counts.
