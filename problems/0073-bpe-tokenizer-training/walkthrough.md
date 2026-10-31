## 1. What the problem is really asking

A language model can't read characters efficiently (sequences get too long) and can't keep a vocabulary of every word (new words appear constantly). Byte-pair encoding sits between them. It starts from single characters and repeatedly fuses the most frequent adjacent pair into a new symbol, so common words become one token and rare words fall apart into reusable pieces.

Strip the story and the problem is **a greedy loop over a frequency table**: count weighted adjacent pairs, pick the best with an exact tie-break, rewrite every word with a left-to-right scan, repeat. Then **replay** the learned merges, in order, on new words. The output is two lists of strings, compared exactly, so every tie-break and every boundary rule is visible to the judge.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `corpus` | a string of words separated by any whitespace | `Counter(corpus.split())` gives word frequencies |
| `num_merges` | the maximum number of merges to learn | the training loop bound; may stop early |
| `test_words` | words to tokenize after training | start from characters, apply every merge in order |

The data structure that matters is **distinct word → (symbol list, frequency)**. `"low low low"` is one entry, `(["l", "o", "w"], 3)`.

Easy to miss:

- **Ties go to the smallest tuple.** Not the first pair seen (`Counter.most_common` does that) and not the smallest joined string `a + b`.
- **Merging compares whole symbols.** Joining symbols with spaces and calling `str.replace` can match across a boundary.
- **Encoding replays merges, it doesn't look words up.** A test word that was in the corpus gets the same segmentation either way, but an unseen word must still be merged.
- **`split()` with no argument** splits on any run of spaces, tabs or newlines and drops empty strings. Case and punctuation stay: `"the,"` and `"the"` are different words.

## 3. The math

Let the corpus have distinct words $w$ with frequency $f_w$ and current segmentation $s_w = (s_{w,1}, \dots, s_{w,n_w})$. The pair count is

$$
c(a, b) = \sum_{w} f_w \cdot \big|\{\, i : s_{w,i} = a,\ s_{w,i+1} = b \,\}\big| .
$$

Each round picks

$$
(a^*, b^*) = \arg\min_{(a,b)} \big(-c(a, b),\ (a, b)\big)
$$

under tuple ordering: highest count first, then the smallest pair, comparing $a$ and then $b$ by Unicode code point.

**Overlaps count.** In a run of $r$ identical symbols there are $r - 1$ adjacent pairs, so `"aaa"` with frequency 2 contributes $2 \cdot 2 = 4$ to `("a", "a")`. But merging is left to right and non-overlapping: the run becomes `aa a`, not `a aa`, and only one merge is applied, not two.

**What each merge buys.** Write $N = \sum_w f_w\, n_w$ for the total number of tokens in the corpus. A merge that is applied $k_w$ times in word $w$ shrinks it by $k_w$ symbols, so

$$
N_{\text{after}} = N_{\text{before}} - \sum_w f_w\, k_w .
$$

Without overlaps $k_w$ equals the pair's occurrences in $w$, so the greedy step removes exactly $c(a^*, b^*)$ tokens, the most any single merge could remove. BPE is a greedy compressor: each merge is the locally best reduction in corpus length, and the vocabulary grows by one symbol per merge.

**Why tuples and strings disagree.** Tuples compare the first element first. `("a", "z") < ("ab", "c")` because `"a" < "ab"` (a prefix is smaller). Joined, `"az" > "abc"` because `"z" > "b"` at the second character. "tuple vs concat ties" is built so these two orders pick different merges.

## 4. Trace Example 1 by hand

`corpus = "low low low lower newest newest"`, `num_merges = 4`. Distinct words: `low` ×3, `lower` ×1, `newest` ×2.

**Round 1.** Counts, highest first:

| pair | count | from |
|---|---|---|
| `(l, o)` | 4 | low ×3, lower ×1 |
| `(o, w)` | 4 | low ×3, lower ×1 |
| `(w, e)` | 3 | lower ×1, newest ×2 |
| `(e, s)`, `(e, w)`, `(n, e)`, `(s, t)` | 2 each | newest ×2 |
| `(e, r)` | 1 | lower |

`(l, o)` and `(o, w)` tie at 4; `"l" < "o"`, so merge `(l, o)`. Words: `lo w`, `lo w e r`, `n e w e s t`.

**Round 2.** `(lo, w)` has 4, the unique maximum. Words: `low`, `low e r`, `n e w e s t`.

**Round 3.** `(w, e)` dropped to 2 because `lower`'s `w` is now inside `low`. Five pairs tie at 2: `(e, s)`, `(e, w)`, `(n, e)`, `(s, t)`, `(w, e)`. The smallest tuple is `(e, s)`. Words: `n e w es t`.

