## 1. What the problem is really asking

When you stream a reply from the Anthropic Messages API, you don't get a finished message. You get a list of small events: a block opens, some text arrives, a few fragments of JSON arrive, the block closes, and so on. Tool-call arguments come as `partial_json` fragments split wherever the model's tokens happened to fall, often in the middle of a key or a string. Your backend has to rebuild the message, and decide which tool calls are safe to run.

Strip the story and this is a **per-key buffer with a close event**. Keep one buffer per block `index`, append every delta to the buffer its `index` names, and interpret a tool block's buffer exactly once, at its `content_block_stop`. Anything that never closed is not trusted.

The judge calls `assemble(events)` and compares the returned dict exactly: the `content` list, the runnable `tool_calls`, the `errors`, `stop_reason` and `usage`. The `tool_calls` list is the one that matters in production, because those are the calls your backend will actually execute.

## 2. Understand the inputs before writing anything

| event `type` | carries | how you use it |
|---|---|---|
| `message_start` | `message.usage.input_tokens` | store `input_tokens` |
| `content_block_start` | `index`, `content_block` (`text`, or `tool_use` with `id`, `name`, a placeholder `input: {}`) | open a new block at that index, empty buffer |
| `content_block_delta` | `index`, `delta` (`text_delta` with `text`, or `input_json_delta` with `partial_json`) | append to block `index`'s buffer |
| `content_block_stop` | `index` | mark closed; for a tool block, parse the joined buffer now |
| `message_delta` | `delta.stop_reason`, maybe `usage.output_tokens` | store whichever fields are present |
| `message_stop` | nothing | stop reading: everything after it is ignored |
| `ping` | nothing | ignore |

Three details are easy to miss:

- **Deltas for different blocks interleave.** When the model makes parallel tool calls, fragments of block 0 and block 1 alternate. "The block that started last" is the wrong target. The delta's own `index` is the only right one.
- **The `input: {}` in `content_block_start` is a placeholder.** It is not the arguments, and it is not the fallback for a broken call.
- **Empty is valid, malformed is not.** A tool with no parameters may stream no deltas, or `partial_json: ""`. That is `input = {}`. But `json.loads("")` raises, so you need an explicit check for an empty or whitespace-only buffer *before* parsing.

## 3. Trace the examples by hand

**Example 2** is the one that teaches the most: two tool calls whose fragments interleave. Here are the two buffers after each event:

| # | event | buffer 0 (`lookup_order`) | buffer 1 (`get_shipping_status`) |
|---|---|---|---|
| 1 | `message_start` (input 1290) | — | — |
| 2 | `ping` | — | — |
| 3 | start 0 | `''` | — |
| 4 | start 1 | `''` | `''` |
| 5 | delta 0 | `{"order_id": ` | `''` |
| 6 | delta 1 | `{"order_id": ` | `{"tracking` |
| 7 | delta 0 | `{"order_id": "A-1182"` | `{"tracking` |
| 8 | delta 1 | `{"order_id": "A-1182"` | `{"tracking_number": "1Z999AA1"` |
| 9 | delta 1 | `{"order_id": "A-1182"` | `{"tracking_number": "1Z999AA1", "carrier": "UPS"}` |
| 10 | **stop 1** | (still open) | parsed: `{"tracking_number": "1Z999AA1", "carrier": "UPS"}` |
| 11 | delta 0 | `{"order_id": "A-1182", "include_items": true}` | closed |
| 12 | **stop 0** | parsed: `{"order_id": "A-1182", "include_items": True}` | closed |
| 13 | `message_delta` | `stop_reason = "tool_use"`, `output_tokens = 64` | |
| 14 | `message_stop` | end | |

Look at row 6: `{"tracking` is not valid JSON, and neither is anything in buffer 0 until row 11. You can only parse at the stop event. Block 1 stops first, but the output lists `toolu_ord` (index 0) first, because `content` and `tool_calls` are sorted by index, not by finish order.

**Example 3** shows the two edge cases of parsing:

- Block 0 (`list_open_tickets`) starts and stops with no deltas. The buffer is `""`, so `input = {}`, and it is a valid tool call.
- Block 1 (`issue_refund`) joins to `{"order_id": "A-1182", "amount_cents": 4999`, missing its closing brace. `json.loads` raises, so the block gets `invalid_json`, `input: None`, and it is **not** in `tool_calls`.

Output: `tool_calls` has only `toolu_tix`, and `errors` is `[{"index": 1, "id": "toolu_ref", "reason": "invalid_json"}]`.

**The tricky hidden case, "cut off before stop, valid-looking buffer":** block 0 (`get_weather`, Denver) streams and stops normally. Block 1 (`get_weather`) streams `{"city": "Boise"}`, then a `message_delta` arrives, and the list ends. There is no `content_block_stop` for block 1. Its buffer *would* parse, but the expected output is `input: None` with reason `unterminated`. You can't know the model was finished: the next fragment might have been `, "unit": "celsius"}`. Only block 0 runs.

