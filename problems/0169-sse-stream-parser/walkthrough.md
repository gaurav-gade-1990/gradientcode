## 1. What the problem is really asking

Strip the chat-UI story and this is a **two-level state machine that survives being cut anywhere**:

> characters → lines (split on `\r\n`, `\n` or `\r`) → fields → events (dispatched on a blank line)

The catch is the word *incremental*. The network decides where chunks end, not you. A chunk can stop in the middle of a field name, in the middle of a JSON payload, or between the `\r` and the `\n` of one line ending. So the parser can't look at a chunk as a whole. It has to remember, between `feed` calls, the unfinished line, whether the last character was a `\r`, and the event it is building.

The judge feeds the chunks one at a time and records **which `feed` call returned which events**, as `events_per_chunk`, plus the final `last_event_id`, `retry` and `done`. Returning the right events one call too late is a Wrong Answer, so timing is graded as well as content.

## 2. Understand the inputs before writing anything

| piece | what it is | how you use it |
|---|---|---|
| `SSEParser()` | built once per stream | holds state across `feed` calls |
| `feed(chunk)` | the next `str` off the socket, possibly `""` | returns the list of events this chunk completed |
| event dict | `{"event", "data", "id"}` | exactly these three keys |
| `last_event_id` | sticky id, starts `""` | set by `id:` lines, never cleared on dispatch |
| `retry` | reconnect delay in ms, starts `None` | set only by an all-digits value |
| `done` | starts `False` | set by a dispatched `[DONE]`; after that, ignore everything |

The judge's driver is short:

```python
for chunk in chunks:
    events = parser.feed(chunk)
    per_chunk.append([{"event": e["event"], "data": e["data"], "id": e["id"]} for e in events])
```

Three details are easy to miss:

- **A `\r` ends a line immediately.** You don't wait to see whether a `\n` follows. You emit, then remember to swallow a `\n` if it is the next character, even in the next chunk.
- **Only one leading space is stripped.** `data:  two spaces` has value `" two spaces"`. `data:   three spaces` keeps two.
- **The field is the text before the first colon.** `data: url: https://...` has value `url: https://...`. A line with no colon at all, like `id` or `data`, is a field with value `""`.

## 3. Trace Example 1 by hand

Chunks: `'data: {"delta":"Hel'`, `'lo"}\n\ndata: {"delta":"!"}\n'`, `'\ndata: [DONE]\n\n'`.

| after feed | returned | unfinished line | data lines | `done` |
|---|---|---|---|---|
| 1 | `[]` | `data: {"delta":"Hel` | `[]` | False |
| 2 | `[{"event": "message", "data": '{"delta":"Hello"}', "id": ""}]` | `""` | `['{"delta":"!"}']` | False |
| 3 | `[{"event": "message", "data": '{"delta":"!"}', "id": ""}]` | `""` | `[]` | True |

Chunk 1 has no line ending at all, so everything waits in the buffer. Chunk 2 finishes that line (`data: {"delta":"Hello"}`), then the blank line dispatches it. It then reads `data: {"delta":"!"}` and its `\n`, but the blank line for that event isn't there yet. The second event comes out of chunk 3, whose first character is the blank line. Then `data: [DONE]` and its blank line dispatch the sentinel, which sets `done` and is not emitted.

**The trickiest hidden case is "CRLF split across chunks":** `"data: first half\r"` then `"\ndata: second half\r\n\r\n"`.

| step | what the parser sees | state after |
|---|---|---|
| chunk 1, `\r` | ends the line `data: first half` | data `["first half"]`, `_skip_lf = True` |
| chunk 1 returns | no blank line yet | `[]` |
| chunk 2, `\n` | `_skip_lf` is set, so this LF belongs to the CRLF: swallow it | `_skip_lf = False` |
| chunk 2, rest | `data: second half`, then `\r\n\r\n` gives one blank line | dispatch |

Expected: `[[], [{"event": "message", "data": "first half\nsecond half", "id": ""}]]`. If you treat that leading `\n` as its own line ending, it's an empty line, and you dispatch `first half` and `second half` as **two** events. That's exactly what `wrong_crlf_split_across_chunks.py` outputs.

## 4. Key idea: a CR ends the line now, and a flag eats the LF later

There are two ways to handle `\r\n`, and only one is right for streams.

The **lazy** way holds a `\r` until you see the next character, so you know whether it's a pair. That's wrong here, because the next character might not arrive for a long time, or ever. "bare CR endings" ends with chunk `"\r"`: the lazy parser holds it, never sees another character, and never emits `beta`. "LF then CR at chunk end" fails the same way. I checked a lazy version: it fails exactly those two cases.

