Build a tiny **reverse-mode automatic differentiation** engine over scalars.

Implement a class `Value` that wraps a Python float. It needs:

- `Value(data)`, with attributes `.data` (a float) and `.grad` (starts at `0.0`).
- Operators that return new `Value`s and record how they were made: `+`, `*`, `-` (binary and unary), `/`, and `** k`, where `k` is an int or float constant. Each must work with plain numbers on either side, e.g. `2 * a` and `a + 1`.
- Methods `.tanh()`, `.relu()` and `.exp()`.
- `.backward()`. It sets the output's grad to `1` and fills `.grad` on every `Value` that the output depends on with $\partial \text{out} / \partial \text{node}$.

The judge builds an expression from your `Value`s, calls `backward()` on the result, and compares `out.data` with the `.grad` of each input.

A `Value` can be used more than once in an expression, for example `a * a + a`. Your gradients must account for every path through the graph.

**Constraints**

- Expressions have at most 200 operations
- Use `relu(0) = 0`, with gradient `0` at `0`
