## 1. What the problem is really asking

A RAG answer says "[2]" at the end of a sentence. That marker is a promise: "passage 2 says this." Models break that promise in three ways. They cite nothing, they cite a passage that doesn't exist (`[7]` when four were retrieved), or they cite a real passage that doesn't contain the claim. You're writing the cheap, deterministic check that catches all three on every answer before it's shown.

Under the story, this is **set overlap with careful bookkeeping**. Each sentence becomes a set of content words $C$. Each passage becomes a set $P$. The score for one citation is $\lvert C \cap P_n\rvert / \lvert C\rvert$: what share of the sentence's content words appear in the passage it cites. Everything else is classification rules and ordering.

The judge compares the whole returned dict: every sentence's `citations`, `overlap` and `status`, the ordered `issues` list, and `supported_rate`. Floats are compared with `rtol=1e-9`, so the overlap must be computed exactly the way the statement says, with sets and the same normalization on both sides.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `answer` | the model's answer, one string | split into sentences with the given regex |
| `passages` | list of retrieved passage strings | `[n]` means `passages[n - 1]` |
| `stopwords` | list of words to ignore | lowercase them into a set once |
| `tau` | support threshold in `(0, 1]` | a citation supports the sentence if overlap `>= tau` |
| `tokenize` | from `gc_runtime`: `\w+` or a single punctuation mark | `tokenize("$75 per day")` gives `['$', '75', 'per', 'day']` |

Three details are easy to miss:

- **Pull the citation numbers before you remove the markers, and remove them with a space.** `tokenize` turns `[4]` into `'['`, `'4'`, `']'`. If you leave the marker in, `'4'` becomes a claim word. Replacing with a space (not an empty string) keeps `day[4]` from gluing into one token.
- **Citations are 1-based.** `[0]` is out of range. In Python, `passages[0 - 1]` is the last passage, so a lazy bounds check turns a hallucinated `[0]` into a citation of passage 4.
- **Decimals split.** `tokenize("1.5 days")` gives `['1', '.', '5', 'days']`. The `.` is dropped by the `\w+` filter, so `1.5` becomes the two claim words `1` and `5`. That's fine as long as passages go through the same pipeline.

## 3. Trace Example 2 by hand

The passage sets, after tokenize, lowercase, `\w+` filter and stopwords:

- `P2 = {12, 16, adoption, birth, birthing, full, leave, months, non, parental, parents, pay, start, weeks}`
- `P3 = {30, allowed, approval, calendar, country, days, home, longer, manager, ops, outside, people, remote, require, review, stays, tax, work, year}`
- `P4 = {60, 75, day, days, expense, meals, purchase, reimbursed, reports, submitted, travelling, while}`

The answer splits into five sentences:

| i | sentence | cites | claim set $C$ | $C \cap P_n$ | overlap | status |
|---|---|---|---|---|---|---|
| 0 | Parental leave is 26 weeks for all parents [2]. | [2] | {26, all, leave, parental, parents, weeks} | {leave, parental, parents, weeks} | 4/6 = 0.666667 | supported |
| 1 | You can work remotely abroad for 90 days without approval [3]. | [3] | {90, abroad, approval, days, remotely, without, work} | {approval, days, work} | 3/7 = 0.428571 | unsupported |
| 2 | Meals are reimbursed up to $75 per day [4][7]. | [4, 7] | {75, day, meals, reimbursed} | P4: all 4; P7: none | [1, None] | supported |
| 3 | Contact People Ops for exceptions. | [] | {contact, exceptions, ops, people} | | [] | uncited |
| 4 | Thanks! | [] | {} | | [] | no_claim |

The issues, in sentence order and then citation order:

```python
[{"sentence": 1, "citation": 3, "issue": "unsupported"},
 {"sentence": 2, "citation": 7, "issue": "out_of_range"},
 {"sentence": 3, "citation": None, "issue": "missing"}]
```

`supported_rate` counts the four graded sentences (the `no_claim` one is excluded): 2 supported out of 4 is `0.5`.

Two things to notice. Sentence 0 changed 16 weeks to 26 and still passes: token overlap can't see a wrong number. And sentence 2 is supported even though it also cites a passage that doesn't exist. The `[7]` still gets logged as an issue.

