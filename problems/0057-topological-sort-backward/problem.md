You are given a scalar **computation graph** as a list of `n` nodes. Node `i` has an operation `ops[i]` and a list of parent node indices `parents[i]`. Compute every node's value, then the gradient of node `output` with respect to every node.

The nodes are **not** listed in topological order: a parent can have a larger index than its child. The graph is guaranteed to be acyclic.

| op | parents | value |
|---|---|---|
| `"input"` | none | `inputs[i]` |
| `"add"` | `[a, b]` | $a + b$ |
| `"sub"` | `[a, b]` | $a - b$ |
| `"mul"` | `[a, b]` | $a \cdot b$ |
| `"div"` | `[a, b]` | $a / b$ |
| `"neg"` | `[a]` | $-a$ |
| `"exp"` | `[a]` | $e^a$ |
| `"log"` | `[a]` | $\ln a$ |
| `"tanh"` | `[a]` | $\tanh a$ |
| `"sigmoid"` | `[a]` | $1 / (1 + e^{-a})$ |
| `"relu"` | `[a]` | $\max(a, 0)$, with gradient $0$ at $a = 0$ |

`inputs` maps each `"input"` node's index to its float value. A node can list the same parent twice, e.g. `mul` with parents `[3, 3]` computes $x_3^2$.

Return a tuple `(values, grads)` of two float arrays of length `n`:

- `values[i]` is the value of node `i`. Compute it for **every** node, including ones the output doesn't depend on.
- `grads[i]` is $\partial\, \text{values[output]} / \partial\, \text{values[i]}$, treating node `i` as a variable and holding everything upstream of it fixed. `grads[output] = 1`. A node the output does not depend on (including the output's own descendants) has gradient `0`.

**Constraints**

- `1 <= n <= 300`
- The graph is a DAG, and every parent index is in `[0, n)`
- Every `log` argument is positive and every `div` denominator is nonzero
