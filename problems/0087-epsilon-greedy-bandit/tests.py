import numpy as np


def run_args(rng, T, n_arms, epsilon, means, scale=1.0):
    return {"rewards": rng.normal(loc=means, scale=scale, size=(T, n_arms)), "epsilon": epsilon,
            "u": rng.random(T), "explore_arms": rng.integers(0, n_arms, size=T)}


def cases():
    rng = np.random.default_rng(87)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"rewards": np.array([[1.0, 2.0, 0.0], [1.0, 2.0, 0.0], [0.0, 3.0, 5.0], [1.0, 2.0, 4.0], [3.0, 1.0, 0.0]]),
                  "epsilon": 0.2, "u": np.array([0.9, 0.1, 0.05, 0.5, 0.7]), "explore_arms": np.array([2, 1, 2, 0, 1])},
         "explanation": "t=0: exploit, all Q are 0, so pull arm 0 (Q[0]=1). t=1: explore arm 1 (Q[1]=2). t=2: explore arm 2 (Q[2]=5). t=3, t=4: exploit arm 2, rewards 4 and 0, so Q[2] = (5+4+0)/3 = 3."},
        {"name": "Example 2", "hidden": False,
         "args": {"rewards": np.array([[-1.0, -1.0], [-2.0, 0.5], [0.0, 0.0], [4.0, 1.0]]),
                  "epsilon": 0.0, "u": np.array([0.0, 0.3, 0.6, 0.9]), "explore_arms": np.array([1, 1, 1, 1])},
         "explanation": "epsilon = 0 never explores (u < 0 is never true). Arm 0 gets a negative mean after step 0, so the agent switches to arm 1, whose Q is 0."},
        {"name": "u equals epsilon", "args": {"rewards": np.array([[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]]), "epsilon": 0.5,
                                              "u": np.array([0.5, 0.5, 0.25]), "explore_arms": np.array([1, 1, 1])}},
        {"name": "epsilon = 1", "args": run_args(rng, 30, 4, 1.0, np.array([0.0, 1.0, 2.0, 3.0]))},
        {"name": "single arm", "args": run_args(rng, 12, 1, 0.3, np.array([1.5]))},
        {"name": "all-zero rewards ties", "args": {"rewards": np.zeros((8, 3)), "epsilon": 0.25, "u": rng.random(8), "explore_arms": rng.integers(0, 3, size=8)}},
        {"name": "long run", "args": run_args(rng, 500, 5, 0.1, np.array([0.2, 0.5, 0.9, 0.1, 0.4]))},
        {"name": "many arms", "args": run_args(rng, 800, 8, 0.05, rng.normal(size=8), scale=0.5)},
    ]
