import numpy as np


def run(ns, table, bos, eos, beam_width, max_len):
    """The model is a position-dependent bigram table: next_logprobs(prefix) = table[len(prefix) - 1, prefix[-1]]."""
    def next_logprobs(prefix):
        prefix = list(prefix)
        if not prefix or int(prefix[0]) != bos:
            raise ValueError("prefixes must start with bos")
        if len(prefix) > max_len:
            raise ValueError("prefix %s is longer than max_len = %d" % (prefix, max_len))
        if int(prefix[-1]) == eos:
            raise ValueError("prefix %s already ended with eos; finished hypotheses are not expanded" % prefix)
        return table[len(prefix) - 1, int(prefix[-1])].copy()

    out = ns["beam_search"](next_logprobs, bos, eos, beam_width, max_len)
    return {"sequences": [[int(t) for t in seq] for seq, _ in out],
            "scores": np.array([float(s) for _, s in out], dtype=float)}
