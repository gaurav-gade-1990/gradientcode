Implement five common activation functions and their derivatives, applied elementwise to an array `x`.

$$
\begin{aligned}
\sigma(x) &= \frac{1}{1 + e^{-x}}, & \sigma'(x) &= \sigma(x)\,(1 - \sigma(x)) \\
\tanh(x), & & \tanh'(x) &= 1 - \tanh^2(x) \\
\operatorname{relu}(x) &= \max(0, x), & \operatorname{relu}'(x) &= [x > 0] \\
\operatorname{leaky}(x) &= \begin{cases} x & x > 0 \\ \alpha x & x \le 0 \end{cases}, & \operatorname{leaky}'(x) &= \begin{cases} 1 & x > 0 \\ \alpha & x \le 0 \end{cases}
\end{aligned}
$$

For **GELU**, use the tanh approximation, with $c = \sqrt{2/\pi}$ and $u = c\,(x + 0.044715\,x^3)$:

$$
\operatorname{gelu}(x) = \tfrac12\, x\, (1 + \tanh u)
$$

You derive $\operatorname{gelu}'(x)$ yourself. It is the exact derivative of the formula above, not of the erf-based GELU.

Return a dict with exactly these ten keys, each an array with the same shape as `x`:

`"sigmoid"`, `"d_sigmoid"`, `"tanh"`, `"d_tanh"`, `"relu"`, `"d_relu"`, `"leaky_relu"`, `"d_leaky_relu"`, `"gelu"`, `"d_gelu"`.

The derivatives at exactly `x = 0` are defined above: `d_relu` is `0` and `d_leaky_relu` is `alpha`. The sigmoid must not produce `nan` or overflow warnings for inputs like `±1000`.

**Constraints**

- `x` is a float array of any shape, with `-1000 <= x <= 1000`
- `0 <= alpha < 1`
