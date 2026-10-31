## Approach

Walk the schema and the value together, carrying the JSON pointer of the current spot. At each node, apply every keyword that fits the value's kind and add any failure to a set. Then recurse into `properties`, `additionalProperties` and `items`. Sort the set at the end.

```python
def _validate(schema, value, path, errors):
    if "type" in schema and not any(_type_ok(value, t) for t in as_list(schema["type"])):
        errors.add((path, "type"))
    if "enum" in schema and not any(_json_equal(value, e) for e in schema["enum"]):
        errors.add((path, "enum"))
    if is_number(value):            # bool excluded
        ...minimum / maximum
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.add((path + "/" + esc(key), "required"))
        for key, sub in value.items():
            child = path + "/" + esc(key)
            if key in props:                 _validate(props[key], sub, child, errors)
            elif extra is False:             errors.add((child, "additionalProperties"))
            elif isinstance(extra, dict):    _validate(extra, sub, child, errors)
```

Making each keyword type-gated (`minimum` only looks at numbers) is what keeps the output to one error per real mistake. `"2"` for an integer field is a `type` error. It isn't also a `minimum` error.

## Common mistakes

- **`isinstance(True, int)`.** A Python bool is an int, so a naive check accepts `"amount_cents": true` and `minimum` compares `True >= 1`. Check for bool first, everywhere.
- **`value in enum`.** Python's `in` uses `==`, where `True == 1` and `False == 0`. JSON equality keeps booleans apart from numbers.
- **Rejecting `3.0` for `integer`.** Models often emit `2.0` for counts. JSON Schema says that's an integer. Rejecting it causes pointless retries.
- **Fail-fast validation.** If you return the first error only, a call with four mistakes takes four round trips to the model. Every round trip costs latency and tokens.
- **Unescaped pointers.** A header key like `content/type` turns into a path that names a field that doesn't exist, and the model edits the wrong thing.

## Production notes

- The Anthropic and OpenAI tool-use APIs describe tools with JSON Schema (`input_schema` / `parameters`). Models follow it well but not perfectly, so validate on your side before any side effect runs. OpenAI's strict mode and Anthropic's structured outputs narrow this gap but don't remove it for every schema.
- Feed the errors back as a `tool_result` with `is_error: true` and a short message per pointer. Models repair from pointer-addressed errors far better than from a stack trace.
- Real validators (`jsonschema` in Python, Ajv in JS) cover far more: `$ref`, `oneOf`, `pattern`, `format`. Compile the schema once per tool version and cache the validator. Don't re-parse it per call.
- MCP servers return a schema error as a `-32602 Invalid params` protocol error (problem 114). In your own agent loop, prefer a tool result the model can see and fix.
- Pairs with **structured-output-repair** (116), which repairs and re-asks, and **tool-permission-scopes** (117), which runs after validation and before execution.
