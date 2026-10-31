import json
import re

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def extract(text):
    m = FENCE.search(text)
    if m:
        return m.group(1)
    i, j = text.find("{"), text.find("}")
    if i == -1 or j < i:
        return None
    return text[i:j + 1]


def parse(text, required):
    cand = extract(text)
    if cand is None:
        return None, ["no_json"]
    try:
        obj = json.loads(cand)
    except ValueError:
        fixed = re.sub(r",\s*([}\]])", r"\1", cand)
        fixed = re.sub(r"'([^'\"]*)'\s*:", r'"\1":', fixed)
        try:
            obj = json.loads(fixed)
        except ValueError:
            return None, ["invalid_json"]
    if not isinstance(obj, dict):
        return None, ["not_object"]
    errors = []
    for field, kind in required.items():
        if field not in obj:
            errors.append("missing:" + field)
        elif not TYPES[kind](obj[field]):
            errors.append("type:" + field)
    return obj, errors


def get_structured(llm, messages, required):
    first = llm.complete(messages).content or ""
    obj, errors = parse(first, required)
    if not errors:
        return {"ok": True, "data": obj, "attempts": 1}
    retry = list(messages) + [
        {"role": "assistant", "content": first},
        {"role": "user", "content": "Your reply was not valid JSON for the schema. Errors: "
                                    + "; ".join(errors) + ". Reply with only the corrected JSON object."},
    ]
    second = llm.complete(retry).content or ""
    obj, errors = parse(second, required)
    if not errors:
        return {"ok": True, "data": obj, "attempts": 2}
    return {"ok": False, "errors": errors, "attempts": 2}
