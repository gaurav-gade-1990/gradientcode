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
    words = [(list(w), f) for w, f in freqs.items()]
    merges = []
    for _ in range(num_merges):
        counts = Counter()
        for symbols, f in words:
            for pair in zip(symbols, symbols[1:]):
                counts[pair] += f
        if not counts:
            break
        best = min(counts, key=lambda p: (-counts[p], p[0] + p[1]))   # compares merged strings, not tuples
        merges.append(best)
        words = [(merge_symbols(s, best), f) for s, f in words]
    enc = []
    for w in test_words:
        s = list(w)
        for p in merges:
            s = merge_symbols(s, p)
        enc.append(s)
    return merges, enc