The **eager** way ends the line at the `\r`, processes it, and sets `_skip_lf = True`. On the next character, wherever it arrives, if it is `\n` you drop it. Each `\r` or `\n` is looked at once, so the cost stays linear and nothing is held back.

## 5. Key idea: what survives a dispatch and what doesn't

| state | after a dispatch |
|---|---|
| data lines | cleared |
| event type | cleared, back to `"message"` |
| `last_event_id` | **kept** |
| `retry` | kept |

The event type clears even when the dispatch emits nothing. "event type resets after dispatch and after empty event" starts with `event: ping\n\n`: no data, so nothing is emitted, but the next event `data: hello` must come out as `"message"`, not `"ping"`. The id is the opposite. In Example 2 the last event has no `id:` line and still reports `"42"`, because the client sends `last_event_id` as `Last-Event-ID` on reconnect (problem 179, websocket-reconnect-resume).

## 6. Plan before you code

```
state: line buffer, skip_lf, data lines, event type
feed(chunk):
    for each character:
        if done: stop
        if skip_lf: clear it; if this char is "\n", skip it
        if char is "\r" or "\n":
            skip_lf = (char == "\r")
            process the buffered line, collect any event it dispatched
            clear the buffer
        else: buffer it
    return collected events

process(line):
    ""          -> dispatch
    ":..."      -> comment, ignore
    has ":"     -> field before first ":", value after, drop one leading space
    no ":"      -> field = line, value = ""
    data / event / id / retry / other  -> per the field table
dispatch:
    take and clear data lines and type
    no data lines -> nothing
    joined == "[DONE]" -> done = True, nothing
    else -> {"event": type or "message", "data": joined, "id": last_event_id}
```

## 7. Build it one piece at a time

**Step 1: state.** Everything that must survive a chunk boundary lives on `self`.

```python
def __init__(self):
    self.last_event_id = ""
    self.retry = None
    self.done = False
    self._line = []        # characters of the unfinished line
    self._skip_lf = False  # the previous character was a CR
    self._data = []        # data lines of the event being built
    self._event = ""
```

**Step 2: the character loop.** This is the whole line-splitting layer.

```python
def feed(self, chunk):
    out = []
    for ch in chunk:
        if self.done:
            break
        if self._skip_lf:
            self._skip_lf = False
            if ch == "\n":
                continue
        if ch == "\r" or ch == "\n":
            self._skip_lf = ch == "\r"
            event = self._process("".join(self._line))
            self._line = []
            if event is not None:
                out.append(event)
        else:
            self._line.append(ch)
    return out
```

The `if self.done: break` check sits at the top of the loop, so the characters after `[DONE]`'s line in the *same* chunk are ignored too. In "everything after DONE ignored", `id: 6` and `retry: 999` come after `[DONE]` in chunk 1, and the expected final state is still `last_event_id = "5"`, `retry = 100`. An empty chunk just runs zero iterations and returns `[]`.

**Step 3: one line.**

```python
def _process(self, line):
    if line == "":
        return self._dispatch()
    if line.startswith(":"):
        return None
    if ":" in line:
        field, value = line.split(":", 1)
        if value.startswith(" "):
            value = value[1:]
    else:
        field, value = line, ""
```

`split(":", 1)` splits at the first colon only, so `id: run_7:evt_1` gives id `run_7:evt_1`. Don't use `value.strip()` or `lstrip()`. Models stream whitespace tokens and indented code, and both would be corrupted.

**Step 4: the fields.**

```python
    if field == "data":
        self._data.append(value)
    elif field == "event":
        self._event = value
    elif field == "id":
        self.last_event_id = value
    elif field == "retry":
        if value.isdigit() and value.isascii():
            self.retry = int(value)
    return None
```

`append`, not assign: one event can have many `data:` lines. `isdigit()` alone accepts some non-ASCII digits, which `int()` would also take, so the `isascii()` keeps it to `0-9`. `"3s"`, `""` and `"-1"` are all ignored.

**Step 5: dispatch.**

```python
def _dispatch(self):
    data, event_type = self._data, self._event
    self._data, self._event = [], ""
    if not data:
        return None
    text = "\n".join(data)
    if text == "[DONE]":
        self.done = True
        return None
    return {"event": event_type or "message", "data": text, "id": self.last_event_id}
```

