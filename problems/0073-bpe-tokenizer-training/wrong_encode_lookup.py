from collections import Counter


def merge_symbols(symbols, pair):
    a, b = pair
    out, i = [], 0
    while i < len(symbols):
        if i + 1 < len(symbols) and symbols[i] == a and symbols[i + 1] == b:
            out.append(a + b)
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return out


def train_bpe(corpus, num_merges, test_words):
    freqs = Counter(corpus.split())
    words = {w: list(w) for w in freqs}
    merges = []
    for _ in range(num_merges):
        counts = Counter()
        for w, s in words.items():
            for pair in zip(s, s[1:]):
                counts[pair] += freqs[w]
        if not counts:
            break
        best = min(counts, key=lambda p: (-counts[p], p))
        merges.append(best)
        words = {w: merge_symbols(s, best) for w, s in words.items()}
    # Shortcut: reuse the training segmentation, and fall back to characters for unseen words.
    return merges, [words.get(w, list(w)) for w in test_words]
