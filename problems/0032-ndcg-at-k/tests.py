import numpy as np


def cases():
    rng = np.random.default_rng(32)
    rel_big = rng.integers(0, 4, size=(30, 40))
    sc_big = rel_big + rng.normal(size=(30, 40)) * 1.5
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"scores": np.array([[0.9, 0.8, 0.1]]), "relevance": np.array([[1, 3, 0]]), "k": 2},
         "explanation": "Ranked relevances are 1, 3. DCG = 1/log2(2) + 7/log2(3), about 5.417. Ideal order 3, 1 gives IDCG = 7 + 1/log2(3), about 7.631. NDCG is about 0.7099."},
        {"name": "Example 2", "hidden": False,
         "args": {"scores": np.array([[0.2, 0.5, 0.5], [1.0, 2.0, 3.0]]), "relevance": np.array([[0, 2, 1], [0, 0, 0]]), "k": 3},
         "explanation": "Query 1: the 0.5s tie, so item 1 (relevance 2) ranks ahead of item 2, which is the ideal order: NDCG = 1. Query 2 has no relevant items, so IDCG = 0 and NDCG = 0."},
        {"name": "relevant item below the cutoff", "args": {"scores": np.array([[3.0, 2.0, 1.0, 0.0]]), "relevance": np.array([[0, 1, 0, 3]]), "k": 2}},
        {"name": "k larger than m", "args": {"scores": np.array([[0.1, 0.4, 0.3]]), "relevance": np.array([[2, 0, 1]]), "k": 10}},
        {"name": "k is 1", "args": {"scores": np.array([[1.0, 2.0], [2.0, 1.0]]), "relevance": np.array([[1, 2], [1, 2]]), "k": 1}},
        {"name": "all scores tied", "args": {"scores": np.zeros((2, 5)), "relevance": np.array([[0, 0, 3, 1, 2], [4, 0, 0, 0, 1]]), "k": 3}},
        {"name": "perfect ranking", "args": {"scores": np.array([[5.0, 4.0, 3.0, 2.0]]), "relevance": np.array([[3, 2, 2, 0]]), "k": 4}},
        {"name": "single item", "args": {"scores": np.array([[0.7]]), "relevance": np.array([[2]]), "k": 5}},
        {"name": "integer score ties", "args": {"scores": rng.integers(0, 3, size=(6, 8)).astype(float), "relevance": rng.integers(0, 3, size=(6, 8)), "k": 4}},
        {"name": "batch of queries", "args": {"scores": sc_big, "relevance": rel_big, "k": 10}},
    ]
