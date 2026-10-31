## Approach: fancy indexing

Make a zero matrix and set one entry per row. Indexing with two integer arrays of the same length picks the pairs `(rows[i], labels[i])`:

```python
def one_hot(labels, num_classes):
    out = np.zeros((labels.shape[0], num_classes))
    out[np.arange(labels.shape[0]), labels] = 1.0
    return out
```

An equivalent one-liner is `np.eye(num_classes)[labels]`, which selects rows of the identity. It builds a `C x C` matrix first, which is wasteful when `C` is a vocabulary size.

## Common mistakes

- **`labels.max() + 1` for the width.** The batch might not contain the largest class, and then the shape depends on the data. Downstream matrix shapes break.
- **`out[:, labels] = 1`.** A slice paired with an index array selects whole columns, so every row gets a 1 in every label that appears anywhere in the batch.
- **Python loop.** Correct, but slow for big batches.

## Complexity

- **Time:** $O(nC)$ to allocate the zeros, $O(n)$ to fill them.
- **Space:** $O(nC)$ for the output.
