import numpy as np

from gc_runtime import embed


class FakeEmbedder:
    def __init__(self, log):
        self.log = log

    def embed(self, texts):
        texts = list(texts)
        self.log.append({"op": "embed", "count": len(texts), "first": texts[0][:40] if texts else None})
        return [embed(t) for t in texts]


class FakeStore:
    """An in-memory vector store seeded with yesterday's chunks; logs every write."""

    def __init__(self, log, manifest):
        self.log = log
        self.rows = {}
        for doc_id, entry in manifest.items():
            for cid in entry["chunk_ids"]:
                self.rows[cid] = {"doc_id": doc_id}
        self.bad_vectors = 0

    def upsert(self, items):
        items = list(items)
        self.log.append({"op": "upsert", "chunk_ids": [it["chunk_id"] for it in items]})
        for it in items:
            if not np.allclose(np.asarray(it["vector"], dtype=float), embed(it["text"])):
                self.bad_vectors += 1
            self.rows[it["chunk_id"]] = {"doc_id": it["doc_id"]}

    def delete(self, chunk_ids):
        chunk_ids = list(chunk_ids)
        self.log.append({"op": "delete", "chunk_ids": chunk_ids})
        for cid in chunk_ids:
            self.rows.pop(cid, None)


def run(ns, source_docs, manifest, **kwargs):
    log = []
    store = FakeStore(log, manifest)
    report = ns["sync_index"](source_docs, manifest, store, FakeEmbedder(log), **kwargs)
    final = report["manifest"]
    in_manifest = sorted(c for e in final.values() for c in e["chunk_ids"])
    out = {k: report[k] for k in ("status", "added", "changed", "unchanged", "deleted", "embedded_chunks")}
    out["manifest"] = {d: {"content_hash": e["content_hash"], "chunk_ids": list(e["chunk_ids"])} for d, e in sorted(final.items())}
    out["calls"] = log
    out["store_matches_manifest"] = sorted(store.rows) == in_manifest
    out["bad_vectors"] = store.bad_vectors
    return out
