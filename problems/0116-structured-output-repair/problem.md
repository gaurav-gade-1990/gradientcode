Your support pipeline asks a model to pull refund details out of customer emails as JSON. The model usually complies, but sometimes it wraps the JSON in a code fence, adds a sentence of prose, leaves a trailing comma, or single-quotes a key. Write the wrapper that extracts, repairs, validates, and re-asks **at most once**.

`get_structured(llm, messages, required)`:

- `llm` is a `gc_runtime.FakeLLM`. Call `llm.complete(messages)` and read `.content` (a string; treat `None` as `""`).
- `messages` is the chat transcript to send. Don't modify the caller's list.
- `required` maps each field name to a type name.

**Step 1. Extract a candidate** from the reply text.

1. If the text matches the regex ```` ```[^\n]*\n(.*?)``` ```` (with `re.DOTALL`), meaning an opening fence with an optional info string such as `json`, a newline, and then a closing fence, the candidate is group 1 of the **first** match.
2. Otherwise, if the text contains a `{` and a `}` after it, the candidate runs from the first `{` through the **last** `}`, inclusive.
3. Otherwise the attempt fails with errors `["no_json"]`.

**Step 2. Parse** the candidate with `json.loads`. If that raises, repair it and parse again:

1. Remove trailing commas: `re.sub(r",\s*([}\]])", r"\1", s)`.
2. Then double-quote single-quoted keys: `re.sub(r"'([^'\"]*)'\s*:", r'"\1":', s)`.

If the repaired string still fails, the errors are `["invalid_json"]`. If the parsed value isn't a dict, the errors are `["not_object"]`.

**Step 3. Validate** each field in `required`, in its iteration order:

| type name | accepts (Python value after `json.loads`) |
|---|---|
| `string` | `str` |
| `integer` | `int`, but not `bool` |
| `number` | `int` or `float`, but not `bool` |
| `boolean` | `bool` |
| `array` | `list` |
| `object` | `dict` |

A key that's absent adds `"missing:<field>"`. A key that's present with the wrong type, including `null`, adds `"type:<field>"`. Extra keys are allowed and kept.

**Step 4. Re-ask once.** If attempt 1 produced any errors, call `llm.complete` a second time with:

```
messages + [
  {"role": "assistant", "content": <attempt 1's raw reply text>},
  {"role": "user", "content": "Your reply was not valid JSON for the schema. Errors: "
                              + "; ".join(errors) + ". Reply with only the corrected JSON object."},
]
```

Process the second reply with the same steps. Never make a third call.

Return:

- on success: `{"ok": True, "data": <parsed dict>, "attempts": n}`, where `n` is 1 or 2
- on failure after the re-ask: `{"ok": False, "errors": <attempt 2's errors>, "attempts": 2}`

The judge records every message list you send to the model.

**Constraints**

- `1 <= len(required) <= 8`
- Use only `json` and `re` for parsing. Don't use `eval` or `ast.literal_eval`.