**Round 4.** Four pairs tie at 2: `(e, w)`, `(es, t)`, `(n, e)`, `(w, es)`. The smallest is `(e, w)`. Words: `n ew es t`.

Merges: `[(l, o), (lo, w), (e, s), (e, w)]`.

**Encoding `lowest`**, an unseen word: `l o w e s t` → `(l, o)` → `lo w e s t` → `(lo, w)` → `low e s t` → `(e, s)` → `low es t` → `(e, w)` doesn't occur. Result `["low", "es", "t"]`. **`new`** → only `(e, w)` applies → `["n", "ew"]`.

Comparing joined strings instead agrees in round 3 (`"es"` is also the smallest joined string), but in round 4 it picks `(es, t)` because `"est" < "ew"`, so the fourth merge comes out as `("es", "t")` instead of `("e", "w")`.

**Example 2's encoding** shows the boundary trap. Training gives `[(a, a), (aa, a), (a, b)]`. Encoding `aaaa`: `(a, a)` scans left to right and gives `aa aa`; `(aa, a)` needs symbol `aa` followed by symbol `a`, and there is none, so the answer is `["aa", "aa"]`. With strings, `"aa aa".replace("aa a", "aaa")` matches the first `aa`, the space, and the first character of the second `aa`, producing `"aaaa"`, one symbol.

## 5. Key idea: merge on symbol lists, never on strings

A symbol list makes boundaries explicit: `["aa", "aa"]` has two elements and no element is `"a"`. The scan compares `symbols[i] == a and symbols[i + 1] == b` on whole symbols, emits `a + b` on a match and jumps two places, otherwise emits `symbols[i]` and moves one. Jumping two is what makes `a a a` become `aa a` and prevents a symbol from taking part in two merges at once. A space-joined string loses that: `"aa a"` occurs inside `"aa aa"` even though no symbol there is `"a"`.

## 6. Plan before you code

```
words = [(list(w), freq) for each distinct word]
merges = []
repeat num_merges times:
    counts = weighted adjacent-pair counts over all words
    if counts empty: stop
    best = min over pairs of (-count, pair)
    append best; rewrite every word with merge_symbols(symbols, best)
encode each test word: list(w), then merge_symbols with every merge in order
return merges, encodings
```

| tie-break | `(es, t)` vs `(e, w)` in round 4 | correct? |
|---|---|---|
| smallest tuple | `(e, w)`, since `"e" < "es"` | yes |
| smallest joined string | `(es, t)`, since `"est" < "ew"` | no |
| first seen | depends on corpus order | no |

## 7. Build it one piece at a time

**Step 1: merge one pair in one word.**

```python
def merge_symbols(symbols, pair):
    a, b = pair
    out, i = [], 0
    while i < len(symbols):
        if i + 1 < len(symbols) and symbols[i] == a and symbols[i + 1] == b:
            out.append(a + b)
            i += 2                      # both symbols consumed; no overlapping reuse
        else:
            out.append(symbols[i])
            i += 1
    return out
```

**Step 2: the frequency table.** `zip(symbols, symbols[1:])` yields every adjacent pair, overlaps included.

```python
freqs = Counter(corpus.split())
words = [(list(w), f) for w, f in freqs.items()]
counts = Counter()
for symbols, f in words:
    for pair in zip(symbols, symbols[1:]):
        counts[pair] += f
```

**Step 3: pick and apply.** `min` with key `(-count, pair)` does both rules: the negation turns "highest count" into "smallest key", and the tuple breaks ties.

```python
if not counts:
    break
best = min(counts, key=lambda p: (-counts[p], p))
merges.append(best)
words = [(merge_symbols(symbols, best), f) for symbols, f in words]
```

**Step 4: encode by replay.**

```python
symbols = list(w)
for pair in merges:
    symbols = merge_symbols(symbols, pair)
```

## 8. Full solution

