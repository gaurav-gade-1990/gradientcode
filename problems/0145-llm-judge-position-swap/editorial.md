## Approach

A pairwise judge has a well-documented position bias: given two similar answers, many models favor whichever they see first. Swapping the order exposes it. A verdict counts only if it survives the swap.

```python
ab = _ask(judge, q, candidate, baseline)    # slot 1 = candidate
ba = _ask(judge, q, baseline, candidate)    # slot 1 = baseline
w_ab = {"1": "candidate", "2": "baseline"}.get(ab, "tie")
w_ba = {"1": "baseline", "2": "candidate"}.get(ba, "tie")
final = w_ab if w_ab == w_ba else "tie"
biased = ab == ba and ab in ("1", "2")      # the same slot won twice
```

Then decide whether to trust the judge before you trust its score. Cohen's kappa corrects raw agreement for chance:

$$
\kappa = \frac{p_o - p_e}{1 - p_e}, \qquad p_e = \sum_{\ell} \frac{\text{judge}_\ell}{m}\cdot\frac{\text{human}_\ell}{m}
$$

A judge that says "candidate" every time agrees 80% with labels that are 80% "candidate", and its kappa is 0.

## Common mistakes

- **One order only.** Then you're measuring the judge's slot preference as much as the models. Calling once and "inferring" the swap hides exactly the bias you need to see.
- **Not flipping the swapped answer.** In the second call, "1" means the baseline won. If you forget, a judge that always says "1" looks perfectly consistent and splits wins evenly.
- **Dropping inconsistent pairs.** The pairs a judge can't decide are often near-ties. Removing them inflates the win rate in favor of whichever side wins the clear cases.
- **Raw agreement as kappa.** It rewards a judge for matching the label distribution, not the labels.
- **Substring parsing.** "Response 2 is better than response 1" contains both digits. Ask for a strict format and treat anything else as a parse error you can count and alert on.

## Production notes

- MT-Bench and Chatbot Arena's judge work (Zheng et al., 2023) report position bias in GPT-4 judges and use exactly this swap-and-tie rule. AlpacaEval randomizes the order instead and calibrates for length bias.
- Keep a human-labeled calibration set (100 to 300 pairs is common) and re-run kappa whenever the judge model or the judge prompt changes. A judge prompt is code: version it and gate it like any other prompt (see `prompt-regression-gate`).
- Use structured output (a JSON schema or a tool call with an enum) for the verdict, at temperature 0, and log the judge's rationale separately for debugging. Never parse free text into a release decision.
- For a ship decision, put a confidence interval on the score (bootstrap over pairs), or run a sign test on the consistent wins and losses, as in `ab-test-significance`.
