## 1. What the problem is really asking

Plain top-k retrieval (problem 84, top-k-cosine-retrieval) often returns five chunks that say the same thing: the same paragraph from three versions of a document, or overlapping windows from a chunker. In a RAG prompt that wastes context and gives the model less to work with. MMR re-ranks the candidates so that each new pick is close to the query **and** far from what's already been picked.

Under the story this is **a greedy selection loop over a precomputed similarity matrix**, with one running array that tracks each document's worst-case redundancy. Each round is one vector expression and one `argmax`.

The judge compares the array of selected indices, in order, exactly. One different pick at any step changes everything after it, so the tie rule and the exact scoring formula both matter.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `query` | `(d,)` | the query embedding | relevance `rel = cos(q, d_j)` |
| `docs` | `(n, d)` | candidate embeddings | relevance, and doc-doc similarity |
| `k` | int, `1 <= k <= n` | how many to select | number of greedy rounds |
| `lam` | float in `[0, 1]` | relevance weight | `lam · rel − (1 − lam) · redundancy` |
| return | `(k,)` int | indices in **selection order** | not sorted |

The details that are easy to miss:

- **`lam` weights relevance**, and `1 - lam` weights redundancy. `lam = 1` is plain ranking.
- **The penalty is a max, not a sum.** A document is redundant if it's close to **any** selected document.
- **Similarities can be negative.** The max over the selected set can be below 0, which makes the penalty a **bonus**. Starting a running max at 0 hides that.
- **Zero vectors** have similarity 0 to everything, including the query.

## 3. The math

Write $r_j = \cos(q, d_j)$ for relevance and $M_{jl} = \cos(d_j, d_l)$ for the doc-doc matrix, $M \in \mathbb{R}^{n \times n}$, symmetric, with $M_{jj} = 1$ for nonzero docs. With unit rows $\hat D$ (zero rows left at zero),

$$r = \hat D\, \hat q \in \mathbb{R}^n, \qquad M = \hat D \hat D^\top \in \mathbb{R}^{n \times n}.$$

**The objective.** Given the selected set $S$, each remaining document $j$ scores

$$\text{MMR}(j) = \lambda\, r_j - (1 - \lambda)\, \rho_j(S), \qquad \rho_j(S) = \max_{s \in S} M_{js},$$

and $\rho_j(\varnothing) = 0$ by the spec's convention. Pick $j^* = \arg\max_{j \notin S} \text{MMR}(j)$, lowest index on ties, and set $S \leftarrow S \cup \{j^*\}$.

**The extremes.**

- $\lambda = 1$: $\text{MMR}(j) = r_j$, so the order is plain relevance ranking.
- $\lambda = 0$: $\text{MMR}(j) = -\rho_j(S)$. The first pick is the lowest-index document (every score is 0, a tie). After that, each pick is the document **least** similar to everything selected. The query is ignored.

**The incremental update.** Recomputing $\rho_j$ from scratch costs $O(|S|)$ per document per round. But a max over a growing set updates in one step:

$$\rho_j(S \cup \{j^*\}) = \max\Big(\max_{s \in S} M_{js},\ M_{j j^*}\Big) = \max\big(\rho_j(S),\ M_{jj^*}\big).$$

That holds for any non-empty $S$. For the **first** pick, $S$ is empty, and $\max(\rho_j(\varnothing), M_{jj^*}) = \max(0, M_{jj^*})$ would be wrong whenever $M_{jj^*} < 0$: the true value is $\rho_j(\{j^*\}) = M_{jj^*}$. So after the first pick you **set** $\rho = M_{j^*}$, and only after later picks do you take the element-wise max.

**Why a negative penalty matters.** If a document points away from everything selected, $\rho_j < 0$ and $-(1 - \lambda)\rho_j > 0$: it gets a bonus for adding something new. Clipping $\rho$ at 0 removes that bonus and changes the picks (see "negative similarities" below).

## 4. Trace an example by hand

**Example 1:** query `[1, 0]`, `k = 3`, `lam = 0.5`.

```python
docs = [[1.0, 0.1],     # doc 0
        [1.0, 0.12],    # doc 1, nearly a copy of doc 0
        [0.6, 0.8],     # doc 2
        [0.0, 1.0]]     # doc 3
```

Relevance `r = [0.995, 0.9929, 0.6, 0]`. The relevant rows of `M`:

| | doc 0 | doc 1 | doc 2 | doc 3 |
|---|---|---|---|---|
| `M[0]` | `1` | `0.9998` | `0.6766` | `0.0995` |
| `M[1]` | `0.9998` | `1` | `0.691` | `0.1191` |

