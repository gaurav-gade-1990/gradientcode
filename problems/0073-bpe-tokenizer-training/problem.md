Train a **byte-pair encoding** (BPE) tokenizer (Sennrich et al., 2016) on a small corpus, then use the learned merges to tokenize new words.

**Pre-tokenization.** Split `corpus` with Python's `corpus.split()` (any run of whitespace separates words). Each word is kept exactly as written: case and punctuation are preserved and there is no end-of-word marker. A word's frequency is the number of times it appears. Each word starts as the list of its single characters.

**Training.** Repeat up to `num_merges` times:

1. For every word, count each pair of adjacent symbols `(a, b)` in its current segmentation, weighted by the word's frequency. Overlapping occurrences all count: the word `aaa` with frequency 2 contributes `4` to `("a", "a")`.
2. If there are no pairs at all (every word is a single symbol), stop early.
3. Choose the pair with the **highest count**. Break ties by choosing the **smallest pair** under Python tuple comparison: compare `a` first, then `b`, using Python's default string ordering (by Unicode code point, so `"B" < "a"` and `"a" < "ab"`).
4. Record the merge `(a, b)`, then apply it to every word: scan the symbols **left to right**, and wherever symbol `a` is immediately followed by symbol `b`, replace the two with the single symbol `a + b` and continue scanning after it. So `a a a` with merge `("a", "a")` becomes `aa a`.

**Encoding.** To tokenize a test word, start from its characters and apply every learned merge **in the order it was learned**, each one with the same left-to-right rule. Characters never seen in training simply stay as single symbols.

Return a tuple `(merges, encodings)`:

- `merges`: a list of `(a, b)` tuples of strings, in the order learned. It is shorter than `num_merges` if training stopped early.
- `encodings`: a list with one entry per test word, each a list of symbol strings.

**Constraints**

- `corpus` has at most 2,000 characters
- `0 <= num_merges <= 200`
- Every test word is a non-empty string without whitespace
