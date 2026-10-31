## Approach

"Grounded" has to be something you can check mechanically, or it is just a vibe. The contract here is strict and cheap: every sentence cites a source **and** quotes it verbatim, and a quote only counts if it appears in a source *that sentence cites*.

**Normalize both sides identically.** Real sources come from PDF and HTML extraction, with hard line wraps, non-breaking spaces and curly apostrophes, and models write curly quotes and ASCII hyphens. Map them to ASCII, lowercase, and collapse whitespace:

```python
def norm(s):
    for k, v in ASCII.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s.lower()).strip()
```

**A fixed status priority** makes every sentence get exactly one label you can count and show in the repair prompt:

```python
if not cites:                                   status = "no_citation"
elif any(n < 1 or n > len(sources) for n in cites): status = "bad_citation"
elif not quotes:                                status = "no_quote"
elif not all(any(q in normed[n - 1] for n in cites) for q in quotes):
                                                status = "unsupported_quote"
else:                                           status = "supported"
```

**One repair, then stop.** The repair prompt carries the specific failures and the sources, which is what makes the second attempt likely to succeed. A loop until grounded can spin forever on a question the sources don't answer, so after one retry, reject and let the product say "I couldn't find that in the policy."

## Common mistakes

- **Matching a quote against any source.** The quote is real, but the citation points at the wrong document, and users who click through find nothing. That is a misattribution, and it erodes trust as much as a fabrication.
- **No whitespace collapse.** `within\n30 days` in the PDF never matches `within 30 days` in the answer, so good answers get rejected.
- **Dropping out-of-range citations.** `[3]` with two sources is a fabricated reference. Silently ignoring it lets the sentence pass on its other citation.
- **Ignoring curly quotes.** Models often emit `“…”`, and every quote becomes invisible, so the sentence reads as `no_quote`.
- **Calling the model when the answer is already grounded,** or more than once: extra latency and cost with no benefit.

## Production notes

- Anthropic's Citations API returns `cited_text` with character or page locations for each claim, so you check spans rather than parse quotes. OpenAI file search returns file citations with indexes. Either way, verify server-side before rendering.
- Verbatim quotes check *presence*, not *entailment*. A quote can be real and still not support the sentence around it. Production stacks add an NLI or LLM-judge pass (RAGAS faithfulness, TruLens groundedness) on the sentences that pass this cheap check, and token-overlap checks (problem 142) for paraphrased claims.
- Log the groundedness per answer and alert on drops. A falling score usually means retrieval broke (an index sync wiped docs, problem 156) or a prompt change stopped the model from quoting.
- Run this alongside structured-output repair (problem 116). Both follow the same pattern: validate, re-ask once with the exact errors, then fail closed.
