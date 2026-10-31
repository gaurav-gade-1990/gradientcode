## 1. What the problem is really asking

You're grading a new assistant build against production with an LLM judge: "here are two answers, which is better?" LLM judges have a well-known flaw: given two similar answers, many prefer whichever one they read first. So a single call measures the judge's slot preference as much as the answers. The fix is to ask twice, with the answers swapped, and only believe a verdict that survives the swap.

Under the story there are three small pieces:

1. **A parse-and-map step.** Turn the judge's raw text into `"1"`, `"2"`, `"tie"` or `"invalid"`, then translate the slot number back into a model name. In the swapped call, `"1"` means the **baseline** won.
2. **Counting.** Win, loss and tie rates, a score, and two judge-health rates (inconsistency and position bias).
3. **An agreement statistic.** Cohen's kappa between the judge's final verdicts and a small set of human labels, which decides whether the judge can be trusted at all.

The driver records how many calls you made and the exact text of every prompt, then compares those plus your full report. Calling once per pair, or building the prompt with the slots in the wrong order, fails on the prompts before the numbers are even checked.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `judge` | a `FakeLLM` that replays scripted replies, one per call | `judge.complete(messages).content` |
| `pairs` | `{pair_id, question, candidate, baseline}` | two calls each, in list order |
| `human` | `{pair_id: "candidate" / "baseline" / "tie"}` for **some** pairs | kappa is computed on those pairs only |
| `policy` | `{ship_score, min_kappa, max_position_bias}` | the decision thresholds |
| `SYSTEM`, `TEMPLATE` | constants in the starter | the two messages of every call |

Three details are easy to miss:

- **The fake hands out replies in call order.** It doesn't look at your prompt. If you skip the second call for a pair, every later pair reads the wrong reply, and the whole report shifts.
- **Parsing is strict.** `strip().lower().rstrip(".")` accepts `"1."`, `" TIE "` and `"Tie."`. It rejects `"Response 1"`, `"Response 2 is better than response 1"` and `""`. Those are `invalid`, count as parse errors, and are read as a tie.
- **Inconsistent pairs stay in every denominator.** They become ties. You never drop them.

## 3. Trace Example 1 by hand

Three pairs, replies `["1", "2", "2", "1", "1", "1"]`, humans label `q000` and `q002` as `"candidate"`.

| pair | ab (cand in slot 1) | → | ba (base in slot 1) | → | consistent? | final | same slot both times? |
|---|---|---|---|---|---|---|---|
| q000 | `1` | candidate | `2` | candidate | yes | candidate | no |
| q001 | `2` | baseline | `1` | baseline | yes | baseline | no |
| q002 | `1` | candidate | `1` | baseline | **no** | tie | **yes**, slot 1 |

Rates over all `N = 3`: win, loss and tie are each `0.333333`. `score = (1 + 0.5·1) / 3 = 0.5`. One pair is inconsistent and one is position-biased, so both rates are `0.333333`.

Kappa uses only `q000` and `q002` (`m = 2`):

- Judge finals: `[candidate, tie]`. Human labels: `[candidate, candidate]`.
- $p_o$ = agreements / m = 1/2.
- $p_e$ = (judge candidate share)(human candidate share) + (baseline)(baseline) + (tie)(tie) = (1/2)(2/2) + 0 + (1/2)(0) = 1/2.
- $\kappa = (0.5 - 0.5) / (1 - 0.5) = 0$.

`0 < min_kappa = 0.4`, so the decision is `"judge_unreliable"`. The first rule fires, and the score never gets looked at.

**Example 2 shows the parser.** Replies `["1.", "2", " TIE ", "tie", "Response 1", "2"]`. `"1."` becomes `1`, `" TIE "` becomes `tie`, and `"Response 1"` is `invalid`: one parse error, read as a tie. That tie disagrees with the candidate win from `"2"` in the swapped order, so q002 is inconsistent. Finals are candidate, tie, tie, the score is `(1 + 0.5·2) / 3 = 0.666667 >= 0.55`, and with no human labels `kappa` is `None`, so the decision is `"ship"`.

## 4. Key idea: map slots back to models before comparing

