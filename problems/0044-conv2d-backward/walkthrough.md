## 1. What the problem is really asking

Problem 43 built the convolution forward pass. Training needs its backward pass: given `dout` $= \partial L / \partial\, \text{out}$, return the gradients for the input (to pass to the layer below), for the weights and for the bias.

The standard textbook answer is "`dx` is a full convolution of `dout` with the flipped kernel, and `dw` is a cross-correlation of the input with `dout`", which is true for stride 1 and gets confusing with stride and padding. This walkthrough takes the route that works for every stride and padding with no flips to reason about: write the forward pass as a **sum over kernel offsets** of simple bilinear terms, and differentiate each term.

Under the story, that gives three rules:

- `db`: sum `dout` over everything except the filter axis.
- `dw[:, :, i, j]`: contract `dout` with the input window for offset `(i, j)`.
- `dx`: for each offset, push `dout` back through `w[:, :, i, j]` and **add** it into the same strided slice of a padded buffer, then crop the padding.

The judge compares `(dx, dw, db)` with `rtol=1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `dout` | `(N, F, out_h, out_w)` | upstream gradient | the source of all three gradients |
| `x` | `(N, C, H, W)` | forward input | padded to `xp`, windowed for `dw` |
| `w` | `(F, C, kh, kw)` | forward weights | used for `dx` |
| `stride`, `pad` | ints | same as the forward pass | slices and crop |
| return | `(N, C, H, W)`, `(F, C, kh, kw)`, `(F,)` | `dx, dw, db` | each shaped like its variable |

The details that are easy to miss:

- **Windows overlap** whenever `stride < kernel size`. One input pixel then sits in several windows, and its gradient is the **sum** of what each window sends back. Assigning with `=` keeps only the last one.
- **`dx` is for the unpadded input.** Accumulate into a padded buffer, then crop with `pad:pad + H`. The tempting `pad:-pad` returns an **empty** array when `pad = 0`.
- **Pixels no window reaches get gradient 0.** With a leftover at the edge (stride doesn't divide evenly), those pixels never affected the output.
- **`db` is a sum, not a mean.** The bias is added at every position of every image.

## 3. The math

**Forward, as a sum over offsets.** For kernel offset $(i, j)$, define the window

$$\text{win}_{ij}[n, c, y, z] = \text{xp}[n, c,\, ys + i,\, zs + j], \qquad \text{win}_{ij} \in \mathbb{R}^{N \times C \times \text{out\_h} \times \text{out\_w}}.$$

Then the forward pass is

$$\text{out}[n, f, y, z] = b_f + \sum_{i, j} \sum_{c} w[f, c, i, j]\; \text{win}_{ij}[n, c, y, z].$$

**Bias.** $\partial\, \text{out}[n, f, y, z] / \partial b_{f'} = [f = f']$, so

$$db_f = \sum_{n, y, z} dout[n, f, y, z].$$

**Weights.** $w[f, c, i, j]$ appears only in offset $(i, j)$'s term, multiplied by $\text{win}_{ij}[n, c, y, z]$, for every $n, y, z$:

$$dw[f, c, i, j] = \sum_{n, y, z} dout[n, f, y, z]\; \text{win}_{ij}[n, c, y, z].$$

That's `np.einsum("nfhw,nchw->fc", dout, win_ij)`: the shared indices `n, h, w` are summed, leaving `(F, C)`.

**Windows.** The gradient flowing into offset $(i, j)$'s window is

$$d\,\text{win}_{ij}[n, c, y, z] = \sum_{f} dout[n, f, y, z]\; w[f, c, i, j],$$

or `np.einsum("nfhw,fc->nchw", dout, w[:, :, i, j])`, shape `(N, C, out_h, out_w)`.

**Input.** A padded pixel $\text{xp}[n, c, p, q]$ appears in $\text{win}_{ij}$ at position $(y, z)$ whenever $p = ys + i$ and $q = zs + j$. By the chain rule its gradient sums over **every** $(i, j, y, z)$ where that happens:

$$d\text{xp}[n, c, p, q] = \sum_{\substack{i, j, y, z:\\ ys + i = p,\; zs + j = q}} d\,\text{win}_{ij}[n, c, y, z].$$

For a fixed $(i, j)$, the positions $(ys + i, zs + j)$ are exactly the strided slice the window came from. So: for every offset, **add** $d\,\text{win}_{ij}$ into `dxp[:, :, i : i + s*out_h : s, j : j + s*out_w : s]`. Then $dx = d\text{xp}$ with the padding removed, because the pad zeros are constants, not inputs.

**The stride-1 shortcut, for reference.** With $s = 1$, substituting $y = p - i$ gives $d\text{xp}[n, c, p, q] = \sum_{f, i, j} dout[n, f, p - i, q - j]\, w[f, c, i, j]$, which is a full convolution of `dout` with the kernel. Written as a cross-correlation, the kernel is flipped. That's where the "flipped kernel" rule comes from. In the offset form there's no flip: offset $(i, j)$ pairs with `w[:, :, i, j]` itself.

## 4. Trace an example by hand

**Example 1:** `x` is `[[1, 2, 3], [4, 5, 6], [7, 8, 9]]` as `(1, 1, 3, 3)`, `w = [[1, 2], [3, 4]]` as `(1, 1, 2, 2)`, `dout = [[1, 0], [0, 0]]` as `(1, 1, 2, 2)`. Only the top-left output has gradient.

- `db = sum(dout) = [1]`.
- `dw[0, 0, i, j]` is `dout` dotted with `win_ij`. Only position `(y, z) = (0, 0)` counts, and `win_ij[0, 0, 0, 0] = x[i, j]`. So `dw = [[x[0,0], x[0,1]], [x[1,0], x[1,1]]] = [[1, 2], [4, 5]]`: the top-left window.
- For `dx`, offset `(i, j)` sends `w[i, j] · dout` back into the slice starting at `(i, j)`. Only `dout[0, 0]` is nonzero, so offset `(i, j)` adds `w[i, j]` at pixel `(i, j)`. Result: `[[1, 2, 0], [3, 4, 0], [0, 0, 0]]`, the kernel placed in the top-left corner.

**Example 2:** the same `x`, `w` all ones, `dout` all ones. Now every window has gradient.

| offset `(i, j)` | `win_ij` | `dw[i, j] = sum(win_ij)` | slice of `dxp` it adds 1 to |
|---|---|---|---|
| `(0, 0)` | `[[1, 2], [4, 5]]` | 12 | rows 0–1, cols 0–1 |
| `(0, 1)` | `[[2, 3], [5, 6]]` | 16 | rows 0–1, cols 1–2 |
| `(1, 0)` | `[[4, 5], [7, 8]]` | 24 | rows 1–2, cols 0–1 |
| `(1, 1)` | `[[5, 6], [8, 9]]` | 28 | rows 1–2, cols 1–2 |

`dx` counts how many windows contain each pixel: `[[1, 2, 1], [2, 4, 2], [1, 2, 1]]`. The center pixel is in all 4 windows. With `=` instead of `+=`, every pixel would just hold the last offset's value, `[[1, 1, 1], [1, 1, 1], [1, 1, 1]]`. `db = [4]`.

## 5. Key idea: accumulate into a padded buffer, crop at the end

```python
dxp = np.zeros_like(xp)                          # (N, C, H+2p, W+2p)
...
dxp[:, :, hs, ws] += np.einsum("nfhw,fc->nchw", dout, w[:, :, i, j])
...
dx = dxp[:, :, pad:pad + H, pad:pad + W]         # (N, C, H, W)
```

Working in padded coordinates means the slice for offset `(i, j)` is exactly the one the forward pass used; no index arithmetic near the borders. Gradients that land in the padding belong to constant zeros and are thrown away by the crop.

`dxp[:, :, hs, ws] += ...` on a strided slice is a view update: NumPy adds into the existing buffer in place. Within one offset the positions are all distinct (stride ≥ 1), so there are no duplicate-index problems; overlap only happens **across** offsets, which the loop handles by adding one offset at a time.

The crop `pad:pad + H` works for every `pad`, including 0, where it's `0:H`. `pad:-pad` with `pad = 0` is `0:0`, an empty slice.

## 6. Plan before you code

```
xp  = pad x
dxp = zeros like xp;  dw = zeros like w
for each kernel offset (i, j):
    hs, ws = the forward pass's strided slices for this offset
    dw[:, :, i, j] = contract dout with xp[:, :, hs, ws] over n, h, w      # (F, C)
    dxp[:, :, hs, ws] += contract dout with w[:, :, i, j] over f           # (N, C, out_h, out_w)
