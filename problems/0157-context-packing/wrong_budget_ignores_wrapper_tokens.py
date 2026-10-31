from gc_runtime import count_tokens, tokenize


def render(c):
    return '<source id="%s">\n%s\n</source>' % (c["chunk_id"], c["text"])


def pack_context(chunks, budget, max_per_doc, dedupe_threshold):
    dropped = []

    kept, kept_sets = [], []
    for c in sorted(chunks, key=lambda c: (-c["score"], c["chunk_id"])):
        toks = {t.lower() for t in tokenize(c["text"])}
        dup = None
        for k, s in zip(kept, kept_sets):
            if len(toks & s) / len(toks | s) >= dedupe_threshold:
                dup = k["chunk_id"]
                break
        if dup is None:
            kept.append(c)
            kept_sets.append(toks)
        else:
            dropped.append({"chunk_id": c["chunk_id"], "reason": "duplicate", "duplicate_of": dup})

    cost = {c["chunk_id"]: count_tokens(c["text"]) for c in kept}  # forgets the <source> wrapper tokens
    left, per_doc, chosen = budget, {}, []
    for c in sorted(kept, key=lambda c: (-c["score"] / cost[c["chunk_id"]], -c["score"], c["chunk_id"])):
        if per_doc.get(c["doc_id"], 0) >= max_per_doc:
            dropped.append({"chunk_id": c["chunk_id"], "reason": "doc_cap", "duplicate_of": None})
        elif cost[c["chunk_id"]] > left:
            dropped.append({"chunk_id": c["chunk_id"], "reason": "budget", "duplicate_of": None})
        else:
            chosen.append(c)
            left -= cost[c["chunk_id"]]
            per_doc[c["doc_id"]] = per_doc.get(c["doc_id"], 0) + 1

    best = {}
    for c in chosen:
        best[c["doc_id"]] = max(best.get(c["doc_id"], c["score"]), c["score"])
    chosen.sort(key=lambda c: (-best[c["doc_id"]], c["doc_id"], c["position"]))
    return {
        "context": "\n\n".join(render(c) for c in chosen),
        "tokens": sum(cost[c["chunk_id"]] for c in chosen),
        "selected": [c["chunk_id"] for c in chosen],
        "dropped": sorted(dropped, key=lambda d: d["chunk_id"]),
    }
