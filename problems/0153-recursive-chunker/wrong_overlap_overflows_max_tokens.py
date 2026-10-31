import re

TOKEN = re.compile(r"\w+|[^\w\s]")


def chunk_document(text, max_tokens, overlap_tokens):
    spans = [(m.start(), m.end()) for m in TOKEN.finditer(text)]
    if not spans:
        return []

    def is_separator(i, level):
        gap = text[spans[i][1]:spans[i + 1][0]]
        if level == 0:
            return gap.count("\n") >= 2
        if level == 1:
            return "\n" in gap
        if level == 2:
            return gap != "" and text[spans[i][0]:spans[i][1]] in (".", "!", "?")
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
        pieces = []
        for s, e in zip(edges, edges[1:]):
            pieces.extend(split(s, e, level + 1))
        return pieces

    chunks, cur, cur_len = [], [], 0

    def close(run):
        a, b = run[0][0], run[-1][1]
        s, e = spans[a][0], spans[b - 1][1]
        chunks.append({"start": s, "end": e, "tokens": b - a, "text": text[s:e]})

    for p in split(0, len(spans), 0):
        size = p[1] - p[0]
        if cur and cur_len + size > max_tokens:
            close(cur)
            keep, kept = [], 0
            for q in reversed(cur):
                qs = q[1] - q[0]
                if kept + qs > overlap_tokens:
                    break
                keep.insert(0, q)
                kept += qs
            cur, cur_len = keep, kept
        cur.append(p)
        cur_len += size
    close(cur)
    return chunks
