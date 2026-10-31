## 1. What the problem is really asking

Accuracy hides which classes a model is bad at. A classifier that labels everything as the majority class can score 86% accuracy on an imbalanced set and never find a single example of the rare classes. Per-class precision and recall expose that, and **macro averaging** turns them back into single numbers in which every class counts equally, however rare.

Under the story, this is **three ratios read off a confusion matrix**, computed per class, with a "0 when the denominator is 0" rule, then averaged. The confusion matrix is problem 25 (confusion-matrix); everything you need is its diagonal, its column sums and its row sums.

The judge compares three floats to `rtol = 1e-9`. That tolerance is tight enough that every averaging choice matters: macro versus micro, mean of per-class F1 versus F1 of the means, and all `num_classes` classes versus only the ones that appeared. Each choice gives a different number, and only one matches scikit-learn's `average="macro"` with `labels=range(num_classes)` and `zero_division=0`.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `y_true` | `(n,)` int | real classes in `0..C-1` | confusion-matrix rows |
| `y_pred` | `(n,)` int | predictions in `0..C-1` | confusion-matrix columns |
| `num_classes` | int, `1..100` | `C`, the fixed class set | every class is averaged, even absent ones |
| return | `(float, float, float)` | macro precision, recall, F1 | compared to `rtol = 1e-9` |

Three details are easy to miss:

- **F1 is averaged per class.** Compute $F_c$ for each class, then take the mean. The harmonic mean of macro $P$ and macro $R$ is a different number.
- **Absent classes count as zeros.** In "absent class counts", `num_classes = 4` but only classes 0 and 1 appear. Classes 2 and 3 each contribute $P = R = F = 0$ and pull every average down.
- **Zero denominators give 0, not `nan`.** A class that's never predicted has $TP + FP = 0$; a class that never occurs has $TP + FN = 0$. Both scores are defined as 0.

## 3. The math

**Counts from the confusion matrix.** With $M[t, p]$ the number of samples with true class $t$ and prediction $p$ (rows are truth):

$$
TP_c = M[c, c], \qquad
TP_c + FP_c = \sum_{t} M[t, c] \;\;(\text{column } c), \qquad
TP_c + FN_c = \sum_{p} M[c, p] \;\;(\text{row } c).
$$

A false positive for class $c$ is a sample predicted as $c$ that isn't $c$: the off-diagonal part of column $c$. A false negative is a true $c$ predicted as something else: the off-diagonal part of row $c$.

**Per-class scores.**

$$
P_c = \frac{TP_c}{TP_c + FP_c}, \qquad
R_c = \frac{TP_c}{TP_c + FN_c}, \qquad
F_c = \frac{2 P_c R_c}{P_c + R_c}.
$$

$F_c$ is the harmonic mean of $P_c$ and $R_c$: $\frac{1}{F_c} = \frac12\left(\frac{1}{P_c} + \frac{1}{R_c}\right)$. The harmonic mean is dominated by the smaller value, so a class can't score well by maximizing one at the expense of the other. Substituting the counts gives an equivalent form that's handy for checking: $F_c = \frac{2\,TP_c}{2\,TP_c + FP_c + FN_c}$.

**Macro averages.** $P = \frac1C \sum_c P_c$, $R = \frac1C \sum_c R_c$, $F_1 = \frac1C \sum_c F_c$.

**Why F1 of the means is different.** The harmonic mean is not linear, so in general

$$
\frac{1}{C}\sum_c \frac{2 P_c R_c}{P_c + R_c} \;\neq\; \frac{2 P R}{P + R}.
$$

In Example 1, the per-class F1 scores average to $0.6556$, while $2PR/(P+R)$ with $P = 0.7222$ and $R = 0.6667$ is $0.6933$. Both are called "macro F1" in the literature, which is why the problem pins down scikit-learn's definition.

**Why micro averaging is just accuracy here.** Micro averaging pools the counts before dividing. In single-label multiclass, every wrong prediction is one false positive (for the predicted class) and one false negative (for the true class), so

$$
\sum_c FP_c = \sum_c FN_c = n - \sum_c TP_c
\quad\Longrightarrow\quad
P_{\text{micro}} = R_{\text{micro}} = F_{\text{micro}} = \frac{\sum_c TP_c}{n} = \text{accuracy}.
$$

**Zero division.** A naive `tp / (tp + fp)` produces `nan` (from $0/0$) with a RuntimeWarning, and `nan` poisons the mean. `np.divide(a, b, out=zeros, where=b != 0)` only divides where it's allowed and leaves 0 elsewhere.

## 4. Trace an example by hand

**Example 1.** `y_true = [0, 0, 1, 1, 2, 2]`, `y_pred = [0, 1, 1, 1, 2, 0]`, `C = 3`. The confusion matrix, shape `(3, 3)`:

