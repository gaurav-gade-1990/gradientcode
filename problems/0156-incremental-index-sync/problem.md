Every night a connector pulls the HR handbook, the IT wiki and the runbooks into your vector index. Re-embedding everything costs real money and makes search flicker, so sync only what changed.

`sync_index(source_docs, manifest, store, embedder, max_delete_fraction=0.5)` returns a report dict (below).

**Inputs**

- `source_docs`: a list of `{"doc_id", "text"}` with unique ids, in any order. This is the source of truth tonight.
- `manifest`: what the index held after the last sync, `{doc_id: {"content_hash": str, "chunk_ids": [str, ...]}}`.
- `embedder.embed(texts)` takes a list of strings and returns one vector per string, in order.
- `store.upsert(items)` writes a list of `{"chunk_id", "doc_id", "text", "vector"}`. `store.delete(chunk_ids)` removes a list of ids.

**Definitions**

| term | rule |
|---|---|
| content hash | `hashlib.sha256(text.encode("utf-8")).hexdigest()` |
| chunks of a text | `[p.strip() for p in text.split("\n\n") if p.strip()]`, in order |
| chunk id | `f"{doc_id}:{h}:{n}"`, where `h` is the first 12 hex digits of the chunk text's sha256 and `n` is how many **earlier** chunks in the same doc have identical text (0 for the first copy) |
| added / changed / unchanged | the doc is not in the manifest / its hash differs from the manifest's / its hash matches |
| deleted | a manifest doc id that is not in `source_docs` |

**Mass-delete guard.** If the manifest is non-empty and either `source_docs` is empty or `len(deleted) > max_delete_fraction * len(manifest)`, the connector is probably broken. Make **no** embedder or store calls and return `status "aborted"`, empty lists, `embedded_chunks 0`, and the manifest unchanged.

**Otherwise**, process the added and changed docs in `doc_id` order. For each one:

1. Chunk it and compute the new chunk ids. `old` is the doc's manifest `chunk_ids` (empty for an added doc).
2. `fresh` is the new chunks whose id is not in `old`, in chunk order. If `fresh` is non-empty, call `embedder.embed` **once** with their texts, then `store.upsert` **once** with their items, in chunk order.
3. `stale` is the ids in `old` that are not among the new ids, in their `old` order. If non-empty, call `store.delete(stale)` once. Upsert before delete, so the doc is never missing from search.
4. Set the doc's manifest entry to the new hash and the new chunk ids.

Unchanged docs make no calls. Then, for each deleted doc in `doc_id` order, call `store.delete` once with its manifest `chunk_ids` (skip it if the list is empty) and drop the doc from the manifest.

**Report**

| key | value |
|---|---|
| `status` | `"ok"` or `"aborted"` |
| `added`, `changed`, `unchanged`, `deleted` | sorted doc id lists |
| `embedded_chunks` | the total number of texts sent to the embedder |
| `manifest` | the manifest after the sync (a new dict; the input may be left as is) |

The judge records every embedder and store call in order and checks that the final store matches the manifest.

**Constraints**

- up to 40 docs, each up to 3,000 characters
- `0 <= max_delete_fraction <= 1`
- Use `hashlib.sha256`, never Python's `hash()`, which changes between processes.
