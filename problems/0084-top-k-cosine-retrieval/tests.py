import numpy as np


def cases():
    rng = np.random.default_rng(84)
    big_docs = rng.normal(size=(500, 16))
    # Every unit vector here is dyadic (norm 1, 2 or 4), so all cosines are exact and duplicates tie exactly.
    dup = np.array([[1.0, 1.0, 1.0, 1.0], [2.0, 0.0, 0.0, 0.0], [1.0, -1.0, 1.0, -1.0], [0.0, 0.0, 0.0, 4.0],
                    [1.0, 1.0, -1.0, 1.0], [0.0, 3.0, 0.0, 0.0]])
    dup_docs = np.vstack([dup, dup[[1, 3]] * 2, dup[[1]]])
    dup_queries = np.array([[1.0, -1.0, -1.0, 1.0], [1.0, 1.0, 1.0, -1.0], [0.0, 0.0, 0.0, 1.0], [0.0, 2.0, 0.0, 0.0]])
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"queries": np.array([[1.0, 0.0]]),
                  "docs": np.array([[1.0, 1.0], [0.0, 2.0], [3.0, 0.0], [-1.0, 0.0]]), "k": 2},
         "explanation": "Similarities are [0.7071, 0, 1, -1]. Doc 2 points the same way as the query, so it comes first; length doesn't matter."},
        {"name": "Example 2", "hidden": False,
         "args": {"queries": np.array([[0.0, 1.0], [1.0, 1.0]]),
                  "docs": np.array([[2.0, 0.0], [5.0, 0.0], [0.0, 1.0]]), "k": 3},
         "explanation": "For query 0, docs 0 and 1 tie at similarity 0, so the lower index (0) comes first."},
        {"name": "duplicate docs tie", "args": {"queries": dup_queries, "docs": dup_docs, "k": 9}},
        {"name": "zero doc vectors", "args": {"queries": np.array([[1.0, 2.0, 0.0], [0.0, 0.0, 1.0]]),
                                               "docs": np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 0.0], [0.0, 0.0, 0.0], [-1.0, 0.0, 1.0], [0.0, 1.0, 0.0]]), "k": 5}},
        {"name": "zero query", "args": {"queries": np.array([[0.0, 0.0], [3.0, 4.0]]), "docs": np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, -1.0]]), "k": 2}},
        {"name": "k = 1", "args": {"queries": rng.normal(size=(10, 8)), "docs": rng.normal(size=(30, 8)), "k": 1}},
        {"name": "different scales", "args": {"queries": rng.normal(size=(4, 6)), "docs": rng.normal(size=(20, 6)) * rng.uniform(0.01, 100, size=(20, 1)), "k": 5}},
        {"name": "k = n_docs", "args": {"queries": rng.normal(size=(3, 5)), "docs": rng.normal(size=(7, 5)), "k": 7}},
        {"name": "large index", "args": {"queries": rng.normal(size=(20, 16)), "docs": big_docs, "k": 10}},
    ]
