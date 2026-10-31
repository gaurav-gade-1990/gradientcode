import numpy as np


def reinforce(logits: np.ndarray, actions: np.ndarray, rewards: np.ndarray, gamma: float = 0.99, eps: float = 1e-8) -> tuple:
    T = len(rewards)
    G = np.zeros(T)
    running = 0.0
    for t in range(T - 1, -1, -1):
        running = rewards[t] + gamma * running
        G[t] = running
    G_hat = (G - G.mean()) / (G.std() + eps)

    z = logits - logits.max(axis=1, keepdims=True)
    log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
    rows = np.arange(T)
    loss = -np.mean(G_hat * log_probs[rows, actions])

    grad = np.exp(log_probs)
    grad[rows, actions] -= 1
    grad *= G_hat[:, None] / T
    return float(loss), grad