Clearing comes first, so an empty event still resets the type. `[DONE]` is compared after joining, so `data: [DONE]` followed by `data: x` is the two-line data `"[DONE]\nx"` and is a normal message ("DONE-like data is not DONE").

## 8. Full solution

```python
class SSEParser:  # one parser per stream; it keeps state between feed() calls
    def __init__(self):  # start with nothing buffered
        self.last_event_id = ""  # sticky id the client sends back as Last-Event-ID on reconnect
        self.retry = None  # no reconnect delay until the server sends one
        self.done = False  # becomes True once [DONE] is dispatched
        self._line = []  # characters of the line being read, kept across chunk boundaries
        self._skip_lf = False  # the previous character was a CR, so a following LF belongs to it
        self._data = []  # data lines of the event being built
        self._event = ""  # the event type set by an event: line, "" means "message"

    def feed(self, chunk):  # called with each piece of the body, wherever the network cut it
        out = []  # events completed by this chunk, in order
        for ch in chunk:  # character by character, so a split can land anywhere
            if self.done:  # [DONE] was seen: ignore the rest of this chunk and every later one
                break  # stop reading this chunk
            if self._skip_lf:  # the last character was a CR, maybe in the previous chunk
                self._skip_lf = False  # the pair can only be CR followed directly by LF
                if ch == "\n":  # this LF is the second half of a CRLF
                    continue  # drop it, or it would read as a blank line and dispatch early
            if ch == "\r" or ch == "\n":  # any of the three line endings ends the line now
                self._skip_lf = ch == "\r"  # remember a CR so its LF is swallowed later
                line = "".join(self._line)  # the finished line
                self._line = []  # start buffering the next line
                event = self._process(line)  # a blank line may complete an event
                if event is not None:  # a real event was dispatched
                    out.append(event)  # report it from this feed() call
            else:  # an ordinary character
                self._line.append(ch)  # it stays buffered until a line ending arrives
        return out  # possibly empty, never None

    def _process(self, line):  # apply one complete line to the parser state
        if line == "":  # a blank line ends the event
            return self._dispatch()  # emit it if it has data
        if line.startswith(":"):  # a comment, usually a keep-alive ping
            return None  # ignore it entirely
        if ":" in line:  # field: value
            field, value = line.split(":", 1)  # split at the first colon only, so values may contain colons
            if value.startswith(" "):  # the format allows one space after the colon
                value = value[1:]  # remove exactly that one space, keep any others
        else:  # a bare field name such as "id" or "data"
            field, value = line, ""  # its value is empty
        if field == "data":  # one more line of payload
            self._data.append(value)  # append: an event can have many data lines
        elif field == "event":  # a named event type
            self._event = value  # applies to the event being built
        elif field == "id":  # the resume point
            self.last_event_id = value  # an empty value resets it to ""
        elif field == "retry":  # reconnect delay in milliseconds
            if value.isdigit() and value.isascii():  # only plain 0-9 digits are valid
                self.retry = int(value)  # anything else ("3s", "", "-1") is ignored
        return None  # field lines never complete an event

    def _dispatch(self):  # a blank line arrived: finish the current event
        data, event_type = self._data, self._event  # take what was built
        self._data, self._event = [], ""  # reset both even if nothing is emitted
        if not data:  # no data lines, e.g. a bare event: line
            return None  # nothing to emit
        text = "\n".join(data)  # multi-line data joins with newlines
        if text == "[DONE]":  # the end-of-stream sentinel, not a message
            self.done = True  # stop parsing from here on
            return None  # never hand [DONE] to the UI
        # the type defaults to "message"; the id is the sticky last_event_id
        return {"event": event_type or "message", "data": text, "id": self.last_event_id}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[]`, then one event, then one event; `done` True | the line buffer across chunks, `[DONE]` not emitted |
