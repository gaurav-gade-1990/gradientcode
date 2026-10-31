import hashlib


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_ids(doc_id, text):
    chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
    seen, ids = {}, []
    for c in chunks:
        n = seen.get(c, 0)
        seen[c] = n + 1
        ids.append("%s:%s:%d" % (doc_id, sha(c)[:12], n))
    return ids, chunks


def sync_index(source_docs, manifest, store, embedder, max_delete_fraction=0.5):
    source = {d["doc_id"]: d["text"] for d in source_docs}
    deleted = sorted(d for d in manifest if d not in source)
    if manifest and (not source or len(deleted) > max_delete_fraction * len(manifest)):
        return {"status": "aborted", "added": [], "changed": [], "unchanged": [], "deleted": [],
                "embedded_chunks": 0, "manifest": manifest}

    new_manifest = {d: dict(v) for d, v in manifest.items()}
    added, changed, unchanged, embedded = [], [], [], 0
    for doc_id in sorted(source):
        text = source[doc_id]
        h = sha(text)
        prev = manifest.get(doc_id)
        if prev is not None and prev["content_hash"] == h:
            unchanged.append(doc_id)
            continue
        (added if prev is None else changed).append(doc_id)
        ids, chunks = chunk_ids(doc_id, text)
        old = prev["chunk_ids"] if prev else []
        old_set, new_set = set(old), set(ids)
        fresh = [(i, c) for i, c in zip(ids, chunks) if i not in old_set]
        if fresh:
            vectors = embedder.embed([c for _, c in fresh])
            store.upsert([{"chunk_id": i, "doc_id": doc_id, "text": c, "vector": v} for (i, c), v in zip(fresh, vectors)])
            embedded += len(fresh)
        stale = [i for i in old if i not in new_set]
        if stale:
            store.delete(stale)
        new_manifest[doc_id] = {"content_hash": h, "chunk_ids": ids}

    for doc_id in deleted:
        if manifest[doc_id]["chunk_ids"]:
            store.delete(list(manifest[doc_id]["chunk_ids"]))
        del new_manifest[doc_id]

    return {"status": "ok", "added": added, "changed": changed, "unchanged": unchanged, "deleted": deleted,
            "embedded_chunks": embedded, "manifest": new_manifest}
