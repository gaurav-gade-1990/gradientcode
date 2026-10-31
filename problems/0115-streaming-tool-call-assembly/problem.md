Your chat backend streams model replies to the browser and runs tool calls as soon as the model finishes them. The events follow the **Anthropic Messages streaming format** (`message_start`, `content_block_start`, `content_block_delta` with `text_delta` or `input_json_delta`, `content_block_stop`, `message_delta`, `message_stop`, `ping`). Write the assembler that turns the event list into the final message.

`assemble(events)` takes a list of event dicts, already parsed from SSE, and returns the assembled message.

| event `type` | fields | what to do |
|---|---|---|
| `message_start` | `message.usage.input_tokens` | record `input_tokens` |
| `content_block_start` | `index`, `content_block` = `{"type": "text", "text": ""}` or `{"type": "tool_use", "id", "name", "input": {}}` | open block `index`. The `input: {}` placeholder carries no arguments; ignore it. |
| `content_block_delta` | `index`, `delta` = `{"type": "text_delta", "text"}` or `{"type": "input_json_delta", "partial_json"}` | append the fragment to block `index`'s buffer |
| `content_block_stop` | `index` | close block `index`. For a `tool_use` block, parse its buffer now. |
| `message_delta` | `delta.stop_reason`, optional `usage.output_tokens` | record them; a later `message_delta` overwrites each field it carries, and a field it leaves out keeps its earlier value |
| `message_stop` | none | the stream is over: ignore every event after it |
| `ping` | none | ignore |

Deltas for different blocks can **interleave**, so route each delta by its `index`.

Parsing a `tool_use` block at its stop event:

| concatenated `partial_json` | result |
|---|---|
| empty or only whitespace | `input = {}`, valid |
| parses (with `json.loads`) to a dict | `input` = that dict, valid |
| parses to anything else (list, string, number, null) | error `"not_object"` |
| fails to parse | error `"invalid_json"` |

A `tool_use` block that has no `content_block_stop` before the stream ends (the end of the list, or `message_stop`) gets error `"unterminated"`, and its buffer is **not** parsed. A block with an error has `input: None` and is never returned as a tool call. Text blocks never produce errors: they keep whatever text arrived, stopped or not.

Return a dict:

- `"content"`: one entry per opened block, sorted by `index`. A text block is `{"type": "text", "text": <concatenated text>}`. A tool block is `{"type": "tool_use", "id", "name", "input"}`.
- `"tool_calls"`: `[{"id", "name", "input"}]` for the valid tool blocks only, sorted by `index`.
- `"errors"`: `[{"index", "id", "reason"}]` for the failed tool blocks, sorted by `index`.
- `"stop_reason"`: the last recorded stop reason, or `None` if no `message_delta` arrived.
- `"usage"`: `{"input_tokens", "output_tokens"}`, with `0` for anything not reported.

**Constraints**

- `0 <= len(events) <= 200`
- Block indexes are distinct non-negative integers. Every delta and stop refers to a block that has already started, and a delta's type matches its block's type.
- Indexes may arrive out of order or with gaps, so sort them; don't assume they are `0..n-1`.
- Use `json.loads` for parsing. Don't repair malformed JSON.
