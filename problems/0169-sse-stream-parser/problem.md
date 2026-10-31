Your chat UI streams model output from your backend over Server-Sent Events. The network hands you the response body in chunks that can split anywhere, including inside a JSON payload or between the `\r` and `\n` of a line ending. Write the incremental parser that turns those chunks into events.

Implement `class SSEParser` with:

- `feed(chunk)`: takes the next piece of the body as a `str` and returns the list of events **completed by this chunk**, in order (an empty list if none). An event is a dict `{"event": str, "data": str, "id": str}`.
- `last_event_id` (str, starts `""`), `retry` (int or `None`, starts `None`) and `done` (bool, starts `False`) as attributes.

**Lines.** A line ends at `\r\n`, `\n` or `\r`. A `\r\n` pair is one line ending even when the `\r` is the last character of one chunk and the `\n` is the first of the next. Characters after the last line ending stay buffered until a later chunk ends the line.

**Each line**, in order:

| line | what to do |
|---|---|
| empty | dispatch (below) |
| starts with `:` | a comment (keep-alive ping): ignore it |
| contains `:` | the field is the text before the **first** `:`, the value is the rest; if the value starts with one space, remove that one space only |
| no `:` | the whole line is the field, and the value is `""` |

| field (case-sensitive) | what to do |
|---|---|
| `data` | append the value to this event's data lines |
| `event` | set this event's type |
| `id` | set `last_event_id` to the value (an empty value resets it to `""`) |
| `retry` | if the value is a non-empty string of ASCII digits, set `retry = int(value)`; otherwise ignore the line |
| anything else | ignore |

**Dispatch** on an empty line. If the event has no data lines, emit nothing. Otherwise the event's `data` is its data lines joined with `"\n"`, its `event` is the type set by `event:` or `"message"` if none was set, and its `id` is the current `last_event_id`. In both cases, clear the data lines and the event type afterwards. `last_event_id` is **not** cleared: it carries over to later events, because the client sends it as `Last-Event-ID` when it reconnects.

**`[DONE]`.** If a dispatched event's data is exactly `[DONE]`, do not emit it. Set `done = True` and ignore every character after that line ending, in this chunk and in every later one (no events, no `id` or `retry` changes). An event that never gets its blank line is never emitted.

The judge feeds your parser one chunk at a time and grades which events each `feed` call returned, plus the final `last_event_id`, `retry` and `done`.

**Constraints**

- `1 <= len(chunks) <= 400`; chunks may be empty strings
- Total stream length is at most 4,000 characters
- Return plain dicts with exactly the keys `event`, `data` and `id`
