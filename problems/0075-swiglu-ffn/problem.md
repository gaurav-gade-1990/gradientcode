Implement the **SwiGLU** feed-forward block used in LLaMA and PaLM (Shazeer, 2020).

$$
\operatorname{FFN}(x) = \big(\operatorname{SiLU}(x W_1) \odot (x W_3)\big)\, W_2,
\qquad \operatorname{SiLU}(z) = z\,\sigma(z) = \frac{z}{1 + e^{-z}}
$$

$x W_1$ is the **gate**: SiLU is applied to it. $x W_3$ is the **value**: it is not activated. $\odot$ is the elementwise product. There are no biases.

`x` has shape `(..., d)`. Return an array of shape `(..., d)`.

**Constraints**

- `x` is a float array with `1 <= x.ndim <= 3`, last axis of size `d`
- `W1` and `W3` have shape `(d, h)`; `W2` has shape `(h, d)`
- `1 <= d, h <= 128`
- Gate pre-activations satisfy `|x W1| <= 50`
