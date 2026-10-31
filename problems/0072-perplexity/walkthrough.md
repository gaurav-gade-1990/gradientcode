## 1. What the problem is really asking

Perplexity is the headline number for a language model: how surprised it is, on average, by real text. It's the exponential of the cross-entropy, and it reads as an **effective branching factor**. A perplexity of 4 means the model is as unsure as if it were choosing uniformly among 4 tokens at every step.

Strip the story and the problem is **a masked mean followed by `exp`**. The batch is padded to a rectangle, so some positions are not real tokens. The two things to get right are what you average over (every real token in the batch pooled together, not per sequence) and how you exclude padding (by selecting, not multiplying, because padding may hold `-inf`). The judge compares a single float at `rtol = 1e-9`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `logprobs` | `(B, T)` float | `log p` of the actual token at each position | summed over real positions |
| `mask` | `(B, T)` bool | `True` for real tokens, `False` for padding | selects positions and counts them |

Easy to miss:

- **Padding can hold anything**: `0`, `-50`, or `-inf`. Your result must not depend on it at all.
- **`0 * -inf` is `nan`** in IEEE arithmetic. So `logprobs * mask` turns every `-inf` padding position into `nan`, and the sum becomes `nan`.
- **The denominator is the number of real tokens**, `mask.sum()`, not `B * T` and not `B`.
- **A whole row can be padding.** "one real token" has a second sequence with no real tokens at all. Per-sequence averaging divides by zero there.

## 3. The math

Let $N = \sum_{b,t} m_{bt}$ be the number of real tokens. The mean negative log-likelihood (the cross-entropy per token, in nats) is

$$
\text{NLL} = -\frac{1}{N} \sum_{b,t} m_{bt} \log p_{bt}, \qquad \operatorname{PPL} = e^{\text{NLL}} .
$$

**Why it's a branching factor.** Pull the exponential inside the sum:

$$
\operatorname{PPL} = \exp\!\left(-\frac{1}{N} \sum \log p\right) = \left(\prod_{\text{real}} p\right)^{-1/N} = \left(\prod_{\text{real}} \frac{1}{p}\right)^{1/N}.
$$

So perplexity is the **geometric mean of $1/p$** over real tokens. If the model gives every token probability $1/k$, the geometric mean of $k$ is $k$. A perfect model ($p = 1$ everywhere, "perfect model") has perplexity 1. Perplexity is never below 1, because every $\log p \le 0$.

**Why pooled and per-sequence means differ.** Say sequence $b$ has $n_b$ real tokens and mean NLL $\ell_b$. The pooled NLL is a weighted average,

$$
\text{NLL} = \frac{\sum_b n_b \ell_b}{\sum_b n_b},
$$

with weight $n_b$. Averaging $\ell_b$ with equal weights gives short sequences too much say. Averaging per-sequence perplexities $e^{\ell_b}$ is worse: since $e^x$ is convex, Jensen's inequality gives $\frac{1}{B}\sum_b e^{\ell_b} \ge e^{\frac{1}{B}\sum_b \ell_b}$, so the mean of perplexities is pulled up by the worst sequences.

**Sensitivity.** Differentiating $\log \operatorname{PPL} = \text{NLL}$ with respect to one real log-probability gives

$$
\frac{\partial \log \operatorname{PPL}}{\partial \log p_{bt}} = -\frac{m_{bt}}{N}.
$$

Every real token has the same weight $1/N$, and padding has weight 0. That's the precise sense in which "every token counts equally".

**Numerics.** Work in log space throughout: the product form underflows for long texts. The sum of logs is finite because every real value is finite, and `np.where(mask, logprobs, 0.0)` never evaluates arithmetic on the padding.

## 4. Trace Example 2 by hand

`logprobs` and `mask`, both `(2, 3)`:

| sequence | position 0 | position 1 | position 2 |
|---|---|---|---|
| 0 | `ln 0.5`, real | `ln 0.5`, real | `0`, pad |
| 1 | `ln 0.125`, real | `0`, pad | `0`, pad |

`np.where(mask, logprobs, 0.0)` keeps the three real values and puts `0` everywhere else. The sum is $\ln 0.5 + \ln 0.5 + \ln 0.125 = -(1 + 1 + 3)\ln 2 = -5 \ln 2$. There are $N = 3$ real tokens, so

$$
\text{NLL} = \tfrac{5}{3}\ln 2 = 1.1552, \qquad \operatorname{PPL} = 2^{5/3} = 3.1748 .
$$

Compare the two per-sequence variants on the same batch:

| method | computation | result |
|---|---|---|
| pooled (correct) | $\exp(\frac{5}{3}\ln 2)$ | `3.1748` |
| mean of sequence NLLs | $\exp(\frac{\ln 2 + 3\ln 2}{2}) = e^{2\ln 2}$ | `4` |
| mean of sequence perplexities | $\frac{2 + 8}{2}$ | `5` |
| ignore the mask | $\exp(\frac{5\ln 2}{6})$ | `1.7818` |

The pooled answer gives sequence 0's two tokens twice the weight of sequence 1's one token. The per-sequence NLL mean gives the two sequences equal weight, and the perplexity mean is larger still, as Jensen predicts. Ignoring the mask counts three fake tokens with log-probability 0 (certainty), which makes the model look far better than it is.

