POLICY = {"approval_required": ["issue_refund", "delete_account"], "blocked": ["wire_transfer"], "approvers": ["lead.maria", "lead.omar"]}


def call(t, id, tool, **args):
    return {"t": t, "op": "call", "id": id, "tool": tool, "args": args}


def approve(t, id, by):
    return {"t": t, "op": "approve", "id": id, "by": by}


def reject(t, id, by):
    return {"t": t, "op": "reject", "id": id, "by": by}


def tick(t):
    return {"t": t, "op": "tick"}


REFUND = call(10, "c2", "issue_refund", order_id="A-1182", amount=84.0)


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"policy": POLICY, "ttl": 300, "ops": [
            call(0, "c1", "get_order", order_id="A-1182"), REFUND, call(20, "c3", "send_email", to="dana@example.com"),
            approve(65, "c2", "lead.maria")]},
         "explanation": "get_order runs at once. The refund pauses the run until t=310. The email arrives while paused and is queued. Maria approves at t=65: the refund executes, then the queued email runs."},
        {"name": "Example 2", "hidden": False, "args": {"policy": POLICY, "ttl": 300, "ops": [
            REFUND, approve(30, "c2", "agent.bot"), reject(40, "c2", "lead.omar"), call(50, "c4", "wire_transfer", amount=5000)]},
         "explanation": "agent.bot isn't an approver, so its approval is ignored and the run stays paused. Omar rejects: nothing executes. The wire transfer is blocked by policy."},
        {"name": "Example 3", "hidden": False, "args": {"policy": POLICY, "ttl": 60, "ops": [REFUND, tick(69), tick(70), approve(71, "c2", "lead.maria")]},
         "explanation": "The approval expires at 10 + 60 = 70. The tick at t=70 notices it (now >= expires_at). The late approval is ignored, so the refund never runs."},
        {"name": "approve exactly at expiry", "args": {"policy": POLICY, "ttl": 60, "ops": [REFUND, approve(70, "c2", "lead.maria")]}},
        {"name": "approve just before expiry", "args": {"policy": POLICY, "ttl": 60, "ops": [REFUND, approve(69.5, "c2", "lead.maria")]}},
        {"name": "duplicate approve does not re-execute", "args": {"policy": POLICY, "ttl": 300, "ops": [
            REFUND, approve(20, "c2", "lead.maria"), approve(21, "c2", "lead.omar"), call(30, "c5", "get_order", order_id="A-1")]}},
        {"name": "queued risky call pauses again", "args": {"policy": POLICY, "ttl": 100, "ops": [
            REFUND, call(11, "c3", "delete_account", user="u_77"), call(12, "c4", "get_order", order_id="A-9"),
            approve(20, "c2", "lead.omar"), approve(30, "c3", "lead.maria")]}},
        {"name": "queued blocked call denied on drain", "args": {"policy": POLICY, "ttl": 100, "ops": [
            REFUND, call(11, "c3", "wire_transfer", amount=9000), call(12, "c4", "send_email", to="ops@example.com"), reject(15, "c2", "lead.omar")]}},
        {"name": "expiry noticed by next call drains queue", "args": {"policy": POLICY, "ttl": 30, "ops": [
            REFUND, call(15, "c3", "send_email", to="dana@example.com"), call(50, "c4", "get_order", order_id="A-1182")]}},
        {"name": "approve wrong id", "args": {"policy": POLICY, "ttl": 300, "ops": [REFUND, approve(12, "c9", "lead.maria"), approve(13, "c2", "lead.maria")]}},
        {"name": "outsider approving the wrong id is not_pending", "args": {"policy": POLICY, "ttl": 300, "ops": [
            REFUND, approve(12, "c9", "agent.bot"), approve(13, "c2", "lead.maria")]}},
        {"name": "tool in both lists is denied", "args": {"policy": dict(POLICY, blocked=["wire_transfer", "delete_account"]), "ttl": 300, "ops": [
            call(0, "c7", "delete_account", user="u_77"), call(5, "c8", "get_order", order_id="A-1")]}},
        {"name": "approve when nothing pending", "args": {"policy": POLICY, "ttl": 300, "ops": [call(0, "c1", "get_order", order_id="A-1"), approve(5, "c1", "lead.maria")]}},
        {"name": "expired then re-requested", "args": {"policy": POLICY, "ttl": 20, "ops": [
            REFUND, tick(40), call(41, "c6", "issue_refund", order_id="A-1182", amount=84.0), approve(42, "c2", "lead.maria"), approve(43, "c6", "lead.maria")]}},
    ]
