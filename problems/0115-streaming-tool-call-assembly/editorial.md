## Approach

A streamed message is a set of **independent blocks**, each with its own buffer, plus message-level metadata. Keep a dict from block index to buffer, append every delta to the buffer its `index` names, and only interpret a tool block's JSON once its `content_block_stop` arrives.

```python
blocks = {}
for ev in events:
    if ev["type"] == "message_stop":
        break
    if ev["type"] == "content_block_start":
        blocks[ev["index"]] = new_block(ev["content_block"])
    elif ev["type"] == "content_block_delta":
        d = ev["delta"]
        blocks[ev["index"]]["buf"].append(d.get("text", d.get("partial_json")))
    elif ev["type"] == "content_block_stop":
        b = blocks[ev["index"]]; b["stopped"] = True
        if b["type"] == "tool_use":
            raw = "".join(b["buf"])
            # "" or whitespace -> {}; json.loads -> dict or not_object; ValueError -> invalid_json
```

After the loop, any `tool_use` block that never stopped is `unterminated`. Then walk the blocks in sorted index order to build `content`, `tool_calls` and `errors`.

The fragment boundaries are arbitrary. The API splits `partial_json` wherever the model's tokens fall, often in the middle of a key or a string, so a fragment is almost never valid JSON on its own. Only the concatenation is meaningful, and only once the block is closed.

## Common mistakes

- **Parsing each fragment.** `json.loads('{"city": "Aus')` fails, so the code drops it and the tool runs with missing arguments.
- **Routing by arrival.** Appending a delta to "the current block" works until the model emits parallel tool calls whose deltas interleave. Then two tools get each other's arguments spliced together.
- **Running a malformed call with `{}`.** Falling back to empty arguments turns a parse error into a real side effect: `issue_refund()` with defaults, or a search for nothing.
- **Treating empty input as an error.** A tool with no parameters streams no `input_json_delta`, or one with `partial_json: ""`. `json.loads("")` raises, but the right input is `{}`.
- **Running a cut-off block.** If the connection drops before `content_block_stop`, the buffer may still parse, as in `{"city": "Boise"}`, but you can't know the model was done. Never execute it.

## Production notes

- The Anthropic SDKs do exactly this in their `MessageStream` helpers: they accumulate `partial_json` per block and expose `input` once the block stops. OpenAI's Chat Completions streams `tool_calls[i].function.arguments` fragments keyed by `index`, and the same routing rule applies.
- For a live UI you can show partial arguments with a tolerant partial-JSON parser, but you should only **execute** the tool from the strict parse at stop.
- Pass a malformed call back to the model as a `tool_result` with `is_error: true` so it can re-emit the call, rather than silently dropping it. Validate the parsed input against the tool's `input_schema` before running it (problem 113).
- Pair with **SSE parsing** (problem 169), which produces these event dicts from raw bytes, and **structured output repair** (problem 116) for free-text JSON.
