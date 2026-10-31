## 1. What the problem is really asking

Almost every transformer is trained with the same learning-rate shape: a straight ramp from 0 up to the peak, then half a cosine wave down to a floor. The ramp protects the first few hundred steps, when Adam's second-moment estimate is built from only a handful of gradients and its steps are unreliable (problem 52). The cosine spends a long time near the peak, where progress is fast, then settles gently to the floor so the final weights stop bouncing.

Strip the story and this is a **piecewise function evaluated on an array**: two formulas, a mask that picks between them, and a clip that keeps the second formula from coming back up after the end. You don't simulate training. You get a batch of step indices, in any order, with repeats, and return one learning rate per index. That makes it a vectorization exercise: no Python loop, and `np.where` instead of `if`.

The judge compares your array with `rtol = 1e-9`, so the formula has to be exact, including the edge cases at `s = 0`, `s = W` and `s >= T`.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `steps` | 1-D int array, any order, repeats allowed | evaluate the schedule at each one; output has the same shape |
| `base_lr` | $\eta_{\max}$, the peak | reached at step `W` |
| `warmup_steps` | $W$, may be `0` | length of the linear ramp |
| `total_steps` | $T \ge W$ | where the cosine reaches the floor |
| `min_lr` | $\eta_{\min}$, default `0.0` | the floor |

Easy to miss:

- **`steps` is not sorted.** Anything that assumes `steps[0]` is the first step, or uses a running state, fails "unordered steps with repeats".
- **`W` can be `0`** (no warmup) and **`W` can equal `T`** (no cosine). Both make a denominator zero unless you guard it.
- **Integer input.** `steps` is an int array. Convert to float before dividing, so you never depend on integer-division behaviour.

## 3. The math

Write $s$ for a step, $W$ for `warmup_steps`, $T$ for `total_steps`.

**Warmup**, for $s < W$: a line through $(0, 0)$ and $(W, \eta_{\max})$,

$$
\text{lr}(s) = \eta_{\max}\,\frac{s}{W}.
$$

**Cosine phase**, for $s \ge W$. First map the step onto progress $p \in [0, 1]$:

$$
p = \min\!\left(1,\ \frac{s - W}{\max(1,\ T - W)}\right).
$$

Then the factor $c(p) = \tfrac12(1 + \cos \pi p)$ goes from $c(0) = \tfrac12(1+1) = 1$ to $c(1) = \tfrac12(1-1) = 0$, and the rate rescales it into $[\eta_{\min}, \eta_{\max}]$:

$$
\text{lr}(s) = \eta_{\min} + (\eta_{\max} - \eta_{\min})\,c(p).
$$

**Why the cosine shape.** Its derivative is $c'(p) = -\tfrac{\pi}{2}\sin(\pi p)$, which is $0$ at both $p = 0$ and $p = 1$. So the rate leaves the peak gently, falls fastest at the midpoint, and lands on the floor with zero slope. A linear decay would have a constant slope and a kink at the end.

**The two continuity checks.** At $s = W$, warmup would give $\eta_{\max} \cdot W/W = \eta_{\max}$ and the cosine gives $p = 0$, so $\eta_{\max}$: the pieces meet. At $s = T$, $p = 1$ and the rate is exactly $\eta_{\min}$.

**Why clip $p$ at 1.** Cosine is periodic. For $p = 1.5$, $\cos(1.5\pi) = 0$ and $c = 0.5$: the rate climbs halfway back to the peak. For $p = 2$, it is back at $\eta_{\max}$. Clipping keeps every step past $T$ on the floor.

**Why rescale instead of clamp.** A tempting shortcut is $\max(\eta_{\min}, \eta_{\max} c(p))$. That curve decays toward 0, hits the floor partway through, and stays flat with a kink. The rescaled form reaches $\eta_{\min}$ exactly at $p = 1$, smoothly.

## 4. Trace the examples by hand

**Example 1**: `steps = 0..10`, `base_lr = 1`, `W = 2`, `T = 10`, `min_lr = 0`. The cosine phase spans `T - W = 8` steps.