| round | `max_sim` before | scores `0.5·r − 0.5·max_sim` | pick |
|---|---|---|---|
| 1 | `[0, 0, 0, 0]` | `[0.4975, 0.4964, 0.3, 0]` | 0 |
| 2 | `M[0] = [1, 0.9998, 0.6766, 0.0995]` | `[-inf, -0.0035, -0.0383, -0.0498]` | 1 |
| 3 | `max(M[0], M[1]) = [1, 1, 0.691, 0.1191]` | `[-inf, -inf, -0.0455, -0.0596]` | 2 |

The answer is `[0, 1, 2]`. Doc 1 is nearly a duplicate of doc 0, but at `lam = 0.5` its relevance edge over doc 2 (`0.9929` against `0.6`) is still bigger than its extra redundancy (`0.9998` against `0.6766`). It's easy to assume the near-duplicate always loses; at this `lam` it doesn't. Lower `lam` to `0.4` and the second pick becomes doc 3, the document least like doc 0.

**The hidden case "negative similarities"** (`lam = 0.3`) shows why the first update is a copy, not a max. Doc 0 (`[1, 0]`) is picked first. Docs 1 and 2 point the other way, with `M[0, 1] = M[0, 2] = -0.9806`.

| round 2 | `max_sim[1]` | score of doc 1 | score of doc 3 | pick |
|---|---|---|---|---|
| correct, `max_sim = M[0]` | `-0.9806` | `0.3·(-0.9806) − 0.7·(-0.9806) = 0.3922` | `0` | 1 |
| clipped, `max(0, M[0])` | `0` | `-0.2942` | `0` | 3 |

The expected picks are `[0, 1, 4, 3]`. Clipping gives doc 3 at step 2.

**The hidden case "exact duplicates tie"** has docs `[0, 1], [1, 0], [0, 1], [1, 0], [2, 2]` and query `[1, 1]`. Doc 4 goes first (relevance 1). Then all four others tie at `0.1414`, and the lowest index, 0, wins. Then docs 1 and 3 tie and 1 wins. Expected `[4, 0, 1, 2, 3]`.

## 5. Plan before you code

```
D   = unit rows of docs (zero rows stay zero)        # (n, d)
rel = D @ unit(query)                                # (n,)
sim = D @ D.T                                        # (n, n)
max_sim = zeros(n);  chosen = all False;  picks = []
repeat k times:
    score = lam * rel - (1 - lam) * max_sim          # (n,)
    score[chosen] = -inf
    j = argmax(score)                                # first max on ties
    record j; mark chosen
    max_sim = sim[j] if first pick else maximum(max_sim, sim[j])
return picks
```

## 6. Build it one piece at a time

**Step 1: a safe normaliser that works for a vector or a matrix.**

```python
def _unit(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)    # (n, 1) for docs, (1,) for the query
    return x / np.where(n == 0, 1.0, n)
```

`axis=-1` with `keepdims=True` handles both shapes: for `docs` (`(n, d)`) it divides each row by its own norm, and for `query` (`(d,)`) it divides by a `(1,)` array, which broadcasts as a scalar.

**Step 2: precompute everything the loop needs.**

```python
D = _unit(docs)          # (n, d)
rel = D @ _unit(query)   # (n, d) @ (d,) -> (n,)
sim = D @ D.T            # (n, n), symmetric
```

**Step 3: score, mask, pick.**

```python
score = lam * rel - (1 - lam) * max_sim     # (n,)
score[chosen] = -np.inf                      # boolean mask: never pick twice
j = int(np.argmax(score))                    # first maximum, so lowest index on ties
```

`np.argmax` returns the first index among equal maxima, which is exactly the tie rule. `-np.inf` beats any real penalty, so a selected document can't come back even when every remaining score is very negative.

**Step 4: update the running redundancy.**

```python
max_sim = sim[j] if len(picks) == 1 else np.maximum(max_sim, sim[j])   # (n,)
```

`sim[j]` is row `j`, the similarity of every document to the new pick. `np.maximum` is element-wise between two `(n,)` arrays.

## 7. Full solution

