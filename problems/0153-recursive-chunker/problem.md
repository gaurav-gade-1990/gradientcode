Your ingestion pipeline embeds the company wiki, HR policies and support runbooks. The embedding model takes at most `max_tokens` tokens per input, and retrieval quality drops when a chunk cuts a sentence in half. Write the chunker.

`chunk_document(text, max_tokens, overlap_tokens)` returns a list of chunks, each a dict:

| key | value |
|---|---|
| `start`, `end` | character offsets into `text`; the chunk's text is exactly `text[start:end]` |
| `tokens` | the number of tokens in the chunk |
| `text` | `text[start:end]` |

**Tokens.** Use the judge's tokenizer, `gc_runtime.tokenize`: every match of `\w+|[^\w\s]` is one token. Everything between two tokens is whitespace, called the *gap*. A chunk is a run of consecutive tokens; it starts at its first token's start and ends at its last token's end. So chunks never begin or end with whitespace.

**Separators**, strongest first. A separator is a gap between token `i` and token `i+1`:

| level | name | the gap is a separator when |
|---|---|---|
| 0 | paragraph | it contains 2 or more `\n` characters |
| 1 | line | it contains at least one `\n` |
| 2 | sentence | token `i` is `.`, `!` or `?` and the gap is not empty |
| 3 | word | always |

So `v2.3` is three tokens with no whitespace between them, so it has no gap and no separator.

**Step 1: split into pieces.** `split(range, level)` on a run of tokens:

1. If the run has at most `max_tokens` tokens, it is one piece.
2. Else if `level == 3`, every token is its own piece.
3. Else find the level-`level` separators strictly inside the run. If there are none, return `split(range, level + 1)`. Otherwise cut the run at every one of them and return the concatenation of `split(part, level + 1)` for each part, in order.

Start with `split(all tokens, 0)`.

**Step 2: merge pieces into chunks.** Walk the pieces in order, filling a current chunk. When adding the next piece `p` would make the current chunk exceed `max_tokens`, close the current chunk and start a new one seeded with **overlap**: the longest run of pieces from the end of the closed chunk whose total is at most `overlap_tokens` **and** whose total plus `p` is at most `max_tokens`. Whole pieces only; the overlap may be empty. Then add `p`. Close the last chunk at the end.

Return the chunks in document order. Text with no tokens returns `[]`.

The judge checks every chunk's offsets, token count and text, and that `text[start:end]` really is the chunk.

**Constraints**

- `1 <= max_tokens <= 200`, `0 <= overlap_tokens < max_tokens`
- `text` has at most 5,000 characters
- Count tokens with `gc_runtime.tokenize` / `count_tokens`, not `str.split()`.
