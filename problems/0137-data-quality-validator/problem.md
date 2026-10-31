Your LLM gateway writes one log row per request, and the billing and eval pipelines read those rows downstream. Before a batch lands in the warehouse, a validation step checks it against a list of expectations (in the style of Great Expectations) and blocks the load when one fails. Write that step.

`validate(records, expectations, refs=None, id_column="request_id", sample_size=3)`

- `records` is a list of dicts (one per request). A field is **null** when its key is absent or its value is `None`.
- `expectations` is a list of dicts. Each has a `"column"`, a `"check"`, the check's parameters, and an optional `"mostly"` (default `1.0`).
- `refs` maps a reference-table name to a list of valid keys, for foreign keys.

**Checks.** `not_null` evaluates every row. Every other check **skips null rows**: they are neither evaluated nor failed.

| check | parameters | a non-null value fails when |
|---|---|---|
| `not_null` | none | (the row fails when the value is null) |
| `type` | `"type"`: `"int"`, `"float"`, `"str"` or `"bool"` | it is not of that type. `int` means an `int` that is not a `bool`. `float` accepts any `int` or `float` that is not a `bool`. |
| `range` | `"min"` and/or `"max"` (each optional, inclusive) | it is not a number (an `int` or `float` that is not a `bool`), or it lies outside the bounds |
| `regex` | `"pattern"` | it is not a `str`, or `re.fullmatch(pattern, value)` is `None` |
| `in_set` | `"values"`: a list | `value in values` is false |
| `unique` | none | another evaluated row holds an equal value of the same type. Every such row fails, including the first. |
| `foreign_key` | `"ref"`: a key of `refs` | `value in refs[ref]` is false |

**Result per expectation**, in input order:

```
{"column": str, "check": str, "evaluated": int, "failed": int, "fail_rate": float,
 "passed": bool, "sample": [ids]}
```

- `fail_rate = failed / evaluated`, or `0.0` when `evaluated == 0`.
- `passed` is true when `evaluated == 0` or `(evaluated - failed) / evaluated >= mostly`.
- `sample` lists the `id_column` value of the first `sample_size` failing rows, in record order (`None` if a row has no id).

Return

```
{"success": bool, "results": [...], "failed_rows": [row indices]}
```

`success` is true when every expectation passed. `failed_rows` lists, in ascending order, the 0-based index of every row that failed at least one expectation, including expectations that still passed under `mostly`. Do not modify `records`.

**Constraints**

- `0 <= len(records) <= 2000`, `1 <= len(expectations) <= 20`
- `0 <= mostly <= 1`, `1 <= sample_size <= 10`
- Values are JSON values: strings, numbers, booleans, `None`, lists or dicts.
