## 1. What the problem is really asking

You ask several agents the same question (classify this claims ticket) and get back several answers with a confidence each. You need one decision. This is **ensemble voting**, the same idea as self-consistency sampling, applied to a panel of different agents.

Strip the story and it's three small jobs done in order:

1. **Canonicalize** each answer so that `"Billing"` and `"billing."` count as the same vote.
2. **Accumulate** a weighted score and a headcount per answer in a dictionary.
3. **Pick the winner** with an explicit ranking key: highest score, then most votes, then earliest appearance. Or refuse to pick when too few agents actually voted.

The function is a pure function, and the judge compares the whole returned dict: `decision`, `reason`, the full `scores` table (in first-appearance order) and `voters`. A right decision with a wrong score or the wrong `reason` still fails.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `votes` | list of `{"agent", "answer", "confidence"}` | loop with `enumerate`, because the index is the tie-breaker |
| `v["agent"]` | the agent's name | not used in the decision at all |
| `v["answer"]` | a string, or `None` | normalized; `None` or an empty result is an abstention |
| `v["confidence"]` | a float, possibly outside `[0, 1]` | clamped into `[0, 1]`, then added to the answer's score |
| `quorum` | minimum number of real (non-abstaining) votes | compared with `voters` |

Three details are easy to miss:

- **Abstentions come in two forms.** `None` is one. A string that normalizes to nothing is the other: `"  "` in Example 3, and `"..."` in "quorum exactly met", which loses all its characters to the trailing-punctuation strip.
- **`scores` is reported even with no quorum.** Example 3 returns `{"refund": 0.9}` alongside `decision: None`. Build the table first, then decide.
- **Confidence weights the score but not the count.** An agent with confidence `0.0` still adds 1 to its answer's count. In "full tie goes to first appearance", `"Billing"` at `0.0` doesn't change billing's score but does make its count 2.

## 3. Trace Example 2 by hand

`votes = [a: "fraud" 0.5, b: "billing" 0.25, c: "billing" 0.25, d: None 0.9]`, `quorum = 3`.

| i | agent | normalized | clamped conf | scores after | counts after | first |
|---|---|---|---|---|---|---|
| 0 | a | `fraud` | 0.5 | fraud 0.5 | fraud 1 | fraud → 0 |
| 1 | b | `billing` | 0.25 | billing 0.25 | billing 1 | billing → 1 |
| 2 | c | `billing` | 0.25 | billing 0.5 | billing 2 | (unchanged) |
| 3 | d | `None` | skipped | | | |

`voters = 1 + 2 = 3`, which meets `quorum = 3`. Agent `d` was the most confident of all at `0.9`, but it abstained, so it counts for nothing.

Both answers score `0.5`, so `top = ["fraud", "billing"]`. Rank by `(-count, first)`: fraud is `(-1, 0)`, billing is `(-2, 1)`. The smaller tuple is billing's, so:

```python
{"decision": "billing", "reason": "tie_break", "scores": {"fraud": 0.5, "billing": 0.5}, "voters": 3}
```

**The trickiest hidden case, "float sums tie after rounding".** Billing gets `0.1 + 0.2`, fraud gets `0.3 + 0.0`. In Python, `0.1 + 0.2` is `0.30000000000000004`, which is greater than `0.3`. Without rounding, billing wins outright with `reason: "highest_score"`. After `round(..., 9)` both are `0.3`, the top score is shared, both have 2 votes, and billing wins on first appearance with `reason: "tie_break"`. Same decision, different reason, and the test fails if you skip the rounding.

## 4. Key idea: normalize in the right order

The rule is strip, lowercase, collapse whitespace, then strip trailing `.`, `!`, `?`:

```python
" ".join(answer.strip().lower().split()).rstrip(".!?")
```

- `str.split()` with no argument splits on **any** run of whitespace, tabs included, and drops empty pieces. Joining with `" "` collapses `"account\ttakeover?!"` to `"account takeover?!"`.
- `rstrip(".!?")` treats its argument as a **set of characters**, not a suffix. It removes any mix of them from the end, so `"?!"` goes in one call. `"..."` becomes `""`, which is an abstention.
- Doing the whitespace step first matters. `"billing. "` has a trailing space after the dot, so `rstrip(".!?")` on the raw string would remove nothing.

In "whitespace and punctuation", `"Account   Takeover!"`, `"account takeover"` and `"account\ttakeover?!"` all become `"account takeover"`, with a score of `0.5 + 0.5 + 0.25 = 1.25`. That beats phishing's `0.875`, though phishing has the single highest confidence.

## 5. Key idea: one sort key replaces a pile of ifs

