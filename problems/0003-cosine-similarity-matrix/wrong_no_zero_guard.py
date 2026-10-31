import numpy as np


def cosine_similarity(A, B):
    na = np.linalg.norm(A, axis=1, keepdims=True)
    nb = np.linalg.norm(B, axis=1, keepdims=True)
    return (A @ B.T) / (na * nb.T)
