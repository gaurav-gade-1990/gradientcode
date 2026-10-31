def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"corpus": "low low low lower newest newest", "num_merges": 4, "test_words": ["lowest", "new"]},
         "explanation": "Counts: low x3, lower x1, newest x2. (l, o) and (o, w) both have count 4; (l, o) is the smaller tuple, so it merges first. Then (lo, w) has count 4. Next, five pairs tie at 2 and (e, s) is the smallest, then (e, w)."},
        {"name": "Example 2", "hidden": False,
         "args": {"corpus": "aaa aaa ab", "num_merges": 3, "test_words": ["aaaa", "ba"]},
         "explanation": "aaa contributes 2 overlapping (a, a) pairs, so (a, a) has count 4. Merging left to right turns a a a into aa a."},
        {"name": "stops early", "args": {"corpus": "ab ab cd", "num_merges": 10, "test_words": ["abcd", "x"]},
         "explanation": "After merging (a, b) and (c, d) every word is one symbol, so training stops with 2 merges."},
        {"name": "zero merges", "args": {"corpus": "hello world", "num_merges": 0, "test_words": ["hello"]}},
        {"name": "boundary trap", "args": {"corpus": "xab xab xab ab ab xa", "num_merges": 3, "test_words": ["xab", "abxab"]},
         "explanation": "Once xa is a symbol, x a b is xa b. Searching the string 'xa b' for 'a b' would wrongly match inside xa."},
        {"name": "frequency matters", "args": {"corpus": "ab ab ab ab cd cde cdf", "num_merges": 2, "test_words": ["abcd", "cdab"]}},
        {"name": "tuple vs concat ties", "args": {"corpus": "abc abc az az", "num_merges": 3, "test_words": ["abc", "az", "abz"]},
         "explanation": "After (a, b) the pairs (ab, c) and (a, z) tie at 2. As tuples (a, z) < (ab, c); as joined strings 'abc' < 'az'."},
        {"name": "case and punctuation", "args": {"corpus": "The the THE the, the. Then then", "num_merges": 6,
                                                  "test_words": ["the", "The", "then,", "Theta"]}},
        {"name": "unseen test words", "args": {"corpus": "banana bandana banana cabana", "num_merges": 5,
                                               "test_words": ["bananas", "cab", "zzz", "anna"]}},
        {"name": "multiple whitespace", "args": {"corpus": "  hug\tpug  pun\n\nbun hug  hugs ", "num_merges": 6,
                                                 "test_words": ["hugs", "bug", "punk"]}},
        {"name": "long corpus", "args": {"corpus": " ".join(
            ["the quick brown fox jumps over the lazy dog"] * 3 +
            ["low lower lowest newer newest wider widest", "tokenizer tokenize token tokens tokenized",
             "running runner run runs ran", "unbelievable believable believe belief"] * 2),
            "num_merges": 40, "test_words": ["tokenizing", "lowly", "unbelief", "foxes", "quickest", "runway"]}},
    ]
