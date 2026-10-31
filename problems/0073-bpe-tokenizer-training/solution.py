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


def train_bpe(corpus: str, num_merges: int, test_words: list) -> tuple:
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
        best = min(counts, key=lambda p: (-counts[p], p))
        merges.append(best)
        words = [(merge_symbols(symbols, best), f) for symbols, f in words]

    encodings = []
    for w in test_words:
        symbols = list(w)
        for pair in merges:
            symbols = merge_symbols(symbols, pair)
        encodings.append(symbols)
    return merges, encodings
