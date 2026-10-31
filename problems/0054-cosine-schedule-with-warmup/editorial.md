## Approach

Large models diverge if they start at full learning rate, because Adam's second-moment estimates are still noisy. So the rate ramps up linearly for $W$ steps, then follows half a cosine down to a floor. The cosine is flat at both ends: it leaves the peak gently and settles gently into the floor.

$$
p = \operatorname{clip}\!\left(\frac{s - W}{\max(1, T - W)},\, 0,\, 1\right), \qquad
\text{lr} = \eta_{\min} + (\eta_{\max} - \eta_{\min})\cdot\tfrac12\bigl(1 + \cos \pi p\bigr)
$$

Compute both phases for every step, then pick one with `np.where`:

```python
def cosine_lr(steps, base_lr, warmup_steps, total_steps, min_lr=0.0):
    s = np.asarray(steps, dtype=float)
    warm = base_lr * s / max(1, warmup_steps)
    p = np.clip((s - warmup_steps) / max(1, total_steps - warmup_steps), 0.0, 1.0)
    cos = min_lr + (base_lr - min_lr) * 0.5 * (1.0 + np.cos(np.pi * p))
    return np.where(s < warmup_steps, warm, cos)
```

The `max(1, ...)` guards keep the division safe when `warmup_steps = 0` or `warmup_steps = total_steps`.

## Common mistakes

- **Clamping instead of rescaling.** `max(min_lr, base_lr * cosine)` hits the floor early and has a kink there. Rescale the cosine into $[\eta_{\min}, \eta_{\max}]$.
- **Not clipping $p$.** $\cos(\pi p)$ is periodic, so for $p > 1$ the rate climbs back toward `base_lr`.
- **Warmup off by one.** Under this convention step 0 has rate 0 and step $W$ is the peak. Using $(s+1)/W$ shifts the whole ramp.

## Complexity

- **Time:** $O(n)$ for $n$ queried steps.
- **Space:** $O(n)$ for the output.
