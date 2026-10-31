ACME = {"rpm": 60, "tpm": 60000}      # 1 request/s, 1,000 tokens/s
GLOBEX = {"rpm": 6, "tpm": 12000}     # 0.1 request/s, 200 tokens/s
INITECH = {"rpm": 7, "tpm": 1000}     # awkward rates on purpose


def acq(t, tenant, tokens):
    return {"t": t, "op": "acquire", "tenant": tenant, "tokens": tokens}


def settle(t, tenant, reserved, actual):
    return {"t": t, "op": "settle", "tenant": tenant, "reserved": reserved, "actual": actual}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"limits": {"acme": ACME}, "ops": [acq(0, "acme", 25000), acq(0, "acme", 25000), acq(0, "acme", 25000), acq(15, "acme", 25000)]},
         "explanation": "acme starts with 60,000 tokens. Two 25,000-token requests leave 10,000. The third needs 15,000 more at 1,000 tokens/s, a 15 s wait, and max_wait is 0, so it gets a 429 with retry_after 15 and nothing is deducted. At t=15 the bucket is back to 25,000 and the retry goes through."},
        {"name": "Example 2", "hidden": False,
         "args": {"limits": {"acme": ACME}, "max_wait": 30.0,
                  "ops": [acq(0, "acme", 40000), acq(0, "acme", 35000), acq(0, "acme", 5000), settle(2, "acme", 40000, 1200), acq(2, "acme", 10000)]},
         "explanation": "With a 30 s queue, the second request is admitted with a 15 s wait and the token level goes to -15,000. The third queues behind it: (5,000 + 15,000) / 1,000 = 20 s. At t=2 the first response settles with 1,200 real tokens, returning 38,800. The level is -20,000 + 2,000 + 38,800 = 20,800, so the next 10,000-token request goes now."},
        {"name": "Example 3", "hidden": False,
         "args": {"limits": {"acme": ACME, "globex": GLOBEX},
                  "ops": [acq(0, "globex", 100)] * 6 + [acq(0, "globex", 100), acq(0, "acme", 100), acq(0, "initech", 100)]},
         "explanation": "globex may send 6 requests per minute. The seventh at t=0 needs one request token at 0.1/s, so it gets retry_after 10. acme has its own buckets and is admitted. initech has no contract, so the gateway answers 400."},
        {"name": "rejected retries must not drain the bucket",
         "args": {"limits": {"globex": GLOBEX},
                  "ops": [acq(0, "globex", 50)] * 6 + [acq(float(t), "globex", 50) for t in range(1, 10)] + [acq(10.5, "globex", 50), acq(10.5, "globex", 50)]}},
        {"name": "idle tenant does not bank more than one minute",
         "args": {"limits": {"acme": ACME},
                  "ops": [acq(0, "acme", 1000), acq(600, "acme", 30000), acq(600, "acme", 30000), acq(600, "acme", 30000), acq(600, "acme", 30000)]}},
        {"name": "interleaved tenants stay isolated",
         "args": {"limits": {"acme": ACME, "globex": GLOBEX},
                  "ops": [acq(0, "acme", 50000), acq(0, "globex", 12000), acq(1, "acme", 11000), acq(1, "globex", 200),
                          acq(5, "globex", 1000), acq(5, "acme", 1000), acq(10, "acme", 20000)]}},
        {"name": "oversize and unknown tenant",
         "args": {"limits": {"globex": GLOBEX}, "max_wait": 1000.0,
                  "ops": [acq(0, "globex", 12001), acq(0, "umbrella", 10), acq(0, "globex", 12000), acq(0, "globex", 1)]}},
        {"name": "queue chain with settle refund capped at capacity",
         "args": {"limits": {"acme": ACME}, "max_wait": 60.0,
                  "ops": [acq(0, "acme", 60000), acq(0, "acme", 30000), acq(0, "acme", 20000), acq(0, "acme", 1000),
                          settle(3, "acme", 60000, 500), settle(3, "acme", 30000, 0), settle(4, "acme", 20000, 100), acq(4, "acme", 59000), acq(4, "acme", 2000)]}},
        {"name": "actual usage above the reservation",
         "args": {"limits": {"acme": ACME},
                  "ops": [acq(0, "acme", 10000), settle(1, "acme", 10000, 40000), acq(1, "acme", 25000), acq(1, "acme", 20000), acq(2.5, "acme", 20000)]}},
        {"name": "rpm binds before tpm",
         "args": {"limits": {"initech": INITECH}, "max_wait": 20.0,
                  "ops": [acq(0, "initech", 10)] * 9 + [acq(3.3, "initech", 10), acq(30, "initech", 900), acq(30.5, "initech", 300)]}},
        {"name": "tpm binds before rpm",
         "args": {"limits": {"initech": INITECH}, "max_wait": 50.0,
                  "ops": [acq(0, "initech", 600), acq(0, "initech", 600), acq(0.25, "initech", 400), acq(70, "initech", 1000), acq(71, "initech", 1)]}},
    ]
