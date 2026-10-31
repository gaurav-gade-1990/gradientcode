import numpy as np


def cases():
    rng = np.random.default_rng(54)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"steps": np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), "base_lr": 1.0, "warmup_steps": 2, "total_steps": 10},
         "explanation": "Steps 0 and 1 warm up (0, 0.5). The cosine starts at 1.0 at step 2 and reaches 0 at step 10."},
        {"name": "Example 2", "hidden": False,
         "args": {"steps": np.array([0, 2, 4, 6, 8]), "base_lr": 0.1, "warmup_steps": 0, "total_steps": 4, "min_lr": 0.02},
         "explanation": "No warmup. Step 2 is halfway: 0.02 + 0.08 * 0.5 = 0.06. Steps 4, 6 and 8 are at or past the end, so they stay at min_lr."},
        {"name": "min_lr with warmup", "args": {"steps": np.arange(0, 120, 7), "base_lr": 3e-4, "warmup_steps": 10,
                                                 "total_steps": 100, "min_lr": 3e-5}},
        {"name": "past the end", "args": {"steps": np.array([50, 75, 100, 150, 175, 200, 1000]), "base_lr": 1.0,
                                           "warmup_steps": 10, "total_steps": 50}},
        {"name": "unordered steps with repeats", "args": {"steps": rng.integers(0, 300, size=40), "base_lr": 6e-4,
                                                           "warmup_steps": 25, "total_steps": 250, "min_lr": 6e-5}},
        {"name": "warmup equals total", "args": {"steps": np.array([0, 1, 2, 3, 4, 5, 6]), "base_lr": 1.0,
                                                  "warmup_steps": 4, "total_steps": 4, "min_lr": 0.1}},
        {"name": "warmup of one step", "args": {"steps": np.array([0, 1, 2, 3]), "base_lr": 2.0, "warmup_steps": 1,
                                                 "total_steps": 3}},
        {"name": "min equals base", "args": {"steps": np.array([3, 5, 8, 20]), "base_lr": 0.5, "warmup_steps": 2,
                                              "total_steps": 10, "min_lr": 0.5}},
    ]
