## 1. What the problem is really asking

Two retrievers search the same help-desk corpus. BM25 matches exact terms: error codes, ticket ids, product names. The vector index matches meaning: "can't get on the VPN" finds "remote access setup". Each is good where the other is weak, so you run both and merge their rankings into one list.

The catch is that their scores aren't comparable. BM25 scores run from 0 to 50 or so, depending on the query and the corpus; cosine similarities sit between 0 and 1. Adding them lets BM25 drown out the vector index. **Reciprocal rank fusion** sidesteps that by throwing the scores away and using only each hit's **position** in its list:

$$
\text{score}(c) = \frac{w_{\text{bm25}}}{k + r_{\text{bm25}}(c)} + \frac{w_{\text{vector}}}{k + r_{\text{vector}}(c)}
$$

Under the story, this is **a dictionary merge plus one sort with a three-part key**. The driver records both retriever calls and their `limit`, then compares the fused list: ids, scores, both ranks and the order. So fetching the wrong number of candidates or breaking ties differently both fail.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `bm25(query, limit)` | returns `[{chunk_id, doc_id, score}]`, best first | call once with `candidates` |
| `vector(query, limit)` | returns `[{chunk_id, doc_id, similarity}]`, best first | call once with `candidates`, after BM25 |
| `top_n` | how many fused results to return | cut **after** fusing |
| `candidates` | how deep to fetch from each retriever | the `limit` you pass |
| `k` | the RRF rank constant (60 by default) | larger `k` flattens the difference between ranks |
| `weights` | `{"bm25": w, "vector": w}`, keys optional | a missing key or `None` means 1.0 |

Three details are easy to miss:

- **Ranks are 1-based list positions.** The top hit contributes `w / (k + 1)`, not `w / k`.
- **A duplicate keeps its first rank, and still occupies its slot.** If two shards return the same chunk, ignore the second copy, but don't shift the hits after it up. In "duplicate hits count once", BM25 returns `expense-policy#2` at positions 1 and 2, so `travel-policy#1` is still rank 3.
- **Fetch `candidates`, not `top_n`.** A chunk ranked 4th in both lists can beat a chunk ranked 1st in only one, but only if you fetched deep enough to see it.

## 3. Trace Example 1 by hand

Query "how do I reset my VPN password", `k = 60`, both weights 1, `candidates = 4`, `top_n = 3`.

| chunk | BM25 rank | vector rank | score |
|---|---|---|---|
| it-wiki/vpn-setup#3 | 1 | 2 | 1/61 + 1/62 = 0.032522 |
| it-wiki/password-policy#1 | 3 | 1 | 1/63 + 1/61 = 0.032266 |
| tickets/INC-20417#1 | 2 | | 1/62 = 0.016129 |
| it-wiki/sso-faq#2 | | 3 | 1/63 = 0.015873 |
| it-wiki/vpn-setup#1 | 4 | | 1/64 = 0.015625 |
| tickets/INC-19920#2 | | 4 | 1/64 = 0.015625 |

The top 3 are `vpn-setup#3`, `password-policy#1` and `INC-20417#1`. The two chunks both retrievers agree on rise to the top, even though neither is first in both lists. That's what fusion is for. `password-policy#1` has BM25 score 9.5 and similarity 0.83, but neither number appears anywhere in the calculation.

**Example 2 adds weights.** The query is an error code, so `weights = {"bm25": 2.0}`, and vector keeps the default 1.0. `payments-api#4` is rank 2 in both lists: `2/62 + 1/62 = 0.048387`. `INC-30551#1`, BM25 rank 1 only, gets `2/61 = 0.032787`. `payments-api#2`, vector rank 1 only, drops to last at `1/61 = 0.016393`.

## 4. Key idea: why ranks, not scores

In "raw scores ignored", BM25 puts keyword-spam chunks first with scores 48.0 and 47.5, and the genuinely relevant `laptop-refresh#1` third with 3.0. The vector index ranks `laptop-refresh#1` first at 0.92. Summing raw scores gives:

| chunk | raw sum | RRF score |
|---|---|---|
| wiki/glossary#9 | 48.0 | 0.016393 |
| wiki/onboarding#2 | 47.5 + 0.40 = 47.9 | 0.032258 |
| wiki/laptop-refresh#1 | 3.0 + 0.92 = 3.92 | 0.032266 |
| wiki/hardware-catalog#3 | 0.35 | 0.015873 |

