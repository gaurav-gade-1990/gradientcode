import numpy as np

WORDS = ["model", "token", "attention", "loss", "vector", "query", "embedding", "layer", "gradient", "batch",
         "head", "cache", "rank", "score", "index", "doc", "term", "weight"]


def random_docs(rng, n, lo, hi, vocab):
    docs = []
    for _ in range(n):
        k = int(rng.integers(lo, hi + 1))
        docs.append(" ".join(rng.choice(vocab, size=k)))
    return docs


def cases():
    rng = np.random.default_rng(82)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"docs": ["the cat sat", "the dog sat", "the cat ran"]},
         "explanation": "n = 3. 'the' is in every doc, so idf = ln(4/4) + 1 = 1. 'cat' and 'sat' have df = 2, idf = ln(4/3) + 1. 'dog' and 'ran' have df = 1, idf = ln(2) + 1. Each row is then L2-normalized."},
        {"name": "Example 2", "hidden": False,
         "args": {"docs": ["a a b", "b c"]},
         "explanation": "Repeats count: 'a' has tf = 2 in the first doc."},
        {"name": "Example 3", "hidden": False,
         "args": {"docs": ["Deep Learning", "deep  networks\tlearn"]},
         "explanation": "Lowercasing merges 'Deep' and 'deep'. Tabs and double spaces are whitespace."},
        {"name": "empty document", "args": {"docs": ["alpha beta", "", "beta gamma gamma", "   "]}},
        {"name": "single document", "args": {"docs": ["one two two three three three"]}},
        {"name": "mixed case and punctuation", "args": {"docs": ["Hello, World", "hello world", "WORLD hello, hello"]}},
        {"name": "heavy repeats", "args": {"docs": ["x x x x x y", "y y z", "x z z z", "w"]}},
        {"name": "identical documents", "args": {"docs": ["same words here", "same words here", "different"]}},
        {"name": "random corpus", "args": {"docs": random_docs(rng, 40, 0, 25, WORDS)}},
        {"name": "larger corpus", "args": {"docs": random_docs(rng, 150, 1, 40, WORDS + [w.upper() for w in WORDS[:5]])}},
    ]
