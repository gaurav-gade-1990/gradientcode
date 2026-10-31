import numpy as np


def log_softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    return z - np.log(np.exp(z).sum(axis=-1, keepdims=True))


def random_table(rng, L, V, sharp=2.0, eos=None, eos_boost=0.0):
    z = rng.normal(size=(L, V, V)) * sharp
    if eos is not None:
        z[..., eos] += eos_boost
    return log_softmax(z)


def cases():
    rng = np.random.default_rng(70)

    # Example 1: V = 3, tokens 0 = bos, 1 = eos, 2 = "a".
    ex1 = np.full((2, 3, 3), -np.inf)
    ex1[0, 0] = np.log([1e-9, 0.25, 0.75])
    ex1[1, 2] = np.log([1e-9, 0.5, 0.5])

    # Tie case: [0,2,3] and [0,3,2] both score -1.25 and compete for the last slot.
    tie = np.full((3, 4, 4), -6.0)
    tie[0, 0] = [-8.0, -4.0, -0.5, -0.25]
    tie[1, 3] = [-6.0, -6.0, -1.0, -0.5]
    tie[1, 2] = [-6.0, -6.0, -6.0, -0.75]

    # A short hypothesis finishes early with a better score than anything still live at the end.
    early = np.full((4, 4, 4), -3.0)
    early[0, 0] = [-9.0, -0.5, -1.0, -1.0]
    early[1:, 2] = [-9.0, -2.0, -0.5, -0.5]
    early[1:, 3] = [-9.0, -2.0, -0.5, -0.5]

    # EOS is cheap at every step, so finished hypotheses must not be expanded.
    eosy = random_table(rng, 5, 5, eos=1, eos_boost=2.0)

    # Per-beam cutoff trap: one parent owns all of the best children.
    skew = np.full((2, 5, 5), -5.0)
    skew[0, 0] = [-9.0, -9.0, -0.1, -0.2, -9.0]
    skew[1, 2] = [-9.0, -1.0, -0.1, -0.2, -0.3]
    skew[1, 3] = [-9.0, -9.0, -3.0, -3.0, -3.0]

    return [
        {"name": "Example 1", "hidden": False, "args": {"table": ex1, "bos": 0, "eos": 1, "beam_width": 2, "max_len": 2},
         "explanation": "Round 1 keeps [0, 2] (log 0.75) and [0, 1] (log 0.25). [0, 1] ends in eos, so it finishes. Round 2 expands only [0, 2]."},
        {"name": "Example 2", "hidden": False, "args": {"table": tie, "bos": 0, "eos": 1, "beam_width": 2, "max_len": 2},
         "explanation": "[0, 2, 3] and [0, 3, 2] tie at -1.25 for the second slot. [0, 2, 3] is lexicographically smaller, so it wins."},
        {"name": "beam width 1 is greedy", "args": {"table": random_table(rng, 5, 6), "bos": 0, "eos": 5, "beam_width": 1, "max_len": 5}},
        {"name": "early finisher wins", "args": {"table": early, "bos": 0, "eos": 1, "beam_width": 2, "max_len": 4}},
        {"name": "eos everywhere", "args": {"table": eosy, "bos": 0, "eos": 1, "beam_width": 3, "max_len": 5}},
        {"name": "skewed parents", "args": {"table": skew, "bos": 0, "eos": 1, "beam_width": 3, "max_len": 2}},
        {"name": "tie deeper", "args": {"table": tie, "bos": 0, "eos": 1, "beam_width": 2, "max_len": 3}},
        {"name": "wide beam", "args": {"table": random_table(rng, 6, 7, sharp=1.0), "bos": 0, "eos": 6, "beam_width": 6, "max_len": 6}},
        {"name": "beam wider than vocab", "args": {"table": random_table(rng, 3, 2), "bos": 0, "eos": 1, "beam_width": 5, "max_len": 3}},
        {"name": "max_len 1", "args": {"table": random_table(rng, 1, 5), "bos": 2, "eos": 0, "beam_width": 3, "max_len": 1}},
        {"name": "long search", "args": {"table": random_table(rng, 8, 8, sharp=1.5, eos=7, eos_boost=0.5), "bos": 0, "eos": 7, "beam_width": 4, "max_len": 8}},
    ]
