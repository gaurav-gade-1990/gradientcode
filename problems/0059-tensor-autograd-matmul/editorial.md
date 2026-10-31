## Approach: the scalar engine, with shapes

The structure is the scalar `Value` engine's. Each op returns a new `Tensor` holding its parents and a `_backward` closure, and `backward()` runs the closures in reverse topological order. Two things change once the values are arrays.

**1. Matmul's local gradient is a matrix product.** For $C = AB$ with upstream gradient $G = \partial L/\partial C$:

$$
\frac{\partial L}{\partial A} = G B^\top, \qquad \frac{\partial L}{\partial B} = A^\top G
$$

Check the shapes: $G$ is $(n, m)$, $B^\top$ is $(m, k)$, so $GB^\top$ is $(n, k)$, the shape of $A$.

**2. Broadcasting has to be undone.** If `b` has shape `(m,)` and was added to an `(n, m)` matrix, each element of `b` was used $n$ times, so its gradient is the sum of $n$ upstream values. Every broadcasting op passes its gradient through `unbroadcast` before accumulating.

| op | gradient sent to each input |
|---|---|
| $a + b$ | `unbroadcast(G, shape)` |
| $a \odot b$ | `unbroadcast(G * other, shape)` |
| $A B$ | $G B^\top$, $A^\top G$ |
| relu | `G * (a > 0)` |
| sum / mean | `G * ones` / `G * ones / N` |

```python
def __matmul__(self, other):
    out = Tensor(self.data @ other.data, (self, other), "@")
    def _backward():
        self.grad += out.grad @ other.data.T
        other.grad += self.data.T @ out.grad
    out._backward = _backward
    return out

def __add__(self, other):
    other = other if isinstance(other, Tensor) else Tensor(other)
    out = Tensor(self.data + other.data, (self, other), "+")
    def _backward():
        self.grad += _unbroadcast(out.grad, self.data.shape)
        other.grad += _unbroadcast(out.grad, other.data.shape)
    out._backward = _backward
    return out
```

`backward()` seeds the output with `np.ones_like(self.data)` and walks the DFS post-order in reverse, exactly as in the scalar engine.

## Common mistakes

- **No unbroadcast.** The bias gradient comes back with the batch dimension still on it. Its shape no longer matches the parameter.
- **`=` instead of `+=`.** `x * x`, a weight shared by two layers, and a hidden layer that feeds two branches all need gradients summed over paths.
- **Mean without $1/N$.** `mean()`'s gradient is `1/N` per element, and that factor is easy to drop when you copy the `sum()` code.
- **Relu at zero.** The mask is `a > 0`, so exactly-zero inputs pass no gradient. `>=` passes the full gradient there.

## Complexity

- **Time:** the backward pass costs about as much as the forward pass. Each matmul's backward is two matmuls, so about 2x the forward FLOPs.
- **Space:** every intermediate `.data` is kept alive until `backward()` runs. That activation memory is what gradient checkpointing trades for recomputation.
