import json


def assemble(events):
    blocks = {}  # index -> {"type", "id", "name", "buf": [], "stopped": bool, "input"}
    usage = {"input_tokens": 0, "output_tokens": 0}
    stop_reason = None
    for ev in events:
        kind = ev.get("type")
        if kind == "message_stop":
            break
        if kind == "message_start":
            usage["input_tokens"] = ev["message"].get("usage", {}).get("input_tokens", 0)
        elif kind == "content_block_start":
            cb = ev["content_block"]
            blocks[ev["index"]] = {"type": cb["type"], "id": cb.get("id"), "name": cb.get("name"),
                                   "buf": [], "stopped": False, "input": None, "error": None}
        elif kind == "content_block_delta":
            d = ev["delta"]
            b = blocks[ev["index"]]
            b["buf"].append(d["text"] if d["type"] == "text_delta" else d["partial_json"])
        elif kind == "content_block_stop":
            b = blocks[ev["index"]]
            b["stopped"] = True
            if b["type"] == "tool_use":
                raw = "".join(b["buf"])
                if not raw.strip():
                    b["input"] = {}
                else:
                    try:
                        val = json.loads(raw)
                    except ValueError:
                        b["error"] = "invalid_json"
                    else:
                        if isinstance(val, dict):
                            b["input"] = val
                        else:
                            b["error"] = "not_object"
        elif kind == "message_delta":
            if "stop_reason" in ev.get("delta", {}):
                stop_reason = ev["delta"]["stop_reason"]
            if "output_tokens" in ev.get("usage", {}):
                usage["output_tokens"] = ev["usage"]["output_tokens"]

    content, tool_calls, errors = [], [], []
    for idx in sorted(blocks):
        b = blocks[idx]
        if b["type"] == "text":
            content.append({"type": "text", "text": "".join(b["buf"])})
            continue
        if not b["stopped"]:
            b["error"] = "unterminated"
        content.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})
        if b["error"]:
            errors.append({"index": idx, "id": b["id"], "reason": b["error"]})
        else:
            tool_calls.append({"id": b["id"], "name": b["name"], "input": b["input"]})
    return {"content": content, "tool_calls": tool_calls, "errors": errors,
            "stop_reason": stop_reason, "usage": usage}
