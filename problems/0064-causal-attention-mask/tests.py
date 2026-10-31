def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"T_q": 3, "T_k": 3},
         "explanation": "The standard lower-triangular mask. Each token sees itself and everything before it."},
        {"name": "Example 2", "hidden": False, "args": {"T_q": 2, "T_k": 4, "offset": 2},
         "explanation": "Two new queries after a cache of two tokens. They sit at positions 2 and 3."},
        {"name": "Example 3", "hidden": False, "args": {"T_q": 1, "T_k": 5, "offset": 4},
         "explanation": "One decoding step. The new token sees the whole cache, so the row is all zeros."},
        {"name": "single", "args": {"T_q": 1, "T_k": 1}},
        {"name": "more keys no offset", "args": {"T_q": 3, "T_k": 6}},
        {"name": "more queries than keys", "args": {"T_q": 5, "T_k": 2}},
        {"name": "prefill chunk", "args": {"T_q": 4, "T_k": 10, "offset": 6}},
        {"name": "offset past the end", "args": {"T_q": 3, "T_k": 4, "offset": 7}},
        {"name": "big square", "args": {"T_q": 64, "T_k": 64}},
        {"name": "big rectangle", "args": {"T_q": 16, "T_k": 48, "offset": 32}},
    ]
