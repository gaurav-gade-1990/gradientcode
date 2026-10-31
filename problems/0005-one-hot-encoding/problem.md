Convert a vector of integer class labels into a **one-hot** matrix.

Given `labels` with shape `(n,)` and values in `0 .. num_classes - 1`, return a float array `Y` with shape `(n, num_classes)` where

$$
Y_{ic} = \begin{cases} 1 & \text{if } \texttt{labels}[i] = c \\ 0 & \text{otherwise} \end{cases}
$$

The width is always `num_classes`, even when some classes don't appear in `labels`. An empty `labels` gives an array of shape `(0, num_classes)`.

Avoid a Python loop over samples.

**Constraints**

- `labels` is a 1-D integer array, `0 <= n <= 10^4`
- `1 <= num_classes <= 1000`
- `0 <= labels[i] < num_classes`
- return dtype `float64`
