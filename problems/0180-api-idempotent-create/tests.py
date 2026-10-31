BODY = {"agent": "support-triage", "input": {"ticket": "T-1182", "priority": "high"}}
BODY_REORDERED = {"input": {"priority": "high", "ticket": "T-1182"}, "agent": "support-triage"}
OTHER = {"agent": "support-triage", "input": {"ticket": "T-2045", "priority": "low"}}


def req(at, user, key, body=BODY, header="Idempotency-Key"):
    headers = {"Content-Type": "application/json"}
    if key is not None:
        headers[header] = key
    return {"at": at, "user": user, "headers": headers, "body": body}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"requests": [req(0.0, "u_ana", "k-7f3a"), req(0.1, "u_ana", "k-7f3a")]},
         "explanation": "The second request arrives while the first is still inserting. It sees a pending record with the same "
                        "fingerprint, polls every 0.05 s, and at t=0.2 replays the first response. One run is created."},
        {"name": "Example 2", "hidden": False,
         "args": {"requests": [req(0.0, "u_ana", "k-7f3a"), req(1.0, "u_ana", "k-7f3a", OTHER), req(1.0, "u_ben", "k-7f3a")]},
         "explanation": "Reusing a key with a different body is a client bug: 422. The same key from another user is a "
                        "different request, so u_ben gets a second run."},
        {"name": "Example 3", "hidden": False,
         "args": {"requests": [req(0.0, "u_ana", "k-91c0"), req(0.5, "u_ana", "k-91c0")], "fail_creates": [0]},
         "explanation": "The first insert fails, so the handler releases the key and returns 500. The client's retry at "
                        "t=0.5 finds the key free and creates the run."},
        {"name": "three concurrent duplicates", "args": {"requests": [req(0.0, "u_ana", "k-1"), req(0.0, "u_ana", "k-1"), req(0.0, "u_ana", "k-1")]}},
        {"name": "same moment, two users", "args": {"requests": [req(0.0, "u_ana", "k-shared"), req(0.0, "u_ben", "k-shared"), req(0.05, "u_ben", "k-shared")]}},
        {"name": "reordered body is the same request", "args": {"requests": [req(0.0, "u_ana", "k-2"), req(0.3, "u_ana", "k-2", BODY_REORDERED)]}},
        {"name": "reordered body while pending", "args": {"requests": [req(0.0, "u_ana", "k-2"), req(0.1, "u_ana", "k-2", BODY_REORDERED)]}},
        {"name": "lowercase header from HTTP/2 proxy", "args": {"requests": [req(0.0, "u_ana", "k-3", header="idempotency-key"), req(0.5, "u_ana", "k-3", header="IDEMPOTENCY-KEY")]}},
        {"name": "missing and empty key", "args": {"requests": [req(0.0, "u_ana", None), req(0.0, "u_ana", "")]}},
        {"name": "failure while a duplicate waits", "args": {"requests": [req(0.0, "u_ana", "k-4"), req(0.1, "u_ana", "k-4"), req(1.0, "u_ana", "k-4")], "fail_creates": [0]}},
        {"name": "conflict while pending", "args": {"requests": [req(0.0, "u_ana", "k-5"), req(0.1, "u_ana", "k-5", OTHER), req(0.4, "u_ana", "k-5")]}},
        {"name": "many keys mixed", "args": {"requests": [req(0.0, "u_ana", "k-a"), req(0.0, "u_ana", "k-b", OTHER), req(0.15, "u_ana", "k-a"),
                                                           req(0.15, "u_ben", "k-b", OTHER), req(0.3, "u_ana", "k-b", BODY), req(2.0, "u_ben", "k-b", OTHER)],
                                              "fail_creates": [1]}},
    ]