```python
# NumPy for the normalisation, similarity matrices and argmax
import numpy as np


# Scale rows (or a single vector) to unit length; zero vectors stay zero, so their cosines are 0.
def _unit(x):
    # norm along the last axis; keepdims so (n, d) divides by (n, 1) and (d,) by (1,)
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    # divide by 1 where the norm is 0 instead of producing nan
    return x / np.where(n == 0, 1.0, n)


# query: (d,), docs: (n, d); returns the k selected indices in selection order
def mmr(query: np.ndarray, docs: np.ndarray, k: int, lam: float = 0.5) -> np.ndarray:
    D = _unit(docs)  # (n, d) unit rows, so dot products are cosines
    rel = D @ _unit(query)  # (n,) relevance of each document to the query
    sim = D @ D.T  # (n, n) doc-doc cosine similarities, computed once
    n = len(docs)  # number of candidates
    # (n,) max similarity to anything selected; 0 is the spec's value for the empty set
    max_sim = np.zeros(n)
    chosen = np.zeros(n, dtype=bool)  # (n,) which documents are already picked
    picks = []  # selected indices, in the order they were chosen
    # one greedy round per selected document
    for _ in range(k):
        # (n,) lam weights relevance, 1 - lam weights redundancy
        score = lam * rel - (1 - lam) * max_sim
        score[chosen] = -np.inf  # a picked document can never win again
        j = int(np.argmax(score))  # first maximum, so ties go to the lowest index
        picks.append(j)  # record the pick in selection order
        chosen[j] = True  # exclude it from later rounds
        # first pick: copy its row (a max with the initial 0 would clip negative similarities);
        # later picks: the max over S grows by one element, so an element-wise max is enough
        max_sim = sim[j] if len(picks) == 1 else np.maximum(max_sim, sim[j])
    # integer indices, shape (k,)
    return np.array(picks, dtype=int)
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 1, 2]` | the basic loop; relevance still beats redundancy at `lam = 0.5` |
| Example 2 | `[0, 1, 2]` | `lam = 1`: plain relevance order |
| lam = 0 | `[0, 2, 4, 1, 5]` | pure diversity; the first pick is index 0 by the tie rule |
| negative similarities | `[0, 1, 4, 3]` | the first update copies `sim[j]`, so negative similarities give a bonus |
| exact duplicates tie | `[4, 0, 1, 2, 3]` | several exact ties, broken by lowest index |
| zero vector doc | `[3, 2, 0, 4, 1]` | the zero doc scores 0 throughout and beats negative scores |
| near duplicates | `[6, 1, 5, 0, 2, 4]` | docs 5 and 6 are noisy copies of doc 0; at `lam = 0.7` relevance still dominates, so copies 6, 5 and 0 are all picked |
| k = 1 | one index | MMR with `k = 1` is just the most relevant doc |
| low lambda random, larger pool | 12 and 20 picks | diversity-heavy and relevance-heavy at size |

## 9. Complexity

Normalising is $O(nd)$, relevance is $O(nd)$, and the doc-doc matrix is $O(n^2 d)$ time and $O(n^2)$ memory. The loop runs $k$ rounds of $O(n)$ work, so $O(kn)$. Total $O(n^2 d + kn)$.

In a pipeline you never run MMR over the whole corpus. A first-stage retriever returns the top 50 to 200 candidates, and MMR picks 5 to 10 of those, so $n^2$ is tiny. If $n$ were large, you could skip the full matrix and compute only `D @ D[j]` after each pick, which is $O(knd)$ time and $O(n)$ memory.

## 10. If you got Wrong Answer

- **"negative similarities", "zero vector doc" and "low lambda random" fail; the rest pass.** You started `max_sim` at 0 and took `np.maximum` from the first pick (`wrong_max_starts_at_zero.py`). That clips the empty-set max at 0. In "negative similarities", step 2 picks 3 instead of 1.
- **Example 1's third pick is 3 instead of 2.** You summed the similarities to the selected set (`wrong_sum_redundancy.py`). The penalty grows with every pick and overwhelms relevance.
- **Example 2 (`lam = 1`) gives `[0, 3, ...]`.** You swapped `lam` and `1 - lam` (`wrong_lambda_swapped.py`). At `lam = 1`, the swapped version scores only redundancy.
- **The visible examples pass but "near duplicates" and "larger pool" pick different documents.** You used raw dot products instead of cosines (`wrong_dot_product.py`). Long vectors look more relevant and more redundant.
- **A document is picked twice.** You forgot to mask chosen documents with `-np.inf`.

## 11. Follow-ups an interviewer might ask

- *How do you choose `lam`?* Tune it on retrieval evaluations; 0.5 to 0.7 is common. Lower it when sources are known to overlap heavily (multiple versions of the same document).
- *Is greedy MMR optimal?* No. Finding the best set exactly is NP-hard. Greedy is fast and works well; related objectives that are submodular, such as facility location, come with a $(1 - 1/e)$ approximation guarantee for greedy.
- *What other diversity methods exist?* Determinantal point processes, which score the volume spanned by the selected embeddings, and clustering the candidates and taking one per cluster.
- *Where does MMR sit in a RAG pipeline?* After first-stage retrieval (problem 84 or hybrid search, problem 154) and usually after a cross-encoder rerank, just before packing chunks into the prompt (problem 157, context-packing).
- *Can you avoid the `(n, n)` matrix?* Yes: compute `D @ D[j]` once per pick. That's $O(nd)$ per round and $O(n)$ memory.
