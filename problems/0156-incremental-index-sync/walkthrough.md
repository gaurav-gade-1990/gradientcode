## 1. What the problem is really asking

Every night a connector hands you tonight's copy of the source documents. Your vector index holds last night's copy. You need to make the index match the source while doing as little work as possible, because embedding costs money and rewriting chunks makes search results flicker.

Under the story this is a **diff between two snapshots, done twice**:

- **Doc level.** Compare a content hash per doc to sort every doc into added, changed, unchanged or deleted.
- **Chunk level.** Inside a changed doc, compare chunk ids. If the ids come from the chunk's *content*, then a paragraph that didn't change keeps its id, and you skip it.

On top of that sits one safety rule, the **mass-delete guard**: if the diff says most of the index vanished overnight, the connector is broken, so you refuse to touch anything.

The judge records every `embed`, `upsert` and `delete` call in order, with the chunk ids. So the grade is the exact sequence of writes, not just the final manifest. It also checks that the store's rows match the manifest you return (`store_matches_manifest`) and that every upserted vector really is the embedding of its text (`bad_vectors`).

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `source_docs` | tonight's `[{"doc_id", "text"}]`, any order | turn it into a `{doc_id: text}` dict |
| `manifest` | last night's `{doc_id: {"content_hash", "chunk_ids"}}` | the "before" snapshot |
| `embedder.embed(texts)` | list of strings → list of vectors, same order | once per doc, only for fresh chunks |
| `store.upsert(items)` | writes `{"chunk_id", "doc_id", "text", "vector"}` rows | once per doc, right after its embed |
| `store.delete(ids)` | removes chunk ids | stale chunks, then deleted docs |
| `max_delete_fraction` | the guard's threshold, default `0.5` | `len(deleted) > fraction * len(manifest)` aborts |

Three details are easy to miss:

- **The chunk id counts earlier copies of the same text.** A security doc that says "Report lost devices within 1 hour." twice gets two ids, ending `:0` and `:1`. Without the counter both copies get the same id, and the second upsert silently overwrites the first.
- **The guard's comparison is strict `>`.** Deleting exactly half of a 10-doc manifest at `0.5` is allowed. Deleting six is not.
- **The guard also fires when the source is empty**, whatever the fraction, as long as the manifest isn't. An empty manifest and an empty source is just a quiet night: status `"ok"`, no calls.

## 3. Trace Example 1 by hand

Last night's manifest holds `hr/pto-policy`, `it/vpn-setup` and `runbooks/payments-api`. Tonight's source has those three, with one paragraph of the PTO policy edited, plus a new `hr/parental-leave`.

**The guard.** Nothing was deleted: `0 > 0.5 * 3` is false. Carry on.

**Doc level, in `doc_id` order:**

| doc | in manifest? | hash matches? | bucket |
|---|---|---|---|
| hr/parental-leave | no | — | added |
| hr/pto-policy | yes | no | changed |
| it/vpn-setup | yes | yes | unchanged |
| runbooks/payments-api | yes | yes | unchanged |

**Chunk level for `hr/pto-policy`.** The old and new texts each split into three paragraphs on `"\n\n"`:

| paragraph | old id | new id |
|---|---|---|
| `PTO Policy` | `hr/pto-policy:c433c1894e34:0` | `hr/pto-policy:c433c1894e34:0` |
| the accrual sentence | `hr/pto-policy:8a632aae9ab8:0` (1.5 days) | `hr/pto-policy:fa08e1911c23:0` (1.75 days) |
| `Unused PTO carries over up to 10 days.` | `hr/pto-policy:258baa6724a2:0` | `hr/pto-policy:258baa6724a2:0` |

`fresh` is the one new id, `fa08e1911c23:0`. `stale` is the one old id that's gone, `8a632aae9ab8:0`.

**The calls the judge records:**

```python
{"op": "embed",  "count": 2, "first": "Parental Leave"}
{"op": "upsert", "chunk_ids": ["hr/parental-leave:5dc3faa93572:0", "hr/parental-leave:bf2f6161dfdb:0"]}
{"op": "embed",  "count": 1, "first": "Full-time employees accrue 1.75 days of "}
{"op": "upsert", "chunk_ids": ["hr/pto-policy:fa08e1911c23:0"]}
{"op": "delete", "chunk_ids": ["hr/pto-policy:8a632aae9ab8:0"]}
```

`embedded_chunks` is 3. The two unchanged docs make no calls at all. Notice that the PTO doc's delete comes *after* its upsert: for a moment the store holds both the old and the new accrual paragraph, which is harmless, rather than neither.

