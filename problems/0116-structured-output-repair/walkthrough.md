## 1. What the problem is really asking

You asked a model for JSON and got back *text that probably contains JSON*. Your wrapper has to turn that text into a validated dict, cheaply and predictably:

> extract a candidate substring → parse it, with one narrow repair if needed → check each required field's type → if anything failed, ask the model **once** more, showing it its own mistake.

Under the story, this is a **three-stage pure function** (`text → (obj, errors)`) wrapped in a loop that runs at most twice. All the interesting logic is deterministic string work. The model call is just the input source.

The judge records more than your return value. The driver returns `result`, `raised`, `calls` (every message list you sent to `llm.complete`) and `caller_messages_unchanged`. So the exact text of the re-ask message, the order of its errors, the number of calls, and whether you touched the caller's list are all graded.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `llm` | a `FakeLLM` that replays a script | `llm.complete(messages).content or ""` |
| `messages` | the caller's transcript (system + user email) | sent as-is on attempt 1; copied, never modified |
| `required` | `{"order_id": "string", "amount_cents": "integer", ...}` | validated **in its iteration order**, which fixes the error order |
| return | `{"ok": True, "data", "attempts"}` or `{"ok": False, "errors", "attempts": 2}` | `errors` are attempt 2's, not attempt 1's |

Three details are easy to miss:

- **`.content` can be `None`.** The case "null value and empty reply" scripts its second turn as `{}`, so the fake returns `content=None`. `None or ""` turns it into an empty string, which then yields `["no_json"]` instead of a crash.
- **Each failure stage returns a single error and stops.** `no_json`, `invalid_json` and `not_object` are never combined with field errors. Only a parsed dict gets field validation, and that can produce several errors at once.
- **`isinstance(True, int)` is `True` in Python.** `bool` is a subclass of `int`. JSON `true` must not pass as an `integer` or a `number`.

## 3. Trace the examples by hand

**Example 2** (one call, repaired). The reply is:

```
Sure! {'order_id': "A-1182", 'amount_cents': 4999, 'reason': "damaged", 'refund_to_original': true,}
```

There's no fence, so the candidate runs from the first `{` to the last `}`, dropping `Sure! `. `json.loads` raises on the single quotes. The repairs run in order:

| stage | string |
|---|---|
| after trailing-comma fix | `{'order_id': "A-1182", 'amount_cents': 4999, 'reason': "damaged", 'refund_to_original': true}` |
| after key-quote fix | `{"order_id": "A-1182", "amount_cents": 4999, "reason": "damaged", "refund_to_original": true}` |

That parses, all four fields have the right types, and the result is `{"ok": True, ..., "attempts": 1}` with one entry in `calls`.

**Example 3** (re-ask). Attempt 1 is `{"order_id": "A-1182", "amount_cents": "49.99", "refund_to_original": true}`. It parses as a dict. Walk `required` in order:

| field | present? | type ok? | error |
|---|---|---|---|
| `order_id` | yes | `str` | none |
| `amount_cents` | yes | `"49.99"` is a `str` | `type:amount_cents` |
| `reason` | no | n/a | `missing:reason` |
| `refund_to_original` | yes | `bool` | none |

So the second call sends four messages: the system turn, the user email, then

```python
{"role": "assistant", "content": '{"order_id": "A-1182", "amount_cents": "49.99", "refund_to_original": true}'}
{"role": "user", "content": "Your reply was not valid JSON for the schema. Errors: type:amount_cents; missing:reason. Reply with only the corrected JSON object."}
```

Attempt 2 is the good JSON, so the result is `ok` with `attempts: 2`.

**The trickiest hidden case, "single-quoted values are not repaired".** Attempt 1 is `{'order_id': 'A-1182', 'amount_cents': 4999}`. The key repair turns it into `{"order_id": 'A-1182', "amount_cents": 4999}`. The value `'A-1182'` is still single-quoted, because the regex only touches a quoted run **followed by a colon**. `json.loads` fails again, so the error is `invalid_json`, not `missing:reason; missing:refund_to_original`. Attempt 2 has a trailing comma inside an array and another before the closing brace (`["a", "b",],}`); the first regex removes both, and the result is `ok` with `notes: ['a', 'b']` kept.

## 4. Key idea: the last brace, not the first

