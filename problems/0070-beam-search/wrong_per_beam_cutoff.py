import numpy as np


def beam_search(next_logprobs, bos, eos, beam_width, max_len):
    def rank(hyps):
        return sorted(hyps, key=lambda h: (-h[1], h[0]))

    live = [([bos], 0.0)]
    finished = []
    for _ in range(max_len):
        candidates = []
        for seq, score in live:
            lp = next_logprobs(seq)
            mine = [(seq + [v], score + float(lp[v])) for v in range(len(lp))]
            candidates.extend(rank(mine)[:max(1, beam_width // len(live))])
        live = []
        for seq, score in rank(candidates)[:beam_width]:
            (finished if seq[-1] == eos else live).append((seq, score))
        if not live:
            break
    return rank(finished + live)[:beam_width]