The tie rules read like nested conditions, but they're a single lexicographic comparison:

```python
min(top, key=lambda a: (-counts[a], first[a]))
```

Python compares tuples element by element, so `min` picks the most votes (smallest `-count`) and, among those, the earliest first index. Restricting to `top` first, the answers at the best score, means score is already the primary key.

Why first appearance and not alphabetical? An alphabetical tie-break is deterministic, but it's biased: across thousands of tickets, ties always go to `"account"` over `"warranty"`. "alphabetical would differ" is built to catch exactly that: `"Warranty"` comes first and wins.

## 6. Plan before you code

```
scores, counts, first = {}, {}, {}
for i, v in enumerate(votes):
    a = normalize(v["answer"]); if a is None: skip
    c = clamp(confidence, 0, 1)
    first time seen: scores[a]=0, counts[a]=0, first[a]=i
    scores[a] += c; counts[a] += 1
round every score to 9 decimals
voters = total count
if voters < quorum: return no_quorum (with scores)
top = answers whose score equals the max
decision = min(top by (-count, first)); reason = highest_score if len(top)==1 else tie_break
```

| situation | `decision` | `reason` |
|---|---|---|
| `voters < quorum` (including no votes at all) | `None` | `"no_quorum"` |
| one answer at the top score | that answer | `"highest_score"` |
| two or more at the top score | most votes, then earliest | `"tie_break"` |

## 7. Build it one piece at a time

**Step 1: the normalizer.** Return `None` for both kinds of abstention, so the caller has one check.

```python
def normalize(answer):
    if answer is None:
        return None
    s = " ".join(answer.strip().lower().split()).rstrip(".!?")
    return s or None
```

`s or None` turns the empty string into `None`.

**Step 2: accumulate.** Dicts keep insertion order in Python 3.7+, so creating each key the first time the answer appears gives you "order of first appearance" for `scores` for free.

```python
scores, counts, first = {}, {}, {}
for i, v in enumerate(votes):
    a = normalize(v["answer"])
    if a is None:
        continue
    c = min(1.0, max(0.0, float(v["confidence"])))
    if a not in scores:
        scores[a], counts[a], first[a] = 0.0, 0, i
    scores[a] += c
    counts[a] += 1
```

Clamp both ends. In "uncalibrated confidence clamped", billing gets `3.5` and `-2.0`. Raw, that's `1.5` and billing beats fraud's `1.25`. Clamped, it's `1.0 + 0.0 = 1.0` and fraud wins.

**Step 3: round, count voters, check quorum.**

```python
scores = {a: round(s, 9) for a, s in scores.items()}
voters = sum(counts.values())
out = {"decision": None, "reason": "no_quorum", "scores": scores, "voters": voters}
if voters < quorum:
    return out
```

`voters` is the sum of counts, not `len(votes)`. Starting from the no-quorum result and overwriting it keeps one return shape. It also handles `votes = []`: you return before `max()` would fail on an empty dict.

**Step 4: pick the winner.**

```python
best = max(scores.values())
top = [a for a in scores if scores[a] == best]
out["decision"] = min(top, key=lambda a: (-counts[a], first[a]))
out["reason"] = "highest_score" if len(top) == 1 else "tie_break"
return out
```

`==` is safe here only because the scores were rounded in step 3.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# Map an agent's raw answer to a canonical label, or None when it abstained.
def normalize(answer):
    # An explicit None is an abstention.
    if answer is None:
        return None  # nothing to vote with
    # Strip, lowercase, collapse whitespace runs, then drop trailing . ! ? (any mix of them).
    s = " ".join(answer.strip().lower().split()).rstrip(".!?")
    return s or None  # an answer that normalized to nothing is also an abstention


