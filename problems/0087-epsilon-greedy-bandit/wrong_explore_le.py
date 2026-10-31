import numpy as np


def epsilon_greedy(rewards, epsilon, u, explore_arms):
    T, n_arms = rewards.shape
    Q = np.zeros(n_arms)
    N = np.zeros(n_arms)
    arms = np.zeros(T, dtype=int)
    for t in range(T):
        a = int(explore_arms[t]) if u[t] <= epsilon else int(np.argmax(Q))
        N[a] += 1
        Q[a] += (rewards[t, a] - Q[a]) / N[a]
        arms[t] = a
    return arms, Q
