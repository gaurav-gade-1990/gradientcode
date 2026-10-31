## 1. What the problem is really asking

Before a document can be retrieved, it has to be cut into chunks small enough for the embedding model. Cut badly and retrieval suffers: a chunk that ends mid-sentence embeds half an idea, and a cited snippet reads like nonsense. So you cut at the strongest natural boundary that makes the pieces fit (paragraphs, then lines, then sentences, then single tokens), then pack the pieces back together up to the budget, with a little overlap so context carries across chunk edges.

Under the story, this is **a recursive split followed by a greedy merge, all on token indices**:

1. **Split.** If a run of tokens is too long, cut it at every separator of the current level and recurse into each part with the next, weaker level.
2. **Merge.** Walk the pieces and fill chunks greedily. When the next piece doesn't fit, close the chunk and seed the next one with whole trailing pieces as overlap.

The driver audits every chunk: its offsets, its token count, its text, whether `text[start:end]` equals the chunk text, and the *true* token count of that slice using the judge's tokenizer. So you can't fake offsets or token counts; both are recomputed from the source.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `text` | the raw document, up to 5,000 characters | tokenize once; never modify it |
| `max_tokens` | the hard per-chunk limit | split and merge budget |
| `overlap_tokens` | the most tokens a new chunk may repeat from the previous one | overlap budget, whole pieces only |

The tokenizer is the regex `\w+|[^\w\s]`: a run of word characters, or a single punctuation mark. Everything between two tokens is the **gap**. Three details are easy to miss:

- **Tokens are not words.** `Full-time` is three tokens (`Full`, `-`, `time`) and `1.5` is three (`1`, `.`, `5`). Counting with `str.split()` makes the chunker think chunks fit when they don't.
- **Separators live in gaps, so a `.` with no gap isn't a sentence end.** `1.5`, `v2.3` and `security@acme.example` contain dots with no whitespace after them, so they never split. But `Section 1. The` does have a gap after `.`, so it *is* a sentence end by this rule.
- **Chunks start and end on tokens.** A chunk's text is `text[first_token.start : last_token.end]`, so it never begins or ends with whitespace, and it keeps the original whitespace inside.

## 3. Trace Example 1 by hand

The PTO policy has 45 tokens, and `max_tokens = 24`, `overlap_tokens = 0`.

**Split, level 0 (paragraph).** There are two blank lines, so the run is cut into three parts:

| part | text | tokens |
|---|---|---|
| A | `PTO Policy` | 2 |
| B | `Full-time employees accrue 1.5 days ... first day of employment.` | 25 |
| C | `Unused PTO carries over up to 10 days. Anything above the cap expires on January 31.` | 18 |

Each part recurses with level 1. A (2) and C (18) fit, so they're single pieces. B (25) doesn't fit and has no newline, so level 1 finds nothing and falls through to level 2 (sentence). The only sentence end inside B is after `month.`. The dot in `1.5` has no gap. B splits into **B1 = 16 tokens** and **B2 = 9 tokens**, which both fit.

Pieces: `[2, 16, 9, 18]`.

**Merge.**

| piece | current chunk | fits? | action |
|---|---|---|---|
| 2 | [] → [2] | yes | add |
| 16 | 2 + 16 = 18 | yes | add |
| 9 | 18 + 9 = 27 > 24 | no | close chunk `[0:75]`, 18 tokens; overlap budget 0, so start empty; add 9 |
| 18 | 9 + 18 = 27 > 24 | no | close `[76:122]`, 9 tokens; start empty; add 18 |
| end | | | close `[124:208]`, 18 tokens |

Three chunks: 18, 9 and 18 tokens. Notice the first chunk includes the title and the first sentence, joined by the original `\n\n`.

