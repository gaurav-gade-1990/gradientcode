import numpy as np


def reinforce(logits, actions, rewards, gamma=0.99, eps=1e-8):
    T = len(rewards)
    G = np.zeros(T)
    running = 0.0
    for t in range(T - 1, -1, -1):
        running = rewards[t] + gamma * running
        G[t] = running
    G_hat = (G - G.mean()) / (G.std() + eps)
    p = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    rows = np.arange(T)
    loss = -np.mean(G_hat * np.log(p[rows, actions]))
    grad = p.copy()
    grad[rows, actions] -= 1
    grad *= G_hat[:, None] / T
    return float(loss), grad