```python
# a Counter is a dict with default 0, which keeps the counting loops short
from collections import Counter


# rewrite one word: left to right, every a immediately followed by b becomes a+b
def merge_symbols(symbols, pair):
    a, b = pair  # the two symbols to fuse
    out, i = [], 0  # the rewritten word and the scan position
    # scan once; matches never overlap because a match consumes both symbols
    while i < len(symbols):
        # compare whole symbols, so a boundary can never be matched across
        if i + 1 < len(symbols) and symbols[i] == a and symbols[i + 1] == b:
            out.append(a + b)  # the merged symbol replaces the pair
            i += 2  # skip both, so "a a a" becomes "aa a"
        # no match here, so keep this symbol as it is
        else:
            out.append(symbols[i])  # unchanged symbol
            i += 1  # move one place
    return out  # the new segmentation


# learn up to num_merges merges, then tokenize test_words by replaying them
def train_bpe(corpus: str, num_merges: int, test_words: list) -> tuple:
    freqs = Counter(corpus.split())  # distinct word -> count; split() handles any whitespace
    words = [(list(w), f) for w, f in freqs.items()]  # each word starts as single characters
    merges = []  # learned merges in order: this list IS the tokenizer
    # one merge per round
    for _ in range(num_merges):
        counts = Counter()  # adjacent-pair counts for the current segmentation
        # every distinct word, weighted by its frequency
        for symbols, f in words:
            # zip with the shifted list gives every adjacent pair, overlaps included
            for pair in zip(symbols, symbols[1:]):
                counts[pair] += f  # a word seen f times contributes f
        # every word is a single symbol: nothing left to merge
        if not counts:
            break  # stop early with fewer merges
        best = min(counts, key=lambda p: (-counts[p], p))  # highest count, then the smallest tuple
        merges.append(best)  # record before applying, in learned order
        words = [(merge_symbols(symbols, best), f) for symbols, f in words]  # apply to every word

    encodings = []  # one symbol list per test word
    # tokenize each test word independently
    for w in test_words:
        symbols = list(w)  # start from characters, unseen ones included
        # replay every merge in the order it was learned
        for pair in merges:
            symbols = merge_symbols(symbols, pair)  # same left-to-right rule as training
        encodings.append(symbols)  # the final segmentation
    return merges, encodings  # merges as (a, b) tuples, encodings as lists of strings
```

## 9. How the test cases map to the code

| test case | expected merges | what it checks |
|---|---|---|
| Example 1 | `(l, o), (lo, w), (e, s), (e, w)` | frequency weighting and tuple tie-breaks |
| Example 2 | `(a, a), (aa, a), (a, b)`; `aaaa` → `[aa, aa]` | overlapping counts and left-to-right merging |
| stops early | `(a, b), (c, d)` with `num_merges = 10` | the empty-counts break |
| zero merges | `[]`; `hello` → five characters | the loop never runs |
| boundary trap | `(a, b), (x, ab), (x, a)` | merges after an earlier merge has changed the symbols |
| frequency matters | `(a, b), (c, d)` | `ab` ×4 beats pairs that appear in more distinct words |
| tuple vs concat ties | `(a, b), (a, z), (ab, c)` | `(a, z) < (ab, c)` as tuples |
| case and punctuation | `(h, e), (t, he), (T, he), ...` | `The`, `the,` and `THE` are distinct words |
| unseen test words | `bananas` → `[banana, s]`, `zzz` → `[z, z, z]` | replay on unseen words and characters |
| multiple whitespace | `(u, g), (h, ug), ...` | `split()` with tabs, newlines and repeated spaces |
| long corpus | 40 merges | everything at once |

## 10. Complexity

Each round recounts every pair, so training is $O(M \cdot L)$ for $M$ merges and $L$ total symbols across distinct words, and memory is $O(L)$. Encoding a word of length $n$ costs $O(M \cdot n)$, since every merge rescans it. Production tokenizers do better on both sides. Training updates pair counts incrementally (only words containing the merged pair change) with a priority queue. Encoding uses a merge-rank table: repeatedly merge the adjacent pair with the lowest rank (its position in the merge list), which is how GPT-2's encoder works and costs far less than rescanning for every merge. Real tokenizers also start from bytes rather than characters, so no input is ever out of vocabulary.

## 11. If you got Wrong Answer

- **Example 1's third merge is `(n, e)` instead of `(e, s)`.** You broke ties by first-seen order, as `Counter.most_common` does.
- **Example 1's fourth merge is `(es, t)`.** You compared `a + b` strings instead of `(a, b)` tuples. "tuple vs concat ties" fails too.
- **Example 2's `aaaa` encodes to `["aaaa"]`.** You merged with `str.replace` on space-joined symbols, which matches across a boundary. "unseen test words" also learns a different third merge, `(anan, a)`.
- **Example 2's second merge is `(a, b)`, or Example 1's merges look different.** You counted each distinct word once and ignored frequencies.
- **Every merge list is right but encodings of new words are just characters.** You looked words up in the training segmentation instead of replaying merges.

## 12. Follow-ups an interviewer might ask

- *Why byte-level BPE?* Starting from the 256 byte values means any string, in any script or with emoji, can be encoded without an unknown token. GPT-2 and later models do this.
- *Why pre-tokenize at all?* Splitting into words first stops merges from crossing word boundaries, so you never learn tokens like `"e t"`. Real tokenizers use a regex that also separates punctuation and digits.
- *How does WordPiece differ?* It picks the pair maximizing $\frac{c(a, b)}{c(a)\,c(b)}$, a likelihood gain, rather than the raw count. Unigram LM tokenizers instead start large and prune.
- *How does tokenization affect perplexity numbers?* A tokenizer with longer tokens has fewer, harder predictions per text, so per-token perplexities aren't comparable across tokenizers (problem 72).
