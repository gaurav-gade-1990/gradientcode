## 1. What the problem is really asking

Retrieval hands you 10 to 20 candidate chunks. The prompt only has room for `budget` tokens of sources. Something has to decide what the model actually reads, and that something is the packer you're writing.

Strip the story and there are three passes, each a small classic:

1. **Near-duplicate removal.** Jaccard similarity on lowercase token sets, greedy in score order: the best copy survives and the rest point at it.
2. **A greedy knapsack.** Pick chunks by value per token (`score / cost`), with a per-document cap, and skip anything that doesn't fit instead of stopping.
3. **A stable re-sort for reading.** Score order is right for *choosing* and wrong for *reading*. Group by document and put each document's chunks back in their original order.

The judge compares four things: the `selected` ids in context order, every `dropped` entry with its reason, your `tokens` total, and the exact `context` string. It also re-counts the tokens of your context string itself (`measured_tokens`) and checks it's within the budget.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `chunks` | `{"chunk_id", "doc_id", "position", "score", "text"}` | the candidates |
| `position` | the chunk's order inside its doc | the final in-doc sort key |
| `budget` | max total cost of the selected blocks | the knapsack capacity |
| `max_per_doc` | max selected chunks from one doc | checked before the budget |
| `dedupe_threshold` | Jaccard at or above this is a duplicate | `>=`, not `>` |
| `count_tokens`, `tokenize` | the judge's tokenizer: words and single punctuation marks | cost and token sets |

Three details are easy to miss:

- **The cost is the whole rendered block.** `<source id="hr/expense-policy#0">` alone is 14 tokens: `<`, `source`, `id`, `=`, `"`, `hr`, `/`, `expense`, `-`, `policy`, `#`, `0`, `"`, `>`. The text "Employees are reimbursed for reasonable business expenses." is 8 tokens, but its block costs **26**. Budget only the text and you'll go over.
- **`duplicate_of` is the first kept chunk that matches**, in the order chunks were kept, not the most similar one.
- **The doc order uses the best *selected* score**, not the best score the doc had among the candidates. A doc whose top chunk got dropped is ranked by what made it in.

## 3. Trace Example 1 by hand

Five expense chunks, `budget = 90`, `max_per_doc = 3`, `dedupe_threshold = 0.8`.

**Costs and densities** (from running `count_tokens` on each block):

| chunk | score | text tokens | block cost | score / cost |
|---|---|---|---|---|
| hr/expense-policy#2 | 0.91 | 11 | 29 | 0.03138 |
| wiki-export/expense-policy-old#4 | 0.88 | 10 | 32 | 0.02750 |
| hr/expense-policy#0 | 0.84 | 8 | 26 | 0.03231 |
| hr/expense-policy#5 | 0.70 | 34 | 52 | 0.01346 |
| finance/travel-faq#1 | 0.62 | 13 | 31 | 0.02000 |

**Step 1: dedupe, by score descending.** `#2` is kept first. The old wiki export says "Submit receipts in Expensify within 30 days of purchase." against `#2`'s "...within 30 days of the purchase." Lowercased, the token sets share 10 tokens out of 11 in the union, so Jaccard is 10/11 = 0.9091 ≥ 0.8. It's dropped as `duplicate` of `hr/expense-policy#2`. The other three are kept.

**Step 2: select, by density descending.**

| order | chunk | cost | budget left before | result |
|---|---|---|---|---|
| 1 | hr/expense-policy#0 | 26 | 90 | select, 64 left |
| 2 | hr/expense-policy#2 | 29 | 64 | select, 35 left |
| 3 | finance/travel-faq#1 | 31 | 35 | select, 4 left |
| 4 | hr/expense-policy#5 | 52 | 4 | drop: `budget` |

Total `tokens` is 26 + 29 + 31 = **86**.

**Step 3: order.** The expense policy's best selected score is 0.91 and the travel FAQ's is 0.62, so the expense policy comes first. Inside it, `#0` (position 0) comes before `#2` (position 2), even though `#2` scored higher. Final `selected`: `['hr/expense-policy#0', 'hr/expense-policy#2', 'finance/travel-faq#1']`. `dropped`, sorted by `chunk_id`, is `#5` with `budget` and the wiki export with `duplicate`.