```
        pred 0  pred 1  pred 2
true 0 [  1,      1,      0  ]
true 1 [  0,      2,      0  ]
true 2 [  1,      0,      1  ]
```

| class | $TP$ | column sum ($TP+FP$) | row sum ($TP+FN$) | $P_c$ | $R_c$ | $F_c$ |
|---|---|---|---|---|---|---|
| 0 | 1 | 2 | 2 | 1/2 | 1/2 | 1/2 |
| 1 | 2 | 3 | 2 | 2/3 | 1 | 4/5 |
| 2 | 1 | 1 | 2 | 1 | 1/2 | 2/3 |
| **mean** | | | | **0.722222** | **0.666667** | **0.655556** |

Check $F_1$ for class 1 with the count form: $\frac{2 \cdot 2}{2 \cdot 2 + 1 + 0} = 4/5$. The expected output is `(0.722222, 0.666667, 0.655556)`. Accuracy is $4/6 = 0.6667$, the micro answer, which matches only the recall here by coincidence.

**The hidden "absent class counts" case.** `y_true = [0, 1, 1, 0]`, `y_pred = [0, 1, 0, 0]`, `C = 4`:

| class | $P_c$ | $R_c$ | $F_c$ |
|---|---|---|---|
| 0 | 2/3 | 1 | 0.8 |
| 1 | 1 | 1/2 | 0.6667 |
| 2 | 0 (never predicted) | 0 (never occurs) | 0 |
| 3 | 0 | 0 | 0 |
| **mean over 4** | **0.416667** | **0.375** | **0.366667** |

Averaging over only the two classes that appear gives `(0.8333, 0.75, 0.7333)`, which is wrong.

## 5. Plan before you code

```
cm = confusion matrix, (C, C) float              # problem 25's bincount trick
tp = diagonal                                    # (C,)
fp = column sums - tp                            # (C,)
fn = row sums - tp                               # (C,)
p = tp / (tp + fp), 0 where the denominator is 0 # (C,)
r = tp / (tp + fn), 0 where the denominator is 0 # (C,)
f = 2 p r / (p + r), 0 where p + r is 0          # (C,)
return mean(p), mean(r), mean(f) over all C classes
```

| averaging choice | what it computes | matches the spec? |
|---|---|---|
| macro, per-class F1 | mean of $F_c$ | yes |
| macro, F1 of means | $2PR/(P+R)$ | no |
| micro | accuracy, three times | no |
| macro over present classes | mean over classes that appear | no |

## 6. Build it one piece at a time

**Step 1: the confusion matrix.**

```python
C = num_classes
cm = np.bincount(y_true * C + y_pred, minlength=C * C).reshape(C, C).astype(float)   # (C, C)
```

This is the flatten-and-count trick from problem 25. `minlength=C * C` keeps rows and columns for classes that never appear, which is what makes absent classes count. Casting to `float` makes every later division return floats.

**Step 2: per-class counts.**

```python
tp = np.diag(cm)                  # (C,) the diagonal
fp = cm.sum(axis=0) - tp          # (C,) column sums minus the diagonal
fn = cm.sum(axis=1) - tp          # (C,) row sums minus the diagonal
```

`axis=0` sums down the rows, so it gives one total per **column** (per predicted class). `axis=1` gives one per row (per true class). Mixing them up swaps precision and recall.

**Step 3: safe division.**

```python
def _safe_div(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)
```

`where=b != 0` is a `(C,)` boolean mask: `np.divide` computes `a / b` only where it's `True` and leaves the corresponding entries of `out` untouched, which are zeros. There's no $0/0$, so no `nan` and no warning.

**Step 4: scores and means.**

```python
p = _safe_div(tp, tp + fp)        # (C,)
r = _safe_div(tp, tp + fn)        # (C,)
f = _safe_div(2 * p * r, p + r)   # (C,) per-class F1
return float(p.mean()), float(r.mean()), float(f.mean())
```

`.mean()` divides by the array length, `C`, so absent classes are included automatically.

## 7. Full solution

