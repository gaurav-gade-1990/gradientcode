Your policy assistant must back every claim with a word-for-word quote from a cited source. Before an answer reaches the employee, verify it. If it isn't grounded enough, ask the model to fix it once.

`grounded_answer(answer, sources, llm, min_groundedness)`. `sources` is a list of strings. Citation `[n]` refers to `sources[n - 1]`.

**Normalization** `norm(s)`, applied to quotes and sources before matching:

1. Replace `“` `”` with `"`, `‘` `’` with `'`, `–` `—` with `-`, and the non-breaking space ` ` with a space.
2. Lowercase.
3. Collapse every run of whitespace to one space, and strip.

**Checking an answer** `check(text)`:

1. Replace `“` and `”` in the text with `"`. Split it into sentences with `re.split(r"(?<=[.!?])\s+", text.strip())` and drop empty strings. The sentence `text` in the report is that piece as is.
2. In each sentence, `citations` is the integers from `\[(\d+)\]` in order of first appearance, without repeats, and `quotes` is `norm(q)` for every match `q` of `"([^"]+)"`, in order.
3. A sentence's `status` is the first of these that applies:

| status | when |
|---|---|
| `no_citation` | no citations |
| `bad_citation` | a citation is `< 1` or `> len(sources)` |
| `no_quote` | no quotes |
| `unsupported_quote` | some quote is not a substring of `norm(source)` for **any of the sources this sentence cites** |
| `supported` | otherwise |

4. `groundedness` is the number of supported sentences divided by the number of sentences, or `0.0` if there are none.

`check` returns `{"groundedness": float, "sentences": [{"text", "citations", "quotes", "status"}, ...]}`.

**Flow**

1. `r1 = check(answer)`. If `r1["groundedness"] >= min_groundedness`, return `{"status": "grounded", "final": answer, "reports": [r1]}` without calling the model.
2. Otherwise call `llm.complete([{"role": "user", "content": prompt}])` **exactly once**. `prompt` is these lines joined with `"\n"`:
   - `Your answer failed the grounding check (groundedness {g:.2f}, required {m:.2f}).`
   - `Rewrite it so every sentence cites a source like [1] and quotes it word for word in double quotes.`
   - `Failed sentences:`
   - one line `- [{status}] {text}` for each non-supported sentence of `r1`, in order
   - `Sources:`
   - one line `[{n}] {source}` for each source, with the raw source text
3. `r2 = check(response.content or "")`. Return `{"status": "repaired", "final": response.content, "reports": [r1, r2]}` if `r2` meets the threshold, else `{"status": "rejected", "final": None, "reports": [r1, r2]}`.

The judge records every message you send to the model and compares the reports and the outcome.

**Constraints**

- up to 10 sources of at most 1,500 characters each, and answers of at most 1,500 characters
- `0 <= min_groundedness <= 1`
- The model may answer with curly quotes, or with no text at all.