dx = crop dxp to (N, C, H, W)
db = sum of dout over n, h, w                                             # (F,)
```

| gradient | einsum | result shape |
|---|---|---|
| `dw[:, :, i, j]` | `"nfhw,nchw->fc"` with `dout`, `win` | `(F, C)` |
| `d win` | `"nfhw,fc->nchw"` with `dout`, `w[:, :, i, j]` | `(N, C, out_h, out_w)` |
| `db` | `dout.sum(axis=(0, 2, 3))` | `(F,)` |

## 7. Build it one piece at a time

**Step 1: sizes and buffers.**

```python
N, C, H, W = x.shape
F, _, kh, kw = w.shape
_, _, out_h, out_w = dout.shape                                  # read from dout, no recomputation
xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))         # (N, C, H+2p, W+2p)
dxp = np.zeros_like(xp)
dw = np.zeros_like(w)                                            # (F, C, kh, kw)
```

**Step 2: the offset loop.**

```python
for i in range(kh):
    for j in range(kw):
        hs = slice(i, i + stride * out_h, stride)                # same rows the forward pass read
        ws = slice(j, j + stride * out_w, stride)
        dw[:, :, i, j] = np.einsum("nfhw,nchw->fc", dout, xp[:, :, hs, ws])
        dxp[:, :, hs, ws] += np.einsum("nfhw,fc->nchw", dout, w[:, :, i, j])
