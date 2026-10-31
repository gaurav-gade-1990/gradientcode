## 1. What the problem is really asking

BM25 is the ranking function inside Lucene, Elasticsearch and OpenSearch, and it's the keyword half of almost every hybrid RAG retriever. Given a query, it gives each document a relevance score: rare query words count for more, repeating a word helps but with diminishing returns, and long documents are discounted because they match words by chance.

Under the story this is **a sum over query tokens of `idf × saturated tf`**, where the saturation depends on each document's length. You compute the length factor once per document, then loop over the query tokens and add one vector of `N` contributions per token.

The judge compares your `(N,)` score array with `rtol=1e-6`. The edge cases are the ones the spec spells out: repeated query tokens, unknown tokens, empty documents in the average length, and an empty query.

## 2. Understand the inputs

| name | type | what it is | how you use it |
|---|---|---|---|
| `docs` | list of `N` strings | the corpus | tokenised with `lower().split()` |
| `query` | string | the search text | tokenised the same way, **repeats kept** |
| `k1` | float, default `1.5` | saturation strength | larger means tf keeps mattering longer |
| `b` | float in `[0, 1]`, default `0.75` | length-normalisation strength | `0` off, `1` full |
| return | `(N,)` float | one score per document | input order |

The details that are easy to miss:

- **The query is lowercased too.** In Example 2, `"The dog"` matches `the`.
- **`avgdl` averages over all `N` documents**, empty ones included. Leaving them out raises `avgdl` and changes every score.
- **Query repeats count.** `"cat cat sat"` adds the `cat` term twice. Don't take a `set` of the query.
- **`cat` and `cats` are different tokens.** No stemming.

## 3. The math

Let $N$ be the number of documents, $|d|$ the length of document $d$, $\overline{dl} = \frac{1}{N}\sum_d |d|$, $f = f(q, d)$ the count of token $q$ in $d$, and $\text{df}(q)$ the number of documents containing $q$.

**The tf part: saturation.** Write $K_d = k_1\big(1 - b + b\,|d| / \overline{dl}\big)$, a constant per document. The tf part is

$$\phi(f) = \frac{f\,(k_1 + 1)}{f + K_d}.$$

Three properties follow directly.

- $\phi(0) = 0$: a missing word adds nothing.
- Its derivative is $\phi'(f) = \dfrac{(k_1 + 1)(f + K_d) - f(k_1 + 1)}{(f + K_d)^2} = \dfrac{(k_1 + 1) K_d}{(f + K_d)^2} > 0$, which shrinks as $f$ grows. Each extra occurrence helps less than the last.
- As $f \to \infty$, $\phi(f) \to k_1 + 1$. No amount of repetition exceeds that cap.

For an average-length document ($K_d = k_1 = 1.5$), $\phi = 1, 1.43, 1.67, 1.92, 2.17$ at $f = 1, 2, 3, 5, 10$, approaching $2.5$. Compare TF-IDF (problem 82), where tf is linear.

**The length factor.** $K_d / k_1 = 1 - b + b\,|d|/\overline{dl}$ is a blend of 1 and the document's relative length. A document twice the average length with $b = 0.75$ gets $1 - 0.75 + 1.5 = 1.75$: its denominator grows, so the same count scores lower. With $b = 0$ the factor is always 1 and length is ignored.

**The idf.** The Robertson–Spärck Jones weight is $\ln\frac{N - \text{df} + 0.5}{\text{df} + 0.5}$, the log-odds that a document **doesn't** contain the term, with 0.5 added to each count so it's never $\ln 0$. When $\text{df} > N/2$ the fraction is below 1 and the log is negative: a common term would **lower** a document's score for containing it. Lucene adds 1 inside the log:

$$\text{idf}(q) = \ln\!\left(1 + \frac{N - \text{df}(q) + 0.5}{\text{df}(q) + 0.5}\right) > 0,$$

since the argument is always above 1. With $\text{df} = N/2$ the fraction is 1 and $\text{idf} = \ln 2$.

**Putting it together.** With the query tokens $q_1, \dots, q_m$ (repeats allowed),

$$\text{score}(d) = \sum_{i=1}^{m} \text{idf}(q_i)\, \phi_d\big(f(q_i, d)\big).$$

A token in no document has $f = 0$ everywhere, so it adds 0 even though its idf is large.

## 4. Trace an example by hand

**Example 1:** query `"cat"`, default `k1 = 1.5`, `b = 0.75`.

```python
docs = ["the cat sat on the mat",       # |d| = 6
        "the dog sat",                  # |d| = 3
        "cats and dogs",                # |d| = 3
        "the cat ate the cat food"]     # |d| = 6
```