JSON objects nest. In "nested objects with trailing prose" the reply contains `"items": [{"sku": "TV-55", "qty": 1}]` long before the outer object closes. The first `}` in the text is the one after `"qty": 1`, so `text[:text.find("}") + 1]` gives:

```
{"order_id": "B-204", "items": [{"sku": "TV-55", "qty": 1}
```

That's invalid JSON, and the repair can't fix it. `rfind("}")` gives the end of the whole object instead. The trailing `Hope that helps {:` has a `{` but no `}`, so it doesn't move the last brace. The same reasoning covers "braces inside strings": `"A-{1182}"` and `"{SAVE10}"` contain braces, and the last `}` is still the object's own.

The rule is also why "closing brace before opening" (`} no data here {`) gives `no_json`: the last `}` is at index 0, before the first `{`, so there's no valid span.

## 5. Key idea: show the model its own mistake, and only once

The re-ask is `messages + [assistant: bad reply, user: errors]`, not `messages + [user: errors]`. Without the assistant turn, the model is told "Errors: type:amount_cents" about a reply it can't see, and is likely to regenerate the same output from scratch. With it, the model can edit its own answer.

The cap matters as much. One confused model with an uncapped retry loop becomes a cost spike and a latency tail. Here the cap is exact: two calls, never three. "fails twice, stop at two calls" has a valid third turn in its script, and it's there to catch a loop that keeps going.

## 6. Plan before you code

```
parse(text, required) -> (obj, errors):
    cand = first fence's body, else text[first "{" : last "}"], else -> ["no_json"]
    try json.loads(cand)
    on failure: strip trailing commas, quote single-quoted keys, try once more
        still failing -> ["invalid_json"]
    not a dict -> ["not_object"]
    for field, kind in required: missing:field / type:field
get_structured:
    attempt 1 on messages; no errors -> ok, attempts 1
    retry = copy of messages + assistant(raw reply 1) + user(error text)
    attempt 2 on retry; no errors -> ok, attempts 2; else -> fail with attempt 2's errors
```

The type table is a dict of predicates, so validation is one lookup per field:

| type name | predicate |
|---|---|
| `string` | `isinstance(v, str)` |
| `integer` | `isinstance(v, int) and not isinstance(v, bool)` |
| `number` | `isinstance(v, (int, float)) and not isinstance(v, bool)` |
| `boolean` | `isinstance(v, bool)` |
| `array` | `isinstance(v, list)` |
| `object` | `isinstance(v, dict)` |

## 7. Build it one piece at a time

**Step 1: extract.** Compile the fence regex once. `re.DOTALL` lets `.` cross newlines, and `.*?` is lazy, so the match stops at the *first* closing fence. That's what "first of two fences, no tag" needs: the old-format block is used and the `{"orderId": 1}` block is ignored. The code writes three backticks as `` `{3} ``, a regex quantifier that matches exactly the same thing; it only keeps this page's code block from closing early.

```python
FENCE = re.compile(r"`{3}[^\n]*\n(.*?)`{3}", re.DOTALL)

def extract(text):
    m = FENCE.search(text)
    if m:
        return m.group(1)
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j < i:
        return None
    return text[i:j + 1]
```

A fence wins over braces because it's the model's explicit statement of where the payload is. In "fenced array is not an object" the fence body is `[{...}]`, a list, so the candidate is that list, and the error is `not_object`.

**Step 2: parse, then repair only on failure.** Try the raw candidate first. Valid JSON never goes through the regexes, so a valid string value like `"promo code {SAVE10} failed"` is never at risk.

```python
    try:
        obj = json.loads(cand)
    except ValueError:
        fixed = re.sub(r",\s*([}\]])", r"\1", cand)
        fixed = re.sub(r"'([^'\"]*)'\s*:", r'"\1":', fixed)
        try:
            obj = json.loads(fixed)
        except ValueError:
            return None, ["invalid_json"]
```

`json.JSONDecodeError` is a subclass of `ValueError`, so catching `ValueError` is enough.

**Step 3: validate in `required` order.** Check `field not in obj` first; a key that's present with value `null` (`None`) falls through to the type check and gets `type:order_id`, as "null value and empty reply" expects.

```python
    errors = []
    for field, kind in required.items():
        if field not in obj:
            errors.append("missing:" + field)
        elif not TYPES[kind](obj[field]):
            errors.append("type:" + field)
    return obj, errors
```

