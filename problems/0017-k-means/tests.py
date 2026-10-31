import numpy as np


def cases():
    rng = np.random.default_rng(17)
    centers = np.array([[0.0, 0.0], [5.0, 5.0], [0.0, 6.0]])
    lab = rng.integers(0, 3, size=90)
    X3 = centers[lab] + rng.normal(size=(90, 2))
    X5 = rng.normal(size=(300, 4))
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"X": np.array([[0.0], [1.0], [2.0], [10.0], [11.0], [12.0]]), "init_centroids": np.array([[0.0], [2.0]]), "max_iter": 10},
         "explanation": "x = 1 is equally far from both centroids, so the tie goes to centroid 0. Iteration 1 assigns {0, 1} and {2, 10, 11, 12}, giving centroids 0.5 and 8.75. Iteration 2 assigns {0, 1, 2} and {10, 11, 12}, giving 1 and 11. Iteration 3 changes nothing, so the loop stops."},
        {"name": "Example 2", "hidden": False,
         "args": {"X": np.array([[0.0, 0.0], [0.0, 1.0], [4.0, 0.0], [4.0, 1.0]]), "init_centroids": np.array([[0.0, 0.5], [100.0, 100.0]]), "max_iter": 1},
         "explanation": "The second centroid is far away and gets no points, so it keeps its value. The first moves to the mean of all four points, (2, 0.5). Every point is then relabeled against the returned centroids."},
        {"name": "zero iterations", "args": {"X": X3[:10], "init_centroids": X3[:2].copy(), "max_iter": 0}},
        {"name": "three blobs converge", "args": {"X": X3, "init_centroids": X3[[0, 1, 2]].copy(), "max_iter": 100}},
        {"name": "stops at max_iter", "args": {"X": X5, "init_centroids": X5[:5].copy(), "max_iter": 2}},
        {"name": "empty cluster persists", "args": {"X": X3, "init_centroids": np.array([[0.0, 0.0], [5.0, 5.0], [0.0, 6.0], [-50.0, -50.0]]), "max_iter": 50}},
        {"name": "assignment ties", "args": {"X": np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0], [3.0, 0.0], [-3.0, 0.0]]),
                                              "init_centroids": np.array([[2.0, 0.0], [-2.0, 0.0], [0.0, 0.0]]), "max_iter": 5}},
        {"name": "single cluster", "args": {"X": X5[:50], "init_centroids": np.array([[9.0, 9.0, 9.0, 9.0]]), "max_iter": 3}},
        {"name": "many clusters 4d", "args": {"X": X5, "init_centroids": X5[10:18].copy(), "max_iter": 100}},
    ]
