Your agent gateway checks every tool call the model emits before the tool runs. A bad call gets one `tool_result` with `is_error: true` that lists **every** problem, so the model can fix them all in a single retry.

Implement `validate_tool_args(schema, args)`. `schema` is the tool's `input_schema`, written in the JSON Schema subset below, and `args` is the decoded `arguments` object from the model. Return a list of errors, each `{"path": <JSON pointer>, "keyword": <keyword>}`, sorted by `(path, keyword)` as plain strings. Return `[]` when the arguments are valid.

**Types.** These are the Python values that match each JSON type:

| `type` | matches |
|---|---|
| `"object"` | `dict` |
| `"array"` | `list` |
| `"string"` | `str` |
| `"integer"` | `int` that is not `bool`, or a `float` with `x.is_integer()` (JSON Schema treats `3.0` as an integer) |
| `"number"` | `int` or `float`, but not `bool` |
| `"boolean"` | `bool` |
| `"null"` | `None` |

`type` is either one of these names or a list of them, and the value has to match at least one.

**Keywords.** A keyword that doesn't apply to the value's kind is ignored, the way JSON Schema works. For example, `minimum` only checks numbers, so `{"type": "integer", "minimum": 1}` against `"5"` reports only `type`.

| keyword | applies to | error when |
|---|---|---|
| `type` | anything | the value matches none of the listed types |
| `enum` | anything | the value equals none of the entries (see equality below) |
| `minimum`, `maximum` | numbers (not bool) | `x < minimum` or `x > maximum` (inclusive bounds) |
| `minLength`, `maxLength` | strings | `len(s)` is out of bounds |
| `minItems`, `maxItems` | arrays | `len(a)` is out of bounds |
| `items` | arrays | (a schema) validate each element at `path/i` |
| `properties` | objects | validate each **present** key at `path/key` |
| `required` | objects | a listed key is missing. The error's path is the missing key's path, `path/key` |
| `additionalProperties` | objects | `false`: every key not in `properties` is an error at `path/key`. A schema: validate each such key's value against it. `true` or absent: allow it |

Any other keyword is ignored.

**Equality for `enum`** is JSON equality: `1 == 1.0`, but `True` never equals `1` and `False` never equals `0`. Lists and dicts compare element by element with the same rule.

**Paths** are JSON pointers (RFC 6901). The root is `""`, an object key `k` adds `"/" + k`, and an array index adds `"/" + str(i)`. Escape `~` as `~0` first, then `/` as `~1`.

Each `(path, keyword)` pair appears at most once. Never mutate `args`.

**Constraints**

- The schema nests at most 6 levels and is always well formed.
- `args` contains only JSON values: dicts with string keys, lists, strings, ints, floats, bools and `None`.
- Sorting is plain string order, so `"/lines/10"` comes before `"/lines/2"`.
