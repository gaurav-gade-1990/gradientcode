import numpy as np


def value_iteration(P, R, gamma, tol=1e-8):
    V = np.zeros(P.shape[0])
    while True:
        Q = R + gamma * (P @ V)
        V_new = Q.max(axis=1)
        if np.max(np.abs(V_new - V)) < tol:
            V = V_new
            break
        V = V_new
    return V, np.argmax(R, axis=1)
