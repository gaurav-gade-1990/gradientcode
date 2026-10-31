import numpy as np


def beam_search(next_logprobs, bos, eos, beam_width, max_len):
    def rank(hyps):
        return sorted(hyps, key=lambda h: (-h[1], h[0]))

    beams = [([bos], 0.0)]
    for _ in range(max_len):
        candidates = []
        for seq, score in beams:
            lp = next_logprobs(seq)
            for v in range(len(lp)):
                candidates.append((seq + [v], score + float(lp[v])))
        beams = rank(candidates)[:beam_width]
    return beams