The raw tokens `"1"` and `"2"` name positions, not models. Compare them directly and a judge that always says `"1"` looks perfectly consistent: `1` and `1` match. Map each call's token through its own table first:

```python
WINNER = {
    "ab": {"1": "candidate", "2": "baseline"},
    "ba": {"1": "baseline", "2": "candidate"},
}
```

Now that always-`"1"` judge maps to candidate, then baseline: inconsistent, a tie, and flagged as position bias. Position bias is the one check that *does* compare raw tokens: the same slot (`"1"` twice or `"2"` twice) won both times. A `tie` twice isn't bias.

## 5. Key idea: why kappa and not raw agreement

In "always prefers candidate text", the judge says candidate on all 10 pairs, and humans say candidate on 8. Raw agreement is 0.8, which looks great. But a judge that ignores the answers and always says "candidate" gets exactly that against labels that are 80% candidate. Kappa subtracts the agreement you'd expect by chance:

$$
p_e = \sum_\ell \frac{\text{judge}_\ell}{m}\cdot\frac{\text{human}_\ell}{m} = 1.0 \cdot 0.8 = 0.8, \qquad \kappa = \frac{0.8 - 0.8}{1 - 0.8} = 0
$$

Kappa is 0, below `min_kappa = 0.2`, so the judge is unreliable even though its score of 1.0 would ship. The special case $p_e = 1$ happens when both sides use a single label ("all one label agreement": judge and humans all say baseline). The formula would divide by zero, and the spec says to return `1.0`.

## 6. Plan before you code

```
for each pair, in order:
    ab = ask(question, first=candidate, second=baseline)
    ba = ask(question, first=baseline, second=candidate)
    count invalid tokens as parse errors
    map each token to a winner (invalid and tie -> "tie")
    consistent = same winner; final = winner or "tie"
    biased = ab == ba and ab in ("1", "2")
rates over N = len(pairs)
kappa over the pairs present in human (None if none)
decision: unreliable (kappa) > unreliable (bias) > ship > hold
```

| condition, checked in order | decision |
|---|---|
| `kappa is not None and kappa < min_kappa` | `judge_unreliable` |
| `position_bias_rate > max_position_bias` | `judge_unreliable` |
| `score >= ship_score` | `ship` |
| otherwise | `hold` |

## 7. Build it one piece at a time

**Step 1: one judge call and the parser.** Guard against `content` being `None` with `or ""`:

```python
def _ask(judge, question, first, second):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": TEMPLATE.format(question=question, first=first, second=second)},
    ]
    token = (judge.complete(messages).content or "").strip().lower().rstrip(".")
    return token if token in ("1", "2", "tie") else "invalid"
```

Don't search for a digit in the text. `"Response 2 is better than response 1"` contains both, and a substring parser reads it as `1`. In "verbose judge replies" that flips q000 from an inconsistent tie to a candidate win.

**Step 2: both orders, mapped.** `.get(token, "tie")` sends both `"tie"` and `"invalid"` to a tie in one line:

```python
ab = _ask(judge, p["question"], p["candidate"], p["baseline"])
ba = _ask(judge, p["question"], p["baseline"], p["candidate"])
parse_errors += (ab == "invalid") + (ba == "invalid")
w_ab, w_ba = WINNER["ab"].get(ab, "tie"), WINNER["ba"].get(ba, "tie")
consistent = w_ab == w_ba
```

**Step 3: kappa.** Count labels over the labeled pairs only, and handle both edge cases:

```python
def _kappa(judged, labels):
    m = len(labels)
    if m == 0:
        return None
    p_o = sum(1 for a, b in zip(judged, labels) if a == b) / m
    p_e = sum((judged.count(l) / m) * (labels.count(l) / m) for l in LABELS)
    if p_e == 1:
        return 1.0
    return (p_o - p_e) / (1 - p_e)
```

Build the labeled list by walking `pairs`, not `human`, so judge and human lists line up and only pairs that were actually judged count.

**Step 4: the decision chain.** The order matters. An unreliable judge's score isn't worth reading, so both health checks come first. Position bias uses a strict `>`: in "bias exactly at limit" the rate is exactly `0.3` against a limit of `0.3`, and the build ships.

## 8. Full solution

