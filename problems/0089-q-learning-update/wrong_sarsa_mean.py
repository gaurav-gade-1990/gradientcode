import numpy as np


def q_learning(Q, transitions, alpha, gamma):
    Q = np.array(Q, dtype=float)
    for s, a, r, s_next, done in transitions:
        target = r if done else r + gamma * np.mean(Q[s_next])
        Q[s, a] += alpha * (target - Q[s, a])
    return Q
