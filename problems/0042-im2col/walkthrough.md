## 1. What the problem is really asking

A 2-D convolution slides a small kernel over an image and takes a dot product at every position. Written as loops, that's six nested loops and very slow in Python. **im2col** ("image to columns") is the trick that turns all of those dot products into **one matrix multiplication**: copy every window of the input into a column of a big matrix, flatten the kernel into a row, and multiply.

Under the story, this is **pure indexing**. There's no arithmetic at all, just copying values from a padded 4-D array into a 2-D array in exactly the specified order. The judge compares with `rtol=1e-12, atol=0`, so every element has to land in its exact row and column. The ordering is the whole problem:

- rows ordered `(c, i, j)`: channel, then kernel row, then kernel column;
- columns ordered `(n, y, z)`: image, then output row, then output column.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `x` | `(N, C, H, W)` batch of images, NCHW | padded, then windowed |
| `kh`, `kw` | kernel height and width | window size |
| `stride` | step between windows, default 1 | slice step |
| `pad` | zeros added on **each** side of `H` and `W` | `np.pad` |
| return | `(C·kh·kw, N·out_h·out_w)` | one column per window |

The details that are easy to miss:

- **Padding goes on both sides.** `np.pad` takes `(before, after)` per axis. `(pad, pad)` is right; `(0, 2*pad)` gives the same size but shifts every window.
- **The batch index is the slowest column index.** All of image 0's windows come first, then image 1's. Some popular implementations (CS231n's `im2col_indices`) put `n` fastest instead.
- **Leftover rows are dropped.** With `stride > 1`, if the windows don't tile the padded image exactly, the last few rows or columns are never touched. Floor division handles this.

## 3. The math

**Output size.** After padding, the image has height $H_p = H + 2\,\text{pad}$. Window $y$ starts at row $y \cdot s$ (with $s$ = stride) and covers rows $y s, \dots, y s + kh - 1$. It fits when $y s + kh - 1 \le H_p - 1$, i.e. $y \le (H_p - kh)/s$. Counting $y = 0, 1, \dots$:

$$\text{out\_h} = \left\lfloor \frac{H + 2\,\text{pad} - kh}{s} \right\rfloor + 1,$$

and the same for `out_w` with $W$ and $kw$. The windows use rows up to $(\text{out\_h} - 1)s + kh - 1$; anything past that is unused.

**The index map.** With $\text{xp}$ the padded input:

$$\text{cols}\big[\underbrace{c\,kh\,kw + i\,kw + j}_{\text{row } (c, i, j)},\ \underbrace{n\,\text{out\_h}\,\text{out\_w} + y\,\text{out\_w} + z}_{\text{column } (n, y, z)}\big] = \text{xp}[n, c, y s + i, z s + j].$$

Both indices are **row-major flattenings**: the row index is what you get by flattening an array of shape `(C, kh, kw)` in C order, and the column index by flattening `(N, out_h, out_w)`. That's exactly what NumPy's `reshape` does, which is why the solution builds a 6-D array and reshapes it.

**Why this makes convolution a matmul.** A convolution layer with weights $w \in \mathbb{R}^{F \times C \times kh \times kw}$ computes

$$\text{out}[n, f, y, z] = \sum_{c, i, j} w[f, c, i, j]\; \text{xp}[n, c, ys + i, zs + j].$$

Flatten $w$ to $W_{\text{flat}} \in \mathbb{R}^{F \times C kh kw}$ with `w.reshape(F, -1)`, whose column index is also row-major in $(c, i, j)$. The sum over $(c, i, j)$ is then a dot product between row $f$ of $W_{\text{flat}}$ and column $(n, y, z)$ of `cols`:

$$\text{out}[n, f, y, z] = \big(W_{\text{flat}}\ \text{cols}\big)[f,\ (n, y, z)].$$

The result is `(F, N·out_h·out_w)`; reshape to `(F, N, out_h, out_w)` and transpose to `(N, F, out_h, out_w)`. A scratch run checked this against a six-loop direct convolution on `(2, 3, 5, 5)` input with a `(4, 3, 3, 3)` kernel and `pad = 1`: identical.

## 4. Trace an example by hand

**Example 1:** `x = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]` as `(1, 1, 3, 3)`, `kh = kw = 2`, `stride = 1`, `pad = 0`. So `out_h = out_w = (3 - 2) // 1 + 1 = 2`, and `cols` is `(1·2·2, 1·2·2) = (4, 4)`.

The four windows, in column order `(y, z) = (0,0), (0,1), (1,0), (1,1)`, are `[1, 2, 4, 5]`, `[2, 3, 5, 6]`, `[4, 5, 7, 8]` and `[5, 6, 8, 9]`. Each window is a column, read in kernel order `(i, j) = (0,0), (0,1), (1,0), (1,1)`:

```
cols = [[1, 2, 4, 5],    # row (i=0, j=0): top-left cell of each window
        [2, 3, 5, 6],    # row (0, 1)
        [4, 5, 7, 8],    # row (1, 0)
        [5, 6, 8, 9]]    # row (1, 1)
```

Here the matrix happens to be symmetric, so it can't tell rows from columns. Example 2 can.

**Example 2:** two images `[[1, 2], [3, 4]]` and `[[5, 6], [7, 8]]`, `kh = kw = 2`, `pad = 1`, `stride = 2`. Padding makes each image 4×4:

```
xp[0, 0] = [[0, 0, 0, 0],
            [0, 1, 2, 0],
            [0, 3, 4, 0],
            [0, 0, 0, 0]]
```

`out_h = (2 + 2 - 2) // 2 + 1 = 2`, so `cols` is `(4, 2·2·2) = (4, 8)`. For kernel offset `(i, j) = (0, 0)`, the slice `xp[:, :, 0:4:2, 0:4:2]` picks rows and columns 0 and 2 of each padded image: `[[0, 0], [0, 4]]` for image 0 and `[[0, 0], [0, 8]]` for image 1. Flattened in `(n, y, z)` order, that's row 0 of `cols`: `[0, 0, 0, 4, 0, 0, 0, 8]`. The full result:

```
[[0, 0, 0, 4, 0, 0, 0, 8],
 [0, 0, 3, 0, 0, 0, 7, 0],
 [0, 2, 0, 0, 0, 6, 0, 0],
 [1, 0, 0, 0, 5, 0, 0, 0]]
```

The first four columns are image 0, the last four image 1. Each window contains exactly one real pixel, because stride 2 over a 1-pixel border puts each pixel in a different corner of its window.

## 5. Key idea: loop over kernel offsets, not windows

The obvious loop is over output positions `(n, y, z)`: there are `N·out_h·out_w` of them, up to hundreds. The better loop is over **kernel offsets** `(i, j)`: only `kh·kw` of them, typically 9. For a fixed offset, the pixel under kernel cell `(i, j)` across every window and every image is one strided slice:

```python
xp[:, :, i : i + stride*out_h : stride, j : j + stride*out_w : stride]   # (N, C, out_h, out_w)
```

Window `y` starts at row `y·stride`, so its cell `i` is at row `y·stride + i`. As `y` runs from 0 to `out_h - 1`, those rows are `i, i + stride, ..., i + stride·(out_h - 1)`: exactly the slice `i : i + stride*out_h : stride`. The stop value is exclusive, so it takes exactly `out_h` elements, and any leftover rows are skipped.

Each slice goes into `patches[:, :, i, j]`, where `patches` has shape `(N, C, kh, kw, out_h, out_w)`. The axis order then has to be rearranged to `(C, kh, kw, N, out_h, out_w)` so that one reshape produces rows `(c, i, j)` and columns `(n, y, z)`.

## 6. Plan before you code

```
N, C, H, W = x.shape
xp = pad H and W by `pad` on both sides
out_h, out_w from the formula
patches = empty (N, C, kh, kw, out_h, out_w)
for each kernel offset (i, j):
    patches[:, :, i, j] = strided slice of xp
transpose to (C, kh, kw, N, out_h, out_w) and reshape to (C*kh*kw, N*out_h*out_w)
```

| transpose | rows | columns | correct? |
|---|---|---|---|
| `(1, 2, 3, 0, 4, 5)` | `(c, i, j)` | `(n, y, z)` | yes |
| `(1, 2, 3, 4, 5, 0)` | `(c, i, j)` | `(y, z, n)` | no: batch fastest |
| `(2, 3, 1, 0, 4, 5)` | `(i, j, c)` | `(n, y, z)` | no: channels-last rows |

## 7. Build it one piece at a time

**Step 1: pad and size.**

```python
N, C, H, W = x.shape
xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))   # (N, C, H+2p, W+2p), zeros
out_h = (H + 2 * pad - kh) // stride + 1
out_w = (W + 2 * pad - kw) // stride + 1
```

Batch and channel axes get `(0, 0)`: no padding. `np.pad` pads with zeros by default.

**Step 2: fill the 6-D patches array.**

```python
patches = np.empty((N, C, kh, kw, out_h, out_w), dtype=x.dtype)
for i in range(kh):
    for j in range(kw):
        patches[:, :, i, j] = xp[:, :, i:i + stride * out_h:stride,
                                       j:j + stride * out_w:stride]   # (N, C, out_h, out_w)
```

`patches[:, :, i, j]` selects a `(N, C, out_h, out_w)` sub-array, the same shape as the slice, so the assignment needs no broadcasting.

**Step 3: reorder and flatten.**

```python
return patches.transpose(1, 2, 3, 0, 4, 5).reshape(C * kh * kw, N * out_h * out_w)
```

`transpose` only changes strides; `reshape` on the non-contiguous result makes a copy in the new C order, which is exactly the row-major layout the spec defines.

## 8. Full solution

```python
# NumPy for padding, strided slicing and axis reordering
import numpy as np


# x: (N, C, H, W); returns cols of shape (C*kh*kw, N*out_h*out_w)
def im2col(x: np.ndarray, kh: int, kw: int, stride: int = 1, pad: int = 0) -> np.ndarray:
    # batch, channels, height, width of the unpadded input
    N, C, H, W = x.shape
    # zero-pad only the spatial axes, `pad` on BOTH sides, so windows stay centered
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    # number of window positions vertically; floor drops rows no full window reaches
    out_h = (H + 2 * pad - kh) // stride + 1
    # same horizontally
    out_w = (W + 2 * pad - kw) // stride + 1
    # (N, C, kh, kw, out_h, out_w): every window's pixels, indexed by kernel offset
    patches = np.empty((N, C, kh, kw, out_h, out_w), dtype=x.dtype)
    # loop over the kh*kw kernel offsets (usually 9), not over the many windows
    for i in range(kh):
        # each kernel column offset
        for j in range(kw):
            # (N, C, out_h, out_w): pixel under kernel cell (i, j) in every window = one strided slice
            patches[:, :, i, j] = xp[:, :, i:i + stride * out_h:stride, j:j + stride * out_w:stride]
    # reorder to (C, kh, kw, N, out_h, out_w) so row-major reshape gives rows (c,i,j), columns (n,y,z)
    return patches.transpose(1, 2, 3, 0, 4, 5).reshape(C * kh * kw, N * out_h * out_w)
```

## 9. How the test cases map to the code

| test case | `cols` shape | what it checks |
|---|---|---|
| Example 1 | `(4, 4)` | the basic window-to-column mapping |
| Example 2 | `(4, 8)` | padding on both sides, stride 2, and image 0's columns before image 1's |
| two channels | `(12, 4)` | channel is the slowest row index: rows 0–5 are channel 0 |
| batch and channels | `(18, 48)` | `N = 3`, `C = 2`, `pad = 1`, 3×3 kernel |
| stride with leftover | `(18, 8)` | `H = 6` with `kh = 3`, `stride = 2`: only 5 of the 6 rows are used |
| 1x1 kernel | `(3, 8)` | `kh = kw = 1`: `cols` is just `x` with channels as rows |
| pad 2 stride 3 | `(18, 18)` | the largest pad and stride together |
| full-size kernel | `(12, 3)` | one window per image, `out_h = out_w = 1` |
| non-square padded | `(16, 40)` | `kh != kw` and `H != W` with padding, float input |

## 10. Complexity

`cols` has $C\,kh\,kw \times N\,\text{out\_h}\,\text{out\_w}$ entries, and each is written once: that's the time and the memory. The Python loop runs only $kh \cdot kw$ times; each iteration is a vectorized copy of $N C\, \text{out\_h}\, \text{out\_w}$ values.

The memory cost is im2col's real weakness. Each input pixel is copied into up to $kh \cdot kw$ columns, so for a 3×3 kernel `cols` is about 9 times the size of the input. For a batch of 64 images at 224×224 with 64 channels and `pad = 1`, the input is about 0.82 GB in float32 and `cols` is about 7.4 GB, for a single layer. Production libraries avoid materializing it: cuDNN uses implicit GEMM (computing the column indices on the fly), Winograd or FFT methods, and `np.lib.stride_tricks.sliding_window_view` gives a zero-copy view of the windows.

## 11. If you got Wrong Answer

- **Example 2's columns are interleaved, `[0, 0, 0, 0, 0, 0, 4, 8]` on row 0.** Your columns are ordered `(y, z, n)`, batch fastest (`wrong_column_order.py`). Examples with `N = 1` can't catch this, and neither can "full-size kernel", where each image has only one window.
- **Example 2's row 0 is `[1, 0, 0, 0, 5, 0, 0, 0]`.** You padded only at the end, `(0, 2*pad)` (`wrong_pad_one_side.py`). The shape is right but every window is shifted by `pad` pixels.
- **"two channels" has channel 1's values in row 1.** Your rows are ordered `(i, j, c)`, channels-last (`wrong_row_order.py`). That layout doesn't line up with `w.reshape(F, -1)` for an `(F, C, kh, kw)` kernel. Single-channel cases can't catch it.
- **A shape mismatch inside the loop.** Your slice stop is `H + 2*pad` instead of `i + stride*out_h`, so with leftover rows the slice has one element too many.

## 12. Follow-ups an interviewer might ask

- *How do you compute the convolution from `cols`?* `w.reshape(F, -1) @ cols`, then reshape to `(F, N, out_h, out_w)` and transpose to NCHW (problem 43, conv2d-forward).
- *What's the inverse, col2im?* It scatters each column back into the padded image and **adds** overlapping contributions, then strips the padding. It's the core of the convolution backward pass (problem 44, conv2d-backward).
- *How would you avoid the memory blow-up?* Use `sliding_window_view` for a zero-copy view and `np.einsum` or `tensordot` over it, or compute in tiles.
- *What changes for dilated convolution?* Kernel cell `(i, j)` reads `xp[..., y·s + i·d, z·s + j·d]`, so the slice start becomes `i*d` and the effective kernel size is `d·(kh - 1) + 1`.
- *Why NCHW instead of NHWC?* It's a convention. NHWC (channels last) is often faster on GPUs with tensor cores and is TensorFlow's default; the im2col row order changes to `(i, j, c)` to match.