**Step 4: the re-ask, on a copy.** `list(messages) + [...]` builds a new list. `messages += [...]` would extend the caller's list in place, and `caller_messages_unchanged` would come back `False`.

```python
    retry = list(messages) + [
        {"role": "assistant", "content": first},
        {"role": "user", "content": "Your reply was not valid JSON for the schema. Errors: "
                                    + "; ".join(errors) + ". Reply with only the corrected JSON object."},
    ]
```

`first` is the raw reply text, prose and fences included, not the extracted candidate.

## 8. Full solution

```python
import json  # json.loads is the only parser allowed (no eval)
import re  # the fence search and the two narrow repairs

# Three backticks + optional info string + newline, then the body up to the FIRST closing fence.
# `{3} is the same as three literal backticks; it's written this way so this page's code block stays intact.
FENCE = re.compile(r"`{3}[^\n]*\n(.*?)`{3}", re.DOTALL)
# One predicate per schema type name; bool is excluded from the numeric types because it subclasses int.
TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def extract(text):  # pick the substring most likely to be the JSON payload, or None
    m = FENCE.search(text)  # a fence is the model's explicit marker for the payload
    if m:  # fenced: trust it over any braces in the prose
        return m.group(1)  # the body of the first fence
    i, j = text.find("{"), text.rfind("}")  # first open brace, LAST close brace, so nested objects survive
    if i == -1 or j < i:  # no "{", or the only "}" comes before it: nothing to parse
        return None  # the caller turns this into no_json
    return text[i:j + 1]  # inclusive span from the first "{" to the last "}"


def parse(text, required):  # one attempt: extract, parse, repair, validate -> (obj, errors)
    cand = extract(text)  # stage 1: find the candidate
    if cand is None:  # no JSON-looking span at all
        return None, ["no_json"]  # a single error; nothing else can be checked
    try:  # stage 2: valid JSON should never be touched by the repairs
        obj = json.loads(cand)  # the raw candidate first
    except ValueError:  # JSONDecodeError subclasses ValueError
        fixed = re.sub(r",\s*([}\]])", r"\1", cand)  # repair 1: drop commas before } or ]
        fixed = re.sub(r"'([^'\"]*)'\s*:", r'"\1":', fixed)  # repair 2: double-quote single-quoted keys only
        try:  # one more parse after the repairs
            obj = json.loads(fixed)  # succeeds for the common slips
        except ValueError:  # still broken: don't guess further
            return None, ["invalid_json"]  # the re-ask will tell the model
    if not isinstance(obj, dict):  # a list or a scalar is valid JSON but not an object
        return None, ["not_object"]  # field checks need a dict
    errors = []  # stage 3: collect every field error, in required order
    for field, kind in required.items():  # iteration order fixes the error order the judge expects
        if field not in obj:  # absent key
            errors.append("missing:" + field)  # report it by name
        elif not TYPES[kind](obj[field]):  # present but wrong type, null included
            errors.append("type:" + field)  # report it by name
    return obj, errors  # empty errors means valid; extra keys stay in obj