With raw sums the vector index barely matters. With RRF, `laptop-refresh#1` (ranks 3 and 1) edges out `onboarding#2` (ranks 2 and 2) and the glossary spam drops to third. Ranks put both retrievers on the same scale without any calibration.

## 5. Key idea: a deterministic tie-break

Equal RRF scores are common: any chunk at rank 1 in one list and absent from the other scores `1/61`, whichever list it came from. If ties fall back to dictionary insertion order, the result depends on which retriever answered first. That makes evals flaky and cache keys unstable. The spec fixes a total order:

1. score, descending;
2. **best rank** (the smaller of the two ranks), ascending: a chunk that some retriever put near the top beats one that was mediocre in both;
3. `chunk_id`, ascending, as the final tie-break.

In "tie broken by chunk_id", `kb/zz-badge#1` (BM25 rank 1) and `kb/aa-badge#1` (vector rank 1) both score `0.016393` with best rank 1, so `aa` comes first. In "duplicate hits count once", `expense-policy#2` (ranks 1 and 4) and `per-diem-table#1` (ranks 4 and 1) both score `0.032018`; both have best rank 1, and `expense-policy` sorts first by id.

## 6. Plan before you code

```
lists = [("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))]
fused = {}
for name, hits in lists:
    w = weights.get(name, 1.0); seen = set()
    for pos, hit in enumerate(hits, start=1):
        skip if chunk already seen in this list
        row = fused[chunk] (create with doc_id, score 0, both ranks None)
        row[name_rank] = pos; row.score += w / (k + pos)
sort by (-score, best rank, chunk_id); return first top_n
```

| situation | effect |
|---|---|
| chunk in both lists | two terms, both ranks set |
| chunk in one list | one term, the other rank `None` |
| duplicate within a list | ignored, but its position still counts for the hits after it |
| a retriever returns `[]` | its terms are all 0 |

## 7. Build it one piece at a time

**Step 1: call the retrievers in order, once each.** Build the list before looping, so the call order is explicit:

```python
weights = weights or {}
lists = [("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))]
```

`weights or {}` handles `None`, and `.get(name, 1.0)` handles a missing key.

**Step 2: one pass per list, with a per-list `seen` set.** `enumerate(hits, 1)` gives 1-based positions, and `continue` on a duplicate skips it without renumbering the rest:

```python
for name, hits in lists:
    w = weights.get(name, 1.0)
    seen = set()
    for pos, hit in enumerate(hits, 1):
        cid = hit["chunk_id"]
        if cid in seen:
            continue
        seen.add(cid)
```

The `seen` set is per list. A chunk appearing once in each list is exactly the case that should get two terms.

**Step 3: accumulate.** `setdefault` creates the row on first sight, so `doc_id` comes from the first occurrence, and BM25 is processed first, so its term is added first:

```python
        row = fused.setdefault(cid, {"chunk_id": cid, "doc_id": hit["doc_id"], "score": 0.0,
                                     "bm25_rank": None, "vector_rank": None})
        row[name + "_rank"] = pos
        row["score"] += w / (k + pos)
```

**Step 4: sort with the full key and cut.** Every row has at least one rank, so `min` over the non-`None` ranks is always defined.

## 8. Full solution

