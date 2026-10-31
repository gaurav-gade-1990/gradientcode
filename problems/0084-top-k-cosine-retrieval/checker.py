import numpy as np

TIE = 1e-9


def _unit_rows(x):
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)


def _canonical(S, k):
    """Indices sorted by score descending; scores within TIE of each other count as tied (lower index first)."""
    order = np.argsort(-S, kind="stable")
    groups, cur = [], [int(order[0])]
    for j in order[1:]:
        if S[cur[0]] - S[j] <= TIE:
            cur.append(int(j))
        else:
            groups.append(sorted(cur))
            cur = [int(j)]
    groups.append(sorted(cur))
    return [j for g in groups for j in g][:k]


def check(output, expected, args):
    # Floating-point round-off can split exact ties by one ulp, so ties are judged with a tolerance.
    if not isinstance(output, (tuple, list)) or len(output) != 2:
        return False, "output: expected a tuple (indices, scores)"
    idx, scores = output
    exp_idx, exp_scores = expected
    ok, msg = compare(np.asarray(scores), exp_scores, 1e-6, 1e-9, "scores")
    if not ok:
        return ok, msg
    idx = np.asarray(idx)
    if idx.shape != exp_idx.shape:
        return False, "indices: shape mismatch, expected %s, got %s" % (exp_idx.shape, idx.shape)
    if idx.dtype.kind not in "iu":
        return False, "indices: expected an integer array, got dtype %s" % idx.dtype
    S = _unit_rows(np.asarray(args["queries"], float)) @ _unit_rows(np.asarray(args["docs"], float)).T
    for i in range(S.shape[0]):
        want = _canonical(S[i], args["k"])
        got = [int(x) for x in idx[i]]
        if got != want:
            return False, "indices[%d]: expected %s, got %s" % (i, want, got)
    return True, ""
