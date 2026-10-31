## Approach: sort, sweep forward, sweep back

Reverse-mode autodiff is two sweeps over the same order.

1. **Topological sort.** Every node must come after its parents. Kahn's algorithm counts each node's in-degree, starts from the zero-in-degree nodes (the inputs), and releases a child once all its parents are done.
2. **Forward.** Walk the order and compute each value from its parents' values.
3. **Backward.** Set `grads[output] = 1` and walk the order in **reverse**. When you reach node $i$, every node that consumes it has already been processed, so `grads[i]` is final. Push it to the parents with the chain rule:

$$
\bar x_p \mathrel{+}= \bar x_i \cdot \frac{\partial x_i}{\partial x_p}
$$

| op | local derivatives |
|---|---|
| $a+b$, $a-b$ | $1,\ \pm 1$ |
| $a b$ | $b,\ a$ |
| $a / b$ | $1/b,\ -a/b^2$ |
| $e^a$, $\ln a$ | $e^a$, $1/a$ |
| $\tanh a$, $\sigma(a)$ | $1 - y^2$, $y(1 - y)$ |

```python
order = topo_order(parents)
for i in order:
    values[i] = forward(ops[i], [values[p] for p in parents[i]])
grads[output] = 1.0
for i in reversed(order):
    xs = [values[p] for p in parents[i]]
    for p, d in zip(parents[i], local_grads(ops[i], xs, values[i])):
        grads[p] += grads[i] * d
```

Iterating over parent **slots** with `zip` handles `mul(a, a)` for free: $a$ receives $a$ twice, for a total of $2a$.

## Common mistakes

- **Trusting the index order.** The nodes are shuffled. Running forward over `range(n)` reads parents that haven't been computed yet.
- **`=` instead of `+=`.** A node with several consumers (or one consumer that uses it twice) needs the sum over all paths.
- **BFS from the output.** Visiting each node once in breadth-first order can process a shared node while a longer path to it hasn't delivered its gradient yet. Only reverse topological order guarantees that a node's gradient is complete when it's propagated.

## Complexity

- **Time:** $O(V + E)$ for the sort and for each sweep.
- **Space:** $O(V + E)$ for the child lists, the order, and the values and gradients.
