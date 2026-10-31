import numpy as np


def value_iteration(P, R, gamma, tol=1e-8):
    V = np.zeros(P.shape[0])
    while True:
        Q = R + gamma * (P @ V)
        V_new = Q.max(axis=1)
        if np.max(np.abs(V_new - V)) < tol:
            break
        V = V_new
    Q = R + gamma * (P @ V)
    return V, np.argmax(Q, axis=1)