```python
def hybrid_search(query, bm25, vector, top_n, candidates=50, k=60, weights=None):  # fuse two rankings with weighted RRF
    weights = weights or {}  # None means every weight is 1.0
    # BM25 first, then vector, each asked for the deep candidate pool
    lists = [("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))]
    fused = {}  # chunk_id -> fused row
    for name, hits in lists:  # BM25 terms are added before vector terms
        w = weights.get(name, 1.0)  # a missing key means weight 1.0
        seen = set()  # chunks already counted in this list
        for pos, hit in enumerate(hits, 1):  # 1-based list position is the rank
            cid = hit["chunk_id"]  # the unit being ranked
            if cid in seen:  # a second shard returned the same chunk
                continue  # ignore the copy; later hits keep their positions
            seen.add(cid)  # first occurrence wins
            # create the row on first sight, so doc_id comes from the first occurrence
            row = fused.setdefault(cid, {"chunk_id": cid, "doc_id": hit["doc_id"], "score": 0.0,
                                         "bm25_rank": None, "vector_rank": None})
            row[name + "_rank"] = pos  # record this list's rank
            row["score"] += w / (k + pos)  # reciprocal rank term; the raw score is never used

    def best_rank(r):  # the chunk's best position in either list
        return min(x for x in (r["bm25_rank"], r["vector_rank"]) if x is not None)  # at least one rank always exists

    ranked = sorted(fused.values(), key=lambda r: (-r["score"], best_rank(r), r["chunk_id"]))  # deterministic total order
    return ranked[:top_n]  # cut only after fusing the full candidate pools
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | vpn-setup#3, password-policy#1, INC-20417#1 | basic RRF; raw scores ignored |
| Example 2 | payments-api#4 first at 0.048387 | a BM25 weight of 2, the vector default of 1 |
| duplicate hits count once | expense-policy#2 at 0.032018, tied with per-diem-table#1 | first occurrence only; slots preserved; id tie-break |
| raw scores ignored | laptop-refresh#1 first | ranks, not 48.0 + 0.92 |
| candidates deeper than top_n | kb/sla#1, kb/sla#7, kb/sla#8 | fetch 8, not 3; chunks deep in both lists win |
| tie broken by chunk_id | kb/aa-badge#1 before kb/zz-badge#1 | equal score and best rank, so sort by id |
| tie broken by best rank | hr/benefits#1 to #3 | `k = 10` and a vector weight of 2 |
| vector index empty | the BM25 order, one term each | an empty list adds nothing |
| both empty | `[]` | nothing to fuse |
| fewer results than top_n | 5 results with `top_n = 10`; payments-api#2 before INC-30551#1 at 0.5 | return what exists; id tie-break with `k = 1` |

## 10. Complexity

With `C = candidates`, fusion is O(C) dictionary work per list and the sort is O(C log C), at most 200 items here. The real cost is the two retriever calls, which you could run in parallel. The spec only fixes the order you *call* them in, for the judge's recording.

In production the knob that matters is `candidates` (Elasticsearch calls it `rank_window_size`). Deeper pools give better fusion but cost more retrieval and more reranking downstream. 50 to 100 is typical, followed by a cross-encoder reranker on the top 20 to 50 before packing the prompt.

## 11. If you got Wrong Answer

- **Example 1's scores are 0.033060, 0.032796 and 0.016393.** Your ranks are 0-based in the formula: the top hit is `w / (k + 1)`, not `w / k`.
- **"raw scores ignored" puts `wiki/glossary#9` first with score 48.0.** You're adding raw scores and similarities.
- **"duplicate hits count once" gives `expense-policy#2` 0.048147.** You counted both shard copies.
- **"candidates deeper than top_n" returns `kb/escalation#1` and `kb/sla#2`, and the call log shows `limit = 3`.** You fetched `top_n` instead of `candidates`.
- **"tie broken by chunk_id" puts `zz` before `aa`.** Your sort only uses the score, so ties fall back to insertion order.
- **Example 2's `payments-api#2` scores 0 and `INC-30551#1` moves to the top.** You treated a missing weight key as 0 instead of 1.0.

## 12. Follow-ups an interviewer might ask

- *Why `k = 60`?* It's the constant from the original RRF paper (Cormack et al., 2009), and the default in Elasticsearch, OpenSearch and most vector databases. A larger `k` flattens the curve, so being rank 1 versus rank 5 matters less.
- *When would you change the weights?* Per query. A query that looks like an error code, ticket id or SKU gets more BM25 weight; a natural-language question gets more vector weight. A small classifier or a regex can choose.
- *RRF gives you a candidate list. What comes next?* A cross-encoder reranker (Cohere Rerank, Voyage, bge-reranker) on the top 20 to 50, then context packing with deduplication (problem 157).
- *Where do document permissions fit?* Before either retriever runs (problem 155, acl-aware-retrieval). Fusing first and filtering afterwards can leak restricted titles and leaves you short of results.
- *Why does chunking matter here?* Both retrievers rank chunks, so chunk boundaries decide what can be found. Overlapping chunks (problem 153, recursive-chunker) can return two neighbors of the same passage, which fusion then ranks side by side.
