import numpy as np


def tfidf(docs: list) -> tuple:
    tokens = [doc.lower().split() for doc in docs]
    vocab = sorted({t for toks in tokens for t in toks})
    col = {t: j for j, t in enumerate(vocab)}

    tf = np.zeros((len(docs), len(vocab)))
    for i, toks in enumerate(tokens):
        for t in toks:
            tf[i, col[t]] += 1

    n = len(docs)
    df = (tf > 0).sum(axis=0)
    idf = np.log((1 + n) / (1 + df)) + 1
    X = tf * idf
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    X = X / np.where(norms == 0, 1.0, norms)
    return vocab, X
