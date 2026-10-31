REFUND = {
    "type": "object",
    "properties": {
        "order_id": {"type": "string", "minLength": 6},
        "amount_cents": {"type": "integer", "minimum": 1, "maximum": 50000},
        "reason": {"type": "string", "enum": ["damaged", "late", "wrong_item"]},
        "notify_customer": {"type": "boolean"},
    },
    "required": ["order_id", "amount_cents", "reason"],
    "additionalProperties": False,
}

CREATE_ORDER = {
    "type": "object",
    "properties": {
        "customer": {
            "type": "object",
            "properties": {"email": {"type": "string", "minLength": 3}, "tier": {"enum": ["free", "pro", "enterprise"]}},
            "required": ["email"],
        },
        "lines": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {"sku": {"type": "string"}, "qty": {"type": "integer", "minimum": 1}},
                "required": ["sku", "qty"],
                "additionalProperties": False,
            },
        },
        "coupon": {"type": ["string", "null"], "maxLength": 12},
    },
    "required": ["customer", "lines"],
}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"schema": REFUND, "args": {"order_id": "ord_88213", "amount_cents": 1999, "reason": "damaged"}},
         "explanation": "Every required key is present and each value passes its rules, so there are no errors."},
        {"name": "Example 2", "hidden": False,
         "args": {"schema": REFUND, "args": {"order_id": "ord_9", "amount_cents": 0, "reason": "changed_mind", "priority": "high"}},
         "explanation": "Four problems, all reported: order_id is shorter than 6 characters, amount_cents is below 1, reason isn't in the enum, and priority isn't an allowed property. Sorted by path."},
        {"name": "Example 3", "hidden": False,
         "args": {"schema": CREATE_ORDER, "args": {"customer": {"tier": "pro"}, "lines": [{"sku": "MUG-01", "qty": "2"}]}},
         "explanation": "Errors are reported deep in the structure: the customer's email is missing (the path names the missing key), and lines/0/qty is a string, so only `type` fires and `minimum` is skipped."},
        {"name": "bool is not an integer", "args": {"schema": REFUND,
         "args": {"order_id": "ord_55120", "amount_cents": True, "reason": "late", "notify_customer": 1}}},
        {"name": "float 3.0 is an integer", "args": {"schema": CREATE_ORDER,
         "args": {"customer": {"email": "dana@northwind.io"}, "lines": [{"sku": "TEE-L", "qty": 3.0}, {"sku": "TEE-M", "qty": 2.5}]}}},
        {"name": "enum with true vs 1", "args": {"schema": {"type": "object", "properties": {
            "priority": {"enum": [0, 1, 2]}, "dry_run": {"enum": [False]}, "region": {"enum": ["us-east-1", None]}}},
         "args": {"priority": True, "dry_run": 0, "region": None}}},
        {"name": "enum 1.0 equals 1", "args": {"schema": {"type": "object", "properties": {"level": {"enum": [1, 2, 3]}}},
         "args": {"level": 2.0}}},
        {"name": "pointer escaping", "args": {"schema": {"type": "object", "properties": {
            "headers": {"type": "object", "additionalProperties": {"type": "string"}}}},
         "args": {"headers": {"content/type": 7, "x~trace": "ok", "x~retry/count": 3, "accept": "json"}}}},
        {"name": "many errors sorted as strings", "args": {"schema": CREATE_ORDER,
         "args": {"customer": "dana", "lines": [{"sku": "A", "qty": 1}] * 9 + [{"sku": 5, "qty": 0, "gift": True}] + [{"qty": -1}],
                  "coupon": "SPRINGSALE2026"}}},
        {"name": "root type mismatch", "args": {"schema": REFUND, "args": ["ord_1", 100]}},
        {"name": "empty array and too many", "args": {"schema": {"type": "object", "properties": {
            "tags": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string", "maxLength": 8}}},
            "required": ["tags", "ticket_id"]},
         "args": {"tags": ["billing", "escalation", "vip"]}}},
        {"name": "nullable coupon ok", "args": {"schema": CREATE_ORDER,
         "args": {"customer": {"email": "li@contoso.com", "tier": "enterprise"}, "lines": [{"sku": "BOOK-7", "qty": 1}], "coupon": None}}},
        {"name": "number accepts int and float", "args": {"schema": {"type": "object", "properties": {
            "lat": {"type": "number", "minimum": -90, "maximum": 90}, "lon": {"type": "number", "minimum": -180, "maximum": 180},
            "radius_km": {"type": "number", "minimum": 0.5}}, "required": ["lat", "lon"]},
         "args": {"lat": 30, "lon": -197.25, "radius_km": False}}},
        {"name": "enum of objects", "args": {"schema": {"type": "object", "properties": {
            "sort": {"enum": [{"field": "created_at", "desc": True}, {"field": "total", "desc": False}]}}},
         "args": {"sort": {"field": "created_at", "desc": 1}}}},
    ]
