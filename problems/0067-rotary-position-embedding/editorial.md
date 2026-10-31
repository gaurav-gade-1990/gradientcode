## Approach: rotate each pair by a position-dependent angle

RoPE treats the features as $d/2$ two-dimensional pairs and rotates pair $i$ by the angle $p\,\theta_i$. In the half-split layout, pair $i$ is feature $i$ together with feature $i + d/2$:

$$
\begin{pmatrix} x_1' \\ x_2' \end{pmatrix} = \begin{pmatrix} \cos\phi & -\sin\phi \\ \sin\phi & \cos\phi \end{pmatrix} \begin{pmatrix} x_1 \\ x_2 \end{pmatrix}, \qquad \phi = p \cdot \text{base}^{-2i/d}
$$

```python
def apply_rope(x, positions, base=10000.0):
    d = x.shape[-1]
    half = d // 2
    theta = base ** (-np.arange(half) * 2.0 / d)
    phi = np.asarray(positions, dtype=float)[:, None] * theta[None, :]
    cos, sin = np.cos(phi), np.sin(phi)
    x1, x2 = x[..., :half], x[..., half:]
    return np.concatenate([x1 * cos - x2 * sin, x2 * cos + x1 * sin], axis=-1)
```

`cos` and `sin` have shape `(T, d/2)`, which broadcasts against `(..., T, d/2)` for any number of leading batch and head axes.

### Why it encodes relative position

A rotation by $\alpha$ followed by the transpose of a rotation by $\beta$ is a rotation by $\alpha - \beta$. So for a query at position $m$ and a key at position $n$:

$$
\langle R_m q, R_n k \rangle = \langle q, R_{n-m} k \rangle
$$

The attention score depends only on the offset $n - m$, yet each vector was rotated independently. That property is what lets you rotate keys once and keep them in a KV cache.

## Common mistakes

- **Interleaved pairs.** The original paper and GPT-J pair feature $2i$ with $2i + 1$. That's a valid convention, but it isn't the one specified, and checkpoints trained with one break under the other.
- **Rotating clockwise.** Swapping the signs is still a rotation and still relative, but it is not the standard one.
- **Using the array index as the position.** During decoding with a cache, the new token sits at position `cache_len`, not `0`.

## Complexity

- **Time:** $O(n)$ for $n$ elements of `x`, plus $O(T d)$ for the trig tables.
- **Space:** $O(n)$ for the output. There are no learned parameters.
