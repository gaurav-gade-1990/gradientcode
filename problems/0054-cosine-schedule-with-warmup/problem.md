Compute the learning rate of a **linear warmup + cosine decay** schedule at a batch of step indices. This is the schedule used to train most transformers, in the form of Hugging Face's `get_cosine_with_min_lr_schedule_with_warmup` with half a cosine cycle.

Let $W$ be `warmup_steps` and $T$ be `total_steps`. For each step $s$ (0-indexed):

$$
\text{lr}(s) =
\begin{cases}
\eta_{\max} \cdot \dfrac{s}{W} & s < W \\[2ex]
\eta_{\min} + (\eta_{\max} - \eta_{\min}) \cdot \tfrac12\bigl(1 + \cos(\pi p)\bigr) & s \ge W
\end{cases}
\qquad
p = \min\!\left(1,\ \frac{s - W}{\max(1,\ T - W)}\right)
$$

where $\eta_{\max}$ is `base_lr` and $\eta_{\min}$ is `min_lr`.

- Warmup rises linearly from `0` at step `0`. It reaches `base_lr` at step `W`, where the cosine phase starts.
- The cosine phase falls from `base_lr` at step `W` to `min_lr` at step `T`.
- Steps past `T` stay at `min_lr`. Don't let the cosine come back up.
- With `warmup_steps = 0` there is no warmup.

Return a float array with the same shape as `steps`.

**Constraints**

- `steps` is a 1-D int array of non-negative step indices, in any order, possibly with repeats
- `0 <= warmup_steps <= total_steps`, `total_steps >= 1`
- `0 <= min_lr <= base_lr`
