## Approach

The derivative is a limit of difference quotients, so approximate it with a small finite step. The **central** difference is far more accurate than the one-sided one. Taylor-expand $f(x \pm h)$ and the even terms cancel:

$$
\frac{f(x+h) - f(x-h)}{2h} = f'(x) + \frac{h^2}{6} f'''(x) + O(h^4)
\qquad\text{vs}\qquad
\frac{f(x+h) - f(x)}{h} = f'(x) + \frac{h}{2} f''(x) + O(h^2)
$$

With $h = 10^{-5}$ the central error is about $10^{-10}$, while the forward error is about $10^{-5}$.

Perturb one coordinate at a time. `np.ndindex` walks every index of an array of any shape. Save the original value and restore it, or every later coordinate is evaluated at the wrong point:

```python
for idx in np.ndindex(x.shape):
    old = x[idx]
    x[idx] = old + h; fp = f(x)
    x[idx] = old - h; fm = f(x)
    x[idx] = old
    num[idx] = (fp - fm) / (2 * h)
```

Then report a **relative** error. An absolute error of $10^{-6}$ is excellent for a gradient of size $10^3$ and terrible for one of size $10^{-6}$. Normalizing by $\lVert a \rVert + \lVert n \rVert$ makes the number scale-free. As a rule of thumb, below $10^{-7}$ is correct, around $10^{-4}$ deserves a look, and above $10^{-2}$ is a bug.

## Common mistakes

- **One-sided differences.** They are $O(h)$ accurate, so the estimate is off by about $10^{-5}$ and correct gradients look suspicious.
- **Not restoring `x`.** `x[idx] -= 2*h` without adding `h` back leaves each coordinate shifted by $-h$. Later coordinates are then measured at the wrong point, and the caller's `x` is corrupted.
- **Absolute error.** $\lVert a - n \rVert$ alone depends on the scale of the gradient, so no single threshold works.

## Complexity

- **Time:** $2n$ evaluations of `f` for $n$ elements. That is why gradient checks run on tiny inputs. Backprop gets every element for the cost of about one evaluation.
- **Space:** $O(n)$ for the numerical gradient.
