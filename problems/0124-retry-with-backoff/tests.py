OK = {"content": "Customer wants a refund for order 1182."}
R429 = {"error": "rate_limit"}
J = [0.5, 0.25, 0.9, 0.1, 0.6, 0.3, 0.8, 0.45, 0.7]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"script": [{"error": "server"}, {"error": "timeout"}, OK], "jitter": J},
         "explanation": "Two retryable failures. The sleeps are 0.5*min(8, 0.5*1) = 0.25 and 0.25*min(8, 0.5*2) = 0.25, then the third call succeeds."},
        {"name": "Example 2", "hidden": False, "args": {"script": [{"error": "rate_limit", "retry_after": 3.0}, OK], "jitter": J},
         "explanation": "Jitter gives 0.25 s, but the server asked for 3 s. Sleep max(0.25, 3.0) = 3.0."},
        {"name": "Example 3", "hidden": False, "args": {"script": [{"error": "bad_request"}, OK], "jitter": J},
         "explanation": "A 400 is not retryable. Re-raise it with no sleep."},
        {"name": "success first try", "args": {"script": [OK], "jitter": J}},
        {"name": "exhausted", "args": {"script": [R429] * 5 + [OK], "jitter": J}},
        {"name": "exhausted max_attempts=2", "args": {"script": [{"error": "server"}] * 3, "jitter": J, "max_attempts": 2}},
        {"name": "cap reached", "args": {"script": [{"error": "server"}] * 6 + [OK], "jitter": [0.99] * 9, "max_attempts": 8, "base": 1.0, "cap": 4.0}},
        {"name": "retry_after smaller than jitter", "args": {"script": [{"error": "rate_limit", "retry_after": 0.01}, OK], "jitter": [0.9], "base": 2.0}},
        {"name": "retry_after zero", "args": {"script": [{"error": "rate_limit", "retry_after": 0.0}, {"error": "rate_limit", "retry_after": 1.5}, OK], "jitter": J}},
        {"name": "400 after a retry", "args": {"script": [{"error": "timeout"}, {"error": "bad_request"}, OK], "jitter": J}},
        {"name": "single attempt", "args": {"script": [{"error": "server"}, OK], "jitter": J, "max_attempts": 1}},
    ]
