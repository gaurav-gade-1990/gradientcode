## 1. What the problem is really asking

A system prompt is code. Someone edits one sentence to fix a tone complaint, and the bot quietly starts promising refunds outside policy. This CI gate catches that before merge: replay a golden set against the new prompt, compare with production's last run, and block if things got worse in a way that matters.

Under the story, this is **an eval loop plus three independent block rules**:

1. **Must-pass regressions.** A case marked critical that passed before and fails now blocks on its own, however good the average looks.
2. **Overall drop.** The pass count fell by more than `max_drop_pp` percentage points.
3. **Slice drops.** The same test inside each tag, but only for slices big enough to mean something.

The driver records every message you send and compares them, plus the full report. So you must call the model exactly once per case, in list order, with exactly two messages. Retrying a failed call, or skipping one, changes the recorded calls and fails the case.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `llm` | a `FakeLLM` whose reply depends on the user message | one `complete` call per case |
| `new_prompt` | the edited system prompt | the system message on every call |
| `golden` | cases `{id, input, expect, tags, must_pass}` | `expect` is a list of substrings that must all appear |
| `baseline` | `{case_id: bool}` from the production prompt | `B`, `B_s`, and the must-pass check |
| `max_drop_pp` | allowed drop in percentage points | both drop rules |
| `min_slice` | smallest slice that's allowed to block | slice rule, and the `gated` flag |

Three details are easy to miss:

- **A model error is a failed case, not a crash.** `complete` can raise `ServerError`, `TimeoutError_` or `RateLimitError`. All are subclasses of `gc_runtime.GCError`, so one `except GCError` covers them. Don't retry.
- **Matching is case-insensitive on both sides.** Lowercase the response and each expected string.
- **Slices come from tags, and a case can have several.** In the larger cases every case is tagged with a topic plus a language (`en` or `es`), so one failure counts against two slices.

## 3. Key idea: compare drops in integers

The rule "the pass rate dropped by more than `d` points" is tempting to write as `(B/N - P/N) * 100 > d`. In floats, `(8/10 - 7/10) * 100` is `10.000000000000009`. With `d = 10`, a drop of exactly 10 points blocks the PR. That's the "exact boundary does not block" case.

Multiply both sides by `N` and everything is an integer:

```python
100 * (B - P) > max_drop_pp * N        # 100 * 1 > 10 * 10  ->  100 > 100  ->  False
```

The same comparison works for a slice with `B_s`, `P_s` and `n_s`. A CI gate that flaps on rounding teaches people to ignore it, so exactness matters here.

## 4. Trace Example 2 by hand

Four cases. The baseline passed all four. The new prompt changes two replies:

| case | tags | must_pass | response (new prompt) | expect | passes? |
|---|---|---|---|---|---|
| refund-window | refunds | yes | "Sure, I've refunded you." | `30-day` | no |
| order-status | orders | no | "Order 1182 shipped. Tracking: 1Z999." | `tracking` | yes (case-insensitive) |
| cancel | billing | no | "Done. I've set your plan to cancel at period end." | `cancel` | yes |
| refund-damaged | refunds | no | "Sorry about that! I've issued a full refund." | `replacement` | no |

Counts: `N = 4`, `B = 4`, `P = 2`. Policy: `max_drop_pp = 30`, `min_slice = 3`.

1. **Must-pass:** refund-window is must-pass, passed on baseline and fails now: `"must_pass:refund-window"`.
2. **Overall:** `100 * (4 - 2) = 200 > 30 * 4 = 120`: `"overall"`.
3. **Slices:** billing and orders have 1 case each, refunds has 2. All are under `min_slice = 3`, so they're reported with `gated: False` and can't block, even though refunds dropped from 1.0 to 0.0.

`reasons = ["must_pass:refund-window", "overall"]`, `decision = "block"`.

**Example 1 shows the averages hiding nothing bad.** The baseline failed `cancel`, and the new prompt fixes it, while `refund-damaged` breaks. `B = P = 3`, so the overall rate is flat at 0.75. The must-pass refund-window case still passes because `"30-Day window"` contains `30-day` once lowercased. Nothing blocks.

**Example 3 shows an error.** The model times out on `order-status`. That case fails, the run continues, and the report is still produced. Overall, `100 · (2 - 1) = 100` is not greater than `50 · 2 = 100`, so the overall rule holds exactly at the limit. But `min_slice = 1` lets the one-case orders slice gate, and it dropped 100 points, so the result is `["slice:orders"]`.