| Example 2 | `message_start` id 41, `content_block_delta` id 42, then `message` id 42; `retry` 3000 | comments, named events, sticky id |
| Example 3 | `"line one\n two spaces"` | CRLF, joining with `\n`, one space stripped |
| CRLF split across chunks | one event `"first half\nsecond half"` in chunk 2 | `_skip_lf` survives the boundary |
| bare CR endings, LF then CR at chunk end | `alpha` in chunk 1, `beta` in chunk 2; `a` then `b` | a CR ends the line at once |
| one char per chunk, seven chars per chunk | 4 events, last id `"103"`; the 7-char run ends with `done` True | nothing depends on where chunks split |
| empty chunks and partial field name | `{"token":"ok"}` from the last chunk | `""` chunks, a field name split as `da` + `ta` |
| id sticky, reset and no-colon field | ids `run_7:evt_1`, `run_7:evt_1`, `""`, `9` | split at the first colon, bare `id` resets to `""` |
| event type resets after dispatch and after empty event | `message`, `error`, `message` | type clears even when nothing is emitted |
| retry validation | final `retry` 1000 | `3s`, empty and `-1` are ignored |
| everything after DONE ignored | only `last token`; id `"5"`, retry 100 | nothing after `[DONE]`, even in the same chunk |
| DONE on a named event with id before it | no events; id `"77"`, `done` True | `id:` before `[DONE]` still counts |
| incomplete trailing event never emitted | only `complete` | no blank line, no event |
| field parsing edge cases | `""`, `""`, `"  three spaces"`, `"no space"`, `"url: https://..."`, then nothing twice | bare `data`, one-space rule, case-sensitive `Data`, comments |
| multi-line JSON body | one `tool_result` event with 4 lines | `append` for data |
| DONE split across chunks | `hi`, then `done` True with nothing after | `[DO` + `NE]` + a split CRLF |
| mixed endings in one chunk | `"a\nb\nc"` | `\r\n`, `\r` and `\n` in one chunk |
| DONE-like data is not DONE | `"[DONE] "` and `"[DONE]\nx"` are emitted | exact comparison on the joined data |

## 10. Complexity

Each character is handled once, and each line is joined and split once, so `feed` is O(len(chunk)) and the whole stream is O(total length). Memory is the longest unfinished line plus the data lines of one event.

In production that bound matters: a malicious or broken server can send a line with no ending, and the buffer grows forever. Real parsers cap the line length and the event size. Building the line from a list of characters is fine at 4,000 characters; a faster version scans each chunk with `str.find` for the next `\r` or `\n` and appends slices instead of single characters.

## 11. If you got Wrong Answer

Compare `events_per_chunk` position by position. Which chunk's list is off tells you a lot.

- **"CRLF split across chunks" gives two events, `first half` and `second half`.** You normalize with `chunk.replace("\r\n", "\n")` per chunk (`wrong_crlf_split_across_chunks.py`), so the LF that starts chunk 2 reads as a blank line.
- **Example 1's first feed returns a half event, or an event is missing.** You parse each chunk on its own (`wrong_parses_each_chunk_alone.py`). It also fails "one char per chunk", "seven chars per chunk", "empty chunks and partial field name" and "DONE split across chunks".
- **`beta` or `b` never arrives, or arrives a chunk late.** You hold a `\r` until the next character. It fails "bare CR endings" and "LF then CR at chunk end".
- **An event with data `"[DONE]"` appears in the output.** You forward the sentinel (`wrong_forwards_done_sentinel.py`).
- **Example 3 gives `"two spaces"` with no leading space.** You used `strip()` (`wrong_strips_all_whitespace.py`). It also breaks "field parsing edge cases" and "multi-line JSON body".
- **Multi-line data shows only its last line.** You assign `self._data = [value]` instead of appending (`wrong_overwrites_multiline_data.py`).
- **Example 2's last event has id `""`.** You clear `last_event_id` on dispatch (`wrong_resets_id_per_event.py`).
- **"event type resets..." shows `ping` on the `hello` event.** You only reset the type when an event is emitted. Reset it before the empty-data check.

## 12. Follow-ups an interviewer might ask

- *The socket gives you bytes, not `str`. What changes?* Put an incremental UTF-8 decoder (`codecs.getincrementaldecoder("utf-8")()`) in front of the parser. A multibyte character splits across reads just like a line does, and decoding each chunk separately raises or corrupts it.
- *How do you resume after the connection drops?* Reconnect with `Last-Event-ID: <last_event_id>`, wait `retry` ms first, and drop any events you already applied. Problem 179 (websocket-reconnect-resume) builds that loop.
- *How do you turn `content_block_delta` events into a tool call?* Accumulate `partial_json` per content block and parse it once the block stops. Problem 115 (streaming-tool-call-assembly) consumes exactly these events.
- *Why not just use the browser's `EventSource`?* It only does GET with no body or custom headers, and LLM APIs need a POST with a JSON body and an auth header. So SDKs ship their own parser, like `eventsource-parser` or `httpx-sse`.
- *The stream returned HTTP 200 but the answer is cut off. Why?* Errors can arrive mid-stream as `event: error` (for example an `overloaded_error`). Treat that event as a failure, not as content.
