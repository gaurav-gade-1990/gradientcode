ANTHROPIC = (
    "event: message_start\n"
    "id: 101\n"
    'data: {"type":"message_start","message":{"id":"msg_01","model":"claude"}}\n'
    "\n"
    ": ping\n"
    "event: content_block_delta\n"
    "id: 102\n"
    'data: {"type":"content_block_delta","delta":{"text":"Your refund for order 1182"}}\n'
    "\n"
    "event: content_block_delta\n"
    "id: 103\n"
    'data: {"type":"content_block_delta","delta":{"text":" was issued."}}\n'
    "\n"
    "event: message_stop\n"
    'data: {"type":"message_stop"}\n'
    "\n"
)


def split_every(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"chunks": ['data: {"delta":"Hel', 'lo"}\n\ndata: {"delta":"!"}\n', '\ndata: [DONE]\n\n']},
         "explanation": "The first event's JSON is split across two chunks, so the first feed returns nothing. The second "
                        "chunk completes it. The blank line that ends the second event arrives at the start of the third "
                        "chunk. [DONE] is not emitted; it sets done."},
        {"name": "Example 2", "hidden": False,
         "args": {"chunks": [": keep-alive\n",
                             'event: message_start\nid: 41\ndata: {"type":"message_start"}\n\n',
                             'retry: 3000\nevent: content_block_delta\nid: 42\ndata: {"text":"Your order"}\n\n',
                             'data: {"text":" shipped"}\n\n']},
         "explanation": "The comment is ignored. Named events keep their type, retry is 3000, and the last event has no "
                        "event: line, so its type is \"message\". Its id is still 42 because last_event_id carries over."},
        {"name": "Example 3", "hidden": False,
         "args": {"chunks": ["data: line one\r\ndata:  two spaces\r\n\r\n"]},
         "explanation": "CRLF line endings. Two data lines join with \\n, and only one leading space is removed, so the "
                        "second line keeps one space."},
        {"name": "CRLF split across chunks", "args": {"chunks": ["data: first half\r", "\ndata: second half\r\n\r\n"]}},
        {"name": "bare CR endings", "args": {"chunks": ["data: alpha\r\rdata: beta\r", "\r"]}},
        {"name": "LF then CR at chunk end", "args": {"chunks": ["data: a\n\r", "\ndata: b\n\n"]}},
        {"name": "one char per chunk", "args": {"chunks": split_every(ANTHROPIC, 1)}},
        {"name": "seven chars per chunk", "args": {"chunks": split_every(ANTHROPIC + "data: [DONE]\n\n", 7)}},
        {"name": "empty chunks and partial field name",
         "args": {"chunks": ["", "da", "", "ta", ": {\"tok", "en\":\"ok\"}", "\n", "", "\n"]}},
        {"name": "id sticky, reset and no-colon field",
         "args": {"chunks": ["id: run_7:evt_1\ndata: queued\n\n", "data: running\n\n", "id\ndata: tool_call\n\n",
                             "id: 9\ndata: done\n\n"]}},
        {"name": "event type resets after dispatch and after empty event",
         "args": {"chunks": ["event: ping\n\n", "data: hello\n\n", "event: error\ndata: {\"type\":\"overloaded_error\"}\n\n",
                             "data: after error\n\n"]}},
        {"name": "retry validation",
         "args": {"chunks": ["retry: 2500\n", "retry: 3s\nretry:\nretry: -1\ndata: x\n\n", "retry:1000\n\n"]}},
        {"name": "everything after DONE ignored",
         "args": {"chunks": ["id: 5\nretry: 100\ndata: last token\n\ndata: [DONE]\n\nid: 6\nretry: 999\ndata: junk\n\n",
                             "data: more junk\n\n"]}},
        {"name": "DONE on a named event with id before it",
         "args": {"chunks": ["event: done\nid: 77\ndata: [DONE]\n\n", "data: never\n\n"]}},
        {"name": "incomplete trailing event never emitted",
         "args": {"chunks": ["data: complete\n\n", "data: cut off mid-str", "eam\n"]}},
        {"name": "field parsing edge cases",
         "args": {"chunks": ["data\n\n", "data:\n\n", "data:   three spaces\n\n", "data:no space\n\n",
                             "data: url: https://shop.example.com/o/1182\n\n", "Data: wrong case\nfoo: bar\n\n",
                             ": data: in a comment\n\n"]}},
        {"name": "multi-line JSON body",
         "args": {"chunks": ["event: tool_result\ndata: {\n", "data:   \"order_id\": 1182,\n",
                             "data:   \"status\": \"refunded\"\ndata: }\n", "\n"]}},
        {"name": "DONE split across chunks", "args": {"chunks": ["data: hi\n\ndata: [DO", "NE]\r", "\n\r\ndata: x\n\n"]}},
        {"name": "mixed endings in one chunk", "args": {"chunks": ["data: a\r\ndata: b\rdata: c\n\r\n"]}},
        {"name": "DONE-like data is not DONE", "args": {"chunks": ["data: [DONE] \n\ndata: [DONE]\ndata: x\n\n"]}},
    ]
