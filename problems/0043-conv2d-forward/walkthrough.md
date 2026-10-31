## 1. What the problem is really asking

A convolution layer is the building block of every CNN. Each filter is a small 3-D block of weights `(C, kh, kw)` that slides over the image; at every position it takes a dot product with the patch of input under it (across **all** input channels) and adds a bias. `F` filters give `F` output channels.

Under the story, it's **a sum of shifted, channel-mixed copies of the input**. Written from the definition it's seven nested loops (batch, filter, two output coordinates, channel, two kernel coordinates). The approach here vectorizes all of them except the `kh·kw` kernel offsets. For each offset `(i, j)`, one strided slice of the padded input lines up with every output position at once, and an `einsum` mixes its channels with the weights `w[:, :, i, j]`.

The judge compares the `(N, F, out_h, out_w)` output with `rtol=1e-6`. The things it checks beyond the arithmetic are: no kernel flip, the floor in the output size, and that each filter uses a separate weight for each input channel.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(N, C, H, W)` | batch of images, NCHW | padded to `xp` |
| `w` | `(F, C, kh, kw)` | `F` filters, each spanning all `C` channels | `w[:, :, i, j]` is `(F, C)` |
| `b` | `(F,)` | one bias per filter | broadcast over `N`, `out_h`, `out_w` |
| `stride`, `pad` | ints | window step; zero border on each side | |
| return | `(N, F, out_h, out_w)` | the layer output | |

The details that are easy to miss:

- **No kernel flip.** Deep-learning "convolution" is cross-correlation: `w[f, c, 0, 0]` multiplies the **top-left** pixel of each window. Signal-processing convolution flips the kernel first.
- **Floor in the output size.** A partial window at the bottom or right edge is dropped, not padded.
- **Every filter mixes every channel with its own weights.** `w[f, c, i, j]` depends on both `f` and `c`.

## 3. The math

**Definition.** With $\text{xp}$ the zero-padded input and $s$ the stride,

$$\text{out}[n, f, y, z] = b_f + \sum_{c=0}^{C-1} \sum_{i=0}^{kh-1} \sum_{j=0}^{kw-1} w[f, c, i, j]\; \text{xp}[n, c,\, ys + i,\, zs + j].$$

**Output size.** Window $y$ covers padded rows $ys$ to $ys + kh - 1$, which must be $\le H + 2\,\text{pad} - 1$. So $y \le (H + 2\,\text{pad} - kh)/s$, and

$$\text{out\_h} = \left\lfloor \frac{H + 2\,\text{pad} - kh}{s} \right\rfloor + 1.$$

For "stride 2 with leftover", $H = 6$, $kh = 3$, $s = 2$: $\lfloor 3/2 \rfloor + 1 = 2$. Rounding up would give 3, and the third window would hang off the edge.

**Reordering the sums.** Pull the kernel-offset sums outside:

$$\text{out}[n, f, y, z] = b_f + \sum_{i, j}\ \underbrace{\sum_{c} w[f, c, i, j]\; \text{win}_{ij}[n, c, y, z]}_{\text{a contraction over } c}, \qquad \text{win}_{ij}[n, c, y, z] = \text{xp}[n, c, ys + i, zs + j].$$

For a fixed $(i, j)$, $\text{win}_{ij}$ is an array of shape $(N, C, \text{out\_h}, \text{out\_w})$: the pixel under kernel cell $(i, j)$ for every window of every image. In NumPy it's one strided slice, `xp[:, :, i : i + s*out_h : s, j : j + s*out_w : s]`. The inner sum over $c$ is a matrix product between the `(F, C)` weight slice and the channel axis of $\text{win}_{ij}$, which is what `np.einsum("nchw,fc->nfhw", win, w[:, :, i, j])` computes: multiply along the shared index `c`, sum it out, and keep `n, f, h, w`.

**The im2col view.** Stacking all $\text{win}_{ij}$ as rows gives the im2col matrix (problem 42), and the whole convolution becomes `w.reshape(F, -1) @ cols`, one GEMM. The two approaches compute the same sums in a different order.

**What the bias does.** $b_f$ is added once per output position, independent of the input. With padding, positions where the window covers only zeros output exactly $b_f$. That's the "ring of bias-only outputs" in Example 2.

## 4. Trace an example by hand

**Example 1:** `x = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]` as `(1, 1, 3, 3)`; one filter `w = [[1, 0], [0, -1]]` as `(1, 1, 2, 2)`; `b = [0.5]`. So `out_h = out_w = 2`.

| offset `(i, j)` | `w[0, 0, i, j]` | `win` (the `(2, 2)` slice) | contribution |
|---|---|---|---|
| `(0, 0)` | 1 | `[[1, 2], [4, 5]]` | `[[1, 2], [4, 5]]` |
| `(0, 1)` | 0 | `[[2, 3], [5, 6]]` | 0 |
| `(1, 0)` | 0 | `[[4, 5], [7, 8]]` | 0 |
| `(1, 1)` | -1 | `[[5, 6], [8, 9]]` | `[[-5, -6], [-8, -9]]` |

Sum plus bias: `[[1 - 5, 2 - 6], [4 - 8, 5 - 9]] + 0.5 = -3.5` everywhere. Flipping the kernel would compute `x[y+1, z+1] - x[y, z] + 0.5 = 4.5` instead.

**Example 2:** a `(1, 2, 2, 2)` input with channels `[[1, 2], [3, 4]]` and `[[0, 1], [1, 0]]`; two **1×1** filters, `w[0] = [1, 10]` and `w[1] = [0, -1]` across channels; `b = [0, 1]`; `pad = 1`. With a 1×1 kernel there's one offset, and the window is the whole padded image, `(1, 2, 4, 4)`. The `einsum` contracts the channel axis with the `(2, 2)` weight matrix:

- filter 0: `x0 + 10·x1` = `[[1, 12], [13, 4]]` in the interior;
- filter 1: `1 - x1` = `[[1, 0], [0, 1]]` in the interior.

The border of the `(1, 2, 4, 4)` output is padding only, so it holds just the bias: 0 for filter 0, 1 for filter 1.

## 5. Key idea: one einsum per kernel offset

Each iteration does:

```python
win = xp[:, :, i:i + stride*out_h:stride, j:j + stride*out_w:stride]   # (N, C, out_h, out_w)
out += np.einsum("nchw,fc->nfhw", win, w[:, :, i, j])                  # (N, F, out_h, out_w)
```

The einsum string reads as: the first operand has axes `n, c, h, w`; the second has `f, c`; the output has `n, f, h, w`. The index `c` appears in both inputs but not in the output, so it is multiplied and summed. Every other index is carried through. That's the per-offset channel mixing, for every image and every output position at once.

Note the `w` in the einsum string is just a letter for the width axis, unrelated to the weights array named `w`.

The slice stop `i + stride*out_h` makes the slice exactly `out_h` long. Using `H + 2*pad` as the stop would give extra rows whenever there's a leftover.

## 6. Plan before you code

```
N, C, H, W = x.shape;  F, _, kh, kw = w.shape
xp = pad H and W on both sides
out_h, out_w from the floor formula
out = zeros (N, F, out_h, out_w)
for each kernel offset (i, j):
    win  = strided slice of xp                        # (N, C, out_h, out_w)
    out += contract win with w[:, :, i, j] over C     # (N, F, out_h, out_w)
