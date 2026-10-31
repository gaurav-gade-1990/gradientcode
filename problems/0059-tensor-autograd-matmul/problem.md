Extend scalar autograd to **arrays**. Implement a class `Tensor` that wraps a NumPy array and supports reverse-mode differentiation through matrix multiplication and broadcasting.

It needs:

- `Tensor(data)`, with `.data` (a float64 `ndarray`) and `.grad` (an array of zeros with the same shape as `.data`).
- `a + b` and `a * b`: elementwise, with **NumPy broadcasting**. Either side can be a `Tensor` or a plain Python number, e.g. `x + 1` and `2 * x`.
- `a @ b`: matrix product of two **2-D** Tensors, `(n, k) @ (k, m) -> (n, m)`.
- `.relu()`: elementwise $\max(x, 0)$, with gradient `0` at `0`.
- `.sum()` and `.mean()`: reduce **all** elements to a 0-d Tensor (shape `()`).
- `-a`, `a - b` and `1 - a`, which the starter derives from `+` and `*`.
- `.backward()`, called on a Tensor with a single element. It sets that Tensor's grad to `1` and fills `.grad` on every Tensor it depends on with $\partial\,\text{out} / \partial\,\text{tensor}$. Each grad has the **same shape** as its Tensor's `.data`.

The judge wraps each named input array in your `Tensor`, evaluates an expression such as `((x @ W1 + b1).relu() @ W2 + b2 - y)`, reduces it to a scalar loss, calls `backward()`, and compares the loss with each input's `.grad`.

A Tensor can be used more than once, as in `x * x` or a layer output feeding two branches. When an operand was broadcast in the forward pass (a bias of shape `(m,)` added to an `(n, m)` matrix), its gradient must be summed back to its own shape.

**Constraints**

- Inputs have `0 <= ndim <= 2`, and `@` is only applied to 2-D Tensors
- Expressions have at most 50 operations; arrays have at most 64 elements
