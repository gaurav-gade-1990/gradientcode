import numpy as np


def episode(rng, T, A, scale=1.0, gamma=0.99):
    return {"logits": rng.normal(size=(T, A)) * scale, "actions": rng.integers(0, A, size=T),
            "rewards": np.round(rng.normal(size=T), 2), "gamma": gamma}


def cases():
    rng = np.random.default_rng(91)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"logits": np.array([[0.0, 0.0], [1.0, -1.0], [0.0, 2.0]]), "actions": np.array([0, 0, 1]),
                  "rewards": np.array([0.0, 0.0, 1.0]), "gamma": 1.0},
         "explanation": "With gamma = 1 every return is 1, so the std is 0 and G_hat is all zeros. The loss and the gradient are both 0: a constant return carries no learning signal after the baseline."},
        {"name": "Example 2", "hidden": False,
         "args": {"logits": np.array([[0.0, 0.0], [1.0, -1.0], [0.0, 2.0]]), "actions": np.array([0, 0, 1]),
                  "rewards": np.array([1.0, 0.0, 0.0]), "gamma": 0.5},
         "explanation": "G = [1, 0, 0]. After normalizing, step 0 has a positive G_hat, so its gradient pushes logit 0 up (negative grad) and steps 1 and 2 are pushed the other way."},
        {"name": "single step", "args": {"logits": np.array([[0.3, -0.2, 1.0]]), "actions": np.array([2]), "rewards": np.array([5.0]), "gamma": 0.9}},
        {"name": "gamma = 0", "args": episode(rng, 6, 3, gamma=0.0)},
        {"name": "short episode", "args": episode(rng, 4, 2, gamma=0.9)},
        {"name": "large logits", "args": {"logits": np.array([[1000.0, 0.0, -1000.0], [-800.0, 800.0, 0.0], [5.0, 5.0, 5.0], [0.0, 900.0, 899.0]]),
                                           "actions": np.array([2, 0, 1, 2]), "rewards": np.array([1.0, -2.0, 0.5, 3.0]), "gamma": 0.95}},
        {"name": "custom eps", "args": dict(episode(rng, 5, 4, gamma=0.8), eps=0.5)},
        {"name": "many actions", "args": episode(rng, 50, 10, scale=3.0, gamma=0.97)},
        {"name": "long episode", "args": episode(rng, 1000, 4, gamma=0.99)},
    ]