**"one real token"** has one real value, `-2`, and every other position `-inf`. The answer is $e^{2} = 7.389$. Multiplying by the mask gives `nan`, and the mean-of-sequence-NLLs version divides sequence 1's `0` by its `0` real tokens and also returns `nan`.

## 5. Key idea: select, don't multiply

`np.where(mask, logprobs, 0.0)` builds a new array by choosing, element by element, either the log-probability or `0.0`. The `-inf` at a padded position is never used in arithmetic, so it can't produce `nan`. `logprobs * mask` first converts the mask to `0.0` and `1.0`, then multiplies, and `-inf * 0.0 = nan`. The two are identical when padding is finite, which is why "uneven lengths" and "garbage in padding" (padding `0` and `-50`) don't catch the multiply bug, and only the `-inf` cases do. Boolean indexing, `logprobs[mask].mean()`, also selects and passes every case.

## 6. Plan before you code

```
total = sum of logprobs where mask, 0 elsewhere     # a scalar, <= 0
N     = mask.sum()                                  # number of real tokens, >= 1
return float(exp(-total / N))
```

| design choice | correct | wrong |
|---|---|---|
| exclude padding | `np.where(mask, lp, 0.0)` | `lp * mask` |
| denominator | `mask.sum()` | `lp.size` or `B` |
| averaging | pooled over all real tokens | per sequence, then mean |
| where `exp` goes | once, at the end | per sequence |

## 7. Build it one piece at a time

**Step 1: the masked total.** The result of `np.where` is `(B, T)`; `.sum()` with no axis reduces it to a scalar.

```python
total = np.where(mask, logprobs, 0.0).sum()     # (B, T) -> scalar; padding contributes exactly 0
```

**Step 2: count and exponentiate.** `mask.sum()` counts `True` values as an integer. Dividing a float by it is ordinary float division.

```python
return float(np.exp(-total / mask.sum()))       # mean NLL over real tokens, then exp
```

`float(...)` turns the NumPy scalar into the Python `float` the problem asks for.

## 8. Full solution

```python
# arrays in, Python float out
import numpy as np


# exp of the mean negative log-likelihood over every real token in the batch
def perplexity(logprobs, mask):
    total = np.where(mask, logprobs, 0.0).sum()  # select real positions; -inf padding never enters arithmetic
    return float(np.exp(-total / mask.sum()))  # pooled mean NLL over the real-token count, then exp
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `4` | every token at probability 1/4 gives a branching factor of 4 |
| Example 2 | `3.1748` | pooled averaging over sequences of different lengths |
| no padding | `2.30685` | an all-`True` mask; still breaks mean-of-perplexities |
| padding holds -inf | `2.78755` | `np.where` instead of multiplying |
| uneven lengths | `2.23153` | lengths 1 to 20 with padding `0` |
| garbage in padding | `2.53243` | padding `-50` must not count |
| one real token | `7.38906` | one real value `-2`, a fully padded row |
| perfect model | `1` | `log p = 0` everywhere |
| large batch | `2.67953` | `(20, 40)` with `-inf` padding |

## 10. Complexity

$O(BT)$ time, and $O(BT)$ memory for the masked copy. You could avoid the copy with `np.sum(logprobs, where=mask)`, but at this size it doesn't matter. At scale, perplexity is computed over a whole evaluation set streamed in batches. Keep two running totals, the masked log-probability sum and the real-token count, and take `exp(-sum / count)` at the end. Averaging each batch's perplexity instead repeats the per-sequence mistake at the batch level.

## 11. If you got Wrong Answer

- **The result is `nan` on "padding holds -inf", "one real token" and "large batch".** You multiplied by the mask, and `0 * -inf` is `nan`. Use `np.where`.
- **Example 2 gives `4`.** You averaged per-sequence NLLs. "one real token" also gives `nan`, from a `0 / 0` on the empty row.
- **Example 2 gives `5`.** You averaged per-sequence perplexities. Even "no padding" fails, because equal-length sequences still have different perplexities and the mean of `exp` isn't the `exp` of the mean.
- **Example 2 gives `1.7818`, "garbage in padding" gives `2.48e+08`.** You ignored the mask, so padding values and count both leak in.

## 12. Follow-ups an interviewer might ask

- *How do you compare perplexities of models with different tokenizers?* You can't directly: a model with longer tokens predicts fewer, harder tokens. Normalize per byte or per word instead, for example bits per byte $= \frac{\sum -\log_2 p}{\text{number of bytes}}$.
- *How do you evaluate a document longer than the context window?* Slide the window with a stride and score only the tokens that have enough left context in each window, so every token is scored once with as much context as possible.
- *What's the relationship to cross-entropy loss?* The training loss is exactly the mean NLL in nats, so $\operatorname{PPL} = e^{\text{loss}}$. A loss of 2.0 is a perplexity of 7.39, which is "one real token" here.
- *Where do the log-probabilities come from?* A log-softmax of the logits at each position, gathered at the next token's id, computed stably with log-sum-exp (problem 2).