```python
import numpy as np  # bincount for the confusion matrix, masked divide for the zero-division rule


# Elementwise a / b, with 0 wherever b is 0 (scikit-learn's zero_division=0)
def _safe_div(a, b):
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)  # skip 0/0 instead of making nan


# Macro precision, recall and F1 over all num_classes classes
def precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> tuple:
    C = num_classes  # the fixed class set; absent classes still get averaged in
    # (C, C) confusion matrix, rows = truth, columns = prediction; float so the ratios are floats
    cm = np.bincount(y_true * C + y_pred, minlength=C * C).reshape(C, C).astype(float)
    tp = np.diag(cm)  # (C,) correct predictions per class
    fp = cm.sum(axis=0) - tp  # (C,) predicted as c but truly something else (rest of column c)
    fn = cm.sum(axis=1) - tp  # (C,) truly c but predicted as something else (rest of row c)
    p = _safe_div(tp, tp + fp)  # (C,) precision; 0 for a class never predicted
    r = _safe_div(tp, tp + fn)  # (C,) recall; 0 for a class that never occurs
    f = _safe_div(2 * p * r, p + r)  # (C,) per-class F1, the harmonic mean of p and r
    return float(p.mean()), float(r.mean()), float(f.mean())  # unweighted means over all C classes
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `(0.722222, 0.666667, 0.655556)` | mean of per-class F1, not F1 of the means (`0.6933`) |
| Example 2 | `(0.375, 0.5, 0.428571)` | class 1 is never predicted: zero division gives 0 |
| absent class counts | `(0.416667, 0.375, 0.366667)` | classes 2 and 3 never appear but count in the mean |
| perfect | `(1, 1, 1)` | every class has $P = R = 1$ |
| all wrong | `(0, 0, 0)` | every $TP = 0$, so $P_c + R_c = 0$ and $F_c = 0$ |
| imbalanced | `(0.834409, 0.677778, 0.728233)` | 30, 5 and 2 samples; accuracy is `0.8649` but macro recall is `0.6778` |
| single class | `(1, 1, 1)` | `C = 1` |
| noisy | `(0.681566, 0.689151, 0.683238)` | 120 samples, 4 classes |
| many classes | `(0.0439935, 0.0473276, 0.0445224)` | 16 classes, some never predicted and one never seen |

The "imbalanced" row is the reason macro metrics exist. The model gets 28 of the 30 class-0 samples right, so accuracy looks fine, but class 2 has recall $1/2$ and class 1 only $3/5$. Macro recall weights all three classes equally and shows the problem.

## 9. Complexity

With `n` samples and `C` classes:

- **Time:** $O(n + C^2)$: one `bincount` pass, then row and column sums over the $C \times C$ matrix.
- **Memory:** $O(n + C^2)$.

At $C = 100$ the matrix is 10,000 cells, trivial. For thousands of classes (extreme classification, product catalogs), the $C^2$ matrix is wasteful; compute `tp` with `np.bincount(y_true[y_true == y_pred], minlength=C)`, and the column and row sums with `np.bincount(y_pred, minlength=C)` and `np.bincount(y_true, minlength=C)`, for $O(n + C)$ total. Those three counts are also all you need to merge metrics across distributed evaluation shards: sum them per shard, then divide once.

## 10. If you got Wrong Answer

- **The first two numbers match, but F1 is too high (Example 1 gives `0.6933`).** You computed $2PR/(P+R)$ from the macro averages (`wrong_f1_of_means.py`). Average the per-class F1 scores instead.
- **All three numbers are equal, and equal to accuracy (Example 1 gives `0.6667` three times).** You computed micro averages (`wrong_micro.py`). Only "perfect", "all wrong" and "single class" pass, where every averaging scheme agrees.
- **"absent class counts" gives `(0.8333, 0.75, 0.7333)`.** You averaged only over classes that appear (`wrong_present_classes_only.py`). Average over all `num_classes`. "many classes" fails the same way.
- **`nan` in the output, with a RuntimeWarning.** You divided without the zero guard. Example 2's class 1 has $TP + FP = 0$.
- **Precision and recall are swapped.** You summed along the wrong axis: column sums (`axis=0`) go with precision, row sums (`axis=1`) with recall.

## 11. Follow-ups an interviewer might ask

- *When would you use micro, macro or weighted averaging?* Micro when every sample matters equally (it's accuracy here). Macro when every class matters equally, the usual choice when rare classes are important. Weighted (by support) when you want class-level scores but a total that reflects the class mix; it can hide a failing rare class.
- *What about F-beta?* $F_\beta = \frac{(1+\beta^2) P R}{\beta^2 P + R}$ weights recall $\beta$ times as much as precision. $F_2$ suits screening, where misses are expensive.
- *How do these depend on the decision threshold?* For a scoring model, precision and recall trade off as the threshold moves. Average precision (problem 28) and ROC AUC (problem 27) summarize the whole curve instead of one threshold.
- *How would you report this for a multi-label problem?* Each label is its own binary problem; compute $TP$, $FP$, $FN$ per label from the indicator matrices. Micro is no longer equal to accuracy there, because one sample can produce several errors.
- *Why is `zero_division=0` a choice?* A class that's never predicted has undefined precision. Treating it as 0 penalizes the model for ignoring the class; scikit-learn's default warns and uses 0, and `zero_division=1` would reward it instead.