**The trickiest hidden case, "one per doc".** The on-call and leave chunks together, `max_per_doc = 1`, budget 400. In the leave doc, `hr/leave#0` scores 0.90 but costs 33 (density 0.02727), while `hr/leave#1` scores 0.85 and costs 29 (density 0.02931). Density order visits `hr/leave#1` first, so it takes the doc's only slot and `hr/leave#0` is dropped with `doc_cap`. Now the doc order: `hr/leave` and `hr/leave-faq` both have a best *selected* score of 0.85, so `doc_id` breaks the tie, and `"hr/leave"` sorts first. (If you had wrongly used its best candidate score, 0.90, it would still land second here, so no test catches that mistake. Follow the rule anyway.) The result is `['eng/oncall#1', 'hr/leave#1', 'hr/leave-faq#3', 'eng/sev-matrix#0', 'eng/postmortem-guide#0', 'benefits/overview#7']`.

## 4. Key idea: rank by density, and skip instead of stopping

Picking by raw score sounds natural. But one long, high-scoring chunk can eat the space that two short ones would share. "density beats raw score" shows it: the expense chunks plus a 24-token `finance/per-diem#0` at 0.66, with budget 110.

| strategy | picks | tokens |
|---|---|---|
| by `score / cost` | `#0`, `#2`, per-diem, travel FAQ | 110 |
| by raw score | `#2`, `#0`, `#5` (52 tokens), then nothing else fits | 107 |

Density gets four chunks in; raw score gets three, and one of them is the long meals policy.

`score / cost` is the classic greedy for the *fractional* knapsack. It isn't optimal for whole chunks, but it's fast, predictable and close. The second half of the rule matters just as much: when a chunk doesn't fit, record `budget` and **keep going**. In "smaller chunk fills the gap" the meals chunk (52) doesn't fit in the 24 tokens left after three picks, but the 23-token mileage chunk does, giving 109 tokens. A `break` at the first overflow leaves those 24 tokens empty.

## 5. Key idea: the dedupe threshold is inclusive, and case doesn't count

"case-insensitive dedupe" has two leave chunks that differ only in case and a trailing `!`: "Parental leave is 16 weeks..." and "PARENTAL LEAVE is 16 weeks...!". Lowercased, their sets share 12 of 14 tokens, Jaccard 0.8571, which is ≥ 0.85, so the 2024 copy is a duplicate. Without lowercasing, `Parental`/`PARENTAL` and `leave`/`LEAVE` are different tokens: 10 of 16, Jaccard 0.625, and both copies get in.

"dedupe threshold boundary" sets the threshold to 0.6. `hr/leave-faq#3` against `hr/leave#1` shares 12 of 20 tokens, exactly 0.6. With `>=` it's a duplicate. With `>` it would survive.

## 6. Plan before you code

```
dedupe:
    for c in chunks by (-score, chunk_id):
        toks = lowercase token set
        if Jaccard(toks, any kept set, in kept order) >= threshold:
            drop "duplicate", duplicate_of = first such kept chunk
        else keep c
select:
    cost[c] = count_tokens(render(c)) for kept c
    for c in kept by (-score/cost, -score, chunk_id):
        doc already has max_per_doc  -> drop "doc_cap"
        cost > budget left           -> drop "budget" (keep going)
        else select, subtract cost, count it for its doc
order:
    best[doc] = highest selected score
    sort selected by (-best[doc], doc_id, position)
return context, tokens, selected, dropped sorted by chunk_id
```

## 7. Build it one piece at a time

**Step 1: render a block.** One function, used for both the cost and the context string, so they can never disagree:

```python
def render(c):
    return '<source id="%s">\n%s\n</source>' % (c["chunk_id"], c["text"])
```

**Step 2: dedupe.** Keep the token sets in a list beside the kept chunks so you only tokenize each chunk once. The `break` on the first match is what makes `duplicate_of` the *first* kept match:

```python
    kept, kept_sets = [], []
    for c in sorted(chunks, key=lambda c: (-c["score"], c["chunk_id"])):
        toks = {t.lower() for t in tokenize(c["text"])}
        dup = None
        for k, s in zip(kept, kept_sets):
            if len(toks & s) / len(toks | s) >= dedupe_threshold:
                dup = k["chunk_id"]
                break
```

The union is never empty, because every chunk has non-empty text, so there's no division by zero.

