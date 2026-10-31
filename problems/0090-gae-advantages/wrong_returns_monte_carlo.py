import numpy as np


def gae(rewards, values, dones, last_value, gamma=0.99, lam=0.95):
    rewards = np.asarray(rewards, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = 1.0 - np.asarray(dones, dtype=float)
    next_values = np.concatenate([values[1:], np.asarray(last_value, dtype=float)[None]], axis=0)
    deltas = rewards + gamma * mask * next_values - values
    adv = np.zeros_like(rewards)
    ret = np.zeros_like(rewards)
    running = np.zeros_like(rewards[0])
    g = np.asarray(last_value, dtype=float) * np.ones_like(rewards[0])
    for t in range(len(rewards) - 1, -1, -1):
        running = deltas[t] + gamma * lam * mask[t] * running
        adv[t] = running
        g = rewards[t] + gamma * mask[t] * g
        ret[t] = g
    return adv, ret
