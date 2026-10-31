## Approach: build a graph, then walk it backward

Every operation creates a new `Value` that remembers:

1. its **children**, the inputs it was computed from, and
2. a `_backward` closure. Given `out.grad`, the closure adds the local derivative times `out.grad` to each child's grad.

That's the **chain rule** applied one edge at a time.

| op | local gradient |
|---|---|
| $a + b$ | $1, 1$ |
| $a \cdot b$ | $b, a$ |
| $a^k$ | $k a^{k-1}$ |
| $\tanh a$ | $1 - \tanh^2 a$ |
| $\text{relu}(a)$ | $[a > 0]$ |
| $e^a$ | $e^a$ |

### Why `+=`?

If a node feeds several downstream nodes, its total derivative is the **sum over paths** (the multivariate chain rule). Writing `=` keeps only the last path. That's why `a * a + a` gives the wrong gradient.

### Why topological order?

A node's `_backward` must run only after its grad is final, meaning after every node that consumes it has pushed its contribution. A DFS post-order from the output, reversed, guarantees exactly that. A naive stack walk can visit a shared node before all its consumers have finished.

```python
def backward(self):
    order, seen = [], set()
    def build(v):
        if v not in seen:
            seen.add(v)
            for c in v._prev:
                build(c)
            order.append(v)
    build(self)
    self.grad = 1.0
    for v in reversed(order):
        v._backward()
```

## Complexity

- **Time:** $O(V + E)$ for both the forward build and the backward pass. That's the same order as evaluating the expression.
- **Space:** $O(V)$ for the graph and the topological order.

This is the core idea behind PyTorch's autograd. PyTorch applies it to tensors instead of scalars.
