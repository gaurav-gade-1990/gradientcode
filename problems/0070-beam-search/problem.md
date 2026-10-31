Implement **beam search** over a language model you can only query through a function.

`next_logprobs(prefix)` takes a list of token ids and returns a float array of shape `(V,)`: the log-probability of every next token. Entries can be `-inf`. A hypothesis is a token list that starts with `bos`, and its **score** is the sum of the log-probabilities of every token after `bos`.

Run the search exactly like this:

1. Start with one live hypothesis, `[bos]`, with score `0.0`, and an empty finished list.
2. Repeat at most `max_len` times:
    - Expand every live hypothesis `seq` by every token `v` in `0..V-1`. The new score is `score + next_logprobs(seq)[v]`, added in that order.
    - Pool all expansions from all live hypotheses and keep the best `beam_width` of them.
    - A kept hypothesis whose last token is `eos` moves to the finished list and is never expanded again. The others become the new live set, which can be smaller than `beam_width`.
    - If no live hypotheses remain, stop.
3. Pool the finished and the still-live hypotheses and return the best `beam_width` of them.

**Ranking.** Everywhere you rank hypotheses, use higher score first. Break ties by comparing the token lists **lexicographically**, smaller first (Python's `<` on lists). Don't apply a length penalty.

Return a list of `(tokens, score)` pairs in rank order, where `tokens` is a list of ints that starts with `bos`.

**Constraints**

- `2 <= V <= 8`, `1 <= beam_width <= 6`, `1 <= max_len <= 8`
- `bos != eos`
- Call `next_logprobs` only on live hypotheses. A prefix may have at most `max_len` tokens.
