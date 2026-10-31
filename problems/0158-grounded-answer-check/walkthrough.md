## 1. What the problem is really asking

A RAG answer says things like "refunds take 5–7 business days [1]". Nothing stops the model from inventing the number and still putting `[1]` after it. This problem makes "grounded" something a program can check: every sentence must **cite** a source and **quote** it word for word, and the quote has to actually appear in a source that sentence cites.

Under the story there are two small pieces:

- **A classifier per sentence.** Split the answer into sentences, pull out citations and quotes, and give each sentence exactly one status from a fixed priority list. The groundedness score is the fraction labelled `supported`.
- **A one-shot repair.** If the score is under the threshold, call the model exactly once with a prompt that lists the failures and the sources, check the rewrite, and either accept it or reject.

The judge records the outcome (`status`, `final`), both reports sentence by sentence, and **every message you sent to the model**. So the repair prompt is graded character by character, and calling the model when you shouldn't is visible.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `answer` | the model's first draft, a string | `check(answer)` |
| `sources` | a list of source strings; `[n]` means `sources[n - 1]` | normalize each one, look quotes up in the cited ones |
| `llm` | a `FakeLLM` with zero or one scripted rewrite | `llm.complete([{"role": "user", "content": prompt}])` |
| `response.content` | the rewrite; may be `""` | `check(response.content or "")` |
| `min_groundedness` | threshold in `[0, 1]` | `>=` passes |

The details that are easy to miss:

- **Two different quote replacements.** In the answer text you only swap `“` and `”` for `"`, so the quote regex `"([^"]+)"` can see curly-quoted spans. `norm` does more (single curly quotes, en and em dashes, the non-breaking space), and it is applied to every quote and every source.
- **The report's `text` is the sentence after that first replacement**, not after `norm`. In "one bad quote of two" the rewrite is written with `“...”`, and the second report shows `'Refunds go "to the original payment method" "within 5–7 business days" [1].'`: straight quotes, but the en dash is still there.
- **`norm` collapses whitespace.** The expense policy came out of a PDF as `"...within\n30 days of the purchase..."` and `"$75\xa0per person"`. After `norm` it is one line: `"expense policy submit receipts in expensify within 30 days of the purchase. meals with clients are capped at $75 per person. ..."`.
- **If the script is empty, the judge expects no model call.** `FakeLLM([])` raises `GCError: FakeLLM script exhausted after 0 calls` the moment you call it, which shows up as a Runtime Error.

## 3. Trace Example 2 by hand

Answer, with `min_groundedness = 0.8`:

```
Annual customers can get "a prorated refund within 30 days of renewal" [1]. Refunds usually arrive in about a week [1]. You can also get store credit instead.
```

`re.split(r"(?<=[.!?])\s+", ...)` cuts after each `.` that is followed by whitespace, giving three sentences:

| # | citations | quotes | status | why |
|---|---|---|---|---|
| 1 | `[1]` | `['a prorated refund within 30 days of renewal']` | `supported` | the quote is in `norm(sources[0])` |
| 2 | `[1]` | `[]` | `no_quote` | cites, but quotes nothing |
| 3 | `[]` | `[]` | `no_citation` | first rule fires |

Groundedness is 1/3, which the judge shows as `0.333333`. That is below `0.80`, so you build the repair prompt. Its first lines are exactly:

```
Your answer failed the grounding check (groundedness 0.33, required 0.80).
Rewrite it so every sentence cites a source like [1] and quotes it word for word in double quotes.
Failed sentences:
- [no_quote] Refunds usually arrive in about a week [1].
- [no_citation] You can also get store credit instead.
Sources:
[1] Refund Policy (rev. 2026-03)
Customers on annual plans may request ...
```

Note that the sources are printed **raw**, with their line breaks and the en dash, not normalized. The model needs the real text to quote from.

The scripted rewrite is:

```
Annual customers can get “a prorated refund within 30 days of renewal” [1]. Refunds arrive “within 5-7 business days” [1].
```

Curly quotes become straight, so the regex finds both quotes. The second quote has an ASCII hyphen, `5-7`, while the source has an en dash, `5–7`. `norm` maps the source's en dash to `-`, so `'within 5-7 business days'` is a substring. Both sentences are supported, groundedness is `1`, and the result is `{"status": "repaired", "final": <the rewrite as the model wrote it>}`. `final` keeps the curly quotes: you return `response.content`, not your normalized copy.

