def V(agent, answer, confidence):
    return {"agent": agent, "answer": answer, "confidence": confidence}


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"votes": [
            V("gpt-router", "Billing", 0.75), V("claude-triage", "billing.", 0.5), V("rules-v2", "Shipping", 0.875)], "quorum": 2},
         "explanation": "\"Billing\" and \"billing.\" normalize to the same answer: score 0.75 + 0.5 = 1.25, which beats shipping's 0.875."},
        {"name": "Example 2", "hidden": False, "args": {"votes": [
            V("a", "fraud", 0.5), V("b", "billing", 0.25), V("c", "billing", 0.25), V("d", None, 0.9)], "quorum": 3},
         "explanation": "fraud and billing both score 0.5. billing has 2 votes to fraud's 1, so the tie-break picks billing. The abstaining agent d does not count."},
        {"name": "Example 3", "hidden": False, "args": {"votes": [V("a", "refund", 0.9), V("b", "  ", 0.8), V("c", None, 0.7)], "quorum": 2},
         "explanation": "Only one real vote, and the quorum is 2, so the result is no_quorum. The scores are still reported."},
        {"name": "empty", "args": {"votes": [], "quorum": 1}},
        {"name": "whitespace and punctuation", "args": {"votes": [
            V("a", "Account   Takeover!", 0.5), V("b", "account takeover", 0.5), V("c", "account\ttakeover?!", 0.25), V("d", "phishing", 0.875)], "quorum": 3}},
        {"name": "full tie goes to first appearance", "args": {"votes": [
            V("a", "shipping", 0.5), V("b", "billing", 0.5), V("c", "Billing", 0.0), V("d", "Shipping", 0.0)], "quorum": 1}},
        {"name": "alphabetical would differ", "args": {"votes": [V("x", "Warranty", 0.625), V("y", "account", 0.625)], "quorum": 2}},
        {"name": "weights beat headcount", "args": {"votes": [
            V("a", "spam", 0.25), V("b", "spam", 0.25), V("c", "spam", 0.25), V("d", "legal hold", 1.0)], "quorum": 2}},
        {"name": "uncalibrated confidence clamped", "args": {"votes": [
            V("new-model", "billing", 3.5), V("a", "fraud", 0.75), V("b", "fraud", 0.5), V("c", "billing", -2.0)], "quorum": 2}},
        {"name": "float sums tie after rounding", "args": {"votes": [
            V("a", "billing", 0.1), V("b", "billing", 0.2), V("c", "fraud", 0.3), V("d", "fraud", 0.0)], "quorum": 2}},
        {"name": "quorum exactly met", "args": {"votes": [V("a", None, 1.0), V("b", "Refund.", 0.4), V("c", "refund", 0.3), V("d", "...", 0.9)], "quorum": 2}},
    ]
