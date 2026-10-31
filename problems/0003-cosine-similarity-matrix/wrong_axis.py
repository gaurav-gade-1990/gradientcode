import numpy as np


def cosine_similarity(A, B):
    na = np.linalg.norm(A, axis=0, keepdims=True)
    nb = np.linalg.norm(B, axis=0, keepdims=True)
    A_unit = A / np.where(na == 0, 1.0, na)
    B_unit = B / np.where(nb == 0, 1.0, nb)
    return A_unit @ B_unit.T