| `s` | phase | `p` | value |
|---|---|---|---|
| 0 | warmup | – | `1 * 0/2 = 0` |
| 1 | warmup | – | `1 * 1/2 = 0.5` |
| 2 | cosine | `0` | `1.0` |
| 3 | cosine | `0.125` | `0.9619` |
| 4 | cosine | `0.25` | `0.8536` |
| 6 | cosine | `0.5` | `0.5` |
| 8 | cosine | `0.75` | `0.1464` |
| 9 | cosine | `0.875` | `0.0381` |
| 10 | cosine | `1` | `0` |

Note the symmetry: `0.9619` and `0.0381` add to 1, as do `0.8536` and `0.1464`. Half a cosine is point-symmetric about its midpoint.

**Example 2**: `steps = [0, 2, 4, 6, 8]`, `base_lr = 0.1`, `W = 0`, `T = 4`, `min_lr = 0.02`. With `W = 0` no step is in warmup. Step 0 has `p = 0`, rate `0.1`. Step 2 has `p = 0.5`, so `0.02 + 0.08 * 0.5 = 0.06`. Steps 4, 6, 8 have raw progress `1, 1.5, 2`, clipped to `1`, so all are `0.02`. Without the clip, step 6 would come out `0.06` and step 8 `0.1`.

**The edge case, "warmup equals total"**: `W = T = 4`, `min_lr = 0.1`, steps `0..6`. Steps 0 to 3 are warmup: `0, 0.25, 0.5, 0.75`. Step 4 is the first cosine step, with $p = 0 / \max(1, 0) = 0$, so it is `1.0`, the peak. Steps 5 and 6 have $p = 1/1$ and $2/1$, clipped to 1, so `0.1`. The output is `[0, 0.25, 0.5, 0.75, 1, 0.1, 0.1]`. With no room for a cosine, the schedule drops from the peak to the floor in one step. This matches Hugging Face's implementation, where step `T` gives the peak when `W = T`.

## 5. Key idea: compute both branches, then select

With an array of steps you can't write `if s < W`. Compute the warmup formula and the cosine formula for **every** step, then let `np.where(s < W, warm, cos)` pick elementwise. Both arrays are computed on all elements, including the ones you'll discard, so each formula must be safe everywhere:

- The warmup divides by $W$. When $W = 0$, `max(1, W)` makes it divide by 1. Its values are then discarded anyway, since no step is `< 0`.
- The cosine divides by $T - W$. When $W = T$, `max(1, T - W)` avoids a division by zero.
- For warmup steps, $s - W$ is negative, so $p$ would be negative. Clipping $p$ to `[0, 1]` keeps it tidy. Those values are discarded by `np.where`, but you don't want warnings or `nan`s floating around.

## 6. Plan before you code

```
s    = steps as float                         # (n,)
warm = base_lr * s / max(1, W)                # (n,)
p    = clip((s - W) / max(1, T - W), 0, 1)    # (n,)
cos  = min_lr + (base_lr - min_lr) * 0.5 * (1 + cos(pi * p))   # (n,)
return where(s < W, warm, cos)                # (n,)
```

## 7. Build it one piece at a time

**Step 1: a float array.** `np.asarray` accepts a list or an array, and `dtype=float` removes integer arithmetic from the picture.

```python
s = np.asarray(steps, dtype=float)                       # (n,)
```

**Step 2: the warmup branch.** A scalar times an array: broadcasting applies `base_lr / W` to every element.

```python
warm = base_lr * s / max(1, warmup_steps)                # (n,)
```

**Step 3: progress and the cosine branch.** `np.clip` with both bounds handles "past the end" (upper) and the warmup steps (lower).

```python
p = np.clip((s - warmup_steps) / max(1, total_steps - warmup_steps), 0.0, 1.0)  # (n,)
cos = min_lr + (base_lr - min_lr) * 0.5 * (1.0 + np.cos(np.pi * p))           # (n,)
```

**Step 4: select.** `s < warmup_steps` is a boolean `(n,)` array; `np.where` takes `warm` where it's `True` and `cos` elsewhere, keeping the input order and repeats.

```python
return np.where(s < warmup_steps, warm, cos)             # (n,)
```

## 8. Full solution