return out + bias broadcast over N, out_h, out_w
```

| case | `x` | `w` | output shape |
|---|---|---|---|
| random 3x3 pad 1 | `(2, 3, 5, 5)` | `(4, 3, 3, 3)` | `(2, 4, 5, 5)` ("same" padding) |
| stride 2 with leftover | `(2, 2, 6, 7)` | `(3, 2, 3, 3)` | `(2, 3, 2, 3)` |
| non-square kernel | `(1, 2, 5, 6)` | `(2, 2, 2, 3)` | `(1, 2, 8, 8)` |
| stride 3 | `(3, 1, 8, 8)` | `(2, 1, 2, 2)` | `(3, 2, 3, 3)` |
| full-size kernel | `(4, 2, 3, 3)` | `(5, 2, 3, 3)` | `(4, 5, 1, 1)` |
| many channels | `(2, 8, 6, 6)` | `(6, 8, 3, 3)` | `(2, 6, 3, 3)` |

## 7. Build it one piece at a time

**Step 1: shapes and padding.**

```python
N, C, H, W = x.shape
F, _, kh, kw = w.shape
xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))   # (N, C, H+2p, W+2p)
out_h = (H + 2 * pad - kh) // stride + 1
out_w = (W + 2 * pad - kw) // stride + 1
```

**Step 2: accumulate over kernel offsets.**

```python
out = np.zeros((N, F, out_h, out_w))
for i in range(kh):
    for j in range(kw):
        win = xp[:, :, i:i + stride * out_h:stride, j:j + stride * out_w:stride]
        out += np.einsum("nchw,fc->nfhw", win, w[:, :, i, j])
```

`w[:, :, i, j]` keeps both the filter and channel axes: `(F, C)`. Using `w[:, 0, i, j]` (shape `(F,)`) would apply channel 0's weight to every channel.

**Step 3: add the bias.**

```python
return out + b[None, :, None, None]     # (1, F, 1, 1) broadcasts over N, out_h, out_w
```

`b` alone is `(F,)`, and against `(N, F, out_h, out_w)` NumPy would line it up with the **last** axis, `out_w`. That fails, or silently adds the wrong bias when `F == out_w`. Indexing with `None` inserts size-1 axes so `F` lines up with axis 1.

A scratch check against the seven-loop definition on `(2, 3, 5, 5)` input with a `(4, 3, 3, 3)` kernel and `pad = 1` gave identical results.

## 8. Full solution

```python
# NumPy for padding, strided slices and einsum contractions
import numpy as np


