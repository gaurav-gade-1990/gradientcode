Your HR assistant retrieves 10–20 chunks per question, but the prompt has room for only `budget` tokens of sources. Older wiki exports duplicate the policy pages, and one long document can crowd out the rest. Write the packer that decides what the model sees.

`pack_context(chunks, budget, max_per_doc, dedupe_threshold)` gets chunks `{"chunk_id", "doc_id", "position", "score", "text"}`, where `position` is the chunk's order inside its document. It returns a dict:

| key | value |
|---|---|
| `context` | the selected blocks joined with `"\n\n"` |
| `tokens` | the total cost of the selected blocks |
| `selected` | the selected chunk ids, in context order |
| `dropped` | one `{"chunk_id", "reason", "duplicate_of"}` per unselected chunk, sorted by `chunk_id` |

**Block and cost.** A chunk is rendered as

```
<source id="{chunk_id}">
{text}
</source>
```

Its **cost** is `gc_runtime.count_tokens(block)`, wrapper included. The `"\n\n"` joins are whitespace and cost nothing.

**Step 1: dedupe.** Visit the chunks by score descending, then `chunk_id` ascending. A chunk's token set is `{t.lower() for t in tokenize(text)}`. Compare it with every chunk kept so far, in the order they were kept. If its Jaccard similarity $|A \cap B| / |A \cup B|$ with one of them is `>= dedupe_threshold`, drop it with reason `"duplicate"` and `duplicate_of` set to the **first** such kept chunk. Otherwise keep it.

**Step 2: select.** Visit the kept chunks by `score / cost` descending, then score descending, then `chunk_id` ascending. For each one:

1. If its doc already has `max_per_doc` selected chunks, drop it with reason `"doc_cap"`.
2. Else if its cost is more than the budget left, drop it with reason `"budget"` and **keep going**, because a later, smaller chunk may still fit.
3. Else select it.

`duplicate_of` is `None` for these two reasons.

**Step 3: order.** Group the selected chunks by doc. Order the docs by their highest selected score descending, then `doc_id` ascending. Within a doc, order the chunks by `position` ascending, so steps and clauses read in their original order.

The judge re-counts the context's tokens and compares the selection, the drop reasons and the exact context string.

**Constraints**

- up to 40 chunks, with non-empty text, unique `chunk_id`s, and unique `position`s within a doc
- `1 <= budget <= 5000`, `1 <= max_per_doc <= 10`, `0 < dedupe_threshold <= 1`