```python
# NumPy for the vectorized cosine, clip and where
import numpy as np


# learning rate at each requested step: linear warmup to base_lr, then half a cosine down to min_lr
def cosine_lr(steps, base_lr, warmup_steps, total_steps, min_lr=0.0):
    s = np.asarray(steps, dtype=float)             # (n,) floats, so every division below is true division
    warm = base_lr * s / max(1, warmup_steps)      # warmup ramp from 0; max(1, .) keeps W = 0 from dividing by 0
    # cosine progress in [0, 1]; the upper clip keeps steps past T on the floor, the lower one tidies warmup steps
    p = np.clip((s - warmup_steps) / max(1, total_steps - warmup_steps), 0.0, 1.0)
    cos = min_lr + (base_lr - min_lr) * 0.5 * (1.0 + np.cos(np.pi * p))  # rescale the 1 -> 0 factor into [min_lr, base_lr]
    return np.where(s < warmup_steps, warm, cos)   # pick the phase per element; order and repeats preserved
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 0.5, 1, 0.9619, ..., 0.0381, 0]` | both phases; step 0 is 0, step `W` is the peak, step `T` is the floor |
| Example 2 | `[0.1, 0.06, 0.02, 0.02, 0.02]` | `W = 0`, rescaling into `[min_lr, base_lr]`, clipping past `T` |
| min_lr with warmup | starts `0`, ends at `3e-05` | a realistic schedule with a non-zero floor |
| past the end | all `0` for steps `50` to `1000` | the clip: no cosine coming back up |
| unordered steps with repeats | 40 values in input order | no sorting or running state; repeats get the same value |
| warmup equals total | `[0, 0.25, 0.5, 0.75, 1, 0.1, 0.1]` | `T - W = 0` guarded; peak at step `T`, floor after |
| warmup of one step | `[0, 2, 1, 0]` | `W = 1`: step 0 is still 0 |
| min equals base | all `0.5` | a flat schedule after warmup |

## 10. Complexity

$O(n)$ time and memory for $n$ queried steps: a few elementwise passes. In a training loop you'd call the scalar version once per step, which is $O(1)$. The array form is what you'd use to plot or log a whole schedule, or to precompute a lookup table.

In practice, `W` is typically 1–5% of `T` (a few thousand steps for an LLM), `min_lr` is often 10% of `base_lr`, and `T` is the planned run length. If you decide to train longer after the fact, the schedule is already at the floor, which is why some recent runs use "warmup-stable-decay" schedules that keep a flat peak and only decay at the end.

## 11. If you got Wrong Answer

- **Example 2 gives `0.06` at step 6 and `0.1` at step 8.** You didn't clip `p` at 1, so the cosine rises again past `T`. "past the end" shows it most clearly: `0.6913` at step 75 instead of `0`.
- **Example 2 gives `0.05` at step 2 instead of `0.06`.** You clamped with `max(min_lr, base_lr * c)` instead of rescaling. Example 1 still passes because its `min_lr` is `0`.
- **Example 1 starts at `0.5` instead of `0`.** You used `(s + 1) / W` for warmup. Under this convention step 0 has rate 0 and step `W` is the peak.
- **`ZeroDivisionError`, `nan` or a warning on "warmup equals total" or Example 2.** You divided by `T - W` or `W` directly. Guard both with `max(1, ...)`.
- **"unordered steps with repeats" fails, but the sorted cases pass.** Your code assumes the steps are consecutive (for example, computing a rate and updating it step by step). Evaluate each step independently.

## 12. Follow-ups an interviewer might ask

- *Why warm up at all with Adam?* Early on, $\hat v$ is estimated from very few gradients, and a few large early updates can push the network into a bad region it never recovers from. Warmup keeps those steps small until the moment estimates settle (problem 52).
- *How does this interact with AdamW's weight decay?* PyTorch multiplies the decay by `lr`, so the schedule anneals the decay too (problem 53).
- *How would you resume training from a checkpoint?* Store the step counter and recompute `lr(step)`. Because this function is stateless in the step, resuming is exact.
- *What changes for cosine with restarts?* Replace the clip with $p \bmod 1$ over shorter cycles (SGDR), so the rate jumps back to the peak at the start of each cycle. That's the "come back up" behaviour this problem forbids.
