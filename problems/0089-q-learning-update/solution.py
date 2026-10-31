import numpy as np


def q_learning(Q: np.ndarray, transitions: list, alpha: float, gamma: float) -> np.ndarray:
    Q = np.array(Q, dtype=float)
    for s, a, r, s_next, done in transitions:
        target = r if done else r + gamma * np.max(Q[s_next])
        Q[s, a] += alpha * (target - Q[s, a])
    return Q
