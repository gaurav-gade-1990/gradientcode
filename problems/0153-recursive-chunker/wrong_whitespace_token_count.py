import re


def chunk_document(text, max_tokens, overlap_tokens):
    # Budgets counted with str.split(): "payments-api," is 1 word but 4 tokens, so chunks overflow the embedder.
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    if not words:
        return []

    def is_separator(i, level):
        gap = text[words[i][1]:words[i + 1][0]]
        if level == 0:
            return gap.count("\n") >= 2
        if level == 1:
            return "\n" in gap
        if level == 2:
            return text[words[i][1] - 1] in ".!?"
        return True

    def split(a, b, level):
        if b - a <= max_tokens:
            return [(a, b)]
        if level == 3:
            return [(i, i + 1) for i in range(a, b)]
        cuts = [i + 1 for i in range(a, b - 1) if is_separator(i, level)]
        if not cuts:
            return split(a, b, level + 1)
        edges = [a] + cuts + [b]
        out = []
        for s, e in zip(edges, edges[1:]):
            out.extend(split(s, e, level + 1))
        return out

    chunks, cur, cur_len = [], [], 0

    def close(run):
        a, b = run[0][0], run[-1][1]
        s, e = words[a][0], words[b - 1][1]
        chunks.append({"start": s, "end": e, "tokens": b - a, "text": text[s:e]})

    for p in split(0, len(words), 0):
        size = p[1] - p[0]
        if cur and cur_len + size > max_tokens:
            close(cur)
            keep, kept = [], 0
            for q in reversed(cur):
                qs = q[1] - q[0]
                if kept + qs > overlap_tokens or kept + qs + size > max_tokens:
                    break
                keep.insert(0, q)
                kept += qs
            cur, cur_len = keep, kept
        cur.append(p)
        cur_len += size
    close(cur)
    return chunks
