Compute the loss and gradients for one training pair of **word2vec skip-gram with negative sampling** (Mikolov et al., 2013).

There are two embedding tables of shape `(V, d)`: `W_in` holds the center (input) vectors and `W_out` holds the context (output) vectors. For one `(center, context)` pair and `K` sampled negative word indices $n_1, \dots, n_K$, let $v = W_{\text{in}}[\text{center}]$, $u_o = W_{\text{out}}[\text{context}]$ and $u_k = W_{\text{out}}[n_k]$. The loss is

$$
L = -\log\sigma(u_o^\top v) - \sum_{k=1}^{K}\log\sigma(-u_k^\top v), \qquad \sigma(x) = \frac{1}{1 + e^{-x}}
$$

Return a tuple `(loss, dW_in, dW_out)`:

- `loss` is a Python float.
- `dW_in` and `dW_out` have the same shapes as `W_in` and `W_out` and hold $\partial L / \partial W_{\text{in}}$ and $\partial L / \partial W_{\text{out}}$. Rows that the loss doesn't touch are zero.

Treat each entry of `negatives` as its own term, even when an index repeats or equals `context`. Its gradient adds to the same row of `dW_out`.

Your loss must stay finite when $|u^\top v|$ is large (up to a few thousand), where `np.exp` overflows.

**Constraints**

- `2 <= V <= 50`, `1 <= d <= 16`, `1 <= K <= 10`
- `0 <= center, context, negatives[k] < V`
- Don't modify the inputs in place