**Example 2 shows the overlap's second budget.** The runbook has no blank lines, so level 1 cuts at each newline into lines of 7, 12, 21 and 17 tokens. Lines 1 and 2 merge to 19. Line 3 (21) doesn't fit. The overlap candidate is line 2, 12 tokens, which is within `overlap_tokens = 12`. But `12 + 21 = 33 > 30`, so it can't be kept, and the overlap is empty. Line 4 also starts fresh: line 3 alone is 21 tokens, over the 12-token overlap budget.

**Example 3 is the fall-through.** One 42-token sentence with no separator at levels 0 to 2 becomes 42 single-token pieces. With `max_tokens = 12` and `overlap_tokens = 3`, each chunk after the first keeps the last 3 tokens and adds 9 new ones: chunks of 12, 12, 12, 12 and 6 tokens. Single-token pieces can cut `us-east-1` in the middle; that's the price of a sentence with no boundaries.

## 4. Key idea: work on token indices, derive characters last

Every decision (fit, separators, overlap) is about tokens, so represent pieces and chunks as **token index ranges** `(a, b)`. Characters only appear at the end:

```python
spans = [(m.start(), m.end()) for m in TOKEN.finditer(text)]
s, e = spans[a][0], spans[b - 1][1]          # chunk = text[s:e]
```

This makes `tokens = b - a` exact by construction, and offsets point into the original string. The tempting shortcut is building the chunk text and then recovering its offset with `text.find(body)`. Policies repeat boilerplate. In "repeated sentence offsets", "Report lost devices to security@acme.example within 1 hour." appears twice, and `find` returns the first copy's offset `97` for the second chunk instead of `209`, so a citation would highlight the wrong section.

## 5. Key idea: the overlap has two budgets

When a chunk closes, the next one is seeded with the longest run of **whole pieces** from its end such that:

1. their total is at most `overlap_tokens`, and
2. their total **plus the next piece** is at most `max_tokens`.

Check both. Skip the second and Example 2's second chunk becomes line 2 plus line 3, 33 tokens against a 30-token limit, which the embedding API would truncate or reject. Walk the closed chunk's pieces from the end and stop at the first one that breaks either budget; the result is always a contiguous suffix.

## 6. Plan before you code

```
spans = token (start, end) pairs; none -> []
split(a, b, level):
    fits -> [(a, b)]
    level 3 -> one piece per token
    cuts = gaps inside (a, b) that are level separators
    none -> split(a, b, level + 1)
    else -> for each part between cuts: split(part, level + 1)
merge pieces:
    if current non-empty and current + p > max: close; seed with overlap suffix
    add p
close the last
```

| level | separator gap |
|---|---|
| 0 paragraph | contains two or more `\n` |
| 1 line | contains a `\n` |
| 2 sentence | previous token is `.`, `!` or `?`, and the gap is non-empty |
| 3 word | every gap (each token alone) |

## 7. Build it one piece at a time

**Step 1: tokens and separators.** The gap between token `i` and `i + 1` is the text between their spans:

```python
def is_separator(i, level):
    gap = text[spans[i][1]:spans[i + 1][0]]
    if level == 0:
        return gap.count("\n") >= 2
    if level == 1:
        return "\n" in gap
    if level == 2:
        return gap != "" and text[spans[i][0]:spans[i][1]] in (".", "!", "?")
    return True
```

**Step 2: the recursive split.** A cut at gap `i` means the next part starts at token `i + 1`. Only gaps strictly inside the run count, so `i` ranges over `a .. b - 2`:

```python
def split(a, b, level):
    if b - a <= max_tokens:
        return [(a, b)]
    if level == 3:
        return [(i, i + 1) for i in range(a, b)]
    cuts = [i + 1 for i in range(a, b - 1) if is_separator(i, level)]
    if not cuts:
        return split(a, b, level + 1)
    edges = [a] + cuts + [b]
    pieces = []
    for s, e in zip(edges, edges[1:]):
        pieces.extend(split(s, e, level + 1))
    return pieces
```

