## 1. What the problem is really asking

A classifier outputs a probability for every class, but your labels are single integers like `2`. To compare the two (in a loss, a confusion matrix, a gradient), you turn each label into a row with a `1` in its class's column and `0` everywhere else. That row is the label written as a probability distribution with all its mass on one class.

Under the story, this is a **scatter**: start from zeros and write one value per row at a position given by an index array. The NumPy skill being taught is **integer-array (fancy) indexing** with two index arrays at once, and the difference between that and mixing a slice with an index array, which looks almost the same and does something completely different.

The judge compares your array with the reference **exactly** (`rtol=0`, `atol=0`), and checks the shape. So the width must be `num_classes`, not whatever the batch happens to contain.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `labels` | 1-D int array, shape `(n,)`, `0 <= n <= 10^4` | the column to set in each row |
| `num_classes` | int, `1 <= C <= 1000` | the width of the output |
| return | float64, shape `(n, num_classes)` | one `1.0` per row, zeros elsewhere |

Details that are easy to miss:

- **The width comes from `num_classes`, never from the data.** A batch of `[1, 1, 0]` with `num_classes=4` still needs 4 columns. Classes 2 and 3 just get all-zero columns.
- **`n` can be 0.** The answer is then an empty array of shape `(0, num_classes)`, not `[]` with shape `(0,)`.
- **Labels can repeat.** Several rows can have their `1` in the same column.

## 3. The math

Let $e_c \in \mathbb{R}^C$ be the $c$-th standard basis vector: a `1` in position $c$ and `0` elsewhere. With labels $y_1, \dots, y_n \in \{0, \dots, C-1\}$, the one-hot matrix stacks one basis vector per sample:

$$
Y \in \{0,1\}^{n \times C}, \qquad Y_{ic} = [\,y_i = c\,] = \begin{cases} 1 & y_i = c \\ 0 & \text{otherwise.} \end{cases}
$$

Here $[\cdot]$ is the indicator (Iverson bracket). Since $e_c$ is row $c$ of the identity $I_C$, you can also write $Y_i = (I_C)_{y_i}$: one-hot encoding **selects rows of the identity**.

**Useful identities.** Every row sums to 1: $\sum_c Y_{ic} = 1$. Summing columns counts each class: $(\mathbf{1}^\top Y)_c = \#\{i : y_i = c\}$. And $Y^\top X$ sums the feature rows of each class, which is how class means are computed in problem 19 (gaussian-naive-bayes).

**Why it's the target of cross-entropy, and the gradient it produces.** A model outputs logits $z_i \in \mathbb{R}^C$ and probabilities $p_i = \operatorname{softmax}(z_i)$. Cross-entropy for one sample is

$$
L_i = -\sum_c Y_{ic} \log p_{ic} = -\log p_{i, y_i},
$$

because the one-hot row zeroes every term but the true class. To differentiate, write $\log p_{ic} = z_{ic} - \log \sum_k e^{z_{ik}}$. Then

$$
L_i = -\sum_c Y_{ic} z_{ic} + \Big(\sum_c Y_{ic}\Big) \log \sum_k e^{z_{ik}} = -\sum_c Y_{ic} z_{ic} + \log \sum_k e^{z_{ik}},
$$

using $\sum_c Y_{ic} = 1$. Differentiating with respect to $z_{ij}$, the first term gives $-Y_{ij}$ and the second gives $e^{z_{ij}} / \sum_k e^{z_{ik}} = p_{ij}$ (problem 2 derives that step). So

$$
\frac{\partial L_i}{\partial z_i} = p_i - Y_i .
$$

The whole backward pass of a classifier starts from "prediction minus one-hot". Problem 36 (softmax-cross-entropy-gradient) implements it, and it needs exactly the matrix you build here.

## 4. Trace an example by hand

**Example 2:** `labels = [1, 1, 0]`, `num_classes = 4`. It teaches the most because some classes are missing.

```python
n = labels.shape[0]                    # 3
out = np.zeros((n, 4))                 # (3, 4), all zeros
rows = np.arange(n)                    # [0, 1, 2]                    (3,)
# pairs (rows[i], labels[i]) are (0, 1), (1, 1), (2, 0)
out[rows, labels] = 1.0                # writes exactly 3 entries
# [[0, 1, 0, 0],
#  [0, 1, 0, 0],
#  [1, 0, 0, 0]]                       (3, 4)
```

Column sums are `[1, 2, 0, 0]`: one sample of class 0, two of class 1, none of classes 2 and 3. The two empty columns are why the width can't come from `labels.max() + 1`, which would be `2`.

**Now the look-alike that's wrong.** `out[:, labels] = 1.0` on the same input gives

```
[[1, 1, 0, 0],
 [1, 1, 0, 0],
 [1, 1, 0, 0]]
```

A slice `:` paired with an index array means "every row, and these columns". It selects whole columns 1, 1 and 0, so every row gets a `1` in every class that appears anywhere in the batch.

**"empty"**: `labels` is an int array of shape `(0,)`. `np.zeros((0, 3))` is a valid empty matrix, `np.arange(0)` is empty, and the assignment writes nothing. The result has shape `(0, 3)` with no special case.

## 5. Key idea: two index arrays pair up, a slice and an array don't

NumPy indexing with **two integer arrays** of the same shape picks elements **pairwise**: `out[r, c]` touches `(r[0], c[0]), (r[1], c[1]), ...`. That's a scatter of `n` single entries.

Indexing with a **slice and an array** combines them as an outer product: `out[:, c]` is every row crossed with every column in `c`. That's `n * len(c)` entries, which is what you want for "select these columns", and not what you want here.

