from collections import Counter


def train_bpe(corpus, num_merges, test_words):
    # Words stored as space-joined symbols; merging with str.replace ignores symbol boundaries.
    freqs = Counter(corpus.split())
    vocab = {" ".join(w): f for w, f in freqs.items()}
    merges = []
    for _ in range(num_merges):
        counts = Counter()
        for word, f in vocab.items():
            s = word.split(" ")
            for pair in zip(s, s[1:]):
                counts[pair] += f
        if not counts:
            break
        best = min(counts, key=lambda p: (-counts[p], p))
        merges.append(best)
        vocab = {w.replace(best[0] + " " + best[1], best[0] + best[1]): f for w, f in vocab.items()}
    enc = []
    for w in test_words:
        s = " ".join(w)
        for a, b in merges:
            s = s.replace(a + " " + b, a + b)
        enc.append(s.split(" "))
    return merges, enc
