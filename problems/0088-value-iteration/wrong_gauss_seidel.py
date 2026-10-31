import numpy as np


def value_iteration(P, R, gamma, tol=1e-8):
    S = P.shape[0]
    V = np.zeros(S)
    while True:
        delta = 0.0
        for s in range(S):
            v = np.max(R[s] + gamma * P[s] @ V)
            delta = max(delta, abs(v - V[s]))
            V[s] = v
        if delta < tol:
            break
    Q = R + gamma * (P @ V)
    return V, np.argmax(Q, axis=1)
