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


def validate_tool_args(schema, args):
    errors = set()
    _validate(schema, args, "", errors)
    return [{"path": p, "keyword": k} for p, k in sorted(errors)]