**The trickiest hidden case, "repeated paragraphs".** The old security doc is `Security Baseline`, `R`, `Contractors`, `R`, where `R` is "Report lost devices within 1 hour." The new one renames the title and adds a third `R`:

| paragraph | old id | new id |
|---|---|---|
| title | `c08bfa1e6d12:0` (`Security Baseline`) | `2a2da2ff4264:0` (`Security Baseline v2`) |
| R | `875018f13be3:0` | `875018f13be3:0` |
| Contractors | `7b34b528f6fa:0` | `7b34b528f6fa:0` |
| R | `875018f13be3:1` | `875018f13be3:1` |
| R | — | `875018f13be3:2` |

So you embed 2 chunks (the new title and the third copy of `R`), upsert `['sec/baseline:2a2da2ff4264:0', 'sec/baseline:875018f13be3:2']`, and delete `['sec/baseline:c08bfa1e6d12:0']`. The occurrence counter is what lets the store keep three copies of the same sentence.

## 4. Key idea: content-addressed chunk ids

The obvious id is the position: `doc#0`, `doc#1`, `doc#2`. It works until someone inserts a paragraph at the top. Then every paragraph below shifts down by one, every id changes, and you re-embed the whole doc.

"paragraph inserted at top" shows the difference. The on-call handbook gains a new first paragraph. With content ids, the three old paragraphs keep `3784c1c5515b:0`, `e0fb7b4aba8d:0` and `0c5c4ed802b8:0`, so you embed **1** chunk and delete nothing. With positional ids you embed **4** and delete the 3 old ones. On a real wiki where most nightly edits are small, that's the difference between embedding a few dozen paragraphs and embedding everything.

The 12-hex-digit prefix of sha256 is short enough to read and long enough that two different paragraphs in one doc won't collide in practice. Use `hashlib.sha256`, never `hash()`: Python randomises string hashing per process, so tomorrow's run would see every chunk as new.

## 5. Key idea: guard first, upsert before delete

Two ordering rules carry the safety of this function.

**Guard before any call.** An empty or tiny source list is far more likely to be an expired OAuth token or a broken API than the company deleting its wiki. If you deleted first and checked later, the damage is already done. So the guard is the first thing after you compute `deleted`, and when it trips you make zero calls and return the manifest as it was.

**Upsert, then delete, per doc.** A search query can arrive at any moment during the sync. If you delete the stale chunks first, there's a window where the changed paragraph exists in neither version. Upserting first means a mid-sync query sees a little old and new content, never a hole.

## 6. Plan before you code

```
source = {doc_id: text}
deleted = sorted manifest ids not in source
if manifest and (source empty or len(deleted) > fraction * len(manifest)):
    return aborted report, manifest unchanged, no calls
new_manifest = copy of manifest
for doc_id in sorted(source):
    h = sha256(text)
    hash matches the manifest   -> unchanged, no calls
    else added or changed:
        ids, chunks = chunk the text
        fresh = new ids not in old (chunk order)  -> one embed, one upsert
        stale = old ids not in new (old order)    -> one delete
        new_manifest[doc_id] = {hash, ids}
for doc_id in deleted:
    delete its chunk ids (if any), drop it from new_manifest
return ok report
```

## 7. Build it one piece at a time

**Step 1: hashing and chunk ids.** The counter dict gives each repeated paragraph its occurrence number. Read `n` *before* you increment, so the first copy is `0`:

```python
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
```

The `strip()` matters. "whitespace-only edit" adds a blank paragraph and trailing spaces to the on-call handbook. The doc hash changes, so it's "changed", but after stripping the paragraphs are identical, so all three ids match and there are **no calls**. Skip the strip and the edited paragraph gets a new id.

**Step 2: the guard.**

```python
    source = {d["doc_id"]: d["text"] for d in source_docs}
    deleted = sorted(d for d in manifest if d not in source)
    if manifest and (not source or len(deleted) > max_delete_fraction * len(manifest)):
        return {"status": "aborted", ...}
```

The leading `manifest and` is what makes "empty source and empty manifest" a normal `"ok"` run instead of an abort.

**Step 3: the per-doc diff.** Build sets for membership, but keep the lists for order. `fresh` follows the new chunk order and `stale` follows the old manifest order, which is exactly what the judge compares:

```python
        old = prev["chunk_ids"] if prev else []
        old_set, new_set = set(old), set(ids)
        fresh = [(i, c) for i, c in zip(ids, chunks) if i not in old_set]
        if fresh:
            vectors = embedder.embed([c for _, c in fresh])
            store.upsert([{"chunk_id": i, "doc_id": doc_id, "text": c, "vector": v}
                          for (i, c), v in zip(fresh, vectors)])
            embedded += len(fresh)
        stale = [i for i in old if i not in new_set]
        if stale:
            store.delete(stale)
```