So `np.arange(n)` isn't decoration. It's the row half of the coordinate pairs, saying "row `i` goes with `labels[i]`".

## 6. Plan before you code

```
labels = labels as an int array                   # (n,)
out = zeros of shape (n, num_classes), float64    # width from the argument, never the data
out[arange(n), labels] = 1                        # one write per row, pairwise
return out
```

| approach | correct? | cost |
|---|---|---|
| `out[np.arange(n), labels] = 1` | yes | $O(nC)$ to zero, $O(n)$ writes |
| `np.eye(C)[labels]` | yes | builds a $C \times C$ identity first |
| `(labels[:, None] == np.arange(C)).astype(float)` | yes | a broadcast comparison, $O(nC)$ |
| `out[:, labels] = 1` | no | sets whole columns |
| width `labels.max() + 1` | no | the shape depends on the batch |

## 7. Build it one piece at a time

**Step 1: make sure the labels are integers.**

```python
labels = np.asarray(labels, dtype=int)    # (n,)
```

Fancy indexing needs an integer array. A float array raises an IndexError, and a plain list has no `.shape`. This line costs nothing when the input is already right.

**Step 2: the zero matrix, sized by the argument.**

```python
out = np.zeros((labels.shape[0], num_classes), dtype=np.float64)   # (n, C)
```

Use `labels.shape[0]` for `n`, so `n = 0` gives `(0, C)`.

**Step 3: the scatter.**

```python
out[np.arange(labels.shape[0]), labels] = 1.0   # rows (n,) paired with labels (n,)
return out
```

## 8. Full solution

```python
# NumPy gives zero arrays and integer-array (fancy) indexing
import numpy as np


# labels: (n,) ints in 0..num_classes-1; returns a float64 (n, num_classes) one-hot matrix
def one_hot(labels: np.ndarray, num_classes: int) -> np.ndarray:
    # fancy indexing needs integers; this also accepts a plain list
    labels = np.asarray(labels, dtype=int)
    # width comes from num_classes, never labels.max() + 1, since a class may be absent; (n, C)
    out = np.zeros((labels.shape[0], num_classes), dtype=np.float64)
    # pair row i with column labels[i] and write one 1.0 per row (a slice would set whole columns)
    out[np.arange(labels.shape[0]), labels] = 1.0
    # zeros everywhere except each row's label column; shape (0, C) when labels is empty
    return out
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | the 3 x 3 permutation `[[1,0,0],[0,0,1],[0,1,0]]` | the pairwise scatter |
| Example 2 | shape `(3, 4)`, last two columns all zero | width from `num_classes`, repeated labels |
| largest class missing | shape `(4, 5)` | the same rule with three empty columns |
| many classes | shape `(25, 64)`, labels below 50 | `labels.max() + 1` would give 48 columns |
| empty | shape `(0, 3)` | `n = 0` with no special case |
| single class | `[[1], [1], [1]]` | `C = 1` |
| one sample | `[[0, 0, 0, 0, 0, 0, 1]]` | the last column is reachable |
| random | shape `(40, 10)` | general input |

## 10. Complexity

- **Time:** $O(nC)$ to allocate and zero the matrix, $O(n)$ for the writes.
- **Memory:** $O(nC)$ for the output.

That $O(nC)$ is the catch at scale. A language model's targets are token ids over a vocabulary of 50k–200k. A batch of 1M tokens as dense float64 one-hots would be hundreds of gigabytes, almost all zeros. So real training code **never materializes** the one-hot matrix: cross-entropy takes integer labels and indexes the log-probabilities directly, `-logp[np.arange(n), labels]`, which is the same pairwise indexing you used here, read instead of written.

## 11. If you got Wrong Answer

- **"shape mismatch, expected (3, 4), got (3, 2)" on Example 2.** You sized the width as `labels.max() + 1` (`wrong_max_plus_one.py`). It also fails "largest class missing" and "many classes", and passes the cases where every class happens to appear.
- **Rows contain several 1s; "expected 0, got 1" at `output[0, 1]`.** You wrote `out[:, labels] = 1` (`wrong_slice_index.py`). It passes only the cases where every label is the same or `n = 1`: "single class", "one sample" and "empty".
- **"shape mismatch, expected (0, 3), got (0,)" on "empty".** You built the output from a list comprehension or `np.array([...])`, which loses the second dimension when there are no rows.
- **IndexError "arrays used as indices must be of integer (or boolean) type".** The labels arrived as floats. Convert with `np.asarray(labels, dtype=int)`.

## 12. Follow-ups an interviewer might ask

- *How would you go back from one-hot to labels?* `Y.argmax(axis=1)`. The same call turns predicted probabilities into predicted classes.
- *How do you build a confusion matrix with this?* `Y_true.T @ Y_pred` is `(C, n) @ (n, C)`, and entry `(a, b)` counts samples with true class `a` and predicted class `b` (problem 25, confusion-matrix). `np.add.at` on `(true, pred)` pairs does it without the dense matrices.
- *What is label smoothing?* Replace the one-hot row with $(1 - \epsilon)\, Y_i + \epsilon / C$. The model stops being pushed toward infinitely confident logits.
- *Why not encode classes as one integer feature instead?* An integer implies an order and a distance (class 3 is "between" 2 and 4). One-hot puts every class at the same distance from every other.
- *How do you handle a vocabulary of 100k classes?* Don't materialize it. Index log-probabilities with the integer labels, or use an embedding lookup, which is a one-hot matrix multiply done as indexing.
