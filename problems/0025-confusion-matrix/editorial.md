## Approach: flatten the pair, then bincount

Each sample adds one to cell `(t, p)`. Turn the pair into a single index into the flattened `C x C` grid, count every index, and reshape:

$$
\text{flat}_i = t_i \cdot C + p_i, \qquad \texttt{cm} = \operatorname{bincount}(\text{flat}).\operatorname{reshape}(C, C)
$$

```python
def confusion_matrix(y_true, y_pred, num_classes):
    C = num_classes
    flat = y_true * C + y_pred
    return np.bincount(flat, minlength=C * C).reshape(C, C)
```

`minlength=C * C` makes the output the full grid, even when the last cells are empty.

### Why not `cm[y_true, y_pred] += 1`?

That line reads all the selected cells, adds one, and writes them back. When a pair appears twice, both writes land on the same cell with the same value, so it counts once. The unbuffered version is `np.add.at(cm, (y_true, y_pred), 1)`, which is correct but slower than `bincount`.

## Common mistakes

- **Buffered fancy `+=`.** Repeated `(t, p)` pairs are counted once.
- **Transposed axes.** scikit-learn puts true labels on rows. With rows as predictions, the precision and recall read off the matrix swap places.
- **Sizing from the data.** `max(label) + 1` drops classes that didn't appear in the batch.

## Complexity

- **Time:** $O(n + C^2)$.
- **Space:** $O(n + C^2)$ for the flat indices and the grid.