```

Building `slice` objects once lets the same `hs, ws` index both `xp` and `dxp`, so the forward and backward windows can't drift apart.

**Step 3: crop and bias.**

```python
dx = dxp[:, :, pad:pad + H, pad:pad + W]
db = dout.sum(axis=(0, 2, 3))
```

A scratch check against central finite differences of `sum(dout * conv2d_forward(...))` on the "stride 2 with leftover" shapes matched to 9 digits for both a `dx` and a `dw` entry. In that shape (`H = 6`, `kh = 3`, `stride = 2`), the windows reach only rows 0–4, and `dx[:, :, 5, :]` is exactly 0.

## 8. Full solution

```python
# NumPy for padding, strided slices and einsum contractions
import numpy as np


# dout: (N, F, out_h, out_w), x: (N, C, H, W), w: (F, C, kh, kw); returns (dx, dw, db)
def conv2d_backward(dout, x, w, stride=1, pad=0):
    # input sizes, needed for the final crop
    N, C, H, W = x.shape
    # filter count and kernel size
    F, _, kh, kw = w.shape
    # output spatial size, read straight from the upstream gradient
    _, _, out_h, out_w = dout.shape
    # the padded input the forward pass actually windowed
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    # gradient buffer in padded coordinates, so each offset's slice matches the forward pass
    dxp = np.zeros_like(xp)
    # (F, C, kh, kw), filled one kernel offset at a time
    dw = np.zeros_like(w)
    # the forward pass was a sum over kernel offsets, so the backward pass is too
    for i in range(kh):
        # each kernel column offset
        for j in range(kw):
            # rows of xp that kernel row i touched, one per output row
            hs = slice(i, i + stride * out_h, stride)
            # columns of xp that kernel column j touched, one per output column
            ws = slice(j, j + stride * out_w, stride)
            # (F, C): w[:, :, i, j] multiplied this window, so sum dout * window over n, h, w
            dw[:, :, i, j] = np.einsum("nfhw,nchw->fc", dout, xp[:, :, hs, ws])
            # windows overlap when stride < kernel size, so ADD this offset's (N, C, oh, ow) gradient
            dxp[:, :, hs, ws] += np.einsum("nfhw,fc->nchw", dout, w[:, :, i, j])
    # drop the padding; pad:pad+H also works for pad = 0, unlike pad:-pad
    dx = dxp[:, :, pad:pad + H, pad:pad + W]
    # (F,) each bias was added at every position of every image: a plain sum
    db = dout.sum(axis=(0, 2, 3))
    # gradients shaped like x, w and b
    return dx, dw, db
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `dx = [[1, 2, 0], [3, 4, 0], [0, 0, 0]]`, `dw = [[1, 2], [4, 5]]` | no kernel flip in the offset form |
| Example 2 | `dx = [[1, 2, 1], [2, 4, 2], [1, 2, 1]]`, `dw = [[12, 16], [24, 28]]`, `db = [4]` | overlapping windows must add |
| 3x3 pad 1 | shapes `(2, 3, 5, 5)`, `(4, 3, 3, 3)`, `(4,)` | padding: gradients into the border are cropped away |
| stride 2 with leftover | `dx[:, :, 5, :] = 0` | the uncovered last row gets zero gradient |
| non-square kernel pad 2 | `kh = 2`, `kw = 3`, `pad = 2` | the crop for a large pad |
| stride 3 pad 1 | 2×2 kernel, stride 3 | gaps between windows: some pixels get no gradient |
| stride equals kernel | 2×2 kernel, stride 2 | windows tile exactly, no overlap |
| 1x1 kernel | `(2, 4, 3, 3)` input | a single offset, pure channel mixing |
| full-size kernel | one window per image | `dw` is a sum of `dout`-weighted images |
| many channels stride 2 pad 1 | `C = 6`, `F = 5` | everything at once |