The `if fresh` and `if stale` guards stop empty calls. "paragraph appended" has nothing stale, so its log is one embed and one upsert, with no `delete` entry.

**Step 4: tombstones.** Deleted docs come last, one `delete` each, in `doc_id` order. A doc whose manifest entry has no chunks (a doc that was emptied out on an earlier night) makes no call.

## 8. Full solution

```python
import hashlib  # sha256 is stable across processes, unlike the built-in hash()


def sha(text):  # the content hash used for whole docs and for single chunks
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # hex digest of the UTF-8 bytes


def chunk_ids(doc_id, text):  # split a doc into paragraphs and give each a content-derived id
    chunks = [p.strip() for p in text.split("\n\n") if p.strip()]  # paragraphs, trimmed, blanks dropped
    seen, ids = {}, []  # copies seen so far per paragraph text, and the ids in chunk order
    for c in chunks:  # walk the paragraphs in document order
        n = seen.get(c, 0)  # how many earlier chunks in this doc have identical text
        seen[c] = n + 1  # count this copy for any later duplicate
        ids.append("%s:%s:%d" % (doc_id, sha(c)[:12], n))  # same text, same id; repeats get :1, :2
    return ids, chunks  # ids and texts line up index by index


def sync_index(source_docs, manifest, store, embedder, max_delete_fraction=0.5):  # one nightly sync
    source = {d["doc_id"]: d["text"] for d in source_docs}  # tonight's truth, keyed by id
    deleted = sorted(d for d in manifest if d not in source)  # docs that vanished since last night
    # a broken connector looks like a mass deletion, so refuse before touching anything
    if manifest and (not source or len(deleted) > max_delete_fraction * len(manifest)):
        # aborted: no calls were made, and the manifest goes back unchanged
        return {"status": "aborted", "added": [], "changed": [], "unchanged": [], "deleted": [],
                "embedded_chunks": 0, "manifest": manifest}

    new_manifest = {d: dict(v) for d, v in manifest.items()}  # a new dict, so the input stays as it was
    added, changed, unchanged, embedded = [], [], [], 0  # the report buckets and the embed counter
    for doc_id in sorted(source):  # process docs in doc_id order, as the judge expects
        text = source[doc_id]  # tonight's text for this doc
        h = sha(text)  # its content hash
        prev = manifest.get(doc_id)  # last night's entry, or None for a new doc
        if prev is not None and prev["content_hash"] == h:  # same bytes as last night
            unchanged.append(doc_id)  # record it
            continue  # an unchanged doc costs nothing: no embed, no store call
        (added if prev is None else changed).append(doc_id)  # new doc, or an edited one
        ids, chunks = chunk_ids(doc_id, text)  # tonight's chunk ids and texts
        old = prev["chunk_ids"] if prev else []  # last night's ids; none for an added doc
        old_set, new_set = set(old), set(ids)  # sets for fast membership; the lists keep the order
        fresh = [(i, c) for i, c in zip(ids, chunks) if i not in old_set]  # new chunks, in chunk order
        if fresh:  # only call the embedder when there is something new
            vectors = embedder.embed([c for _, c in fresh])  # one embed call for all fresh texts
            # one upsert, pairing each fresh id and text with its vector
            store.upsert([{"chunk_id": i, "doc_id": doc_id, "text": c, "vector": v} for (i, c), v in zip(fresh, vectors)])
            embedded += len(fresh)  # count texts sent to the embedder for the report
        stale = [i for i in old if i not in new_set]  # ids that disappeared, in their old order
        if stale:  # skip the call when nothing went away
            store.delete(stale)  # delete after upsert, so the doc is never missing from search
        new_manifest[doc_id] = {"content_hash": h, "chunk_ids": ids}  # the doc's new state

    for doc_id in deleted:  # tombstone the vanished docs, in doc_id order
        if manifest[doc_id]["chunk_ids"]:  # a doc with no chunks has nothing to delete
            store.delete(list(manifest[doc_id]["chunk_ids"]))  # one delete per vanished doc
        del new_manifest[doc_id]  # and it leaves the manifest

    # the finished sync: sorted buckets, the embed count and the new manifest
    return {"status": "ok", "added": added, "changed": changed, "unchanged": unchanged, "deleted": deleted,
            "embedded_chunks": embedded, "manifest": new_manifest}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 3 chunks embedded; 2 untouched docs make no calls | doc-level hashes and a one-paragraph chunk diff |
| Example 2 | one `delete` of the 3 payments-api chunks | 1 of 3 deleted is within the 0.5 guard; tombstones |
| Example 3 | `"aborted"`, `calls: []`, manifest unchanged | an empty source trips the guard |
| empty source and empty manifest | `"ok"`, no calls, empty manifest | the guard needs a non-empty manifest |
| first sync from empty | 9 chunks, three embed/upsert pairs | every doc is "added" |
| paragraph inserted at top | 1 chunk embedded, no delete | content ids survive a shift |
| paragraph appended | 1 chunk embedded, no delete | no empty `delete` call |
| whitespace-only edit | "changed", but `calls: []` | `strip()` makes the paragraphs identical |
| repeated paragraphs | 2 embedded; delete `c08bfa1e6d12:0` | the occurrence counter `:0`, `:1`, `:2` |
| repeated paragraphs first sync | 7 embedded, the security doc gets 4 ids | duplicates in a brand-new doc |
| guard trips over fraction | 6 of 10 deleted at 0.5: `"aborted"` | `>` against the fraction |
| guard boundary is inclusive | 5 of 10 deleted at 0.5: `"ok"`, five deletes | 5 is not greater than 5 |
| mixed night | 6 embedded, 1 deleted at fraction 0.25 | every bucket at once; 1 of 4 is not over 1.0 |
| doc emptied out | VPN "changed", its 3 chunks deleted, `chunk_ids: []` | a doc with no paragraphs left |

## 10. Complexity

Hashing and chunking are linear in the text: O(T) for T characters across all docs. The per-doc diff is O(c) with sets, for c chunks. Writes are at most two embed/upsert calls and one delete per changed doc, plus one delete per deleted doc. With 40 docs that's instant.

What matters at scale is the number of texts sent to the embedder, because that's the bill and the rate limit. Content ids keep it proportional to what actually changed. In production you'd also batch fresh chunks across docs up to the provider's batch size, retry with backoff (problem 124), and rely on the upsert being idempotent by chunk id so a crashed sync can simply rerun.

## 11. If you got Wrong Answer

Compare the `calls` lists first. The first call that differs points at the bug.

- **Every chunk ID in the output looks like `eng/oncall:0`, `eng/oncall:1`.** Positional ids. They fail even "first sync from empty", because the id format is part of the answer, and "paragraph inserted at top" embeds 4 chunks instead of 1.
- **Ids have no `:0` suffix, and `store_matches_manifest` is `False` in "repeated paragraphs first sync".** You left out the occurrence counter. The manifest lists `875018f13be3` twice but the store keeps one row.
- **Ids end in `:1` where `:0` is expected.** You incremented the counter before reading it.
- **A changed doc shows `delete` of every old chunk, then a full embed.** You deleted and re-indexed the whole doc. Example 1 embeds 5 chunks instead of 3.
- **The `delete` comes before the `upsert` for one doc.** Swap them. Example 1, "repeated paragraphs" and "mixed night" catch this.
- **Example 3 or "guard trips over fraction" shows calls.** There's no guard, or it runs after the writes.
- **"guard boundary is inclusive" or "mixed night" comes back `"aborted"`.** You used `>=`. The rule is strictly greater than.
- **"whitespace-only edit" embeds a chunk.** You didn't `strip()` each paragraph.

## 12. Follow-ups an interviewer might ask

- *The source has a change feed. Do you still need hashes?* Use the feed (Google Drive changes, Confluence `lastmodified`, SharePoint delta queries, Notion `last_edited_time`) to pick which docs to fetch, but keep the hash as the safety net. "Modified" timestamps change on metadata-only edits, and the hash tells you nothing really changed.
- *You switch embedding models or change the chunker. Now what?* Every id or vector is invalid, so diffing in place is wrong. Build a new versioned index (`index_v7`) alongside the old one and switch an alias when it's done. Problem 153 (recursive-chunker) is the chunker side of this.
- *The guard tripped at 2 a.m. What happens next?* Alert a human, keep serving the old index, and retry the connector. A legitimate mass deletion can be approved by rerunning with a higher `max_delete_fraction`.
- *What if the sync crashes halfway?* Because chunk ids are content-derived and upserts are idempotent, rerunning recomputes the same diff and writes the same rows. Save the manifest only after the writes succeed, ideally in the same transaction as an outbox (problem 172, transactional-outbox).
- *Which libraries do this for you?* LlamaIndex's `IngestionPipeline` with a docstore (`DocstoreStrategy.UPSERTS_AND_DELETE`) and LangChain's `index()` with a `RecordManager` (`cleanup="incremental"`) implement this same hash-and-diff loop.