```python
SYSTEM = "You are a strict evaluator. Compare two responses to the same customer question."  # judge persona, sent on every call
TEMPLATE = (  # one prompt shape for both orders, so only the slot contents differ
    "Question: {question}\n\n"
    "[Response 1]\n{first}\n\n"
    "[Response 2]\n{second}\n\n"
    "Which response is better? Reply with exactly one of: 1, 2, tie."
)
LABELS = ("candidate", "baseline", "tie")  # the three outcomes kappa sums over
WINNER = {  # slot number -> model, per call order
    "ab": {"1": "candidate", "2": "baseline"},  # candidate sits in slot 1
    "ba": {"1": "baseline", "2": "candidate"},  # swapped: slot 1 now holds the baseline
}


def _ask(judge, question, first, second):  # one judge call, returning a clean token
    messages = [  # the exact two-message prompt the judge records
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": TEMPLATE.format(question=question, first=first, second=second)},
    ]
    token = (judge.complete(messages).content or "").strip().lower().rstrip(".")  # tolerate case, spaces, a trailing dot
    return token if token in ("1", "2", "tie") else "invalid"  # anything else is a parse error, never a guess


def _kappa(judged, labels):  # Cohen's kappa: agreement corrected for chance
    m = len(labels)  # number of human-labeled pairs
    if m == 0:  # no labels to compare against
        return None  # unknown, so the kappa rule can't fire
    p_o = sum(1 for a, b in zip(judged, labels) if a == b) / m  # observed agreement
    p_e = sum((judged.count(l) / m) * (labels.count(l) / m) for l in LABELS)  # agreement expected by chance
    if p_e == 1:  # both sides used one single label, so the formula divides by zero
        return 1.0  # the spec defines this as perfect agreement
    return (p_o - p_e) / (1 - p_e)  # how much better than chance the judge agrees


def evaluate_with_judge(judge, pairs, human, policy):  # judge every pair both ways and decide
    verdicts = {}  # per-pair tokens, final winner and consistency
    parse_errors = biased = inconsistent = 0  # judge-health counters
    for p in pairs:  # list order, because the judge's replies are consumed in call order
        ab = _ask(judge, p["question"], p["candidate"], p["baseline"])  # order 1: candidate first
        ba = _ask(judge, p["question"], p["baseline"], p["candidate"])  # order 2: baseline first
        parse_errors += (ab == "invalid") + (ba == "invalid")  # each unreadable reply counts once
        w_ab, w_ba = WINNER["ab"].get(ab, "tie"), WINNER["ba"].get(ba, "tie")  # slots -> models; tie and invalid -> tie
        consistent = w_ab == w_ba  # the verdict survived the swap
        inconsistent += not consistent  # a judge that flips is unsure or biased
        biased += ab == ba and ab in ("1", "2")  # the same slot won twice: position bias
        # an inconsistent pair becomes a tie but stays in the data
        verdicts[p["pair_id"]] = {"ab": ab, "ba": ba, "final": w_ab if consistent else "tie", "consistent": consistent}

    n = len(pairs)  # every pair is in every denominator
    finals = [verdicts[p["pair_id"]]["final"] for p in pairs]  # final verdicts in pair order
    wins, losses, ties = finals.count("candidate"), finals.count("baseline"), finals.count("tie")  # outcome counts
    labeled = [p["pair_id"] for p in pairs if p["pair_id"] in human]  # only pairs a human also judged
    kappa = _kappa([verdicts[i]["final"] for i in labeled], [human[i] for i in labeled])  # aligned judge vs human lists
    score = (wins + 0.5 * ties) / n  # a tie is worth half a win
    bias_rate = biased / n  # share of pairs where the slot decided

    if kappa is not None and kappa < policy["min_kappa"]:  # judge disagrees with humans beyond chance
        decision = "judge_unreliable"  # don't trust its score
    elif bias_rate > policy["max_position_bias"]:  # judge picks by position too often
        decision = "judge_unreliable"  # its score is mostly order noise
    elif score >= policy["ship_score"]:  # a trusted judge says the candidate is good enough
        decision = "ship"  # release the new build
    else:  # trusted judge, not good enough
        decision = "hold"  # keep production

    return {  # the full report the driver compares
        "verdicts": verdicts,  # per-pair detail for debugging
        "win_rate": wins / n, "loss_rate": losses / n, "tie_rate": ties / n, "score": score,  # outcome metrics
        "inconsistency_rate": inconsistent / n, "position_bias_rate": bias_rate,  # judge-health metrics
        "parse_errors": parse_errors, "kappa": kappa, "decision": decision,  # trust signal and verdict
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | kappa 0.0, `judge_unreliable` | swap mapping, bias detection, the kappa rule firing first |
| Example 2 | parse_errors 1, score 0.666667, `ship` | strict parsing of `"1."`, `" TIE "`, `"Response 1"` |
| Example 3 | kappa 1.0, score 0.5, `hold` | perfect agreement but not good enough |
| first-slot biased judge | bias 0.325, kappa -0.09375, `judge_unreliable` | a judge that says `"1"` 45% of the time regardless |
| honest judge ships | score 0.6875, `ship` | 80 calls, no bias, no labels |
| always prefers candidate text | score 1.0, kappa 0.0, `judge_unreliable` | kappa, not raw agreement (which would be 0.8) |
| all one label agreement | kappa 1.0, `hold` | the $p_e = 1$ special case |
| verbose judge replies | parse_errors 2, score 0.6 | free-text and empty replies are invalid, not substrings |
| inconsistency dilutes wins | win_rate 0.375, inconsistency 0.625 | inconsistent pairs stay in the denominator |
| bias exactly at limit | bias 0.3, `ship` | strict `>` on the bias limit |

## 10. Complexity

Two judge calls per pair, so `2N` calls. That's the real cost: each is a full LLM request, and at `N = 100` you're paying for 200 judge calls per release candidate. The counting is O(N), and kappa is O(m) per label with `list.count`, so O(3m). Memory is O(N) for the verdicts.

Doubling the judge cost is the price of seeing position bias. Cheaper alternatives (randomizing the order once per pair, as AlpacaEval does) average the bias out over many pairs but can't flag it per pair. At a few hundred pairs per release, paying for the swap is usually worth it.

## 11. If you got Wrong Answer

- **`calls` is `N` instead of `2N`, and everything after the first pair is shifted.** You call once per pair and infer the swapped verdict.
- **Example 1's q000 and q001 come out as inconsistent ties, and q002 as a candidate win.** You didn't flip the swapped call: in `"ba"`, `"1"` means baseline.
- **Example 2 shows parse_errors 0 and q002 as a candidate win.** You're parsing with substrings; `"Response 1"` must be invalid.
- **"inconsistency dilutes wins" has win_rate 1.0 and an inconsistency_rate above 1.** You dropped inconsistent pairs from the denominators.
- **"always prefers candidate text" gives kappa 0.8 and ships.** You returned raw agreement $p_o$ instead of kappa.
- **"all one label agreement" crashes with `ZeroDivisionError`.** You're missing the $p_e = 1$ case.
- **"bias exactly at limit" says `judge_unreliable`.** Use `>`, not `>=`, for the bias limit.

## 12. Follow-ups an interviewer might ask

- *How would you make parsing robust in production?* Don't parse free text. Use structured output (a tool call or JSON schema with an enum of `1`, `2`, `tie`) at temperature 0, and log the judge's rationale in a separate field. Alert when `parse_errors` rises.
- *How big should the human calibration set be?* Commonly 100 to 300 pairs, re-labeled whenever the domain shifts. Re-run kappa whenever the judge model or the judge prompt changes. A judge prompt is code; gate it like any prompt (problem 149, prompt-regression-gate).
- *What other judge biases are there?* Length bias (preferring longer answers), self-preference (a model favoring its own outputs) and style over substance. AlpacaEval's length-controlled win rate regresses out the length effect.
- *Score 0.58 against a 0.55 bar. Ship?* Put a confidence interval on it first, by bootstrapping over pairs, or run a sign test on the consistent wins and losses as in problem 146 (ab-test-significance). Forty pairs give a wide interval.
- *Does the swap trick work for single-answer grading, like 1-to-10 scores?* Not directly. There you'd check calibration against human scores, or convert to pairwise comparisons, which are more stable than absolute scores.
