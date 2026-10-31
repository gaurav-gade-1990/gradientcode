## 1. What the problem is really asking

When a model calls a tool, it sends an `arguments` object it *believes* matches the tool's `input_schema`. Usually it does. Sometimes the amount is `0`, the reason is a value that isn't in the list, or there's an extra key nobody asked for. If that call reaches your refund API, the damage is already done. So a gateway checks the arguments first and, if anything is wrong, sends the model a single error result listing **every** problem, so one retry can fix them all.

Strip the story and this is a **recursive walk over two trees at once**: the schema and the value. At every node you apply the keywords that fit the value's kind, record failures as `(path, keyword)` pairs, then recurse into the children. The path you carry down is a JSON pointer, like `/lines/0/qty`.

The judge calls `validate_tool_args(schema, args)` and compares the returned list exactly. That means three things are graded at once: *which* errors you find (no more, no fewer), the *path* string of each, and the *order* (plain string sort on `(path, keyword)`).

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `schema` | a dict in a JSON Schema subset: `type`, `enum`, `minimum`/`maximum`, `minLength`/`maxLength`, `minItems`/`maxItems`, `items`, `properties`, `required`, `additionalProperties` | read the keywords at the current level; recurse with the sub-schema |
| `args` | the decoded tool arguments: dicts, lists, strings, ints, floats, bools, `None` | the value you walk alongside the schema |
| return value | `[{"path": ..., "keyword": ...}, ...]` sorted by `(path, keyword)` | build a `set` of tuples, sort it at the end |

Three details are easy to miss:

- **Python's `bool` is a subclass of `int`.** `isinstance(True, int)` is `True`, and `True == 1`. JSON keeps booleans and numbers apart, so every type check and every equality check has to rule out `bool` first.
- **Keywords are gated by kind.** `minimum` only looks at numbers, `minLength` only at strings, `required` only at objects. A string `"2"` against `{"type": "integer", "minimum": 1}` is one `type` error, not a `type` error plus a crash or a `minimum` error.
- **A `required` error lives at the missing key's path**, not at the parent. A missing `email` inside `customer` is reported at `/customer/email`.

## 3. Trace the examples by hand

**Example 2** uses the `REFUND` schema (`additionalProperties: false`, `required: [order_id, amount_cents, reason]`) with:

```python
{"order_id": "ord_9", "amount_cents": 0, "reason": "changed_mind", "priority": "high"}
```

Walk the root object. All three required keys are present, so no `required` errors. Then each key in turn:

| key | rule | value | error |
|---|---|---|---|
| `order_id` | `string`, `minLength: 6` | `"ord_9"` has length 5 | `("/order_id", "minLength")` |
| `amount_cents` | `integer`, `minimum: 1`, `maximum: 50000` | `0` is an integer but below 1 | `("/amount_cents", "minimum")` |
| `reason` | `string`, `enum: [damaged, late, wrong_item]` | `"changed_mind"` is a string, not in the enum | `("/reason", "enum")` |
| `priority` | not in `properties`, and `additionalProperties` is `false` | anything | `("/priority", "additionalProperties")` |

Sorted by path, the output is:

```python
[{"path": "/amount_cents", "keyword": "minimum"},
 {"path": "/order_id", "keyword": "minLength"},
 {"path": "/priority", "keyword": "additionalProperties"},
 {"path": "/reason", "keyword": "enum"}]
```

Notice the order isn't the order the keys appeared in. It is string order of the paths.

**Example 3** goes deeper. With `CREATE_ORDER` and `{"customer": {"tier": "pro"}, "lines": [{"sku": "MUG-01", "qty": "2"}]}`:

- `customer` is an object whose schema requires `email`. It's missing, so the error is `("/customer/email", "required")`. `tier: "pro"` is in its enum.
- `lines` is an array of 1 item (inside `minItems: 1`, `maxItems: 20`). Item 0 is walked at `/lines/0`. `sku` is a string, fine. `qty` is `"2"`, a string, so `type` fails at `/lines/0/qty`. Because the value isn't a number, `minimum` never looks at it.

Output: `[{"path": "/customer/email", "keyword": "required"}, {"path": "/lines/0/qty", "keyword": "type"}]`.

