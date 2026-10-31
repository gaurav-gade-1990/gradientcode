Implement a **numerical gradient check**: the standard way to test a hand-written backward pass.

`f` is a function that takes a float array shaped like `x` and returns a scalar. Estimate its gradient at `x` with **central differences**, one element at a time:

$$
n_k = \frac{f(x + h\,e_k) - f(x - h\,e_k)}{2h}
$$

where $e_k$ is the array with a `1` at index $k$ and `0` elsewhere. Then compare the estimate $n$ with the given `analytic_grad` $a$ using the relative error

$$
\text{rel\_error} = \frac{\lVert a - n \rVert_2}{\max\left(\lVert a \rVert_2 + \lVert n \rVert_2,\; 10^{-12}\right)}
$$

where $\lVert \cdot \rVert_2$ is the Euclidean norm over all elements.

Return a tuple `(num_grad, rel_error)`: an array with the shape of `x`, and a float.

You may perturb `x` in place, but it must hold its **original values** when `grad_check` returns. The judge checks this.

The judge builds `f` from expressions such as `np.sum(x ** 3)` or `np.log(np.sum(np.exp(x)))` and passes in an `analytic_grad`, which is sometimes deliberately wrong. It compares your gradient, your relative error, and `x` after the call.

**Constraints**

- `x` is a float64 array of any shape with at most 64 elements
- `analytic_grad` has the same shape as `x`
- `h = 1e-5` unless a case sets it
