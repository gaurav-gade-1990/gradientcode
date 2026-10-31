## Approach

LoRA freezes the pretrained weight $W$ and learns a low-rank update $\Delta W = \tfrac{\alpha}{r} A B$. Only $A$ and $B$ train, which is $r(d_{in} + d_{out})$ parameters instead of $d_{in} d_{out}$.

$$
y = x W + \tfrac{\alpha}{r}\,(x A) B, \qquad W' = W + \tfrac{\alpha}{r} A B
$$

```python
def lora_forward_and_merge(x, W, A, B, alpha):
    scale = alpha / A.shape[1]
    y = x @ W + scale * ((x @ A) @ B)
    W_merged = W + scale * (A @ B)
    return y, W_merged
```

During training, compute `(x @ A) @ B`: it goes through an `(N, r)` bottleneck and never forms the full `d_in x d_out` update. For inference, merge once so the adapter costs nothing: `x @ W_merged` equals `y`.

### Why alpha / r?

The scale keeps the size of the update roughly independent of the rank, so you can change `r` without retuning the learning rate. `B` is initialized to zero, so training starts exactly at the pretrained model.

## Common mistakes

- **Scaling by `alpha` alone.** The scale is `alpha / r`.
- **Merging without the scale.** Then `x @ W_merged` no longer equals `y`.
- **Reading the rank from the wrong axis.** `r` is `A.shape[1]` (equivalently `B.shape[0]`), not `B.shape[1]`.

## Complexity

- **Time:** $O(N d_{in} d_{out} + N r (d_{in} + d_{out}))$ for the forward, $O(d_{in} r d_{out})$ for the merge.
- **Space:** $O(N r)$ extra for the bottleneck, plus $O(d_{in} d_{out})$ for the merged weight.
