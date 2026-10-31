## Approach

Treat the index as a cache of the source and the manifest as the cache's table of contents. Each night is a diff:

1. **Doc level.** Comparing content hashes sorts every doc into added, changed, unchanged or deleted. Unchanged docs, usually 95%+ of a wiki, cost nothing.
2. **Chunk level.** Inside a changed doc, **content-addressed chunk ids** make the diff almost free: a paragraph that didn't change keeps its id, so it is neither re-embedded nor rewritten.

```python
def chunk_ids(doc_id, text):
    chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
    seen, ids = {}, []
    for c in chunks:
        n = seen.get(c, 0); seen[c] = n + 1
        ids.append("%s:%s:%d" % (doc_id, sha(c)[:12], n))
    return ids, chunks
```

The occurrence suffix `n` handles boilerplate that repeats inside one doc ("Report lost devices within 1 hour."). Without it, two chunks share an id and one silently overwrites the other.

3. **Write order.** Upsert the fresh chunks first, then delete the stale ones. A query that lands mid-sync then sees a little old and new content, never an empty doc.
4. **Guard.** Before writing anything, refuse a sync that would delete most of the index. An empty or tiny source list is far more likely to be an expired OAuth token than a real mass deletion.

## Common mistakes

- **Positional ids (`doc#0`, `doc#1`).** Insert one paragraph at the top and every id shifts, so you re-embed and rewrite the whole doc, and cached citations point at the wrong text.
- **Delete, then re-insert.** It is simpler but re-embeds everything, and the doc disappears from search between the two calls.
- **No mass-delete guard.** A connector outage that returns `[]` tombstones the whole knowledge base at 2 a.m., and the assistant answers "I don't know" until someone re-ingests.
- **Duplicate paragraphs sharing one id.** The manifest lists the id twice, the store holds it once, and the next diff gets confused.
- **`hash()` instead of `sha256`.** Python randomizes string hashing per process, so every run looks like a full change.

## Production notes

- LlamaIndex's `IngestionPipeline` with a docstore (`DocstoreStrategy.UPSERTS_AND_DELETE`) and LangChain's `index()` with a `RecordManager` (`cleanup="incremental"` or `"full"`) implement exactly this hash-and-diff loop.
- Prefer the source's own change feed when it has one: Google Drive changes, the Confluence CQL `lastmodified` query, SharePoint delta queries, or Notion `last_edited_time`. Keep content hashes as the safety net, because "modified" timestamps change on metadata-only edits.
- Embedding calls are the cost and the rate limit. Batch fresh chunks across docs up to the provider's batch limit, retry with backoff (problem 124), and make upserts idempotent by chunk id so a crashed sync can simply rerun.
- When the chunker or embedding model changes, every id or vector is invalid. Version the index (`index_v7`), build it alongside the old one, and switch an alias, rather than diffing in place. Pairs with the recursive chunker (problem 153).