def get_structured(llm, messages, required):  # extract, repair, validate, and re-ask at most once
    first = llm.complete(messages).content or ""  # attempt 1; a None reply becomes "" (-> no_json)
    obj, errors = parse(first, required)  # run the three stages on it
    if not errors:  # valid on the first try
        return {"ok": True, "data": obj, "attempts": 1}  # one call, done
    # New list: the caller's history must not gain the failed exchange.
    # The bad reply goes in as an assistant turn so the model can fix its own output.
    retry = list(messages) + [
        {"role": "assistant", "content": first},
        {"role": "user", "content": "Your reply was not valid JSON for the schema. Errors: "
                                    + "; ".join(errors) + ". Reply with only the corrected JSON object."},
    ]
    second = llm.complete(retry).content or ""  # attempt 2, the last call ever made
    obj, errors = parse(second, required)  # same three stages
    if not errors:  # the re-ask fixed it
        return {"ok": True, "data": obj, "attempts": 2}  # report that it took two calls
    return {"ok": False, "errors": errors, "attempts": 2}  # give up with attempt 2's errors; no third call
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | ok, attempts 1 | the fence body is the candidate; the prose around it is ignored |
| Example 2 | ok, attempts 1 | both repairs, in order, without a second call |
| Example 3 | ok, attempts 2; errors `type:amount_cents; missing:reason` | error order follows `required`; the re-ask includes the bad reply |
| no json then valid | ok, attempts 2; first errors `no_json` | the no-brace branch, then a fence with no info string |
| fails twice, stop at two calls | fail, `['missing:reason', 'missing:refund_to_original']` | exactly two calls; the errors are attempt 2's |
| nested objects with trailing prose | ok, attempts 1 | `rfind("}")`; extra keys `items` and `ship_to` are kept |
| bool is not an integer | fail, `['type:refund_to_original']` | `true` rejected as `integer`, and `1` rejected as `boolean` |
| number accepts int and float, rejects bool | ok, attempts 2 | `false` rejected as `number`; `4` accepted |
| float number first try | ok, attempts 1 | `3.5` is a `number`; empty `[]` and `{}` are valid `array` and `object` |
| fenced array is not an object | fail, `['no_json']`; first errors `not_object` | a parsed list isn't a dict; `[]` has no braces |
| null value and empty reply | fail, `['no_json']`; first errors `type:order_id` | `null` is a type error; `content=None` becomes `""` |
| first of two fences, no tag | ok, attempts 1 | the lazy `.*?` takes the first fence |
| single-quoted values are not repaired | ok, attempts 2; first errors `invalid_json` | the key regex only touches keys; trailing commas in arrays |
| braces inside strings | ok, attempts 1 | braces inside values don't break extraction |
| closing brace before opening | fail, `['no_json']` | the `j < i` guard |

## 10. Complexity

Each attempt is linear in the reply length: one regex search, at most two `json.loads` passes and two `re.sub` passes, then O(len(required)) dictionary lookups. With at most two attempts, the wrapper adds microseconds next to a model call that takes seconds.

The real cost is the re-ask: a second full model call that resends the whole transcript plus the bad reply. In production you track the **repair rate** and the **re-ask rate** per prompt version. A prompt change that doubles the re-ask rate doubles a slice of your inference bill and adds a second round trip of latency for those users.

## 11. If you got Wrong Answer

- **"nested objects with trailing prose" and "float number first try" re-ask with `invalid_json`.** You used `text.find("}")`, which stops at the first inner `}`. Use `rfind`.
- **"bool is not an integer" passes on attempt 1.** You wrote `isinstance(v, int)` alone. Add `and not isinstance(v, bool)` to `integer` and `number`.
- **`caller_messages_unchanged` is `False`.** You did `retry = messages; retry += [...]`, which mutates the caller's list. Build a new list with `list(messages) + [...]`.
- **The second transcript has three messages, not four.** You left out the `{"role": "assistant", "content": first}` turn.
- **`calls` has three entries in "fails twice, stop at two calls".** Your retry is a loop with no cap at two.
- **"single-quoted values are not repaired" re-asks with `missing:reason; missing:refund_to_original` instead of `invalid_json`.** You repaired by swapping every `'` for `"`. That happens to fix this reply, but it corrupts real values such as `"Can't log in"`. Keep the repair to keys.
- **Runtime Error on "null value and empty reply".** You called string methods on `None`. Use `.content or ""`.

## 12. Follow-ups an interviewer might ask

- *How would you avoid this repair code entirely?* Use constrained decoding: OpenAI's `response_format` with a JSON schema and `strict: true`, Anthropic's tool use with an `input_schema`, or vLLM's guided decoding. Keep the validator anyway, because schemas drift and a provider can still return something unexpected.
- *How would you validate richer schemas, like enums, nested required fields or string formats?* Replace the type-name table with a full JSON Schema validator (problem 113, tool-args-schema-validation), and put the validator's messages into the re-ask.
- *Why not repair harder, with a lenient parser or `ast.literal_eval`?* Every extra repair is a guess about intent. `literal_eval` also accepts Python syntax JSON doesn't (`True`, tuples). Narrow repairs keep false fixes rare, and the re-ask handles the rest with the model's help.
- *What if the reply arrives as a stream?* Assemble the chunks first, and report malformed JSON instead of repairing it mid-stream (problem 115, streaming-tool-call-assembly).
- *How do transport errors fit in?* A 429 or 5xx isn't a content error and shouldn't use the re-ask. Wrap `llm.complete` in retry with backoff (problem 124) and keep the one-re-ask budget for bad content.
