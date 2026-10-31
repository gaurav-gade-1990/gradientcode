def sess(prefix, n):
    return ["%s-%04d" % (prefix, i) for i in range(n)]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"vnodes": 8, "sessions": sess("sess", 6),
                  "ops": [{"op": "add", "node": "worker-a"}, {"op": "add", "node": "worker-b"},
                          {"op": "lookup", "key": "sess-0003", "n": 2}]},
         "explanation": "The first worker takes all six sessions. When worker-b joins, only the sessions whose ring arc now ends at a worker-b point move, and each of them moves to worker-b. The lookup returns the owner, then the next distinct node clockwise."},
        {"name": "Example 2", "hidden": False,
         "args": {"vnodes": 16, "sessions": sess("chat", 10),
                  "ops": [{"op": "add", "node": "gpu-1"}, {"op": "add", "node": "gpu-2"}, {"op": "add", "node": "gpu-3"},
                          {"op": "remove", "node": "gpu-2"}]},
         "explanation": "Removing gpu-2 moves exactly the sessions gpu-2 owned. Sessions on gpu-1 and gpu-3 stay put."},
        {"name": "empty ring", "args": {"vnodes": 4, "sessions": sess("s", 3),
                                        "ops": [{"op": "lookup", "key": "s-0001", "n": 3},
                                                {"op": "add", "node": "w1"}, {"op": "remove", "node": "w1"},
                                                {"op": "lookup", "key": "s-0001", "n": 3}]}},
        {"name": "one vnode wraparound", "args": {"vnodes": 1, "sessions": sess("tenant-7-sess", 40),
                                                  "ops": [{"op": "add", "node": "agent-a"}, {"op": "add", "node": "agent-b"},
                                                          {"op": "add", "node": "agent-c"}]}},
        {"name": "duplicate add and unknown remove", "args": {"vnodes": 8, "sessions": sess("s", 20),
                                                              "ops": [{"op": "add", "node": "w1"}, {"op": "add", "node": "w2"},
                                                                      {"op": "add", "node": "w1"}, {"op": "remove", "node": "w9"},
                                                                      {"op": "remove", "node": "w2"}]}},
        {"name": "scale out to six", "args": {"vnodes": 32, "sessions": sess("conv", 120),
                                              "ops": [{"op": "add", "node": "node-%d" % i} for i in range(1, 7)]
                                              + [{"op": "remove", "node": "node-3"}, {"op": "add", "node": "node-3"}]}},
        {"name": "failover lists", "args": {"vnodes": 4, "sessions": sess("s", 5),
                                            "ops": [{"op": "add", "node": "us-east-%d" % i} for i in range(1, 5)]
                                            + [{"op": "lookup", "key": "sess-%d" % i, "n": 3} for i in range(12)]
                                            + [{"op": "lookup", "key": "sess-0", "n": 8}]}},
        {"name": "rolling restart", "args": {"vnodes": 12, "sessions": sess("ticket", 60),
                                             "ops": [{"op": "add", "node": "w-%s" % c} for c in "abcd"]
                                             + [{"op": "remove", "node": "w-a"}, {"op": "add", "node": "w-a"},
                                                {"op": "remove", "node": "w-b"}, {"op": "add", "node": "w-b"},
                                                {"op": "lookup", "key": "ticket-0042", "n": 2}]}},
        {"name": "two vnodes many keys", "args": {"vnodes": 2, "sessions": sess("k", 80),
                                                  "ops": [{"op": "add", "node": "n1"}, {"op": "add", "node": "n2"},
                                                          {"op": "lookup", "key": "k-0001", "n": 2}]}},
    ]
