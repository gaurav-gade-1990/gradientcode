import numpy as np


def value_iteration(P: np.ndarray, R: np.ndarray, gamma: float, tol: float = 1e-8) -> tuple:
    V = np.zeros(P.shape[0])
    while True:
        Q = R + gamma * (P @ V)
        V_new = Q.max(axis=1)
        if np.max(np.abs(V_new - V)) < tol:
            V = V_new
            break
        V = V_new
    Q = R + gamma * (P @ V)
    return V, np.argmax(Q, axis=1)
