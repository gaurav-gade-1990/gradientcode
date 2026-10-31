## Approach

An SSE parser is a two-level state machine: characters become lines, and lines become events. The only state you need between chunks is the unfinished line, a flag that says the last character was a `\r`, and the event being built.

```python
for ch in chunk:
    if self._skip_lf:                 # a CR ended the last line
        self._skip_lf = False
        if ch == "\n":
            continue                  # ...so this LF is part of that CRLF
    if ch in "\r\n":
        self._skip_lf = ch == "\r"
        event = self._process("".join(self._line))
        self._line = []
    else:
        self._line.append(ch)
```

A CR ends its line right away, so an event is emitted as soon as its blank line arrives, not one chunk later. `_process` reads the field, strips exactly one leading space from the value, and on a blank line joins the data lines with `\n`. The event type resets after each dispatch, and `last_event_id` does not. A dispatched `[DONE]` sets `done` and stops the loop.

## Common mistakes

- **Parsing each chunk on its own.** `chunk.split("\n")` works in a demo on localhost, where each event arrives in one read. Behind a proxy or on a phone network, a JSON payload splits across reads and you emit half an event or drop it.
- **CRLF split across chunks.** Normalizing `\r\n` with `chunk.replace` misses a pair that straddles two chunks. The stray `\n` reads as a blank line and dispatches the event early, so one multi-line message arrives as two.
- **`value.strip()`.** The spec removes one leading space. Stripping all whitespace corrupts indented code blocks and whitespace-only tokens, which is exactly what a model streams.
- **Keeping only the last `data:` line.** Multi-line data is legal and common. Assigning instead of appending loses all but the last line.
- **Forwarding `[DONE]`.** OpenAI-style streams end with `data: [DONE]`. A client that hands it to `JSON.parse` throws on the last message of every response.
- **Resetting `id` per event.** The id is sticky. If you clear it, a reconnect sends no `Last-Event-ID` and the server replays the whole response.

## Production notes

- The rules here follow the WHATWG EventSource spec, which `EventSource` in the browser implements. Most LLM SDKs and backends can't use `EventSource` because it only does GET with no body or headers, so they ship their own parser: the Anthropic and OpenAI SDKs, `eventsource-parser` in JavaScript, and `httpx-sse` in Python. Each of them has had a bug report about chunk boundaries.
- Decode bytes with an incremental UTF-8 decoder before this parser. A multibyte character (emoji, CJK, an accented name) can split across TCP reads just like a line can.
- Anthropic streams use named events (`message_start`, `content_block_delta`, `message_stop`, plus `ping` and `error`), while OpenAI uses unnamed `data:` lines and the `[DONE]` sentinel. Handle `event: error` mid-stream: an HTTP 200 does not mean the response succeeded.
- Proxies buffer by default. Send `Cache-Control: no-cache` and, for nginx, `X-Accel-Buffering: no`, and emit `: ping` comments every 15 s or so to keep idle connections from being closed.
- Pair with **websocket-reconnect-resume** (179), which uses `last_event_id` to resume without gaps, and **streaming-tool-call-assembly** (115), which consumes these events.