**Example 3 is the misattribution trap.** The sentence quotes `"under Settings > SSO > Certificates"` and cites `[1]`. That text is real, but it is in source 2, the ticket, not source 1, the refund policy. Status: `unsupported_quote`, groundedness `0`. The rewrite cites `[2]` correctly in its first sentence, but its second sentence, `This fixes it permanently [2].`, has no quote. That gives 0.5 against a threshold of 1.0, so the result is `rejected` with `final: None`. One repair, and then you stop.

## 4. Key idea: a fixed priority gives every sentence exactly one label

A sentence can be wrong in several ways at once. `'Refunds are prorated "within 30 days of renewal" [1][3].'` has a real quote and a valid `[1]`, but also `[3]` when there are only two sources. Checking the rules in a fixed order, and taking the first that applies, means you count each sentence once and the repair prompt names one reason per sentence:

1. `no_citation`, then 2. `bad_citation`, then 3. `no_quote`, then 4. `unsupported_quote`, then `supported`.

The order also protects you. You must check `bad_citation` before you index `normed[n - 1]`, or `[3]` raises an `IndexError` and `[0]` silently reads the *last* source (`normed[-1]`).

## 5. Key idea: a quote must be in a source that sentence cites

The support test is "every quote is found in at least one of this sentence's cited sources":

```python
all(any(q in normed[n - 1] for n in cites) for q in quotes)
```

Read it from the inside out. For one quote `q`, `any(...)` asks whether some cited source contains it. `all(...)` demands that for every quote. In "multi-source sentence" the sentence cites `[2][1]` and quotes `"an SSO login loop"` (from source 2) and `"a prorated refund"` (from source 1). Each quote finds a home among the cited sources, so it is `supported`.

The tempting shortcut, "is this quote in *any* source?", lets Example 3's first sentence pass. A user who clicks `[1]` would find nothing about certificates, which hurts trust as much as a made-up quote.

## 6. Plan before you code

```
norm(s): map curly quotes/dashes/nbsp to ASCII, lowercase, collapse whitespace, strip

check(text):
    replace “ ” with "
    normed = [norm(s) for s in sources]
    for each non-empty sentence from the split:
        cites  = ints from [n], first appearance, no repeats
        quotes = norm(q) for each "q"
        status = first matching rule in the priority table
    groundedness = supported / sentences, or 0.0 if no sentences

grounded_answer:
    r1 = check(answer)
    if r1 passes: return grounded, without calling the model
    build the prompt, call the model once
    r2 = check(content or "")
    return repaired or rejected
```

## 7. Build it one piece at a time

**Step 1: normalization.** Apply the character map first, then lowercase, then collapse every whitespace run (spaces, `\n`, tabs) to one space.

```python
import re

ASCII = {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "}


def norm(s):
    for k, v in ASCII.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s.lower()).strip()
```

In Python 3, `\s` already matches ` `, so the collapse alone would cover the non-breaking space. Keeping it in the map follows the spec literally and costs nothing.

**Step 2: one sentence's citations and quotes.** `re.findall` gives the digit strings in order. Turn them into ints and skip repeats by hand, because `set` would lose the order the report needs (`[2, 1]` in "multi-source sentence").

```python
cites = []
for n in re.findall(r"\[(\d+)\]", sent):
    if int(n) not in cites:
        cites.append(int(n))
quotes = [norm(q) for q in re.findall(r'"([^"]+)"', sent)]
```

Keep **every** citation, including out-of-range ones. Dropping `[3]` here is exactly the bug the `bad_citation` status exists to catch.

**Step 3: the status chain and the score.**

```python
if not cites:
    status = "no_citation"
elif any(n < 1 or n > len(sources) for n in cites):
    status = "bad_citation"
elif not quotes:
    status = "no_quote"
elif not all(any(q in normed[n - 1] for n in cites) for q in quotes):
    status = "unsupported_quote"
else:
    status = "supported"
```

Then `supported / len(rows) if rows else 0.0`. An answer of `"   "` strips to `""`, the split gives `['']`, the filter drops it, and you would divide by zero without the guard.

**Step 4: the flow.** The threshold test is `>=`, and the repair prompt is a list of lines joined with `"\n"`. Use `%.2f` for both numbers and `enumerate(sources, 1)` so the numbering matches the citations.

```python
r1 = check(answer, sources)
if r1["groundedness"] >= min_groundedness:
    return {"status": "grounded", "final": answer, "reports": [r1]}
...
response = llm.complete([{"role": "user", "content": "\n".join(lines)}])
r2 = check(response.content or "", sources)
```

