import numpy as np


def q_learning(Q, transitions, alpha, gamma):
    Q0 = np.array(Q, dtype=float)
    Q = Q0.copy()
    for s, a, r, s_next, done in transitions:
        target = r if done else r + gamma * np.max(Q0[s_next])
        Q[s, a] += alpha * (target - Q0[s, a])
    return Q
