def start(n=812):
    return {"type": "message_start", "message": {"id": "msg_01", "role": "assistant", "usage": {"input_tokens": n, "output_tokens": 1}}}


def text(i):
    return {"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}}


def tool(i, id, name):
    return {"type": "content_block_start", "index": i, "content_block": {"type": "tool_use", "id": id, "name": name, "input": {}}}


def td(i, s):
    return {"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": s}}


def jd(i, s):
    return {"type": "content_block_delta", "index": i, "delta": {"type": "input_json_delta", "partial_json": s}}


def stop(i):
    return {"type": "content_block_stop", "index": i}


def mdelta(reason="tool_use", out=None):
    e = {"type": "message_delta", "delta": {"stop_reason": reason, "stop_sequence": None}}
    if out is not None:
        e["usage"] = {"output_tokens": out}
    return e


END = {"type": "message_stop"}
PING = {"type": "ping"}


def cases():
    weather = [
        start(472), text(0), td(0, "Let me check "), td(0, "the forecast."), stop(0),
        tool(1, "toolu_01A", "get_weather"), jd(1, ""), jd(1, '{"city": "Aus'), jd(1, 'tin", "unit"'), jd(1, ': "fahrenheit"}'), stop(1),
        mdelta("tool_use", 89), END,
    ]
    interleaved = [
        start(1290), PING,
        tool(0, "toolu_ord", "lookup_order"), tool(1, "toolu_shp", "get_shipping_status"),
        jd(0, '{"order_id": '), jd(1, '{"tracking'), jd(0, '"A-1182"'), jd(1, '_number": "1Z999AA1"'),
        jd(1, ', "carrier": "UPS"}'), stop(1), jd(0, ', "include_items": true}'), stop(0),
        mdelta("tool_use", 64), END,
    ]
    malformed = [
        start(530),
        tool(0, "toolu_tix", "list_open_tickets"), stop(0),
        tool(1, "toolu_ref", "issue_refund"), jd(1, '{"order_id": "A-1182", '), jd(1, '"amount_cents": 4999'), stop(1),
        mdelta("tool_use", 41), END,
    ]
    return [
        {"name": "Example 1", "hidden": False, "args": {"events": weather},
         "explanation": "Block 0 is text. Block 1's fragments only form valid JSON once concatenated: "
                        "'' + '{\"city\": \"Aus' + 'tin\", \"unit\"' + ': \"fahrenheit\"}'. Parse it at content_block_stop."},
        {"name": "Example 2", "hidden": False, "args": {"events": interleaved},
         "explanation": "Two tool calls stream at once and their deltas interleave. Route each fragment by index. "
                        "Block 1 stops first, but tool_calls is still sorted by index. The ping is ignored."},
        {"name": "Example 3", "hidden": False, "args": {"events": malformed},
         "explanation": "list_open_tickets got no deltas, so its input is {} and it is valid. The refund's JSON is missing "
                        "its closing brace: it is reported as invalid_json, its input is None, and it must not run."},
        {"name": "empty stream", "args": {"events": []}},
        {"name": "text only end_turn", "args": {"events": [
            start(40), text(0), td(0, "Your order "), td(0, "A-1182 shipped on "), td(0, "Oct 28."), stop(0), mdelta("end_turn", 12), END]}},
        {"name": "whitespace only args", "args": {"events": [
            start(), tool(0, "toolu_ws", "get_current_user"), jd(0, "  "), jd(0, "\n"), stop(0), mdelta("tool_use", 5), END]}},
        {"name": "not an object", "args": {"events": [
            start(), tool(0, "toolu_l", "tag_ticket"), jd(0, '["urgent", '), jd(0, '"billing"]'), stop(0),
            tool(1, "toolu_n", "close_ticket"), jd(1, "nu"), jd(1, "ll"), stop(1),
            tool(2, "toolu_s", "escalate"), jd(2, '"tier-2"'), stop(2), mdelta("tool_use", 30), END]}},
        {"name": "stream cut off mid tool", "args": {"events": [
            start(300), text(0), td(0, "Searching the knowledge base"), stop(0),
            tool(1, "toolu_kb", "search_kb"), jd(1, '{"query": "reset 2fa"'), jd(1, "}")]}},
        {"name": "cut off before stop, valid-looking buffer", "args": {"events": [
            start(300), tool(0, "toolu_a", "get_weather"), jd(0, '{"city": "Denver"}'), stop(0),
            tool(1, "toolu_b", "get_weather"), jd(1, '{"city": "Boise"}'), mdelta("tool_use", 22)]}},
        {"name": "events after message_stop ignored", "args": {"events": [
            start(77), tool(0, "toolu_x", "send_email"), jd(0, '{"to": "ana@acme.io", '), mdelta("tool_use", 18), END,
            jd(0, '"subject": "Refund"}'), stop(0), mdelta("end_turn", 99)]}},
        {"name": "unterminated text block keeps text", "args": {"events": [
            start(10), text(0), td(0, "Partial ans"), td(0, "wer")]}},
        {"name": "sparse out-of-order indexes", "args": {"events": [
            start(900), tool(5, "toolu_5", "lookup_order"), text(2), td(2, "Checking both."), tool(9, "toolu_9", "get_weather"),
            jd(9, '{"city": "Paris"'), jd(5, '{"order_id"'), jd(9, ', "unit": "celsius"}'), stop(2), stop(9),
            jd(5, ': "B-77"}'), stop(5), PING, mdelta("tool_use", 70), END]}},
        {"name": "multiple message_delta, missing usage", "args": {"events": [
            start(15), text(0), td(0, "Hi"), stop(0), mdelta("max_tokens", 3), mdelta("end_turn"), END]}},
        {"name": "no message_start or delta", "args": {"events": [
            tool(0, "toolu_q", "get_weather"), jd(0, '{"city": "Oslo"}'), stop(0)]}},
        {"name": "nested args split mid-string", "args": {"events": [
            start(2048), tool(0, "toolu_cr", "create_ticket"),
            jd(0, '{"title": "Can\'t log in", "tags": ["auth", "sso"'), jd(0, '], "requester": {"email": "li@contoso.com", '),
            jd(0, '"plan": "enter'), jd(0, 'prise"}, "priority": 2}'), stop(0),
            tool(1, "toolu_bad", "issue_refund"), jd(1, '{"amount_cents": 12,}'), stop(1),
            tool(2, "toolu_ok", "notify_slack"), jd(2, '{"channel": "#support", "text": "{escalated}"}'), stop(2),
            mdelta("tool_use", 140), END]}},
        {"name": "interleaved with a broken sibling", "args": {"events": [
            start(600), tool(0, "toolu_a", "lookup_order"), tool(1, "toolu_b", "lookup_order"), tool(2, "toolu_c", "list_open_tickets"),
            jd(1, '{"order_id": "C-'), jd(0, '{"order_id": '), jd(1, '3"}'), jd(0, '"C-1"}'), jd(0, ""),
            stop(0), stop(1), stop(2), mdelta("tool_use", 33), END]}},
    ]
