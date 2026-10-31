SYSTEM = {"role": "system", "content": "Extract refund details from the customer email. Reply with a JSON object with keys "
                                       "order_id (string), amount_cents (integer), reason (string), refund_to_original (boolean)."}
EMAIL = {"role": "user", "content": "Hi, order A-1182 arrived with a cracked screen. I paid $49.99 and would like the money "
                                    "back on my Visa please. - Dana"}
MSGS = [SYSTEM, EMAIL]
REFUND = {"order_id": "string", "amount_cents": "integer", "reason": "string", "refund_to_original": "boolean"}

GOOD = '{"order_id": "A-1182", "amount_cents": 4999, "reason": "damaged", "refund_to_original": true}'


def c(text):
    return {"content": text}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"script": [c("Here is the extracted data:\n```json\n" + GOOD + "\n```\nLet me know if you need anything else.")],
                  "messages": MSGS, "required": REFUND},
         "explanation": "The reply has a ```json fence. The candidate is the fenced body, which parses and validates. One call, attempts = 1."},
        {"name": "Example 2", "hidden": False,
         "args": {"script": [c("Sure! {'order_id': \"A-1182\", 'amount_cents': 4999, 'reason': \"damaged\", "
                               "'refund_to_original': true,}")],
                  "messages": MSGS, "required": REFUND},
         "explanation": "There's no fence, so take the first '{' through the last '}'. json.loads fails on the single-quoted keys "
                        "and the trailing comma. The two repairs fix both, so this is still one call."},
        {"name": "Example 3", "hidden": False,
         "args": {"script": [c('{"order_id": "A-1182", "amount_cents": "49.99", "refund_to_original": true}'), c(GOOD)],
                  "messages": MSGS, "required": REFUND},
         "explanation": "Attempt 1 parses, but amount_cents is a string and reason is missing. Errors in required order: "
                        "type:amount_cents, missing:reason. The re-ask sends the original messages, the bad reply as an "
                        "assistant turn, and the error message. Attempt 2 is valid."},
        {"name": "no json then valid", "args": {
            "script": [c("I'm sorry, I can't find an order number in this email."), c("```\n" + GOOD + "\n```")],
            "messages": MSGS, "required": REFUND}},
        {"name": "fails twice, stop at two calls", "args": {
            "script": [c("{'order_id': 'A-1182'}"), c('{"order_id": "A-1182", "amount_cents": 4999}'), c(GOOD)],
            "messages": MSGS, "required": REFUND}},
        {"name": "nested objects with trailing prose", "args": {
            "script": [c('Result: {"order_id": "B-204", "items": [{"sku": "TV-55", "qty": 1}], "ship_to": {"city": "Austin"}, '
                         '"amount_cents": 89900, "reason": "wrong item", "refund_to_original": false} Hope that helps {:'),
                       c(GOOD)],
            "messages": MSGS, "required": REFUND}},
        {"name": "bool is not an integer", "args": {
            "script": [c('{"order_id": "A-1182", "amount_cents": true, "reason": "damaged", "refund_to_original": true}'),
                       c('{"order_id": "A-1182", "amount_cents": 4999, "reason": "damaged", "refund_to_original": 1}')],
            "messages": MSGS, "required": REFUND}},
        {"name": "number accepts int and float, rejects bool", "args": {
            "script": [c('{"ticket_id": "T-9", "csat": false, "tags": ["billing"], "customer": {"tier": "gold"}}'),
                       c('{"ticket_id": "T-9", "csat": 4, "tags": ["billing"], "customer": {"tier": "gold"}}')],
            "messages": [{"role": "user", "content": "Summarize ticket T-9 as JSON."}],
            "required": {"ticket_id": "string", "csat": "number", "tags": "array", "customer": "object"}}},
        {"name": "float number first try", "args": {
            "script": [c('{"ticket_id": "T-10", "csat": 3.5, "tags": [], "customer": {}}')],
            "messages": [{"role": "user", "content": "Summarize ticket T-10 as JSON."}],
            "required": {"ticket_id": "string", "csat": "number", "tags": "array", "customer": "object"}}},
        {"name": "fenced array is not an object", "args": {
            "script": [c("```json\n[" + GOOD + "]\n```"), c("[]")],
            "messages": MSGS, "required": REFUND}},
        {"name": "null value and empty reply", "args": {
            "script": [c('{"order_id": null, "amount_cents": 4999, "reason": "damaged", "refund_to_original": true}'), {}],
            "messages": MSGS, "required": REFUND}},
        {"name": "first of two fences, no tag", "args": {
            "script": [c("Old format:\n```\n{\"order_id\": \"A-1182\", \"amount_cents\": 4999, \"reason\": \"late\", "
                         "\"refund_to_original\": false, \"carrier\": \"UPS\"}\n```\nNew format:\n```json\n{\"orderId\": 1}\n```")],
            "messages": MSGS, "required": REFUND}},
        {"name": "single-quoted values are not repaired", "args": {
            "script": [c("{'order_id': 'A-1182', 'amount_cents': 4999}"), c("{\"order_id\": \"A-1182\", \"amount_cents\": 4999, "
                                                                            "\"reason\": \"damaged\", \"refund_to_original\": true, \"notes\": [\"a\", \"b\",],}")],
            "messages": MSGS, "required": REFUND}},
        {"name": "braces inside strings", "args": {
            "script": [c('{"order_id": "A-{1182}", "amount_cents": 0, "reason": "promo code {SAVE10} failed", "refund_to_original": false}')],
            "messages": MSGS, "required": REFUND}},
        {"name": "closing brace before opening", "args": {
            "script": [c("} no data here {"), c("still nothing")],
            "messages": MSGS, "required": {"order_id": "string"}}},
    ]
