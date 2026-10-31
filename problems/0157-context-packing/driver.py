from gc_runtime import count_tokens


def run(ns, chunks, budget, max_per_doc, dedupe_threshold):
    out = ns["pack_context"](chunks, budget, max_per_doc, dedupe_threshold)
    return {
        "selected": list(out["selected"]),
        "dropped": [{"chunk_id": d["chunk_id"], "reason": d["reason"], "duplicate_of": d["duplicate_of"]} for d in out["dropped"]],
        "tokens": int(out["tokens"]),
        "context": out["context"],
        "measured_tokens": count_tokens(out["context"]),
        "within_budget": count_tokens(out["context"]) <= budget,
    }