**The tricky hidden case, "many errors sorted as strings":**

```python
{"customer": "dana",
 "lines": [{"sku": "A", "qty": 1}] * 9 + [{"sku": 5, "qty": 0, "gift": True}] + [{"qty": -1}],
 "coupon": "SPRINGSALE2026"}
```

| path | what happens | error |
|---|---|---|
| `/coupon` | a string, so the `["string", "null"]` type passes, but length 14 > 12 | `maxLength` |
| `/customer` | `"dana"` is not an object. `required: [email]` is skipped because it only applies to objects | `type` |
| `/lines/0` … `/lines/8` | all valid | none |
| `/lines/9/sku` | `5` is not a string | `type` |
| `/lines/9/qty` | `0 < 1` | `minimum` |
| `/lines/9/gift` | not in the item's `properties`, `additionalProperties: false` | `additionalProperties` |
| `/lines/10/sku` | missing | `required` |
| `/lines/10/qty` | `-1 < 1` | `minimum` |

The reference output lists `/lines/10/qty` and `/lines/10/sku` **before** `/lines/9/...`, because `"1" < "9"` as characters. That is exactly what `sorted()` on string tuples does, and the problem says so. Don't try to sort indexes numerically.

## 4. Key idea: one error per real mistake

The whole design goal is a list the model can act on. A good list has one line per thing the model got wrong. Two habits get you there.

**Gate every keyword on the value's kind.** Check `minimum` only when the value is a number (and not a bool), `minLength` only for strings, `items`/`minItems` only for lists, `properties`/`required` only for dicts. This is how real JSON Schema behaves, and it also keeps your code from crashing. If you drop the gate on `minimum`, Example 3 compares `"2" < 1` and raises `TypeError: '<' not supported between instances of 'str' and 'int'`.

**Collect into a set, never return early.** A `set` of `(path, keyword)` tuples gives you the "at most once" rule for free, and sorting a list of tuples sorts by path and then keyword, which is what the judge wants.

## 5. Key idea: JSON types are not Python types

Here is where Python fights you:

| value | `isinstance(v, int)` | JSON `integer`? | JSON `number`? | JSON `boolean`? |
|---|---|---|---|---|
| `True` | `True` | no | no | yes |
| `3` | `True` | yes | yes | no |
| `3.0` | `False` | **yes** | yes | no |
| `2.5` | `False` | no | yes | no |

So the type check tests `bool` *before* it tests `integer` or `number`, and `integer` also accepts a float whose `is_integer()` is true. Models often emit `2.0` for a count, and JSON Schema says that is an integer.

Equality for `enum` has the same trap. Python's `in` uses `==`, so `True in [0, 1, 2]` is `True` and `0 in [False]` is `True`. JSON equality says neither matches. You need a small `_json_equal` that rejects a bool on one side and a number on the other, compares numbers by value (`1 == 1.0`), and recurses into lists and dicts with the same rule. The "enum of objects" case needs the recursion: `{"field": "created_at", "desc": 1}` looks equal to `{"field": "created_at", "desc": True}` under Python `==`, but it is not.

## 6. Plan before you code

```
validate_tool_args(schema, args):
    errors = set()
    walk(schema, args, path="")
    return sorted errors as dicts

walk(schema, value, path):
    type:     value matches none of the listed types        -> (path, "type")
    enum:     value json-equals none of the entries         -> (path, "enum")
    if number (not bool): minimum / maximum
    if string:            minLength / maxLength
    if list:              minItems / maxItems, then walk items at path/i
    if dict:
        required keys missing                               -> (path/key, "required")
        for each present key:
            in properties          -> walk(properties[key], ..., path/key)
            additionalProperties false  -> (path/key, "additionalProperties")
            additionalProperties schema -> walk(that schema, ..., path/key)
```

And the decision table for an object key:

| key in `properties`? | `additionalProperties` | what to do |
|---|---|---|
| yes | anything | validate against `properties[key]` |
| no | `False` | error `additionalProperties` at `path/key` |
| no | a dict | validate against that dict |
| no | `True` or absent | allow, do nothing |

## 7. Build it one piece at a time