## 5. Key idea: averages hide the case you care about

In "must-pass hidden by gains", the new prompt adds "Always offer a coupon." The baseline failed three cases that now pass, and the new prompt breaks one, `refunds-00`, a must-pass case. Overall the pass rate goes *up*, from 0.85 to 0.95. An average-only gate would merge this. The must-pass rule catches it: `["must_pass:refunds-00", "slice:refunds"]`. The refunds slice also dropped from 1.0 to 0.8, 20 points against a 10-point limit.

A must-pass case only regresses if it passed on the baseline. A case that was already broken in production isn't this PR's fault, so it doesn't block.

## 6. Plan before you code

```
results = {id: passes(case)} for each case in order
    passes: one call; GCError -> False; all expected substrings in lowercased text
reasons = must_pass ids where must_pass and baseline and not result, in golden order
if overall integer drop rule: append "overall"
for each tag, sorted:
    n_s, B_s, P_s; gated = n_s >= min_slice
    if gated and integer drop rule: append "slice:<tag>"
decision = "block" if reasons else "pass"
```

| rule | condition | order in `reasons` |
|---|---|---|
| must-pass | `must_pass and baseline[id] and not results[id]` | first, in golden order |
| overall | `100 * (B - P) > max_drop_pp * N` | after must-pass |
| slice | `gated and 100 * (B_s - P_s) > max_drop_pp * n_s` | last, sorted by tag |

## 7. Build it one piece at a time

**Step 1: run one case.** Put only the call inside the `try`, so a bug in your own matching code isn't swallowed:

```python
def _passes(llm, prompt, case):
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": case["input"]}]
    try:
        text = (llm.complete(messages).content or "").lower()
    except GCError:
        return False
    return all(e.lower() in text for e in case["expect"])
```

**Step 2: the shared drop rule.** One function for overall and every slice, so they can't drift apart:

```python
def _drop_blocks(base, new, n, max_drop_pp):
    return 100 * (base - new) > max_drop_pp * n
```

**Step 3: results and must-pass reasons.** A dict comprehension over `golden` calls the model in list order, which is the order the driver expects:

```python
results = {c["id"]: _passes(llm, new_prompt, c) for c in golden}
reasons = ["must_pass:%s" % c["id"] for c in golden
           if c["must_pass"] and baseline[c["id"]] and not results[c["id"]]]
```

**Step 4: slices.** Collect every tag with a set comprehension, sort it, and report every slice whether or not it's gated. In "flaky tiny slice ignored", the two-case `legal` slice drops from 1.0 to 0.5. It shows up in `slices` with `gated: False` and doesn't block.

## 8. Full solution

