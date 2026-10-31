## 1. What the problem is really asking

A 70B-parameter model in float16 needs 140 GB just for its weights. Storing each weight as one signed byte instead halves that, and int8 matmuls are fast on most hardware. Absmax quantization is the simplest way to get there: for each row of the weight matrix, map the largest magnitude to `±127` and scale everything else linearly onto the integers in between.

Under the story this is **a per-row linear map, a rounding rule and a clip**. Three things decide whether you pass: the scale is **per row**, rounding is **half away from zero** (not NumPy's default), and an **all-zero row** gets scale 1 instead of 0.

The judge compares the tuple `(q, scales, W_hat)` element by element with `rtol=1e-7`. One code off by one fails the case, so the rounding rule has to be exact.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `W` | `(n, m)` float64 | weight matrix, one output channel per row | quantized row by row |
| `q` (return) | `(n, m)` int8 | integer codes in `[-127, 127]` | what you'd store on disk |
| `scales` (return) | `(n,)` float64 | one scale per row | what you'd store next to `q` |
| `W_hat` (return) | `(n, m)` float64 | `q * scale`, the dequantized weights | what the model actually computes with |

The details that are easy to miss:

- **`np.round` rounds halves to even.** `np.round(2.5)` is `2.0`, `np.round(-0.5)` is `-0.0`, `np.round(3.5)` is `4.0`. The spec wants `3`, `-1`, `4`.
- **`floor(x + 0.5)` is not "half away from zero" either.** It rounds halves **up**: `floor(-2.5 + 0.5) = -2`, not `-3`.
- **The absmax can be negative.** Row `[-3, 1, 2]` has absmax `3`, so `-3` maps to `-127`. Take `abs` before `max`.
- **Casting to int8 truncates toward zero.** `np.array([-63.9, 2.7]).astype(np.int8)` is `[-63, 2]`. Round first, then cast.

## 3. The math

Fix a row $i$ with entries $W_{i1}, \dots, W_{im}$. Let $\alpha_i = \max_j |W_{ij}|$, the row's absmax.

**Choosing the scale.** You want a single number $s_i > 0$ such that $W_{ij} \approx q_{ij}\, s_i$ with integers $|q_{ij}| \le 127$. The entry with the biggest magnitude needs the biggest code, so set it to exactly $\pm 127$:

$$s_i\, 127 = \alpha_i \quad\Longrightarrow\quad s_i = \frac{\alpha_i}{127}.$$

Any smaller $s_i$ would push some code past 127; any larger one wastes codes, because the largest code used would be below 127.

**Quantize and dequantize.** With $x_{ij} = W_{ij} / s_i$, which lies in $[-127, 127]$ by construction,

$$q_{ij} = \operatorname{clip}\big(\operatorname{round}(x_{ij}), -127, 127\big), \qquad \hat W_{ij} = q_{ij}\, s_i.$$

**Half away from zero.** For any real $x$,

$$\operatorname{round}(x) = \operatorname{sign}(x)\, \big\lfloor |x| + \tfrac12 \big\rfloor.$$

Work it out for $x = -2.5$: $|x| + 0.5 = 3$, $\lfloor 3 \rfloor = 3$, times $\operatorname{sign}(-2.5) = -1$ gives $-3$. For $x = 2.4$: $\lfloor 2.9 \rfloor = 2$. The formula rounds the magnitude, then restores the sign, so it is symmetric about zero.

**The error bound.** Rounding moves $x_{ij}$ by at most $\tfrac12$, so

$$|W_{ij} - \hat W_{ij}| = s_i\, |x_{ij} - q_{ij}| \le \frac{s_i}{2} = \frac{\alpha_i}{254}.$$

The error of every element in a row is set by that row's largest element. That's why per-row scales matter: a single scale for the whole tensor would be set by the largest element **anywhere**.

**Zero rows.** If $\alpha_i = 0$, the formula gives $s_i = 0$ and $x_{ij} = 0/0 = \text{nan}$. The spec sets $s_i = 1$, so every $x_{ij} = 0$, every code is 0 and $\hat W_{ij} = 0$, which is exact.

## 4. Trace an example by hand

**Example 1:** `W = [[1.27, -0.635, 0.3]]`, shape `(1, 3)`.

| step | value | shape |
|---|---|---|
| `absmax` | `[1.27]` | `(1,)` |
| `scales` | `[0.01]` | `(1,)` |
| `x = W / scales[:, None]` | `[[127, -63.5, 30]]` | `(1, 3)` |
| round half away | `[[127, -64, 30]]` | `(1, 3)` |
| `W_hat` | `[[1.27, -0.64, 0.3]]` | `(1, 3)` |

`-63.5` is a tie. Half away from zero sends it to `-64`. `np.round` would give `-64` here too (64 is even), which is why `wrong_round_half_even.py` passes Example 1. `floor(x + 0.5)` gives `-63`.

**Example 2:** three rows, one of them all zero.

| row | `W` | absmax | scale | `x` | `q` |
|---|---|---|---|---|---|
| 0 | `[2, -1, 0.5]` | `2` | `0.015748` | `[127, -63.5, 31.75]` | `[127, -64, 32]` |
| 1 | `[0, 0, 0]` | `0` | `1` | `[0, 0, 0]` | `[0, 0, 0]` |
| 2 | `[-4, 1, 3]` | `4` | `0.031496` | `[-127, 31.75, 95.25]` | `[-127, 32, 95]` |

Without the zero-row rule, row 1's `x` is `[nan, nan, nan]`.

**The hidden case "exact halves"** has scale exactly 1, so `x = W` and every `.5` is a tie: `[127, 2.5, -2.5, 0.5, -0.5, 3.5, -126.5, 1.4]` must become `[127, 3, -3, 1, -1, 4, -127, 1]`. `np.round` gives `2, -2, 0, -0, 4, -126` for the ties.

## 5. Key idea: one scale per row

The hidden case "outlier row" has a row of values near 1, a row near 0.01, and a row of small values plus a single `900`. With per-row scales, the largest reconstruction error in each row is `0.0065`, `0.0000446` and `0.249`, each under its own bound $s_i / 2$.

With one scale for the whole tensor (`900 / 127 = 7.087`), every entry of rows 0 and 1 rounds to code 0. Row 0's error rises to `1.98`: the matrix has lost those rows entirely. Rows of a weight matrix are output channels with very different ranges, and LLM activations and weights are known for exactly these outlier channels.

## 6. Plan before you code

```
absmax = max |W| over each row                     # (n,)
scales = absmax / 127, or 1 where absmax == 0      # (n,)
x      = W / scales[:, None]                       # (n, m)
r      = sign(x) * floor(|x| + 0.5)                # (n, m), still float
q      = clip(r, -127, 127) as int8                # (n, m)
W_hat  = q as float64 * scales[:, None]            # (n, m)
```

| rounding of | `np.round` | `floor(x + 0.5)` | `sign * floor(|x| + 0.5)` |
|---|---|---|---|
| `2.5` | `2` | `3` | `3` |
| `-2.5` | `-2` | `-2` | `-3` |
| `-0.5` | `-0` | `0` | `-1` |
| `-63.5` | `-64` | `-63` | `-64` |

## 7. Build it one piece at a time

**Step 1: the per-row scale.**

```python
absmax = np.max(np.abs(W), axis=1)                       # (n,)
scales = np.where(absmax > 0, absmax / 127.0, 1.0)       # (n,)
```

`np.where` evaluates both branches, but `absmax / 127.0` never divides by zero, so there's no warning. The zero test is on `absmax`, not on the scale.

**Step 2: divide, with broadcasting.**

```python
x = W / scales[:, None]       # (n, m) / (n, 1) -> (n, m)
```

`scales[:, None]` turns `(n,)` into `(n, 1)`, so each row is divided by its own scale. `W / scales` would line `(n,)` up with the **last** axis `m`: a shape error when `n != m`, and silently wrong when `n == m`. The spec says to divide rather than multiply by `1 / scales`, so the ties land exactly where the reference puts them. "divide, not reciprocal" checks this: `0.15 / (0.3 / 127)` is exactly `63.5`, but `0.15 * (1 / (0.3 / 127))` is `63.49999999999999`.

**Step 3: round, clip, cast.**

```python
r = np.sign(x) * np.floor(np.abs(x) + 0.5)      # (n, m) float, halves away from zero
q = np.clip(r, -127, 127).astype(np.int8)       # (n, m) int8
```

The clip is a safety net: $|x| \le 127$ by construction. It also keeps `-128` out, so the code range stays symmetric.

**Step 4: dequantize.**

```python
W_hat = q.astype(np.float64) * scales[:, None]  # (n, m)
```

Convert `q` to float **before** multiplying. NumPy would upcast `int8 * float64` anyway, but writing it out makes clear you never do arithmetic in int8, where `127 + 1` wraps to `-128`.

## 8. Full solution

```python
# NumPy for the row-wise max, rounding and the int8 cast
import numpy as np


# W: (n, m) float64; returns q (n, m) int8, scales (n,), W_hat (n, m)
def absmax_quantize(W: np.ndarray) -> tuple:
    # (n,): the largest magnitude in each row; abs first so a negative extreme counts
    absmax = np.max(np.abs(W), axis=1)
    # (n,): map each row's absmax to code 127; an all-zero row gets scale 1 instead of 0/0
    scales = np.where(absmax > 0, absmax / 127.0, 1.0)
    # (n, m): (n, 1) broadcasts so each row is divided by its own scale
    x = W / scales[:, None]
    # round the magnitude half up, then restore the sign: halves go away from zero
    r = np.sign(x) * np.floor(np.abs(x) + 0.5)
    # keep codes in the symmetric range, and cast only after rounding (a cast truncates)
    q = np.clip(r, -127, 127).astype(np.int8)
    # (n, m): back to float before scaling, so no arithmetic happens in int8
    W_hat = q.astype(np.float64) * scales[:, None]
    # codes, the per-row scales needed to decode them, and the decoded weights
    return q, scales, W_hat
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `q = [[127, -64, 30]]`, `scales = [0.01]` | the basic map, one negative tie |
| Example 2 | `scales = [0.0157, 1, 0.0315]` | per-row scales and the zero-row rule |
| exact halves | `[127, 3, -3, 1, -1, 4, -127, 1]` | half away from zero on every kind of tie |
| halves at another scale | row 0 `q = [127, 3, -3, 1, -2, 4]` | ties after a scale of 2 (`5 / 2 = 2.5`, `-3 / 2 = -1.5`) |
| negative absmax row | row 0 `q = [-127, 42, 85]` | `abs` before `max` |
| rows with very different ranges | row 0 scale about `1.8e-5`, row 2 `1.2242` | per-row scales over five orders of magnitude |
| single element rows | `q = [[127], [-127], [0]]` | `m = 1`, including a zero row |
| outlier row | row 2 `q` is fifteen `0`s and one `127` | one outlier doesn't wreck the other rows |
| zero rows mixed | `scales = [1, 0.0079, 1]` | several zero rows |
| large matrix | `(32, 64)` | the same rules at size |
| divide, not reciprocal | `q = [[127, 64, -64], [127, 63, -63]]` | dividing by the scale, not multiplying by `1 / s` |

## 10. Complexity

Each of the absmax, divide-and-round and dequantize steps is one pass over the matrix, so time is $O(nm)$ and the extra memory is $O(nm)$ for `x`, `q` and `W_hat`.

The point at scale is storage: `q` takes $nm$ bytes against $4nm$ for float32 and $2nm$ for float16, plus $n$ scales, which is negligible when $m$ is in the thousands. Inference kernels keep weights in int8 and dequantize tile by tile inside the matmul, so the memory-bandwidth saving shows up directly as faster decoding.

## 11. If you got Wrong Answer

- **"exact halves" and "halves at another scale" fail with `3` where `2` came out.** You used `np.round`, which rounds halves to even (`wrong_round_half_even.py`). Example 1 still passes, because `-63.5` rounds to the even `-64`.
- **Negative ties are one too high: `-63` instead of `-64` in Example 1.** You used `floor(x + 0.5)` (`wrong_floor_plus_half.py`), which rounds halves up, not away from zero.
- **The zero row's scale is `0` instead of `1`.** You divided first and cleaned the `nan` afterwards (`wrong_zero_row_nan.py`). The codes come out right, but `scales` is wrong. It fails Example 2, "single element rows" and "zero rows mixed".
- **Single-row cases pass, multi-row cases don't.** You used one scale for the whole tensor (`wrong_per_tensor.py`). In Example 2 row 0's absmax `2` maps to `64`, not `127`.
- **Only "divide, not reciprocal" fails, with `63` and `64` swapped between its rows.** You multiplied by `1 / scales` instead of dividing (`wrong_reciprocal_scale.py`). The two differ in the last bit, which moves an exact `.5` tie to `63.49999999999999` or back.
- **Codes like `-63` where `-63.9` was expected to round to `-64`.** You cast to int8 before rounding.

## 12. Follow-ups an interviewer might ask

- *What does LLM.int8() add on top of this?* It finds the few activation dimensions with outliers above a threshold, keeps those in float16, and runs the rest in int8 with per-row and per-column absmax scales.
- *Why symmetric `[-127, 127]` and not `[-128, 127]`?* A symmetric range keeps 0 exactly representable and makes `-q` always valid. Asymmetric (zero-point) schemes use all 256 codes and suit ReLU activations that are never negative.
- *How do you go below 8 bits?* Use smaller groups, e.g. one scale per 64 or 128 weights instead of per row, for int4. GPTQ and AWQ also pick the rounding to minimize the layer's output error, not the weight error.
- *How do you fine-tune a quantized model?* Freeze the quantized weights and train a low-rank adapter in higher precision on top (QLoRA; problem 79, lora-forward-and-merge).
- *How would you measure the damage?* Compare perplexity on held-out text before and after (problem 72, perplexity).
