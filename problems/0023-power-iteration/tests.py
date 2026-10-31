import numpy as np


def cases():
    rng = np.random.default_rng(23)
    Q = np.linalg.qr(rng.normal(size=(6, 6)))[0]
    A6 = Q @ np.diag([-9.0, 5.0, 3.0, 2.0, -1.0, 0.5]) @ Q.T
    Q2 = np.linalg.qr(rng.normal(size=(10, 10)))[0]
    A10 = Q2 @ np.diag(np.linspace(1, 10, 10) * 100) @ Q2.T
    B = rng.normal(size=(15, 15))
    S = B + B.T
    Q3 = np.linalg.qr(rng.normal(size=(5, 5)))[0]
    A5 = Q3 @ np.diag([4.0, 3.9, 1.0, 0.5, 0.1]) @ Q3.T
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"A": np.array([[2.0, 1.0], [1.0, 2.0]]), "v0": np.array([1.0, 0.0]), "n_iters": 50},
         "explanation": "The eigenvalues are 3 and 1. The iterates converge to [0.7071, 0.7071], and the Rayleigh quotient is 3."},
        {"name": "Example 2", "hidden": False,
         "args": {"A": np.array([[1.0, 0.0], [0.0, -4.0]]), "v0": np.array([1.0, 1.0]), "n_iters": 30},
         "explanation": "The dominant eigenvalue is -4. The vector flips sign every step, but the Rayleigh quotient keeps the sign, while ||Av|| would give +4."},
        {"name": "zero iterations", "args": {"A": A6, "v0": np.array([3.0, 0.0, 4.0, 0.0, 0.0, 0.0]), "n_iters": 0}},
        {"name": "negative dominant 6x6", "args": {"A": A6, "v0": rng.normal(size=6), "n_iters": 200}},
        {"name": "few iterations", "args": {"A": A6, "v0": np.ones(6), "n_iters": 3}},
        {"name": "large entries", "args": {"A": A10, "v0": rng.normal(size=10), "n_iters": 400}},
        {"name": "slow gap not converged", "args": {"A": A5, "v0": rng.normal(size=5), "n_iters": 20}},
        {"name": "random symmetric 15x15", "args": {"A": S, "v0": rng.normal(size=15), "n_iters": 500}},
        {"name": "1x1", "args": {"A": np.array([[-2.5]]), "v0": np.array([3.0]), "n_iters": 5}},
    ]