# x: (N, C, H, W), w: (F, C, kh, kw), b: (F,); returns (N, F, out_h, out_w)
def conv2d_forward(x, w, b, stride=1, pad=0):
    # batch, input channels, height, width
    N, C, H, W = x.shape
    # number of filters and kernel size (the channel count must match C)
    F, _, kh, kw = w.shape
    # zero border on both sides of H and W only
    xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
    # floor: a partial window at the bottom edge is dropped, not padded
    out_h = (H + 2 * pad - kh) // stride + 1
    # same for the right edge
    out_w = (W + 2 * pad - kw) // stride + 1
    # (N, F, out_h, out_w) accumulator for the sum over kernel offsets
    out = np.zeros((N, F, out_h, out_w))
    # loop only over the kh*kw kernel offsets; everything else is vectorized
    for i in range(kh):
        # each kernel column offset
        for j in range(kw):
            # (N, C, out_h, out_w): the pixel under kernel cell (i, j) for every window; no flip
            win = xp[:, :, i:i + stride * out_h:stride, j:j + stride * out_w:stride]
            # mix channels with this offset's (F, C) weights: sum over c, keep n, f, h, w
            out += np.einsum("nchw,fc->nfhw", win, w[:, :, i, j])
    # bias reshaped to (1, F, 1, 1) so it lines up with the filter axis, not the width axis
    return out + b[None, :, None, None]
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `-3.5` everywhere | no kernel flip (a flip gives `4.5`) |
| Example 2 | `[[1, 12], [13, 4]]` inside a ring of `0` (filter 0) | 1×1 channel mixing; padding gives bias-only borders |
| random 3x3 pad 1 | shape `(2, 4, 5, 5)` | the common "same" convolution with several filters and channels |
| stride 2 with leftover | shape `(2, 3, 2, 3)` | the floor in the output size |
| non-square kernel | shape `(1, 2, 8, 8)` | `kh != kw` with `pad = 2` |
| stride 3 | shape `(3, 2, 3, 3)` | `(8 + 2 - 2) / 3` is not an integer |
| full-size kernel | shape `(4, 5, 1, 1)` | one window per image: a dense layer over the whole image |
| many channels | shape `(2, 6, 3, 3)` | `C = 8`, stride 2 and pad 1 together |

## 10. Complexity

Every output entry is a sum over $C \cdot kh \cdot kw$ products, so the work is $O(N F C\, kh\, kw\, \text{out\_h}\, \text{out\_w})$ multiply-adds. Memory is $O(N F\, \text{out\_h}\, \text{out\_w})$ for the output plus the padded input; the slices are views, so no window copies are made beyond what `einsum` uses internally. The im2col route adds $O(C\, kh\, kw \cdot N\, \text{out\_h}\, \text{out\_w})$ for the column matrix.

For a ResNet-style layer (64 channels in and out, 3×3, 56×56 output) that's about $64 \cdot 64 \cdot 9 \cdot 56 \cdot 56 \approx 1.2 \times 10^8$ multiply-adds per image. Production libraries pick between direct, im2col-GEMM, Winograd and FFT algorithms per layer shape, and lay data out as NHWC for tensor cores.

## 11. If you got Wrong Answer

- **Example 1 gives `4.5` instead of `-3.5`.** You flipped the kernel (`wrong_flipped_kernel.py`). It passes Example 2, whose 1×1 kernels look the same flipped.
- **Example 2's filter 0 interior is `[[1, 3], [4, 4]]` instead of `[[1, 12], [13, 4]]`.** You used one weight per filter for every channel, `w[:, 0, i, j]` (`wrong_channel_sum.py`). Single-channel cases can't catch it.
- **The output has an extra row or column on "stride 2 with leftover", "stride 3" or "many channels".** You rounded the output size up and padded the partial window (`wrong_out_size.py`). For "stride 3" that gives `(4, 4)` outputs instead of `(3, 3)`.
- **A broadcast error, or a bias that varies along the width.** You added `b` without reshaping it to `(1, F, 1, 1)`.

## 12. Follow-ups an interviewer might ask

- *How do you get the same result with one matrix multiply?* im2col: `w.reshape(F, -1) @ cols` (problem 42, im2col). It's faster on BLAS but uses `kh·kw` times the input memory.
- *What's the backward pass?* `db` sums `dout`, `dw` correlates the input with `dout`, and `dx` scatters `dout` back through the kernel (problem 44, conv2d-backward).
- *How do you count parameters and FLOPs?* Parameters: `F·C·kh·kw + F`. Multiply-adds: that times `N·out_h·out_w`, minus the bias.
- *What's a depthwise convolution?* Each input channel has its own filter and channels aren't mixed: drop the sum over `c`. MobileNet pairs it with a 1×1 convolution, like Example 2, for the mixing.
- *Why does padding matter?* Without it, each layer shrinks the image by `kh - 1` and edge pixels are seen by fewer windows. `pad = (k - 1)/2` with stride 1 keeps the size ("same" padding).