`response.content or ""` matters because the model may return no text. In "out of range citation" the rewrite is `""`, so `r2` is `{"groundedness": 0, "sentences": []}` and the answer is rejected.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# Regexes split sentences and pull out citations and quotes.
import re

# Typographic characters that PDFs, HTML and models produce, mapped to the ASCII the quotes are written in.
ASCII = {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "}


# Put a quote or a source into one canonical form so a substring test is fair to both sides.
def norm(s):
    # Swap curly quotes, dashes and the non-breaking space for their ASCII forms.
    for k, v in ASCII.items():
        s = s.replace(k, v)  # one character class at a time
    # Lowercase, then turn PDF line wraps and double spaces into single spaces.
    return re.sub(r"\s+", " ", s.lower()).strip()


# Label every sentence of `text` and score the fraction that is supported.
def check(text, sources):
    # Curly double quotes would hide quoted spans from the quote regex, so straighten them first.
    text = text.replace("“", '"').replace("”", '"')
    # Normalize each source once, not once per quote.
    normed = [norm(s) for s in sources]
    # rows is the per-sentence report; supported counts the sentences that pass.
    rows, supported = [], 0
    # Split after . ! or ? followed by whitespace, dropping the empty piece a blank answer leaves.
    for sent in [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]:
        # Citation numbers in order of first appearance, without repeats.
        cites = []
        # Every [n] in the sentence, as digit strings, left to right.
        for n in re.findall(r"\[(\d+)\]", sent):
            # Skip a number already seen; a set would lose the order the report needs.
            if int(n) not in cites:
                cites.append(int(n))  # keep it even if out of range: that is what bad_citation catches
        # Every double-quoted span, normalized the same way as the sources.
        quotes = [norm(q) for q in re.findall(r'"([^"]+)"', sent)]
        # Rule 1: a sentence that cites nothing can't be grounded.
        if not cites:
            status = "no_citation"  # first matching rule wins
        # Rule 2: a citation that points at no source is fabricated; checked before any indexing.
        elif any(n < 1 or n > len(sources) for n in cites):
            status = "bad_citation"  # also stops [0] from reading the last source via normed[-1]
        # Rule 3: a citation without a word-for-word quote proves nothing.
        elif not quotes:
            status = "no_quote"  # cited, but nothing to verify
        # Rule 4: every quote must appear in at least one source THIS sentence cites.
        elif not all(any(q in normed[n - 1] for n in cites) for q in quotes):
            status = "unsupported_quote"  # missing, or found only in an uncited source
        # Every rule passed.
        else:
            status = "supported"  # this sentence is grounded
            supported += 1  # count it toward the score
        # Record the sentence as the report shows it: straight quotes, otherwise as written.
        rows.append({"text": sent, "citations": cites, "quotes": quotes, "status": status})
    # Score is supported / total, with 0.0 for an answer that has no sentences at all.
    return {"groundedness": supported / len(rows) if rows else 0.0, "sentences": rows}


# Check the answer; if it falls short, ask the model to fix it exactly once.
def grounded_answer(answer, sources, llm, min_groundedness):
    # Grade the first draft.
    r1 = check(answer, sources)
    # Good enough already (>=, so a tie passes): no model call, no extra latency or cost.
    if r1["groundedness"] >= min_groundedness:
        return {"status": "grounded", "final": answer, "reports": [r1]}  # ship the draft as is
    # The repair prompt opens with the score, the target and the rule the model must follow.
    lines = ["Your answer failed the grounding check (groundedness %.2f, required %.2f)." % (r1["groundedness"], min_groundedness),
             "Rewrite it so every sentence cites a source like [1] and quotes it word for word in double quotes.",
             "Failed sentences:"]
    # Name each failed sentence with its reason, so the model knows exactly what to fix.
    lines += ["- [%s] %s" % (s["status"], s["text"]) for s in r1["sentences"] if s["status"] != "supported"]
    # Then the sources, raw and numbered from 1, so the model can quote them exactly.
    lines.append("Sources:")
    # enumerate from 1 so the numbers match the [n] citations.
    lines += ["[%d] %s" % (i, s) for i, s in enumerate(sources, 1)]
    # The single repair call.
    response = llm.complete([{"role": "user", "content": "\n".join(lines)}])
    # Grade the rewrite; the model may return no text, which counts as zero sentences.
    r2 = check(response.content or "", sources)
    # The rewrite passes: return it exactly as the model wrote it.
    if r2["groundedness"] >= min_groundedness:
        return {"status": "repaired", "final": response.content, "reports": [r1, r2]}  # fixed in one try
    # Still not grounded after one repair: fail closed rather than show an unsupported answer.
    return {"status": "rejected", "final": None, "reports": [r1, r2]}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `grounded`, groundedness 1, no model call | the happy path skips the model |
| Example 2 | `repaired`, 0.333333 then 1 | the repair prompt; curly quotes and an ASCII hyphen still match |
| Example 3 | `rejected`, 0 then 0.5 | a real quote under the wrong citation is `unsupported_quote`; only one repair |
| pdf line wraps and nbsp | `grounded`, three supported | `norm` collapses `\n` and maps `\xa0` and `’` |
| out of range citation | `rejected`; `[1][3]` is `bad_citation`; empty rewrite gives 0 sentences | keep invalid citations; `content or ""` |
| misattributed quote | `grounded` at exactly 0.5; first sentence `unsupported_quote` | cited sources only |
| multi-source sentence | `grounded`, 0.5, citations `[2, 1]` | first-appearance order; each quote may come from a different cited source; `!` and `?` split sentences |
| one bad quote of two | `repaired`, 0 then 1 | every quote must be found, not just one |
| empty answer | `grounded`, groundedness 0, no sentences | the zero-sentence guard; `0 >= 0.0` passes |
| threshold equality | `grounded` at 2/4 = 0.5 | `>=`, not `>` |
| rewrite still bad | `rejected`; `[0]` is `bad_citation` | the lower bound of the range check |
| case and spacing in quote | `grounded` | the quote is normalized too: case and double spaces |

## 10. Complexity

For `S` sentences, `Q` quotes per sentence, `C` citations per sentence and sources of length `L`, the check is O(S · Q · C · L) for the substring tests, plus O(total text) for normalization and the regexes. With 10 sources of 1,500 characters that is microseconds. Normalize the sources once per `check` (as the solution does), not once per quote.

In production the cost that matters is the model call. The early return saves a full round trip on every answer that is already grounded, and the single repair caps the worst case at two model calls per question. A loop that retries until it passes can spin forever on a question the sources simply don't answer.

## 11. If you got Wrong Answer

- **Runtime Error `FakeLLM script exhausted after 0 calls` on "pdf line wraps and nbsp" or "case and spacing in quote".** Your normalization doesn't collapse whitespace, so `within 30 days` never matches the PDF's `within\n30 days` (groundedness 2/3 instead of 1) and you call a model that has nothing scripted.
- **"out of range citation" comes back `grounded` with `citations: [1]`.** You dropped `[3]` while collecting citations. The sentence passes on `[1]` alone. "rewrite still bad" fails the same way for `[0]`.
- **Example 2 is `rejected` and the rewrite's sentences are `no_quote`.** You didn't map `“` and `”` in the answer text before running the quote regex.
- **Example 3's first sentence is `supported`, or "misattributed quote" scores 1.0.** You searched every source instead of the cited ones.
- **"threshold equality" calls the model.** You used `>` instead of `>=`.
- **Runtime Error `ZeroDivisionError` on "empty answer".** Guard `len(rows) == 0`.
- **The prompt differs only in the numbers.** Use `%.2f`: `0.33`, not `0.3333333333333333`.

## 12. Follow-ups an interviewer might ask

- *A quote can be real and still not support the claim around it. How do you catch that?* Verbatim quotes check presence, not entailment. Run an NLI model or an LLM judge (RAGAS faithfulness, TruLens groundedness) on the sentences that pass this cheap check, and token-overlap checks for paraphrased claims (problem 142, citation-hallucination-check).
- *Why not loop until the answer is grounded?* If the sources don't contain the answer, no rewrite can pass, and you pay for every attempt. One repair with the exact failures fixes most fixable answers. After that, fail closed and show "I couldn't find that in the policy."
- *How would this change with a native citations API?* Anthropic's Citations returns `cited_text` with character or page locations, so you verify spans against the document instead of parsing quotes. You still check that each span sits inside the document it claims.
- *What would you monitor?* Groundedness per answer and the repair and reject rates. A sudden drop usually means retrieval broke, for example an index sync that wiped documents (problem 156, incremental-index-sync), not that the model got worse.
- *How does this relate to structured-output repair?* It is the same shape: validate, re-ask once with the exact errors, then fail closed (problem 116).
