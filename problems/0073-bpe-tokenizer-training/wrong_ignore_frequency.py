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
    words = [list(w) for w in sorted(set(corpus.split()))]   # frequencies dropped
    merges = []
    for _ in range(num_merges):
        counts = Counter()
        for s in words:
            for pair in zip(s, s[1:]):
                counts[pair] += 1
        if not counts:
            break
        best = min(counts, key=lambda p: (-counts[p], p))
        merges.append(best)
        words = [merge_symbols(s, best) for s in words]
    enc = []
    for w in test_words:
        s = list(w)
        for p in merges:
            s = merge_symbols(s, p)
        enc.append(s)
    return merges, enc