`avgdl = 18 / 4 = 4.5`. The per-document constant `K_d = 1.5 · (0.25 + 0.75 · |d| / 4.5)` is `[1.875, 1.125, 1.125, 1.875]`.

`cat` appears in docs 0 and 3 (`cats` doesn't count), so `df = 2` and `idf = ln(1 + 2.5 / 2.5) = ln 2 = 0.6931`.

| doc | `f` | `f · 2.5 / (f + K_d)` | score |
|---|---|---|---|
| 0 | 1 | `2.5 / 2.875 = 0.8696` | `0.6027` |
| 1 | 0 | `0` | `0` |
| 2 | 0 | `0` | `0` |
| 3 | 2 | `5 / 3.875 = 1.2903` | `0.8944` |

Doc 3 has twice the count of doc 0 but only about 1.5 times the score. That's saturation.

**Example 2:** query `"The dog"`, `k1 = 1.2`, `b = 0.5`. Now `K_d = 1.2 · (0.5 + 0.5 · |d| / 4.5) = [1.4, 1, 1, 1.4]`, and `k1 + 1 = 2.2`.

| token | df | idf |
|---|---|---|
| `the` | 3 | `ln(1 + 1.5 / 3.5) = 0.3567` |
| `dog` | 1 | `ln(1 + 3.5 / 1.5) = 1.2040` |

Doc 1 (`"the dog sat"`): `the` gives `0.3567 · 2.2 / 2 = 0.3923`, `dog` gives `1.2040 · 1.1 = 1.3244`, total `1.7167`. Doc 0 has `the` twice: `0.3567 · 4.4 / 3.4 = 0.4616`. Final scores `[0.4616, 1.7167, 0, 0.4616]`. With the Robertson idf, `the` would get `ln(1.5 / 3.5) = -0.847` and doc 0 would score below an unrelated document.

**The hidden case "empty doc in corpus"** has lengths `[3, 0, 2, 5]`. The correct `avgdl` is `10 / 4 = 2.5`. Averaging only non-empty docs gives `10 / 3 = 3.33`, and doc 0's score rises from `1.5663` to `1.7489`.

## 5. Plan before you code

```
toks   = [d.lower().split() for d in docs]
counts = one Counter per document
dl     = document lengths                          # (N,)
K      = k1 * (1 - b + b * dl / dl.mean())         # (N,), once
scores = zeros(N)
for each token q in query.lower().split():         # repeats included
    f   = count of q in each doc                   # (N,)
    df  = number of nonzero f
    idf = ln(1 + (N - df + 0.5) / (df + 0.5))      # scalar
    scores += idf * f * (k1 + 1) / (f + K)         # (N,)
return scores
```

Every line inside the loop is a scalar or an `(N,)` vector, so the broadcasting is simple: the scalar `idf` and `k1 + 1` spread over the `N` documents, and `f + K` adds two `(N,)` vectors element by element.

## 6. Build it one piece at a time

**Step 1: tokens, counts, lengths.**

```python
toks = [d.lower().split() for d in docs]
counts = [Counter(t) for t in toks]                 # N dicts, token -> count
N = len(docs)
dl = np.array([len(t) for t in toks], dtype=float)  # (N,)
```

A `Counter` returns 0 for a missing key, so `c[q]` never raises for unknown tokens.

**Step 2: the per-document length constant.**

```python
norm = k1 * (1 - b + b * dl / dl.mean())    # (N,)
```

It depends only on the document, so it's computed once and reused for every query token. `dl.mean()` includes zero-length documents.

**Step 3: one query token's contribution.**

```python
f = np.array([c[q] for c in counts], dtype=float)   # (N,)
df = np.count_nonzero(f)
idf = np.log(1 + (N - df + 0.5) / (df + 0.5))
scores += idf * f * (k1 + 1) / (f + norm)           # (N,)
```

Can `f + norm` be 0? Only when `b = 1` and the document is empty: then `norm = 0` and `f = 0`, and the term is `0 / 0 = nan`. The constraints allow that combination, but no test uses it, and the reference behaves the same way, so the spec doesn't ask you to special-case it. Every other document has `norm > 0`.

**Step 4: loop with repeats.**

```python
for q in query.lower().split():
    ...
```

An empty query yields no tokens, so `scores` stays all zeros.

## 7. Full solution

```python
# Counter gives per-document term counts with a default of 0 for missing tokens
from collections import Counter

# NumPy for the per-document vectors
import numpy as np


# docs: N strings, query: a string; returns (N,) BM25 scores in input order
def bm25_scores(docs: list, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
    # same tokeniser as the query: lowercase, split on whitespace, punctuation kept
    toks = [d.lower().split() for d in docs]
    # one token -> count map per document, so f(q, d) is a dictionary lookup
    counts = [Counter(t) for t in toks]
    # number of documents, including empty ones
    N = len(docs)
    # (N,) document lengths as floats for the ratio below
    dl = np.array([len(t) for t in toks], dtype=float)
    # (N,) k1 * (1 - b + b |d| / avgdl); avgdl averages over all N docs, empty ones too
    norm = k1 * (1 - b + b * dl / dl.mean())

    # (N,) running totals; an empty query leaves them at 0
    scores = np.zeros(N)
    # every query token, repeats included: a repeated token contributes again
    for q in query.lower().split():
        # (N,) count of this token in each document; Counter gives 0 when absent
        f = np.array([c[q] for c in counts], dtype=float)
        # number of documents that contain the token
        df = np.count_nonzero(f)
        # Lucene idf: the 1 + keeps it positive even for terms in most documents
        idf = np.log(1 + (N - df + 0.5) / (df + 0.5))
        # (N,) saturating tf part times idf; f = 0 adds exactly 0, so unknown tokens are harmless
        scores += idf * f * (k1 + 1) / (f + norm)
    # one score per document
    return scores
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0.6027, 0, 0, 0.8944]` | saturation and length; `cats` doesn't match `cat` |
| Example 2 | `[0.4616, 1.7167, 0, 0.4616]` | query lowercasing, two tokens, custom `k1` and `b` |
| repeated query term | `[1.8082, 0.8155, 0, 1.7888]` | `cat cat sat` counts `cat` twice |
| term in every doc | `[0.1335, 0.109, 0.1723]` | `df = N`: Lucene idf stays positive |
| majority df | `[0.274, 0.274, 0.3596, 1.7329, 0.3384]` | `df > N/2`, where Robertson goes negative |
| empty doc in corpus | `[1.5663, 0, 0.7617, 1.1363]` | `avgdl` includes the empty document |
| b = 0 | `[0.1335, 0.1908, 0.1335]` | length ignored: docs 0 and 2 tie despite different lengths |
| small k1 | `[0.9489, 0.9562, 1.0245]` | `k1 = 0.1`: tf saturates almost at once |
| empty query | `[0, 0]` | no tokens, no score |
| unknown terms | `[0.1823, 0.1823]` | `zzz` and `yyy` add 0 |
| random corpus | starts `[3.1816, 3.8299, ...]` | 60 documents of varied length, a repeated query token (`query`) |

## 9. Complexity

Tokenising and counting is $O(L)$ for $L$ total document tokens. Each of the $m$ query tokens then does $O(N)$ work, so scoring is $O(L + mN)$ time and $O(L)$ memory for the counters.

A search engine never scans all $N$ documents. It keeps an **inverted index**: for each term, the list of documents containing it with their counts, plus each document's length. A query token touches only its posting list, so the cost is the sum of the query terms' df values. Rare terms have short lists and high idf, which is also what lets engines skip low-scoring documents early (WAND, block-max WAND).

## 10. If you got Wrong Answer

- **Scores are negative or exactly 0 where they should be positive (Example 1 doc 0 gives `0` instead of `0.602737`).** You dropped the `1 +` from the idf (`wrong_robertson_idf.py`). With `df = N/2` the Robertson idf is `ln 1 = 0`.
- **Every score is a little too high; only "b = 0", "empty query" and "unknown terms" pass.** You left out length normalisation, `f + k1` in the denominator (`wrong_no_length_norm.py`).
- **Only "empty doc in corpus" fails (`1.7489` instead of `1.56631`).** You averaged lengths over non-empty documents (`wrong_avgdl_nonempty.py`).
- **"repeated query term" and "random corpus" are too low.** You deduplicated the query with `set` (`wrong_unique_query_terms.py`). `cat cat sat` gives `1.20547` instead of `1.80821` for doc 0.
- **Example 2 is wrong but Example 1 is right.** You didn't lowercase the query.

## 11. Follow-ups an interviewer might ask

- *How do you pick `k1` and `b`?* Tune them on labelled queries. `k1` in `[1.2, 2.0]` and `b = 0.75` are standard; short uniform texts like titles want a smaller `b`.
- *How do you combine BM25 with dense embeddings?* Scores live on different scales, so fuse ranks instead with reciprocal rank fusion (problem 154, hybrid-search-rrf).
- *What does BM25 miss?* Synonyms and paraphrases: "car" never matches "automobile". Dense retrieval (problem 84, top-k-cosine-retrieval) fills that gap; BM25 is better at exact identifiers, names and error codes.
- *What's BM25F?* A variant that weights fields differently (title, body, anchor text) by combining per-field term frequencies before saturation.
- *How would you return only the top 10?* `np.argpartition` on the scores, then sort those 10 (problem 9, top-k-per-row).