**The tricky one, Example 3:** `"Unused PTO is forfeited on January 1. [1] Remote stays ..."`. The model put `[1]` after the period. The splitter breaks on the whitespace after `1.`, so sentence 0 is `"Unused PTO is forfeited on January 1."` with no citation (`uncited`, a `missing` issue). The `[1]` moves to the start of sentence 1, which now cites `[1, 3]`. Its claim set is `{30, days, longer, need, remote, review, stays, tax, than}` (9 words). Passage 1 shares `{30, days}`, 2/9 = 0.222222, so `[1]` is logged as unsupported. Passage 3 shares 7, 0.777778, so the sentence is supported. You don't repair the model's punctuation; you report what the splitter sees.

## 4. Key idea: one normalizer for both sides

Every overlap compares a claim set with a passage set. If the two sides are normalized differently, every score is skewed. Write one helper and call it for both:

```python
def _terms(text, stop):
    return {t.lower() for t in tokenize(text) if WORD.fullmatch(t) and t.lower() not in stop}
```

- **Lowercase** so that the model's `pto` matches the policy's `PTO`.
- **`fullmatch`, not `match`.** Tokens are already split, so this just drops punctuation tokens like `$`, `.`, `[`.
- **A set**, so a word the model repeats counts once. Otherwise "Remote work and remote travel" counts `remote` twice and inflates its own score.

The stopword list is lowercased once into a set up front, so the membership test is fast and case-insensitive.

## 5. Key idea: score each cited passage on its own

It's tempting to ask "is the claim somewhere in the retrieved context?" That's the wrong question. A claim that's true in passage 2 but cited as `[1]` is a wrong citation. Users click `[1]` and find nothing. So the overlap is always against `sources[n - 1]`, the one passage named. The sentence is `supported` if **any** of its in-range citations reaches `tau`, but every citation that misses is still reported as its own `unsupported` issue.

## 6. Plan before you code

```
stop = lowercase set of stopwords
sources = [_terms(p) for p in passages]
for i, sentence in enumerate(non-empty split pieces):
    cites = citation numbers, first occurrence kept, in order
    claim = _terms(sentence with [n] markers replaced by " ")
    if claim empty: no_claim
    elif no cites: uncited, issue "missing" (citation None)
    else for each n in cites:
        out of range -> overlap None, issue out_of_range
        else overlap = |claim & sources[n-1]| / |claim|; if < tau: issue unsupported
        status = supported if any overlap >= tau else unsupported
rate = supported / graded, or 1.0 if nothing graded
```

| sentence | status | issues |
|---|---|---|
| empty claim set | `no_claim` | none, even if it has citations |
| claim, no citations | `uncited` | one `missing` |
| claim, citations, one reaches `tau` | `supported` | one per citation that doesn't |
| claim, citations, none reaches `tau` | `unsupported` | one per citation |

## 7. Build it one piece at a time

**Step 1: split and extract citations.** `dict.fromkeys` keeps the first occurrence of each key in insertion order, which is exactly "dedupe, keep order":

```python
for i, sent in enumerate(s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s):
    cites = list(dict.fromkeys(int(n) for n in CITE.findall(sent)))
```

The `enumerate` wraps the filtered generator, so sentence indices count only non-empty pieces. `int(n)` matters: `findall` returns strings, and the output needs integers.

**Step 2: the claim set.** Replace markers before tokenizing:

```python
    claim = _terms(CITE.sub(" ", sent), stop)
```

Skip this and Example 1 already fails: sentence 1's claim becomes `{balance, capped, 30, days, 1}`, and the stray `1` matches passage 1's `January 1`, so the overlap is 0.8 instead of 0.75.

**Step 3: the two early statuses.** The `no_claim` check goes first, because a sentence made only of stopwords ("Thanks!") isn't graded at all, citations or not:

```python
    row = {"citations": cites, "overlap": [], "status": None}
    if not claim:
        row["status"] = "no_claim"
    elif not cites:
        row["status"] = "uncited"
        issues.append({"sentence": i, "citation": None, "issue": "missing"})
```

