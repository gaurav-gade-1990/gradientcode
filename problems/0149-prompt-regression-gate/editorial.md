## Approach

The gate has two halves: run the golden set exactly the way production would, then apply the blocking rules with no rounding surprises.

```python
def _passes(llm, prompt, case):
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": case["input"]}]
    try:
        text = (llm.complete(messages).content or "").lower()
    except GCError:
        return False
    return all(e.lower() in text for e in case["expect"])
```

Then there are three independent checks. Must-pass regressions come first because they're the ones an average hides. Then the overall drop and each slice drop, all in integer arithmetic:

```python
def _drop_blocks(base, new, n, max_drop_pp):
    return 100 * (base - new) > max_drop_pp * n
```

That's the same inequality as `base/n - new/n > max_drop_pp/100`, multiplied through by `100 n`, so it's exact.

## Common mistakes

- **Float rate subtraction.** `0.8 - 0.7` is `0.10000000000000009`, so a drop of exactly 10 points against a 10-point limit blocks the PR. CI gates that flap on rounding train people to ignore them.
- **Letting tiny slices block.** With 2 cases in a slice, one flaky case is a 50-point drop. The minimum slice size exists so the gate only speaks when it has evidence.
- **No must-pass check.** A prompt edit that fixes five easy cases and breaks the refund-policy case nets out positive on average and ships a compliance incident.
- **Crashing on a provider error.** A 5xx is one failed case. If it kills the job, people re-run CI until it's green, and the gate stops meaning anything.
- **Case-sensitive matching.** "30-Day" vs "30-day" is formatting drift, not a regression.

## Production notes

- Tools like promptfoo, OpenAI Evals, LangSmith and Braintrust all run this loop in CI. The design question is what blocks, and the answer here (must-pass cases, plus relative drops gated by slice size) is the common shape.
- Substring checks are cheap and deterministic. Add an LLM judge for open-ended cases (see `llm-judge-position-swap`), but keep must-pass checks deterministic so a judge's mood can't block a PR.
- Run each case a few times at the production temperature, or at temperature 0 with a pinned model snapshot. Otherwise the baseline itself is noisy, and your `max_drop_pp` has to absorb that noise.
- Store the baseline per prompt version and model snapshot. When the provider updates the model, re-baseline in a separate PR, so that a model change and a prompt change never land in the same diff.