## 10. Complexity

Each of the two einsums per offset does $O(N F C\, \text{out\_h}\, \text{out\_w})$ multiply-adds, and there are $kh \cdot kw$ offsets, so `dx` and `dw` each cost $O(N F C\, kh\, kw\, \text{out\_h}\, \text{out\_w})$: the same as the forward pass, giving the usual "backward is about twice forward". Memory is $O(N C (H + 2p)(W + 2p))$ for the padded gradient buffer, plus `dw`.

Note that `dw` needs the forward **input** `x`. That's why every conv layer keeps its input alive until backward, which dominates activation memory in CNN training.

## 11. If you got Wrong Answer

- **Example 2's `dx` is all ones.** You assigned with `=` instead of `+=` (`wrong_overwrite.py`). Cases where windows don't overlap ("stride equals kernel", "stride 3 pad 1", "1x1 kernel", "full-size kernel") still pass.
- **Example 1's `dx` is `[[4, 3, 0], [2, 1, 0], [0, 0, 0]]`.** You flipped the kernel inside the offset loop (`wrong_dx_flipped.py`). The flip belongs to the "convolution over output positions" view, not this one.
- **`dx` is an empty array whenever `pad = 0`.** You cropped with `pad:-pad` (`wrong_crop_negative_index.py`). The padded cases pass.
- **`db` is too small by a factor of `N`.** You averaged over the batch (`wrong_db_mean.py`). Examples 1 and 2 have `N = 1`, so they can't catch it, and neither can "non-square kernel pad 2".

## 12. Follow-ups an interviewer might ask

- *How does this look with im2col?* `dw = (dout_mat @ cols.T).reshape(w.shape)` and `dcols = w_mat.T @ dout_mat`, then col2im scatters `dcols` back, also adding overlaps (problem 42, im2col).
- *Why is `dx` "a convolution with the flipped kernel"?* With stride 1, substitute $y = p - i$ in the sum for $d\text{xp}$; section 3 shows it. With stride $s$, it's the same on a `dout` dilated by inserting $s - 1$ zeros between entries, which is how transposed convolution is defined.
- *How do you check it?* Central finite differences on a few entries of `dx` and `dw`, as in section 7 (problem 46, numerical-gradient-check).
- *What's a transposed convolution?* Exactly this `dx` computation used as a forward layer, to upsample.
- *How does pooling backward compare?* Max pooling routes each output's gradient to the single argmax pixel of its window, also adding where windows overlap (problem 45, max-pool-forward-backward).