**Step 4: score each citation.** Check both bounds. The `continue` keeps `overlap` aligned with `citations` by appending `None`:

```python
    else:
        supported = False
        for n in cites:
            if n < 1 or n > len(passages):
                row["overlap"].append(None)
                issues.append({"sentence": i, "citation": n, "issue": "out_of_range"})
                continue
            ov = len(claim & sources[n - 1]) / len(claim)
            row["overlap"].append(ov)
            if ov >= tau:
                supported = True
            else:
                issues.append({"sentence": i, "citation": n, "issue": "unsupported"})
        row["status"] = "supported" if supported else "unsupported"
```

Division by `len(claim)` is safe here because the empty-claim case was handled in step 3.

**Step 5: the rate.** Exclude `no_claim` sentences from the denominator, and return `1.0` when nothing is graded:

```python
graded = [r for r in sentences if r["status"] != "no_claim"]
rate = 1.0 if not graded else sum(r["status"] == "supported" for r in graded) / len(graded)
```

## 8. Full solution

```python
import re  # regexes for sentence splitting, citation markers and the word filter

from gc_runtime import tokenize  # the judge's tokenizer, so tokens match the reference exactly

WORD = re.compile(r"\w+")  # a token is a content word only if it is all word characters
CITE = re.compile(r"\[(\d+)\]")  # a citation marker like [3]; the group captures the number


def _terms(text, stop):  # one normalizer for claims and passages, so both sides match
    # lowercase, drop punctuation tokens and stopwords, and keep a set so repeats count once
    return {t.lower() for t in tokenize(text) if WORD.fullmatch(t) and t.lower() not in stop}


def check_citations(answer, passages, stopwords, tau):  # grade every sentence of one answer
    stop = {w.lower() for w in stopwords}  # lowercase once so the stopword test is case-insensitive
    sources = [_terms(p, stop) for p in passages]  # passage sets built once; [n] reads sources[n - 1]
    sentences, issues = [], []  # per-sentence rows and the flat issue log, both in sentence order
    # split on .!? followed by whitespace; skip empty pieces so indices count real sentences
    for i, sent in enumerate(s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s):
        # read the numbers before stripping markers; dict.fromkeys dedupes and keeps first-seen order
        cites = list(dict.fromkeys(int(n) for n in CITE.findall(sent)))
        claim = _terms(CITE.sub(" ", sent), stop)  # markers become spaces so "4" is never a claim word
        row = {"citations": cites, "overlap": [], "status": None}  # citations are reported whatever happens
        if not claim:  # only stopwords and punctuation ("Thanks!"): nothing to verify
            row["status"] = "no_claim"  # not graded, and its citations are ignored
        elif not cites:  # a real claim with no source behind it
            row["status"] = "uncited"  # graded, and it can never count as supported
            issues.append({"sentence": i, "citation": None, "issue": "missing"})  # one issue, no citation number
        else:  # a claim with at least one citation: score each cited passage on its own
            supported = False  # becomes True if any in-range citation reaches tau
            for n in cites:  # in first-appearance order, so issues come out in citation order
                if n < 1 or n > len(passages):  # 1-based: [0] must not wrap around to passages[-1]
                    row["overlap"].append(None)  # keep overlap aligned with citations
                    issues.append({"sentence": i, "citation": n, "issue": "out_of_range"})  # a hallucinated source
                    continue  # nothing to score for a passage that doesn't exist
                ov = len(claim & sources[n - 1]) / len(claim)  # share of the claim found in the cited passage
                row["overlap"].append(ov)  # record the score for this citation
                if ov >= tau:  # reaching the threshold exactly counts as support
                    supported = True  # one good citation is enough for the sentence
                else:  # this particular source doesn't back the claim
                    issues.append({"sentence": i, "citation": n, "issue": "unsupported"})  # log it even if another passes
            row["status"] = "supported" if supported else "unsupported"  # any passing citation wins
        sentences.append(row)  # rows stay in sentence order
    graded = [r for r in sentences if r["status"] != "no_claim"]  # pleasantries are left out of the rate
    # supported share of graded sentences; with nothing to grade, nothing failed, so 1.0
    rate = 1.0 if not graded else sum(r["status"] == "supported" for r in graded) / len(graded)
    return {"sentences": sentences, "issues": issues, "supported_rate": rate}  # the full report the judge compares
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | all three supported, rate 1 | the basic path; `capped` vs `cap` still clears 0.6 at 3/4 |
| Example 2 | rate 0.5, three issues | every status and issue type in one answer |
| Example 3 | sentence 0 uncited, sentence 1 cites [1, 3] | the splitter decides where a misplaced marker lands |
| citation zero is out of range | `[0]` gives overlap `None`, out_of_range | the `n < 1` bound |
| lowercase acronym from the model | overlap 1 at `tau=0.9` | lowercasing on both sides |
| repeated words do not count twice | overlap 0.666667, unsupported at `tau=0.7` | sets, not lists |
| supported by a passage it did not cite | overlaps 0 and 0.2, rate 0 | scoring against the cited passage only |
| duplicate and mixed citations | citations `[1, 2]` and `[4, 1]`, both supported | dedupe keeps first-occurrence order; one good citation is enough |
| overlap exactly at tau | 0.5 supported at `tau=0.5`, 0.4 not | `>=`, not `>` |
| no passages retrieved | `[1]` out of range, rate 0 | bounds check with an empty list |
| only pleasantries | both `no_claim`, rate 1 | the `1.0` default when nothing is graded |
| questions and exclamations split | sentence 0 uncited, rate 0.666667 | `?` and `!` end sentences too |

## 10. Complexity

Let the answer have `S` sentences of length up to `L` tokens and the passages total `T` tokens. Building the passage sets is O(T). Each sentence is O(L) to normalize plus O(L) per citation for the set intersection. In total that's O(T + S·L·k) for `k` citations per sentence: microseconds for an answer. That's why this check can run on every production response. In production it's the first filter. Only the sentences it flags go to the slow, expensive checker (an NLI model or an LLM judge), which cuts judge cost by however much traffic is clean.

## 11. If you got Wrong Answer

- **"citation zero is out of range" shows `[0]` as supported with overlap 1.** You only check `n > len(passages)`, so `passages[-1]` answered it.
- **"lowercase acronym from the model" is unsupported, or Example 3's second overlap is 0.666667 instead of 0.777778.** You didn't lowercase the tokens. `PTO` and `pto` (or `Remote` and `remote`) don't match.
- **"repeated words do not count twice" gives 0.714286 and supported.** You counted a list of tokens, so `remote` scored twice (5/7).
- **"supported by a passage it did not cite" is supported, rate 1.** You checked the claim against the union of all passages instead of `sources[n - 1]`.
- **Example 1's second overlap is 0.8.** You tokenized the sentence with the `[1]` marker still in it.
- **"duplicate and mixed citations" lists `[1, 2, 2]`.** You didn't dedupe the citation numbers.
- **"overlap exactly at tau" marks 0.5 unsupported.** You used `>` instead of `>=`.

## 12. Follow-ups an interviewer might ask

- *Example 2 passes "26 weeks" against a policy that says 16. How would you catch that?* Add a numeric and entity check: every number and named entity in the claim must appear in the cited passage. Send what's left borderline to an NLI model or an LLM judge, as RAGAS faithfulness and TruLens groundedness do.
- *Can you avoid the overlap heuristic entirely?* Yes, if the provider returns citations as character spans into the source documents (Anthropic's Citations API does). Then you check exact spans instead of word overlap. Problem 158 (grounded-answer-check) covers that.
- *What do you do with each status?* `out_of_range` is always a bug: block or regenerate. `uncited` may be fine for a greeting or a follow-up question. `unsupported` usually means retrieval missed the right chunk, so look at context packing (problem 157) before blaming the model.
- *What would you put on a dashboard?* `supported_rate` per prompt version and per retriever version. A drop right after a deploy is the regression signal that problem 149 (prompt-regression-gate) gates on.
- *Why recall of the claim, not Jaccard?* Passages are much longer than sentences. Jaccard divides by the union, so it would punish a correct sentence for not repeating the whole passage. Dividing by $\lvert C\rvert$ asks only "is what the sentence says in there?"
