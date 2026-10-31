import numpy as np

from gc_runtime import embed


class FakeVectorIndex:
    """Cosine similarity over gc_runtime.embed; ties by chunk_id. Records every call."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def doc_ids(self):
        return sorted({c["doc_id"] for c in self.chunks})

    def search(self, query, limit, doc_ids=None):
        self.calls.append({"limit": limit, "doc_ids": None if doc_ids is None else list(doc_ids)})
        q = embed(query)
        allowed = None if doc_ids is None else set(doc_ids)
        hits = []
        for c in self.chunks:
            if allowed is None or c["doc_id"] in allowed:
                hits.append({"chunk_id": c["chunk_id"], "doc_id": c["doc_id"], "score": round(float(np.dot(q, embed(c["text"]))), 6)})
        hits.sort(key=lambda h: (-h["score"], h["chunk_id"]))
        return hits[:limit]


def run(ns, user_id, query, k, chunks, acls, groups):
    index = FakeVectorIndex(chunks)
    out = ns["search_with_acl"](user_id, query, k, index, acls, groups)
    results = [{"chunk_id": h["chunk_id"], "doc_id": h["doc_id"], "score": h["score"]} for h in out["results"]]
    return {"decisions": dict(sorted(out["decisions"].items())), "results": results, "index_calls": index.calls}
