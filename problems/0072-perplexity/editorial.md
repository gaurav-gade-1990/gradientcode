## Approach: exponentiate the token-level mean NLL

Perplexity is $e^{\text{cross-entropy}}$, where the cross-entropy is averaged over every real token. It reads as an effective branching factor: a perplexity of $k$ means the model is as uncertain as a uniform choice among $k$ tokens.

$$
\operatorname{PPL} = \exp\left(-\frac{1}{N} \sum_{\text{real } (b,t)} \log p_{bt}\right), \qquad N = \sum_{b,t} m_{bt}
$$

```python
def perplexity(logprobs, mask):
    total = np.where(mask, logprobs, 0.0).sum()
    return float(np.exp(-total / mask.sum()))
```

`np.where` *selects* values, so a `-inf` at a padded position never enters the arithmetic. `logprobs * mask` computes `-inf * 0 = nan` first, and the `nan` spreads into the sum.

### Pooled, not per sequence

Pooling every token gives each token equal weight, which is how papers and `lm-eval` report corpus perplexity. Averaging per-sequence NLLs first gives short sequences as much weight as long ones. Averaging per-sequence *perplexities* is worse still, because $e^x$ is convex and the mean overweights the worst sequences. Both disagree with the pooled number whenever lengths differ.

## Common mistakes

- **Ignoring the mask.** Padding adds fake tokens to the count, and whatever values they hold to the sum.
- **Multiplying by the mask** when padding can be `-inf`.
- **Per-sequence averaging**, of either the NLL or the perplexity.

## Complexity

- **Time:** $O(BT)$.
- **Space:** $O(BT)$ for the masked copy. A running sum avoids it.