## 4. Key idea: parse once, at the stop event

A fragment is not a unit of meaning. The API splits `partial_json` at token boundaries, so `"Aus` and `tin"` arrive as separate fragments in Example 1. Parsing each fragment fails on nearly all of them, and code that skips the failures quietly runs the tool with missing or empty arguments. Joining the fragments and parsing once at `content_block_stop` is the only correct place:

- before the stop, the JSON may be incomplete even if it happens to parse;
- after the stop, the API promises no more fragments for that block.

The same reasoning gives you the `unterminated` rule. A block whose stop never came (the list ended, or `message_stop` arrived first) has a buffer you must not parse at all.

## 5. Key idea: a broken call is an error, never `{}`

When a parse fails, it is tempting to fall back to `{}` or to the placeholder `input: {}` from the start event. That turns a parse error into a real action: `issue_refund()` with default arguments, or a search for nothing. The problem makes the safe behaviour explicit: an error block has `input: None`, is listed in `errors`, and never appears in `tool_calls`. In a real backend you'd send that error back to the model so it can re-emit the call.

The three reasons, in the order you check them:

| buffer at stop | outcome |
|---|---|
| `""` or whitespace only | valid, `input = {}` |
| `json.loads` succeeds with a dict | valid, `input` = the dict |
| `json.loads` succeeds with a list, string, number or `null` | `not_object` |
| `json.loads` raises | `invalid_json` |
| no stop event at all | `unterminated` (decided after the loop) |

## 6. Plan before you code

```
blocks = {}; usage = {input 0, output 0}; stop_reason = None
for each event:
    message_stop        -> break
    message_start       -> usage.input_tokens
    content_block_start -> blocks[index] = new block, empty buffer, not stopped
    content_block_delta -> blocks[index].buffer += text or partial_json
    content_block_stop  -> mark stopped; tool block: parse buffer (table above)
    message_delta       -> stop_reason / output_tokens if present
    anything else       -> ignore (ping)
for index in sorted(blocks):
    text block -> content
    tool block not stopped -> error "unterminated"
    tool block -> content; then errors or tool_calls
```

## 7. Build it one piece at a time

**Step 1: the loop, `message_stop`, and the message-level fields.** Use `.get` with defaults, because "no message_start or delta" sends neither event and the usage must still be `0`.

```python
    blocks = {}
    usage = {"input_tokens": 0, "output_tokens": 0}
    stop_reason = None
    for ev in events:
        kind = ev.get("type")
        if kind == "message_stop":
            break
        if kind == "message_start":
            usage["input_tokens"] = ev["message"].get("usage", {}).get("input_tokens", 0)
```

The `break` is what makes "events after message_stop ignored" work: in that case a `stop(0)` arrives *after* `message_stop`, and honouring it would complete a call the stream already ended.

**Step 2: open blocks and route deltas by index.**

```python
        elif kind == "content_block_start":
            cb = ev["content_block"]
            blocks[ev["index"]] = {"type": cb["type"], "id": cb.get("id"), "name": cb.get("name"),
                                   "buf": [], "stopped": False, "input": None, "error": None}
        elif kind == "content_block_delta":
            d = ev["delta"]
            b = blocks[ev["index"]]
            b["buf"].append(d["text"] if d["type"] == "text_delta" else d["partial_json"])
```

The buffer is a list of fragments joined once later, which avoids repeated string copies. Notice the placeholder `cb["input"]` is never read.

**Step 3: parse at the stop event.**

```python
        elif kind == "content_block_stop":
            b = blocks[ev["index"]]
            b["stopped"] = True
            if b["type"] == "tool_use":
                raw = "".join(b["buf"])
                if not raw.strip():
                    b["input"] = {}
                else:
                    try:
                        val = json.loads(raw)
                    except ValueError:
                        b["error"] = "invalid_json"
                    else:
                        if isinstance(val, dict):
                            b["input"] = val
                        else:
                            b["error"] = "not_object"
```

`json.JSONDecodeError` is a subclass of `ValueError`, so either name works. The `try/except/else` keeps the success path out of the `try`, so a bug in it can't be mistaken for bad JSON. In "not an object", `null` parses to `None`, which is a valid JSON value but not a dict, so it is `not_object`, not `invalid_json`.

**Step 4: `message_delta` updates only what it carries.** In "multiple message_delta, missing usage" the second delta has a `stop_reason` but no `usage`, so `stop_reason` becomes `"end_turn"` while `output_tokens` stays `3`.