**Step 1: the type check, bool first.**

```python
def _type_ok(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    if isinstance(value, bool):
        return False
    if t == "integer":
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if t == "number":
        return isinstance(value, (int, float))
    return False
```

The `isinstance(value, bool)` line sits after `boolean` (which needs bools to pass) and before `integer` and `number` (which must reject them). Remove it and `"amount_cents": True` passes as an integer.

**Step 2: JSON equality and the pointer escape.**

```python
def _json_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    return type(a) == type(b) and a == b


def _escape(key):
    return key.replace("~", "~0").replace("/", "~1")
```

The escape order matters. If you replaced `/` with `~1` first and then `~` with `~0`, the `~` you just wrote would become `~01`. RFC 6901 says `~` first. In the "pointer escaping" case, `x~retry/count` becomes `x~0retry~1count`.

**Step 3: the scalar keywords, each gated by kind.**

```python
def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validate(schema, value, path, errors):
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            errors.add((path, "type"))
    if "enum" in schema and not any(_json_equal(value, e) for e in schema["enum"]):
        errors.add((path, "enum"))
    if _is_number(value):
        if "minimum" in schema and value < schema["minimum"]:
            errors.add((path, "minimum"))
        if "maximum" in schema and value > schema["maximum"]:
            errors.add((path, "maximum"))
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.add((path, "minLength"))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.add((path, "maxLength"))
```

`_is_number` also excludes bool. Otherwise `"radius_km": False` against `minimum: 0.5` evaluates `False < 0.5`, which is `True`, and you report a `minimum` error on top of the `type` error.

**Step 4: arrays and objects, which recurse.**

```python
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.add((path, "minItems"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.add((path, "maxItems"))
        if isinstance(schema.get("items"), dict):
            for i, item in enumerate(value):
                _validate(schema["items"], item, "%s/%d" % (path, i), errors)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.add((path + "/" + _escape(key), "required"))
        extra = schema.get("additionalProperties", True)
        for key, sub in value.items():
            child = path + "/" + _escape(key)
            if key in props:
                _validate(props[key], sub, child, errors)
            elif extra is False:
                errors.add((child, "additionalProperties"))
            elif isinstance(extra, dict):
                _validate(extra, sub, child, errors)
```

`extra is False` (identity, not `== False`) keeps the check honest, though with a well-formed schema either works. The loop only reads `value`; it never writes to it, so `args` is not mutated.

**Step 5: the entry point.** Seed the walk with the root path `""` and sort.

```python
def validate_tool_args(schema, args):
    errors = set()
    _validate(schema, args, "", errors)
    return [{"path": p, "keyword": k} for p, k in sorted(errors)]
```

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
def _type_ok(value, t):  # does this one value match this one JSON type name?
    if t == "object":  # JSON objects arrive as Python dicts
        return isinstance(value, dict)  # any dict is an object
    if t == "array":  # JSON arrays arrive as Python lists
        return isinstance(value, list)  # any list is an array
    if t == "string":  # strings map one to one
        return isinstance(value, str)  # any str is a string
    if t == "boolean":  # checked before the bool guard below, so bools can pass here
        return isinstance(value, bool)  # only True and False are booleans
    if t == "null":  # JSON null is Python None
        return value is None  # identity check: nothing else is null
    if isinstance(value, bool):  # True is an int in Python, but never a JSON number
        return False  # so a bool fails integer and number
    if t == "integer":  # whole numbers, including floats like 3.0
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())  # 3.0 counts per JSON Schema
    if t == "number":  # any int or float (bools were ruled out above)
        return isinstance(value, (int, float))  # ints and floats both qualify
    return False  # an unknown type name matches nothing


def _json_equal(a, b):  # equality as JSON defines it, used for enum
    if isinstance(a, bool) or isinstance(b, bool):  # a bool only ever equals a bool
        return isinstance(a, bool) and isinstance(b, bool) and a == b  # so True != 1 and False != 0
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):  # two numbers, neither a bool
        return a == b  # compare by value, so 1 == 1.0
    if isinstance(a, list) and isinstance(b, list):  # arrays compare position by position
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))  # same length, every pair equal
    if isinstance(a, dict) and isinstance(b, dict):  # objects compare key by key
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)  # same keys, every value equal
    return type(a) == type(b) and a == b  # strings and None: same type and same value


