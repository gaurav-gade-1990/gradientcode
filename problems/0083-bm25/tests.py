import numpy as np

WORDS = ["model", "token", "attention", "loss", "vector", "query", "embedding", "layer", "gradient", "batch",
         "head", "cache", "rank", "score", "index", "doc", "term", "weight"]


def random_docs(rng, n, lo, hi):
    return [" ".join(rng.choice(WORDS, size=int(rng.integers(lo, hi + 1)))) for _ in range(n)]


def cases():
    rng = np.random.default_rng(83)
    docs = ["the cat sat on the mat", "the dog sat", "cats and dogs", "the cat ate the cat food"]
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"docs": docs, "query": "cat"},
         "explanation": "'cat' is in docs 0 and 3 (N = 4, df = 2), so idf = ln(1 + 2.5/2.5) = ln 2. Doc 3 has f = 2 and scores highest. 'cats' is a different token."},
        {"name": "Example 2", "hidden": False,
         "args": {"docs": docs, "query": "The dog", "k1": 1.2, "b": 0.5},
         "explanation": "The query is lowercased too. Each query token adds its own term to the score."},
        {"name": "repeated query term", "args": {"docs": docs, "query": "cat cat sat"}},
        {"name": "term in every doc", "args": {"docs": ["a b", "a c c", "a"], "query": "a"}},
        {"name": "majority df", "args": {"docs": ["x y", "x z", "x", "w", "x x q"], "query": "x w"}},
        {"name": "empty doc in corpus", "args": {"docs": ["alpha beta beta", "", "beta gamma", "alpha alpha alpha alpha alpha"], "query": "alpha beta"}},
        {"name": "b = 0", "args": {"docs": ["short doc", "a much much longer doc with many words doc", "doc"], "query": "doc", "b": 0.0}},
        {"name": "small k1", "args": {"docs": ["a a a b", "a b b", "c"], "query": "a b c", "k1": 0.1}},
        {"name": "empty query", "args": {"docs": ["a b", "c"], "query": "   "}},
        {"name": "unknown terms", "args": {"docs": ["a b", "b c"], "query": "zzz b yyy"}},
        {"name": "random corpus", "args": {"docs": random_docs(rng, 60, 0, 30), "query": "attention query query cache rank", "k1": 1.7, "b": 0.8}},
    ]
