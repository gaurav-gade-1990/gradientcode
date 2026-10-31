def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"max_len": 3, "d_model": 4},
         "explanation": "Columns 0-1 use frequency 1 and columns 2-3 use 1/100. Row 1 is [sin 1, cos 1, sin 0.01, cos 0.01]."},
        {"name": "Example 2", "hidden": False, "args": {"max_len": 2, "d_model": 2},
         "explanation": "One pair at frequency 1. Position 0 is always [0, 1]."},
        {"name": "single position", "args": {"max_len": 1, "d_model": 8}},
        {"name": "typical", "args": {"max_len": 50, "d_model": 16}},
        {"name": "long", "args": {"max_len": 300, "d_model": 4}},
        {"name": "wide", "args": {"max_len": 20, "d_model": 64}},
        {"name": "custom base", "args": {"max_len": 10, "d_model": 6, "base": 100.0}},
    ]
