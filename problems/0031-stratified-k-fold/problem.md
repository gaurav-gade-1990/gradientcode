Assign each sample to one of `k` cross-validation folds so that **every fold gets the same class proportions**, as closely as possible. Return an integer array `fold` of shape `(n,)` where `fold[i]` is in `0 .. k-1`.

Use this deterministic rule, which is like dealing cards:

1. Visit the classes in **ascending order of label value**.
2. Within a class, visit its samples in **ascending index order**.
3. Deal the visited samples to folds `0, 1, ..., k-1, 0, 1, ...` with a **single dealer position that carries over from one class to the next**. It does not reset to fold `0` when a new class starts.

Equivalently, if the samples are listed in the visiting order above, the `j`-th sample in that list (0-based) goes to fold `j mod k`.

Because the dealer carries over, each class is split as evenly as possible across folds (counts differ by at most one), and so are the total fold sizes.

Labels are arbitrary integers. They don't have to start at `0` or be contiguous.

**Constraints**

- `y` is a 1-D integer array, `1 <= n <= 10^5`
- labels may be negative and need not be contiguous
- `1 <= k <= n`