**Step 3: select.** The cap check comes first. A chunk from a full doc is `doc_cap` even when it wouldn't have fit the budget either:

```python
    cost = {c["chunk_id"]: count_tokens(render(c)) for c in kept}
    left, per_doc, chosen = budget, {}, []
    for c in sorted(kept, key=lambda c: (-c["score"] / cost[c["chunk_id"]], -c["score"], c["chunk_id"])):
        if per_doc.get(c["doc_id"], 0) >= max_per_doc:
            ...  # doc_cap
        elif cost[c["chunk_id"]] > left:
            ...  # budget, and the loop continues
        else:
            ...  # select
```

The tie-breakers matter. `-score` second means two chunks with equal density go best-first, and `chunk_id` last makes the order total, so the result never depends on input order.

**Step 4: reorder for reading.** Compute each doc's best selected score, then one sort with three keys. `doc_id` sits between the score and the position so that two docs with the same best score don't interleave their chunks:

```python
    best = {}
    for c in chosen:
        best[c["doc_id"]] = max(best.get(c["doc_id"], c["score"]), c["score"])
    chosen.sort(key=lambda c: (-best[c["doc_id"]], c["doc_id"], c["position"]))
```

## 8. Full solution

```python
from gc_runtime import count_tokens, tokenize  # the judge's tokenizer, so our costs match its count


def render(c):  # the exact block the model sees, used for both cost and context
    return '<source id="%s">\n%s\n</source>' % (c["chunk_id"], c["text"])  # wrapper tags with a stable id


def pack_context(chunks, budget, max_per_doc, dedupe_threshold):  # dedupe, select, then order for reading
    dropped = []  # one entry per chunk that doesn't make it in, whatever the reason

    kept, kept_sets = [], []  # survivors of dedupe, and their token sets in the same order
    for c in sorted(chunks, key=lambda c: (-c["score"], c["chunk_id"])):  # best first, so the best copy survives
        toks = {t.lower() for t in tokenize(c["text"])}  # lowercase so case-only copies match
        dup = None  # the first kept chunk this one duplicates, if any
        for k, s in zip(kept, kept_sets):  # compare against kept chunks in the order they were kept
            if len(toks & s) / len(toks | s) >= dedupe_threshold:  # Jaccard at or over the threshold
                dup = k["chunk_id"]  # remember which kept chunk it copies
                break  # the first match wins, so stop looking
        if dup is None:  # nothing kept is close enough
            kept.append(c)  # it survives dedupe
            kept_sets.append(toks)  # and later chunks are compared against it
        else:  # a near-copy of something better
            dropped.append({"chunk_id": c["chunk_id"], "reason": "duplicate", "duplicate_of": dup})  # point at the original

    cost = {c["chunk_id"]: count_tokens(render(c)) for c in kept}  # cost includes the wrapper tags
    left, per_doc, chosen = budget, {}, []  # tokens remaining, selected count per doc, the picks
    # most value per token first; ties go to the higher score, then the smaller id
    for c in sorted(kept, key=lambda c: (-c["score"] / cost[c["chunk_id"]], -c["score"], c["chunk_id"])):
        if per_doc.get(c["doc_id"], 0) >= max_per_doc:  # this doc already has its share
            dropped.append({"chunk_id": c["chunk_id"], "reason": "doc_cap", "duplicate_of": None})  # one doc can't crowd out the rest
        elif cost[c["chunk_id"]] > left:  # it doesn't fit in what's left
            dropped.append({"chunk_id": c["chunk_id"], "reason": "budget", "duplicate_of": None})  # skip it, a smaller one may still fit
        else:  # within the cap and the budget
            chosen.append(c)  # select it
            left -= cost[c["chunk_id"]]  # spend its tokens
            per_doc[c["doc_id"]] = per_doc.get(c["doc_id"], 0) + 1  # count it toward its doc's cap

    best = {}  # each doc's highest selected score, which decides the doc order
    for c in chosen:  # only selected chunks count toward a doc's rank
        best[c["doc_id"]] = max(best.get(c["doc_id"], c["score"]), c["score"])  # keep the maximum
    chosen.sort(key=lambda c: (-best[c["doc_id"]], c["doc_id"], c["position"]))  # best doc first, each doc in reading order
    return {  # the packed context and its bookkeeping
        "context": "\n\n".join(render(c) for c in chosen),  # blank-line joins cost no tokens
        "tokens": sum(cost[c["chunk_id"]] for c in chosen),  # total cost of the selected blocks
        "selected": [c["chunk_id"] for c in chosen],  # ids in context order
        "dropped": sorted(dropped, key=lambda d: d["chunk_id"]),  # sorted so the output is deterministic
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 3 selected, 86 tokens; wiki export `duplicate`, meals `budget` | all three passes, wrapper cost, reading order inside a doc |
| Example 2 | `eng/oncall#1`, `#4`, sev matrix, postmortem; `#2` and `#3` `doc_cap`; 102 tokens | the cap runs before the budget and frees room for other docs |
| case-insensitive dedupe | `hr/leave-2024#0` duplicate of `hr/leave#0` (12/14) | lowercase token sets |
| dedupe threshold boundary | `hr/leave-faq#3` duplicate of `hr/leave#1` at exactly 0.6 | `>=` in the Jaccard test |
| no dedupe at 1.0 | all 5 selected, 170 tokens | near-copies survive when only identical sets count |
| smaller chunk fills the gap | mileage selected after meals is skipped; 109 tokens | continue after an overflow |
| budget below every chunk | nothing selected, all six `budget`, 0 tokens | the cheapest block costs 23 > 12 |
| density beats raw score | per-diem and travel FAQ in, meals out; 110 tokens | `score / cost`, not `score` |
| one per doc | `hr/leave#1` over `hr/leave#0`; `hr/leave` before `hr/leave-faq` | density decides which chunk takes a doc's only slot |
| everything fits, reading order | on-call `#1`..`#4` in position order, 164 tokens | the final sort by `position` |
| single chunk | `['hr/expense-policy#2']`, 29 tokens | the smallest input |

