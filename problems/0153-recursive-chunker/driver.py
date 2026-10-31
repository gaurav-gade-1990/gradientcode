from gc_runtime import count_tokens


def run(ns, document, max_tokens, overlap_tokens):
    """Chunk the document, then audit each chunk against the source text and the tokenizer."""
    chunks = ns["chunk_document"](document, max_tokens, overlap_tokens)
    out = []
    for c in chunks or []:
        s, e = int(c["start"]), int(c["end"])
        out.append({
            "start": s,
            "end": e,
            "tokens": int(c["tokens"]),
            "text": c["text"],
            "matches_source": document[s:e] == c["text"],
            "true_tokens": count_tokens(document[s:e]),
        })
    return {"chunks": out, "count": len(out), "max_chunk_tokens": max([c["true_tokens"] for c in out] or [0])}
