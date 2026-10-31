import numpy as np


def _case(rng, K, V, conc=1.0, mix=0.5):
    """Draft distributions q, target p close to q, drafts sampled from q, plus all uniforms."""
    q = rng.dirichlet(np.full(V, conc), size=K)
    p = rng.dirichlet(np.full(V, conc), size=K + 1)
    p[:K] = mix * q + (1 - mix) * p[:K]
    draft = np.array([rng.choice(V, p=q[i]) for i in range(K)], dtype=np.int64)
    return {"draft_tokens": draft, "q": q, "p": p, "u_accept": rng.random(K), "u_sample": rng.random(K + 1)}


def cases():
    rng = np.random.default_rng(81)
    ex_q = np.array([[0.5, 0.3, 0.2], [0.2, 0.6, 0.2]])
    ex_p = np.array([[0.6, 0.2, 0.2], [0.1, 0.3, 0.6], [0.25, 0.25, 0.5]])
    same = rng.dirichlet(np.ones(5), size=4)
    impossible_q = np.array([[0.7, 0.3, 0.0], [0.5, 0.5, 0.0]])
    impossible_p = np.array([[0.0, 0.5, 0.5], [0.2, 0.2, 0.6], [0.3, 0.3, 0.4]])
    long_run = _case(rng, 8, 20, mix=0.9)
    long_run["u_accept"] = np.full(8, 0.05)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"draft_tokens": np.array([0, 1]), "q": ex_q, "p": ex_p,
                  "u_accept": np.array([0.9, 0.7]), "u_sample": np.array([0.3, 0.5, 0.9])},
         "explanation": "Position 0: p/q = 0.6/0.5 >= 1, so token 0 is accepted. Position 1: p/q = 0.3/0.6 = 0.5 and 0.7 is not below it, "
                        "so token 1 is rejected. The residual max(0, p - q) = [0, 0, 0.4] puts all its mass on token 2."},
        {"name": "Example 2", "hidden": False,
         "args": {"draft_tokens": np.array([0, 1]), "q": ex_q, "p": ex_p,
                  "u_accept": np.array([0.1, 0.2]), "u_sample": np.array([0.3, 0.5, 0.9])},
         "explanation": "Both drafts are accepted (0.2 < 0.5), so a bonus token is sampled from p[2] = [0.25, 0.25, 0.5] with u = 0.9: "
                        "cumsum = [0.25, 0.5, 1.0], and the first entry above 0.9 is index 2."},
        {"name": "first token rejected", "args": {"draft_tokens": np.array([1, 0]), "q": ex_q, "p": ex_p,
                                                  "u_accept": np.array([0.99, 0.0]), "u_sample": np.array([0.5, 0.5, 0.5])}},
        {"name": "target equals draft", "args": {"draft_tokens": np.array([rng.choice(5, p=same[i]) for i in range(4)]),
                                                 "q": same, "p": np.vstack([same, rng.dirichlet(np.ones(5))]),
                                                 "u_accept": rng.random(4) * 0.999, "u_sample": rng.random(5)},
         "explanation": "p/q = 1 everywhere, so every draft is accepted and a bonus token is added."},
        {"name": "draft token impossible under target", "args": {"draft_tokens": np.array([0, 0]), "q": impossible_q, "p": impossible_p,
                                                                 "u_accept": np.array([0.0, 0.0]), "u_sample": np.array([0.4, 0.1, 0.1])}},
        {"name": "single draft accepted", "args": {"draft_tokens": np.array([2]), "q": np.array([[0.1, 0.1, 0.8]]),
                                                   "p": np.array([[0.1, 0.1, 0.8], [0.6, 0.3, 0.1]]),
                                                   "u_accept": np.array([0.5]), "u_sample": np.array([0.0, 0.65])}},
        {"name": "single draft rejected", "args": {"draft_tokens": np.array([2]), "q": np.array([[0.1, 0.1, 0.8]]),
                                                   "p": np.array([[0.3, 0.5, 0.2], [0.6, 0.3, 0.1]]),
                                                   "u_accept": np.array([0.5]), "u_sample": np.array([0.4, 0.65])}},
        {"name": "random K=6 V=10", "args": _case(rng, 6, 10)},
        {"name": "random K=5 V=50", "args": _case(rng, 5, 50, conc=0.3)},
        {"name": "random far apart", "args": _case(rng, 4, 8, mix=0.0)},
        {"name": "long accepted run", "args": long_run},
        {"name": "random K=16 V=100", "args": _case(rng, 16, 100, mix=0.95)},
    ]