Each part recurses at `level + 1`, not `level`. The spec says so, and it's safe: a part between two level-`k` cuts has no level-`k` separator left inside it.

**Step 3: the greedy merge.** The `cur and` guard keeps a lone oversized check from closing an empty chunk. Every piece is at most `max_tokens` after the split, so a fresh chunk always fits its first piece.

**Step 4: the overlap.** Walk `reversed(cur)`, test both budgets, and `insert(0, q)` to keep document order.

## 8. Full solution

```python
import re  # token spans come from the judge's regex

TOKEN = re.compile(r"\w+|[^\w\s]")  # same rule as gc_runtime.tokenize: a word run or one punctuation mark


def chunk_document(text, max_tokens, overlap_tokens):  # recursive split, then greedy merge with overlap
    spans = [(m.start(), m.end()) for m in TOKEN.finditer(text)]  # (start, end) character offsets of every token
    if not spans:  # empty or whitespace-only text
        return []  # nothing to embed

    def is_separator(i, level):  # is the gap after token i a cut point at this level?
        gap = text[spans[i][1]:spans[i + 1][0]]  # the whitespace between token i and token i + 1
        if level == 0:  # paragraph
            return gap.count("\n") >= 2  # a blank line
        if level == 1:  # line
            return "\n" in gap  # any line break
        if level == 2:  # sentence
            # terminal punctuation followed by whitespace; "1.5" has no gap after its dot
            return gap != "" and text[spans[i][0]:spans[i][1]] in (".", "!", "?")
        return True  # level 3: every gap is a word boundary

    def split(a, b, level):  # cut token range [a, b) at the strongest separator that's needed
        if b - a <= max_tokens:  # already fits
            return [(a, b)]  # keep it whole
        if level == 3:  # no structure left to use
            return [(i, i + 1) for i in range(a, b)]  # one token per piece
        cuts = [i + 1 for i in range(a, b - 1) if is_separator(i, level)]  # next part starts after each separator gap
        if not cuts:  # nothing at this level inside the run
            return split(a, b, level + 1)  # try a weaker separator
        edges = [a] + cuts + [b]  # part boundaries
        pieces = []  # pieces in document order
        for s, e in zip(edges, edges[1:]):  # each part between two cuts
            pieces.extend(split(s, e, level + 1))  # recurse with the next level
        return pieces  # all fit within max_tokens

    chunks, cur, cur_len = [], [], 0  # finished chunks, pieces in the open chunk, its token count

    def close(run):  # turn a list of pieces into a chunk dict
        a, b = run[0][0], run[-1][1]  # first and last token index (pieces are contiguous)
        s, e = spans[a][0], spans[b - 1][1]  # offsets come from token spans, never from text.find
        chunks.append({"start": s, "end": e, "tokens": b - a, "text": text[s:e]})  # exact count and exact slice

    for p in split(0, len(spans), 0):  # pieces in document order
        size = p[1] - p[0]  # tokens in this piece
        if cur and cur_len + size > max_tokens:  # adding it would overflow the open chunk
            close(cur)  # finish the chunk
            keep, kept = [], 0  # the overlap seed and its size
            for q in reversed(cur):  # trailing pieces of the chunk just closed, newest first
                qs = q[1] - q[0]  # tokens in that piece
                if kept + qs > overlap_tokens or kept + qs + size > max_tokens:  # breaks either budget
                    break  # the suffix must be contiguous, so stop here
                keep.insert(0, q)  # keep document order
                kept += qs  # grow the overlap
            cur, cur_len = keep, kept  # the new chunk starts with the overlap
        cur.append(p)  # add the piece
        cur_len += size  # update the running count
    close(cur)  # the last chunk
    return chunks  # in document order
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 3 chunks: 18, 9, 18 tokens | paragraph then sentence split; `1.5` isn't a sentence end |
| Example 2 | 3 chunks: 19, 21, 17 | line split; overlap rejected by the `max_tokens` budget |
| Example 3 | 5 chunks: 12, 12, 12, 12, 6 | fall-through to single tokens, 3-token overlap |
| empty and whitespace | `[]` | no tokens |
| fits in one chunk | 1 chunk of 45 tokens | `max_tokens` 45: a run of exactly `max_tokens` tokens is one piece (`<=`, not `<`) |
| one token over | 2 chunks, 27 and 18 tokens | `max_tokens` 44: the 45-token document splits at its blank lines into 2, 25 and 18; 2 + 25 fits, 27 + 18 doesn't, and the 25-token piece is too big for the 5-token overlap |
| repeated sentence offsets | 7 chunks; the repeated sentence at `[209:268]` | offsets from spans, not `text.find` |
| repeated sentence with overlap | 4 chunks, each at most 20 tokens | overlap with repeated text |
| ticket thread | 3 chunks: 37, 27, 32 | mixed paragraphs, lines and sentences |
| ticket tight | 16 chunks, none over 9 | heavy fall-through with overlap |
| wiki paragraphs, wiki sentence overlap | 4 chunks: 24, 25, 25, 25 | each paragraph fits, so pieces stay whole |
| max_tokens 1 | 7 single-token chunks | the smallest budget |
| version numbers are not sentences | 3 chunks: 9, 9, 8 | `v2.3.1` and `v1.9` have no gaps |

## 10. Complexity

Tokenizing is O(L) for `L` characters. The split visits each token once per level, at most four levels, so O(4·n) gap checks for `n` tokens. The merge is O(n) plus the overlap walks, each bounded by `overlap_tokens`. At 5,000 characters this is instant.

In an ingestion pipeline, chunking is never the bottleneck: embedding is. The design choices that matter at scale are the ones that change what gets embedded. Overlap of 10 to 20% is common, but every overlapped token is embedded and stored twice, and duplicates show up together at retrieval time. Keeping `start` and `end` lets you re-chunk only the changed parts of a document when it's edited.

## 11. If you got Wrong Answer

- **`tokens` and `true_tokens` disagree (Example 1's first chunk claims 21 but is really 27).** You counted with `str.split()`. Use the judge's tokenizer.
- **"repeated sentence offsets" gives the second "Report lost devices..." chunk `start = 97`.** You recovered offsets with `text.find`. Compute them from token spans.
- **Example 2's second chunk is 33 tokens.** Your overlap only checks `overlap_tokens`, not `kept + piece <= max_tokens`.
- **Example 1 returns 2 chunks of 24 and 21, and the second starts with `of employment.`.** You used a fixed sliding window, which cuts sentences in half.
- **`1.5` or `v2.3` gets split as a sentence.** Your sentence rule doesn't require a non-empty gap after the punctuation.
- **`matches_source` is `False`.** You stripped or normalized the text before slicing. Offsets must point into the original string.

## 12. Follow-ups an interviewer might ask

- *Which tokenizer should production use?* The embedding model's own (`tiktoken`, or the Voyage or Cohere tokenizer), so your budget matches the API's. A mismatch means silent truncation.
- *Can you do better than a separator list?* Yes, split on structure: Markdown headings, HTML block elements, functions in code. Carry the section path ("Security Baseline > Contractors") into each chunk's metadata or a text prefix, so the chunk embeds with its context.
- *Why keep offsets at all?* For citations with highlights, for grounded-answer checks (problem 158), and for incremental re-indexing when a document changes (problem 156).
- *Overlap creates near-duplicate results. What do you do?* Dedupe at query time when packing context (problem 157, context-packing), and merge overlapping hits from the same document into one span. Hybrid retrieval (problem 154, hybrid-search-rrf) also tends to return both halves of a split idea.
- *How would you pick `max_tokens`?* By evaluating retrieval: too small and a chunk lacks context, too large and its embedding averages several topics. A few hundred tokens is a common starting point; measure recall on a labeled query set.