## 10. Complexity

Dedupe compares each chunk with every kept chunk: O(n² · t) for n chunks of about t tokens. Sorting is O(n log n). Counting costs is O(n · t). With 40 chunks that's nothing.

At production scale, pairwise Jaccard stops being cheap once you have hundreds of candidates. MinHash with locality-sensitive hashing finds near-duplicates in roughly linear time. The bigger production win is the budget itself: count tokens with the target model's tokenizer (Anthropic's token-counting endpoint, or `tiktoken`), and leave headroom for the system prompt, the conversation and the answer.

## 11. If you got Wrong Answer

- **`tokens` is lower than expected on every case, and `measured_tokens` is higher than `tokens`.** You costed only the text. Cost `render(c)`. This fails every case, even "single chunk" (11 instead of 29).
- **"case-insensitive dedupe" selects both leave copies.** You built the token set without `.lower()`. It also breaks "one per doc".
- **"dedupe threshold boundary" keeps `hr/leave-faq#3`.** You used `>` instead of `>=`.
- **Example 2 selects `eng/oncall#3` instead of `#4`, or "density beats raw score" picks the meals chunk.** You sorted by raw score. Use `score / cost`.
- **"smaller chunk fills the gap" drops the mileage chunk with `budget`.** You stopped at the first chunk that didn't fit. Record the drop and continue.
- **`selected` is right as a set but in the wrong order.** You left the context in score order. Example 1 expects `#0` before `#2`, and "everything fits, reading order" expects the on-call steps 1 to 4.

## 12. Follow-ups an interviewer might ask

- *Is greedy by density optimal?* Not for whole chunks: it's a 0/1 knapsack. With 20 candidates and a small budget you could run the exact dynamic program over budget, but greedy is predictable, fast and usually within a chunk of optimal, so most systems use it.
- *Where should the best document go in a long context?* "Lost in the middle" (Liu et al., 2023) found models use the start and end of a long context best. Some teams put the best doc first and the second best last. Whatever you choose, keep it deterministic so evals are comparable.
- *Why wrap each chunk in tags with an id?* Citations and grounded-answer checks depend on a stable id (problem 158, grounded-answer-check), and clear boundaries help the model treat retrieved text as data, not instructions (problem 118).
- *How does this fit with the rest of the prompt budget?* The sources budget is what's left after the system prompt, the conversation and room for the answer. Problem 107 (memory-under-token-budget) budgets the conversation side.
- *What's off the shelf?* LangChain's `EmbeddingsRedundantFilter` and `LongContextReorder`, and LlamaIndex's node postprocessors, implement the dedupe and reorder passes.
