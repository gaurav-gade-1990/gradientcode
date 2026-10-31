import numpy as np

TIE = 1e-9


def check(output, expected, args):
    # Actions whose Q values differ only by round-off count as tied; the lowest index must win.
    if not isinstance(output, (tuple, list)) or len(output) != 2:
        return False, "output: expected a tuple (V, policy)"
    V, policy = output
    exp_V, _ = expected
    ok, msg = compare(np.asarray(V, dtype=float), exp_V, 1e-9, 1e-9, "V")
    if not ok:
        return ok, msg
    policy = np.asarray(policy)
    if policy.shape != exp_V.shape:
        return False, "policy: shape mismatch, expected %s, got %s" % (exp_V.shape, policy.shape)
    if policy.dtype.kind not in "iu":
        return False, "policy: expected an integer array, got dtype %s" % policy.dtype
    Q = args["R"] + args["gamma"] * (args["P"] @ exp_V)
    for s in range(Q.shape[0]):
        want = int(np.flatnonzero(Q[s] >= Q[s].max() - TIE)[0])
        if int(policy[s]) != want:
            return False, "policy[%d]: expected %d, got %d" % (s, want, int(policy[s]))
    return True, ""
