Compute the **perplexity** of a language model on a padded batch.

`logprobs[b, t]` is the natural-log probability the model gave to the actual token at position `t` of sequence `b`. `mask[b, t]` is `True` for real tokens and `False` for padding. Perplexity is the exponential of the mean negative log-likelihood over **all real tokens in the batch**:

$$
\operatorname{PPL} = \exp\left(-\frac{\sum_{b,t} m_{bt} \, \log p_{bt}}{\sum_{b,t} m_{bt}}\right)
$$

Padding positions contribute nothing, whatever value they hold. They may contain `0`, garbage, or `-inf`.

Return a Python `float`.

**Constraints**

- `logprobs` is a float array of shape `(B, T)`, and `mask` is a boolean array of the same shape
- `1 <= B, T <= 64`
- At least one position is real, and every real position holds a finite value `<= 0`