def _escape(key):  # turn an object key into one JSON pointer segment
    return key.replace("~", "~0").replace("/", "~1")  # RFC 6901: escape ~ first, or the ~1 we add gets mangled


def _is_number(v):  # gate for minimum and maximum
    return isinstance(v, (int, float)) and not isinstance(v, bool)  # bools must not be compared to bounds


def _validate(schema, value, path, errors):  # check one value against one schema node, recursing into children
    if "type" in schema:  # type applies to every kind of value
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]  # allow "string" or ["string", "null"]
        if not any(_type_ok(value, t) for t in types):  # the value has to match at least one listed type
            errors.add((path, "type"))  # record it; a set keeps each (path, keyword) once
    if "enum" in schema and not any(_json_equal(value, e) for e in schema["enum"]):  # JSON equality, not Python `in`
        errors.add((path, "enum"))  # the value is none of the allowed entries
    if _is_number(value):  # bounds only look at real numbers, so "2" can't crash the comparison
        if "minimum" in schema and value < schema["minimum"]:  # inclusive lower bound
            errors.add((path, "minimum"))  # too small
        if "maximum" in schema and value > schema["maximum"]:  # inclusive upper bound
            errors.add((path, "maximum"))  # too large
    if isinstance(value, str):  # length limits only apply to strings
        if "minLength" in schema and len(value) < schema["minLength"]:  # shorter than allowed
            errors.add((path, "minLength"))  # too short
        if "maxLength" in schema and len(value) > schema["maxLength"]:  # longer than allowed
            errors.add((path, "maxLength"))  # too long
    if isinstance(value, list):  # array keywords only apply to lists
        if "minItems" in schema and len(value) < schema["minItems"]:  # too few elements
            errors.add((path, "minItems"))  # record the array-level error
        if "maxItems" in schema and len(value) > schema["maxItems"]:  # too many elements
            errors.add((path, "maxItems"))  # still validate the items below, so every error is reported
        if isinstance(schema.get("items"), dict):  # one schema that every element must satisfy
            for i, item in enumerate(value):  # walk each element with its index
                _validate(schema["items"], item, "%s/%d" % (path, i), errors)  # the index becomes the next pointer segment
    if isinstance(value, dict):  # object keywords only apply to dicts
        props = schema.get("properties", {})  # the keys this schema knows about
        for key in schema.get("required", []):  # every key that must be present
            if key not in value:  # the model left it out
                errors.add((path + "/" + _escape(key), "required"))  # reported at the missing key's own path
        extra = schema.get("additionalProperties", True)  # absent means extra keys are allowed
        for key, sub in value.items():  # look at every key the model actually sent
            child = path + "/" + _escape(key)  # pointer to this key's value
            if key in props:  # a known key: validate against its own schema
                _validate(props[key], sub, child, errors)  # recurse one level down
            elif extra is False:  # unknown keys are forbidden
                errors.add((child, "additionalProperties"))  # flag the extra key itself
            elif isinstance(extra, dict):  # unknown keys are allowed but must match this schema
                _validate(extra, sub, child, errors)  # recurse with the additionalProperties schema


