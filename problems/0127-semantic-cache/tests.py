SYS = "You are the support assistant for this workspace. Answer in two sentences."
SYS_V2 = "You are the support assistant for this workspace. Answer in two sentences and link the help center."

RESET = "How do I reset my password?"
RESET_LOWER = "how do i reset my password"          # 0.926 to RESET
RESET_CAN = "How can I reset my password?"          # 0.845 to RESET
REFUND = "What is your refund policy?"
REFUND_ALT = "What's the refund policy?"            # 0.617 to REFUND: a miss
SHIP = "Do you ship to Canada?"
HOURS = "What are your support hours?"
CANCEL = "How do I cancel my subscription?"
EMAIL = "How do I change my email address?"
CFG = {"capacity": 50, "threshold": 0.8, "ttl_s": 3600.0}


def ask(t, tenant, query, system=SYS, model="support-model"):
    return {"t": t, "tenant": tenant, "query": query, "system": system, "model": model}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"config": CFG, "ops": [ask(0, "acme", RESET), ask(5, "acme", RESET_LOWER), ask(9, "acme", REFUND), ask(12, "acme", REFUND_ALT)]},
         "explanation": "The first question misses, calls the model and is stored. The lower-case paraphrase scores 0.926 against it, which is above 0.8, so it is a hit and the model is not called. The two refund phrasings only score 0.617, so the second one is a miss and a second model call."},
        {"name": "Example 2", "hidden": False,
         "args": {"config": CFG, "ops": [ask(0, "acme", RESET), ask(1, "globex", RESET), ask(2, "acme", RESET, system=SYS_V2), ask(3, "acme", RESET, model="support-model-v2")]},
         "explanation": "The same question misses three more times: globex is a different tenant, the system prompt changed (so its sha256 changed), and a different model is a different partition. Each miss is a model call. Serving acme's answer to globex would be a data leak."},
        {"name": "Example 3", "hidden": False,
         "args": {"config": {"capacity": 2, "threshold": 0.8, "ttl_s": 600.0},
                  "ops": [ask(0, "acme", RESET), ask(10, "acme", REFUND), ask(20, "acme", RESET_CAN), ask(30, "acme", SHIP), ask(601, "acme", RESET_LOWER)]},
         "explanation": "The hit at t=20 makes the password entry the most recently used, so when SHIP needs room at t=30, the refund entry is evicted (LRU, not oldest first). At t=601 the password entry is 601 s old, more than the 600 s TTL. It is purged even though it was hit recently, and the question misses."},
        {"name": "ttl counts from store, not from the last hit",
         "args": {"config": {"capacity": 10, "threshold": 0.8, "ttl_s": 600.0},
                  "ops": [ask(0, "acme", RESET), ask(300, "acme", RESET), ask(550, "acme", RESET_LOWER), ask(599, "acme", RESET_CAN), ask(600, "acme", RESET)]}},
        {"name": "capacity is shared across tenants",
         "args": {"config": {"capacity": 3, "threshold": 0.8, "ttl_s": 3600.0},
                  "ops": [ask(0, "acme", RESET), ask(1, "globex", RESET), ask(2, "initech", HOURS), ask(3, "acme", RESET_LOWER),
                          ask(4, "globex", SHIP), ask(5, "initech", HOURS), ask(6, "globex", RESET), ask(7, "acme", CANCEL)]}},
        {"name": "system prompt rollout",
         "args": {"config": CFG, "ops": [ask(0, "acme", RESET), ask(1, "acme", REFUND), ask(2, "acme", RESET_LOWER, system=SYS_V2),
                                          ask(3, "acme", RESET_LOWER), ask(4, "acme", REFUND, system=SYS_V2), ask(5, "acme", RESET_CAN, system=SYS_V2)]}},
        {"name": "warmed entries, overwrite and tie on equal scores",
         "args": {"config": CFG, "ops": [
             {"t": 0, "warm": True, "tenant": "acme", "query": "reset my password", "system": SYS, "model": "support-model", "answer": "faq-v1"},
             {"t": 1, "warm": True, "tenant": "acme", "query": "my password reset", "system": SYS, "model": "support-model", "answer": "faq-v2"},
             ask(2, "acme", "password reset my"),
             {"t": 3, "warm": True, "tenant": "acme", "query": "reset my password", "system": SYS, "model": "support-model", "answer": "faq-v3"},
             ask(4, "acme", "password reset my"),
             ask(5, "globex", "reset my password")]}},
        {"name": "lru with many hits",
         "args": {"config": {"capacity": 3, "threshold": 0.8, "ttl_s": 3600.0},
                  "ops": [ask(0, "acme", RESET), ask(1, "acme", REFUND), ask(2, "acme", SHIP), ask(3, "acme", RESET_LOWER), ask(4, "acme", REFUND),
                          ask(5, "acme", HOURS), ask(6, "acme", SHIP), ask(7, "acme", CANCEL), ask(8, "acme", RESET_CAN), ask(9, "acme", EMAIL)]}},
        {"name": "mass expiry logs oldest first",
         "args": {"config": {"capacity": 10, "threshold": 0.8, "ttl_s": 100.0},
                  "ops": [ask(0, "globex", SHIP), ask(10, "acme", RESET), ask(20, "initech", HOURS), ask(95, "acme", CANCEL), ask(130, "acme", EMAIL),
                          ask(190, "acme", CANCEL), ask(200, "acme", CANCEL)]}},
    ]