# votes: [{"agent", "answer", "confidence"}]; quorum: minimum number of real votes needed to decide.
def aggregate(votes, quorum):
    # Weighted score, headcount and first index per normalized answer; dicts keep first-seen order.
    scores, counts, first = {}, {}, {}
    # The index i is the final tie-breaker, so enumerate.
    for i, v in enumerate(votes):
        a = normalize(v["answer"])  # "Billing" and "billing." become the same key
        # Abstentions add nothing: no score, no count, no quorum.
        if a is None:
            continue  # move to the next agent
        c = min(1.0, max(0.0, float(v["confidence"])))  # clamp, so 3.5 or -2.0 can't distort the vote
        # First time we see this answer: create its entries and remember where it appeared.
        if a not in scores:
            scores[a], counts[a], first[a] = 0.0, 0, i  # insertion here fixes the scores order
        scores[a] += c  # confidence weights the score
        counts[a] += 1  # but every real vote counts once toward the headcount
    scores = {a: round(s, 9) for a, s in scores.items()}  # so 0.1 + 0.2 ties with 0.3
    voters = sum(counts.values())  # real votes only; abstentions are excluded
    # Start from the no-quorum answer; the scores table is reported either way.
    out = {"decision": None, "reason": "no_quorum", "scores": scores, "voters": voters}
    # Too few real votes to trust a decision (also covers an empty vote list).
    if voters < quorum:
        return out  # decision stays None
    best = max(scores.values())  # the top score, safe to compare after rounding
    top = [a for a in scores if scores[a] == best]  # every answer sharing the top score
    # Among the top answers, most votes wins, then whichever appeared first.
    out["decision"] = min(top, key=lambda a: (-counts[a], first[a]))
    out["reason"] = "highest_score" if len(top) == 1 else "tie_break"  # a clear win or a tie
    return out  # the full result the judge compares
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | billing 1.25 over shipping 0.875, `highest_score` | `"Billing"` and `"billing."` merge |
| Example 2 | billing by `tie_break`, `voters` 3 | count breaks a score tie; `None` doesn't vote |
| Example 3 | `None`, `no_quorum`, scores `{"refund": 0.9}`, `voters` 1 | whitespace-only answer abstains; scores reported anyway |
| empty | `None`, `no_quorum`, `{}`, 0 | returning before `max()` on an empty dict |
| whitespace and punctuation | account takeover 1.25, `highest_score` | tabs, repeated spaces, and `?!` together |
| full tie goes to first appearance | shipping by `tie_break` | equal score and equal count; zero confidence still counts as a vote |
| alphabetical would differ | warranty by `tie_break` | first appearance, not alphabetical order |
| weights beat headcount | legal hold 1.0 over spam 0.75 | three 0.25 votes lose to one sure vote |
| uncalibrated confidence clamped | fraud 1.25 over billing 1.0 | clamping at both ends |
| float sums tie after rounding | billing by `tie_break`, both 0.3 | `round(..., 9)` before comparing |
| quorum exactly met | refund 0.7, `voters` 2 | `"..."` abstains; `voters == quorum` is enough |

## 10. Complexity

One pass over the votes, O(n) dictionary updates, plus O(k) for the distinct answers when rounding and picking the winner. Memory is O(k). With at most 50 votes this is instant.

The production cost is upstream: every vote is a full LLM call, so a five-agent panel costs five times one agent. That's why real systems vote only when it pays (high-stakes labels, low single-agent confidence) and log the whole score table. A `tie_break` or `no_quorum` result is a cheap, useful signal for routing the ticket to a human or a stronger model.

## 11. If you got Wrong Answer

- **Example 1 returns `scores` with both `"Billing"` and `"billing."`.** You aren't normalizing. Apply the full chain, in order.
- **"whitespace and punctuation" keeps a `?` or `!`.** You used `rstrip(".")` or `endswith`. `rstrip(".!?")` strips any mix of the three.
- **"weights beat headcount" picks spam with scores 3 and 1.** You counted heads instead of summing confidence.
- **"uncalibrated confidence clamped" picks billing with a score of 1.5.** You used raw confidence. Clamp both ends: clamping only the top gives billing `-1.0`, and the scores table is still wrong.
- **"float sums tie after rounding" says `highest_score`.** You compared unrounded floats.
- **"alphabetical would differ" picks account, or "full tie goes to first appearance" picks billing.** Your final tie-break is the label, not the first index.
- **Example 2 picks fraud.** You skipped the count step and went straight to first appearance.
- **Example 3 decides `refund` and reports `voters` 3.** Abstentions are counting toward quorum. Use `sum(counts.values())`, not `len(votes)`.

## 12. Follow-ups an interviewer might ask

- *The answers are free text, not labels. How do you vote?* Canonicalize harder before voting: map each answer onto the label set with a classifier or constrained output, or extract the final number for math answers (that's classic self-consistency). Exact string match only works on closed label sets.
- *Two agents share a base model and nearly the same prompt. Is that two votes?* Not really. Correlated agents don't add independent evidence. Weight by model family, or cap each family's total weight.
- *Where should the confidence come from?* Self-reported confidence is poorly calibrated. Measure each agent's calibration on labeled history (problem 33, expected-calibration-error) and correct it, or use the token log-probability of the label.
- *What do you do on `no_quorum` or a tie?* Escalate: retry with a stronger model, ask a judge model to compare the top two (problem 145, llm-judge-position-swap), or send the ticket to a human queue.
- *How would you produce the votes?* A supervisor fans the ticket out to workers and collects their answers (problem 104, supervisor-worker-routing).