def validate_tool_args(schema, args):  # entry point the judge calls
    errors = set()  # collect every (path, keyword) pair, never stop at the first
    _validate(schema, args, "", errors)  # the root's JSON pointer is the empty string
    return [{"path": p, "keyword": k} for p, k in sorted(errors)]  # tuples sort by path then keyword, as plain strings
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[]` | a valid call returns an empty list, not `None` |
| Example 2 | 4 errors: `minimum`, `minLength`, `additionalProperties`, `enum` | every error is collected, then sorted by path |
| Example 3 | `/customer/email` `required`, `/lines/0/qty` `type` | recursion into objects and arrays; `required` sits at the missing key's path; `minimum` is skipped for a string |
| bool is not an integer | `type` at `/amount_cents` and `/notify_customer` | `True` is not an integer, and `1` is not a boolean |
| float 3.0 is an integer | only `/lines/1/qty` `type` | `3.0` passes as an integer, `2.5` doesn't |
| enum with true vs 1 | `enum` at `/dry_run` and `/priority` | JSON equality: `True` is not `1`, `0` is not `False`; `None` can be an enum entry |
| enum 1.0 equals 1 | `[]` | numbers compare by value across int and float |
| pointer escaping | `/headers/content~1type`, `/headers/x~0retry~1count` | `~` then `/` escaping, and validating extra keys against an `additionalProperties` schema |
| many errors sorted as strings | 7 errors, `/lines/10/...` before `/lines/9/...` | string sort; `required` skipped on a non-object; many errors at different depths |
| root type mismatch | `[{"path": "", "keyword": "type"}]` | the root pointer is `""`; object keywords don't run on a list |
| empty array and too many | `maxItems` at `/tags`, `maxLength` at `/tags/1`, `required` at `/ticket_id` | array bounds plus per-item validation in the same pass |
| nullable coupon ok | `[]` | a list-valued `type` like `["string", "null"]` accepts `None` |
| number accepts int and float | `minimum` at `/lon`, `type` at `/radius_km` | `number` takes ints and floats but not bools; bounds skip bools |
| enum of objects | `enum` at `/sort` | equality recurses into dicts with the bool rule |

## 10. Complexity

The walk visits every value in `args` once, and at each node does constant work plus an `enum` comparison that costs the size of the enum entries. For `V` values in the arguments and `E` total size of the enum entries touched, time is O(V + E) plus O(k log k) to sort `k` errors. Memory is the error set plus the recursion depth, which the constraints cap at 6.

In production this cost is negligible next to a model call. What matters more is that the validator is **compiled once per tool version**: libraries like `jsonschema` or Ajv parse the schema up front, so per-call validation is just the walk. Also, every round trip you save by reporting all errors at once saves a full model call's latency and tokens.

## 11. If you got Wrong Answer

- **"bool is not an integer" is missing the `/amount_cents` error.** Your integer check accepts `True` because `isinstance(True, int)` is true. Test for `bool` first.
- **"number accepts int and float" is missing `/radius_km` `type`, or has an extra `/radius_km` `minimum`.** The same bool problem, in the type check or in the numeric bounds gate.
- **"enum with true vs 1" or "enum of objects" returns `[]`.** You used `value in schema["enum"]`. Python's `==` says `True == 1`; write a JSON equality helper.
- **"float 3.0 is an integer" also flags `/lines/0/qty`.** Your integer check is `isinstance(value, int)` only. Accept floats with `is_integer()`.
- **"pointer escaping" shows `/headers/content/type`.** You didn't escape keys. If it returns `[]`, you aren't validating extra keys against an `additionalProperties` schema at all.
- **Only one error comes back in Example 2.** You return after the first failure, or slice the list.
- **`required` errors point at `/customer` or `""`.** Append the missing key to the path.
- **Runtime Error, `'<' not supported between 'str' and 'int'`.** `minimum` is running on a string. Gate it on `_is_number`.

## 12. Follow-ups an interviewer might ask

- *What do you send back to the model?* A `tool_result` with `is_error: true` and one short line per error, such as `/amount_cents: must be >= 1`. Models repair from pointer-addressed errors much better than from a stack trace. Problem 116 (structured-output-repair) builds the re-ask loop around this.
- *Isn't strict mode enough?* Provider structured-output modes narrow the gap but don't cover every schema feature, and your tool may be called from places that skip them. Validate at the gateway regardless, before any side effect.
- *How would you add `$ref`, `oneOf` or `pattern`?* `$ref` means resolving a pointer into the schema (and guarding against cycles). `oneOf` means validating against each branch into a scratch set and passing only if exactly one is empty, which also makes error reporting harder: you have to pick which branch's errors to show.
- *Where does this sit next to permissions?* Validate shape first, then check scopes (problem 117, tool-permission-scopes), then run. An MCP server reports the same failure as a `-32602 Invalid params` error (problem 114, mcp-jsonrpc-dispatch).
- *What about a huge array argument?* Cap the number of errors you report (say, the first 20 in sorted order) so the error message itself doesn't blow the context window, and say how many were dropped.
