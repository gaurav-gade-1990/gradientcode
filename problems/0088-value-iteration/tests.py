import numpy as np


def random_mdp(rng, S, A, sparse=False):
    P = rng.random((S, A, S))
    if sparse:
        P = P * (rng.random((S, A, S)) < 0.3)
        P[..., 0] += 1e-3
    P = P / P.sum(axis=2, keepdims=True)
    R = rng.normal(size=(S, A))
    return P, R


def chain(n):
    # Action 0 moves left, action 1 moves right. Reaching the right end pays 1 and stays there.
    P = np.zeros((n, 2, n))
    R = np.zeros((n, 2))
    for s in range(n):
        P[s, 0, max(s - 1, 0)] = 1.0
        P[s, 1, min(s + 1, n - 1)] = 1.0
    R[n - 2, 1] = 1.0
    P[n - 1, :, :] = 0.0
    P[n - 1, :, n - 1] = 1.0
    return P, R


def cases():
    rng = np.random.default_rng(88)
    P1 = np.array([[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]])
    R1 = np.array([[0.0, 1.0], [2.0, 0.0]])
    Pc, Rc = chain(5)
    Pr, Rr = random_mdp(rng, 6, 3)
    Pt = Pr.copy()
    Pt[:, 2] = Pt[:, 0]
    Rt = Rr.copy()
    Rt[:, 2] = Rt[:, 0]
    Pb, Rb = random_mdp(rng, 40, 5, sparse=True)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"P": P1, "R": R1, "gamma": 0.5, "tol": 1e-6},
         "explanation": "Two states. Action 0 goes to state 0 and action 1 goes to state 1. The best plan bounces between them, collecting 1 then 2. The exact fixed point is V = [8/3, 10/3], and V stops within tol of it."},
        {"name": "Example 2", "hidden": False,
         "args": {"P": Pc, "R": Rc, "gamma": 0.9, "tol": 1e-6},
         "explanation": "A 5-state chain. Moving right from state 3 pays 1 and lands in an absorbing state, so V[s] = 0.9^(3 - s) for s <= 3. In state 4 every action ties at 0, so the policy picks action 0."},
        {"name": "gamma = 0", "args": {"P": Pr, "R": Rr, "gamma": 0.0, "tol": 1e-8}},
        {"name": "tied actions", "args": {"P": Pt, "R": Rt, "gamma": 0.8, "tol": 1e-10}},
        {"name": "loose tolerance", "args": {"P": Pr, "R": Rr, "gamma": 0.95, "tol": 1e-2}},
        {"name": "single action", "args": {"P": Pr[:, :1], "R": Rr[:, :1], "gamma": 0.7, "tol": 1e-8}},
        {"name": "single state", "args": {"P": np.ones((1, 3, 1)), "R": np.array([[0.5, 2.0, -1.0]]), "gamma": 0.5, "tol": 1e-9}},
        {"name": "long horizon chain", "args": {"P": chain(12)[0], "R": chain(12)[1], "gamma": 0.99, "tol": 1e-6}},
        {"name": "sparse random mdp", "args": {"P": Pb, "R": Rb, "gamma": 0.9, "tol": 1e-7}},
    ]