```python
        elif kind == "message_delta":
            if "stop_reason" in ev.get("delta", {}):
                stop_reason = ev["delta"]["stop_reason"]
            if "output_tokens" in ev.get("usage", {}):
                usage["output_tokens"] = ev["usage"]["output_tokens"]
```

**Step 5: build the output in index order.** "sparse out-of-order indexes" uses indexes 5, 2 and 9, started in that order, so you must sort, and you can't assume `0..n-1`.

```python
    content, tool_calls, errors = [], [], []
    for idx in sorted(blocks):
        b = blocks[idx]
        if b["type"] == "text":
            content.append({"type": "text", "text": "".join(b["buf"])})
            continue
        if not b["stopped"]:
            b["error"] = "unterminated"
        content.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})
        if b["error"]:
            errors.append({"index": idx, "id": b["id"], "reason": b["error"]})
        else:
            tool_calls.append({"id": b["id"], "name": b["name"], "input": b["input"]})
```

Text blocks skip the stopped check entirely: "unterminated text block keeps text" expects `"Partial answer"` with no error.

## 8. Full solution

```python
import json  # strict JSON parsing for the joined tool arguments


def assemble(events):  # rebuild one streamed assistant message from its events
    blocks = {}  # index -> {"type", "id", "name", "buf": [], "stopped": bool, "input", "error"}
    usage = {"input_tokens": 0, "output_tokens": 0}  # 0 for anything the stream never reports
    stop_reason = None  # stays None if no message_delta arrives
    for ev in events:  # events are already parsed from SSE, in arrival order
        kind = ev.get("type")  # which kind of event this is
        if kind == "message_stop":  # the stream is over
            break  # anything after it, even a block stop, must be ignored
        if kind == "message_start":  # the first event carries input usage
            usage["input_tokens"] = ev["message"].get("usage", {}).get("input_tokens", 0)  # tolerate a missing usage
        elif kind == "content_block_start":  # a new text or tool_use block opens
            cb = ev["content_block"]  # its type, and id and name for tools; the input placeholder is ignored
            # an empty buffer per block, not yet stopped, with no parsed input or error
            blocks[ev["index"]] = {"type": cb["type"], "id": cb.get("id"), "name": cb.get("name"),
                                   "buf": [], "stopped": False, "input": None, "error": None}
        elif kind == "content_block_delta":  # one fragment for some block
            d = ev["delta"]  # either a text_delta or an input_json_delta
            b = blocks[ev["index"]]  # route by the delta's own index, since blocks interleave
            b["buf"].append(d["text"] if d["type"] == "text_delta" else d["partial_json"])  # keep fragments, join later
        elif kind == "content_block_stop":  # the API promises no more fragments for this block
            b = blocks[ev["index"]]  # the block that just closed
            b["stopped"] = True  # remember it closed, so it isn't unterminated
            if b["type"] == "tool_use":  # only tool blocks need parsing
                raw = "".join(b["buf"])  # the full argument text, parsed exactly once
                if not raw.strip():  # no arguments streamed, or only whitespace
                    b["input"] = {}  # a tool with no parameters: valid, empty input
                else:  # there is real text to parse
                    try:  # strict parse, no repair
                        val = json.loads(raw)  # may raise on malformed JSON
                    except ValueError:  # JSONDecodeError is a ValueError
                        b["error"] = "invalid_json"  # broken JSON must never run
                    else:  # it parsed; now check the shape
                        if isinstance(val, dict):  # tool input must be a JSON object
                            b["input"] = val  # the real arguments
                        else:  # a list, string, number or null
                            b["error"] = "not_object"  # valid JSON but not usable as arguments
        elif kind == "message_delta":  # message-level updates near the end
            if "stop_reason" in ev.get("delta", {}):  # only overwrite fields that are present
                stop_reason = ev["delta"]["stop_reason"]  # a later delta wins
            if "output_tokens" in ev.get("usage", {}):  # usage is optional on a message_delta
                usage["output_tokens"] = ev["usage"]["output_tokens"]  # keep the earlier value otherwise

    content, tool_calls, errors = [], [], []  # the three output lists
    for idx in sorted(blocks):  # output follows index order, not arrival or finish order
        b = blocks[idx]  # one block
        if b["type"] == "text":  # text keeps whatever arrived, stopped or not
            content.append({"type": "text", "text": "".join(b["buf"])})  # the concatenated text
            continue  # text blocks never produce tool calls or errors
        if not b["stopped"]:  # the stream ended before this tool block closed
            b["error"] = "unterminated"  # its buffer is never parsed, even if it looks complete
        content.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})  # None on error
        if b["error"]:  # a failed tool block
            errors.append({"index": idx, "id": b["id"], "reason": b["error"]})  # report it, don't run it
        else:  # a valid tool block
            tool_calls.append({"id": b["id"], "name": b["name"], "input": b["input"]})  # safe to execute
    # the assembled message
    return {"content": content, "tool_calls": tool_calls, "errors": errors,
            "stop_reason": stop_reason, "usage": usage}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | text `"Let me check the forecast."`, `get_weather` with `{"city": "Austin", "unit": "fahrenheit"}` | fragments split mid-string only parse once joined |
| Example 2 | both calls valid, `toolu_ord` first | routing by `index` with interleaved deltas; sort by index, not stop order; ping ignored |
| Example 3 | `list_open_tickets` with `{}`, refund `invalid_json` | empty buffer is valid; a malformed call doesn't run |
| empty stream | empty lists, `stop_reason: None`, zero usage | defaults when nothing arrives |
| whitespace only args | `input: {}`, valid | `raw.strip()` before `json.loads` |
| not an object | three `not_object` errors | a list, `null` and a string parse but aren't dicts |
| stream cut off mid tool | `search_kb` `unterminated`, `stop_reason: None` | a tool block without a stop is an error; the text block is kept |
| cut off before stop, valid-looking buffer | Denver runs, Boise `unterminated` | never parse an unstopped buffer, even if it would succeed |
| events after message_stop ignored | `send_email` `unterminated`, `output_tokens: 18` | the `break` on `message_stop` |
| unterminated text block keeps text | `"Partial answer"`, no errors | text blocks never error |
| sparse out-of-order indexes | text (index 2), then 5, then 9 | `sorted(blocks)` with gaps |
| multiple message_delta, missing usage | `stop_reason: "end_turn"`, `output_tokens: 3` | update only the fields present |
| no message_start or delta | `get_weather` Oslo runs, usage `0`, `stop_reason: None` | `.get` defaults |
| nested args split mid-string | `create_ticket` and `notify_slack` run, refund `invalid_json` | nested JSON, a trailing comma is invalid, braces inside a string value |
| interleaved with a broken sibling | `toolu_a` and `toolu_c` valid; `toolu_b` (`{"order_id": "C-3"`, no closing brace) is `invalid_json` at index 1 | one broken block doesn't affect its interleaved siblings; an extra empty fragment; a tool with no deltas |

## 10. Complexity

Each event is O(1) work plus appending its fragment. Joining and parsing a block's buffer is linear in its length, so the whole call is O(E + L) for `E` events and `L` total characters, plus O(B log B) to sort `B` blocks. Memory is the buffered text, O(L).

In production you would run this incrementally rather than over a finished list: keep the same `blocks` dict as SSE events arrive, and dispatch each tool call the moment its `content_block_stop` lands. That's the real latency win of streaming, since a long text block or a second tool call no longer delays the first tool. The same "one buffer per index" rule applies to OpenAI's `tool_calls[i].function.arguments` fragments.

## 11. If you got Wrong Answer

- **Example 1's `get_weather` has `input: {}`.** You're parsing each fragment and dropping the ones that fail. Join first, parse at stop.
- **Example 2 has `lookup_order` with `{}` and `get_shipping_status` as `invalid_json`.** You append deltas to the block that started last, so every fragment landed in block 1. Use `ev["index"]`.
- **Example 3's `list_open_tickets` is `invalid_json`.** `json.loads("")` raises. Check for an empty or whitespace-only buffer first.
- **The refund in Example 3 appears in `tool_calls` with `{}`.** You fall back to empty arguments on a parse error. It must be an error with `input: None`.
- **"cut off before stop" runs the Boise call.** You parse unstopped buffers at the end. A missing stop is `unterminated`, no parse.
- **"events after message_stop ignored" shows `send_email` as valid, or `output_tokens: 99`.** You kept reading after `message_stop`. `break`.
- **"sparse out-of-order indexes" lists index 5 first.** You iterate in insertion order. Sort the indexes.

## 12. Follow-ups an interviewer might ask

- *How would you show the arguments live in the UI while they stream?* Use a tolerant partial-JSON parser for display only, and keep executing from the strict parse at stop. Display can be wrong for a moment; execution can't.
- *What do you do with a block in `errors`?* Send it back to the model as a `tool_result` with `is_error: true` ("your arguments were not valid JSON") so it re-emits the call, and validate good inputs against the tool's schema before running them (problem 113, tool-args-schema-validation).
- *Where do these event dicts come from?* An SSE parser that splits the byte stream into `event:` / `data:` frames and decodes each `data` as JSON (problem 169, sse-stream-parser).
- *Can you start the tool before the message finishes?* Yes. The moment a tool block's stop arrives, its input is final. Start it then, and run parallel calls concurrently, collecting results in index order (problem 103, parallel-tool-dag).
- *What if the model emits free-text JSON rather than a tool call?* That is a different repair problem with re-asking on failure (problem 116, structured-output-repair).