```python
from gc_runtime import GCError  # base class of every simulated provider failure


def _passes(llm, prompt, case):  # run one golden case against the new prompt
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": case["input"]}]  # exactly two messages
    try:  # only the model call can raise a provider error
        text = (llm.complete(messages).content or "").lower()  # None becomes ""; lowercase for case-insensitive matching
    except GCError:  # 5xx, timeout or 429
        return False  # a failed case, not a crashed CI job; no retry
    return all(e.lower() in text for e in case["expect"])  # every expected substring must appear


def _drop_blocks(base, new, n, max_drop_pp):  # one drop rule shared by overall and slices
    return 100 * (base - new) > max_drop_pp * n  # integer form of (base - new) / n > max_drop_pp / 100


def gate_prompt_change(llm, new_prompt, golden, baseline, policy):  # the CI gate for a prompt edit
    results = {c["id"]: _passes(llm, new_prompt, c) for c in golden}  # one call per case, in list order
    # critical cases that worked in production and broke now, in golden order
    reasons = ["must_pass:%s" % c["id"] for c in golden
               if c["must_pass"] and baseline[c["id"]] and not results[c["id"]]]

    n = len(golden)  # number of cases
    b = sum(1 for c in golden if baseline[c["id"]])  # production passes
    p = sum(1 for c in golden if results[c["id"]])  # new-prompt passes
    if _drop_blocks(b, p, n, policy["max_drop_pp"]):  # overall pass rate fell too far
        reasons.append("overall")  # after the must-pass reasons

    slices = {}  # tag -> slice report
    for tag in sorted({t for c in golden for t in c["tags"]}):  # every tag on any case, sorted for reason order
        ids = [c["id"] for c in golden if tag in c["tags"]]  # the cases in this slice
        bs = sum(1 for i in ids if baseline[i])  # production passes in the slice
        ps = sum(1 for i in ids if results[i])  # new passes in the slice
        gated = len(ids) >= policy["min_slice"]  # too few cases means too noisy to block
        # every slice is reported, gated or not
        slices[tag] = {"n": len(ids), "baseline": bs / len(ids), "new": ps / len(ids), "gated": gated}
        if gated and _drop_blocks(bs, ps, len(ids), policy["max_drop_pp"]):  # a big-enough slice regressed
            reasons.append("slice:%s" % tag)  # sorted by tag because the loop is

    return {  # the report CI posts on the PR
        "decision": "block" if reasons else "pass",  # any reason blocks the merge
        "reasons": reasons,  # why, in the spec's order
        "results": results,  # per-case outcome
        "pass_rate": {"baseline": b / n, "new": p / n},  # headline rates for humans
        "slices": slices,  # per-tag detail
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | pass, rates 0.75 and 0.75 | case-insensitive match; gains offset losses; small slices don't gate |
| Example 2 | block: `must_pass:refund-window`, `overall` | must-pass regression and an overall drop |
| Example 3 | block: `slice:orders` | a timeout fails one case; overall exactly at the limit; `min_slice = 1` |
| exact boundary does not block | pass, 0.8 to 0.7 with a 10-point limit | integer comparison |
| one slice regresses | block: `slice:returns` | slice rule when overall (1.0 to 0.9) is within 15 points |
| flaky tiny slice ignored | pass; `legal` at 0.5, `gated: False` | `min_slice` |
| must-pass hidden by gains | block: `must_pass:refunds-00`, `slice:refunds` | overall improved, critical case broke |
| provider errors mid-run | block: `must_pass:orders-00`, `slice:orders` | three server errors fail three cases; the run continues |
| uppercase response | pass, new rate 1.0, `max_drop_pp = 0` | uppercased replies still match |
| missing scripted reply | block: `must_pass:refund-window` only | everything fails, but `max_drop_pp = 100` can never trip the drop rules |

## 10. Complexity

The gate makes `N` model calls; that's the real cost, in latency and tokens. Everything else is counting. The slice loop scans `golden` once per tag, O(T·N) for `T` tags, which is nothing at 60 cases. You could build `tag -> ids` in one pass to make it O(total tags), but it doesn't matter at this size.

In CI, the `N` calls dominate wall time. Run them concurrently with a bounded pool, keep results in golden order, and pin the model snapshot and temperature so the baseline isn't noisy. A golden set of a few hundred cases at temperature 0 typically runs in a minute or two.

## 11. If you got Wrong Answer

- **Example 1 blocks with `must_pass:refund-window` and the new rate is 0.25.** You match case-sensitively: `30-Day` misses `30-day`, and `Tracking` misses `tracking`.
- **"exact boundary does not block" blocks on `overall`.** You subtracted float rates. Use `100 * (B - P) > max_drop_pp * N`.
- **Runtime Error, `TimeoutError_`, on Example 3.** A provider error escaped. Catch `GCError` around the call.
- **"must-pass hidden by gains" only blocks on `slice:refunds`, and "missing scripted reply" passes.** You're missing the must-pass rule.
- **Example 1 blocks on `slice:refunds`, or "flaky tiny slice ignored" blocks on `slice:legal`.** Small slices are blocking; check `gated` first.
- **The recorded messages differ.** You retried, skipped a case, or added messages. Exactly one call per case: system, then user.

## 12. Follow-ups an interviewer might ask

- *Substring checks are crude. What else would you use?* An LLM judge for open-ended cases (problem 145, llm-judge-position-swap). But keep must-pass checks deterministic, so a judge's variance can never block or unblock a PR.
- *The model itself is non-deterministic. How do you keep the baseline stable?* Pin the model snapshot, run at temperature 0, or run each case k times and gate on a pass rate like pass@k (problem 144). Otherwise `max_drop_pp` has to absorb run-to-run noise.
- *The provider ships a new model version. What happens to the baseline?* Re-baseline in a separate PR. A model change and a prompt change should never land in the same diff, or you can't tell which one broke things.
- *How do you choose `min_slice`?* From the noise you can tolerate. With `n` cases, one flip moves the slice by `100/n` points, so `min_slice` should make one flip smaller than `max_drop_pp`.
- *What tools do this?* promptfoo, OpenAI Evals, LangSmith and Braintrust all run this loop in CI. The design question is always what blocks, and must-pass cases plus slice-gated drops is the common answer.
