## Approach

This is the cheap, deterministic first line of a hallucination monitor: it runs on every answer in milliseconds, and an LLM judge only looks at what it flags. The work is careful bookkeeping in four steps.

1. **Split and extract.** Split sentences on terminal punctuation followed by whitespace. Pull the `[n]` numbers out *before* removing the markers, keeping the first occurrence of each.
2. **Normalize.** The same pipeline for claims and passages: `tokenize`, lowercase, keep `\w+` tokens, drop stopwords, and take a set. Any asymmetry (lowercasing one side only, stopwords on one side only) skews every overlap.
3. **Score each cited source on its own.** `|C ∩ P_n| / |C|` is the share of the claim's content words that appear in the passage it cites, the recall of the claim against the source.
4. **Classify and log issues** in sentence order, then citation order.

```python
def _terms(text, stop):
    return {t.lower() for t in tokenize(text) if WORD.fullmatch(t) and t.lower() not in stop}

for i, sent in enumerate(s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s):
    cites = list(dict.fromkeys(int(n) for n in CITE.findall(sent)))
    claim = _terms(CITE.sub(" ", sent), stop)
    ...
    for n in cites:
        if n < 1 or n > len(passages):          # [0] is not passages[-1]
            issues.append(out_of_range); continue
        ov = len(claim & sources[n - 1]) / len(claim)
```

## Common mistakes

- **`[0]` wraps around.** Checking only `n > len(passages)` lets `passages[-1]` answer a citation that does not exist, and a hallucinated reference gets marked as supported.
- **Case-sensitive matching.** The model writes "pto", the policy says "PTO", and a correct answer is flagged.
- **Counting repeated tokens.** A list instead of a set lets a sentence that repeats a matching word inflate its own score.
- **Checking against all retrieved passages.** "The fact is somewhere in the context" is not the same as "the cited source says it". Citation laundering is exactly what legal asked you to catch.

## Production notes

- Token overlap cannot see a changed number (Example 2: 26 weeks passes against 16 weeks). Production pipelines add a numeric and entity check (every number and named entity in the claim must appear in the cited passage), then send borderline sentences to an NLI model or an LLM judge, as in RAGAS faithfulness or TruLens groundedness.
- Anthropic's Citations API and similar provider features return character spans into the source documents, which turns this into an exact-span check; see `grounded-answer-check` (158).
- Log the per-sentence statuses, not just the rate. Dashboards track `supported_rate` by prompt version and retriever version, and a drop after a deploy is a regression signal for `prompt-regression-gate` (149).
- Decide the action per status: `out_of_range` is always a bug (block or regenerate), `uncited` may be fine for a greeting, and `unsupported` usually means retrieval missed the right chunk. Look at `context-packing` (157) before blaming the model.
