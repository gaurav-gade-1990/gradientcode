Your HR policy assistant answers employee questions from retrieved policy passages and cites them as `[1]`, `[2]`, ... Legal wants every production answer checked before it is shown: does each sentence cite something, does the citation exist, and does the cited passage actually contain the claim?

`check_citations(answer, passages, stopwords, tau)` takes the model's answer string, the list of retrieved passage strings (citation `[n]` refers to `passages[n - 1]`), a list of stopwords, and a support threshold `tau`.

**Sentences.** `re.split(r"(?<=[.!?])\s+", answer.strip())`, dropping empty strings. Sentence indices start at 0.

**Citations.** In each sentence, `re.findall(r"\[(\d+)\]", sentence)` as integers. Keep the first occurrence of each number, in order.

**Tokens.** For a sentence, first replace every `[n]` marker with a space. Then for sentences and passages alike: `gc_runtime.tokenize(text)`, lowercase each token, keep tokens that fully match `\w+` (drop punctuation), and drop any token in `stopwords` (compared lowercase). The **claim set** $C$ of a sentence and the **passage set** $P$ of a passage are sets of these tokens.

**Overlap.** For an in-range citation $n$, $\text{overlap} = \lvert C \cap P_n\rvert / \lvert C\rvert$.

| sentence | status | issues added |
|---|---|---|
| $C$ is empty (e.g. "Thanks!") | `no_claim` | none, citations are ignored |
| $C$ non-empty, no citations | `uncited` | one `missing` with `citation: None` |
| otherwise, for each citation $n$ in order | | `out_of_range` if $n < 1$ or $n >$ `len(passages)`; `unsupported` if overlap < `tau` |
| | `supported` if any in-range citation has overlap $\ge$ `tau`, else `unsupported` | |

Return:

```python
{
  "sentences": [{"citations": [2, 5], "overlap": [0.75, None], "status": "supported"}, ...],
  "issues": [{"sentence": 0, "citation": 5, "issue": "out_of_range"}, ...],
  "supported_rate": 0.5,
}
```

- `overlap` is aligned with `citations`: a float for in-range citations, `None` for out-of-range ones. For `no_claim` and `uncited` sentences, `citations` holds what was found and `overlap` is an empty list.
- `issues` are ordered by sentence, then by citation order within the sentence.
- `supported_rate` is the number of `supported` sentences divided by the number of sentences whose status is not `no_claim`, or `1.0` if there are none.

**Constraints**

- `0 < tau <= 1`; up to 40 sentences and 20 passages
- Import `tokenize` from `gc_runtime`; don't write your own tokenizer
