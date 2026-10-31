import copy

from gc_runtime import ToolError


class WorkerCrash(Exception):
    """The worker process died. Nothing after this point ran."""


def order_v1(order):
    res = yield ("reserve_inventory", {"order_id": order["id"], "sku": order["sku"]})
    try:
        charge = yield ("charge_card", {"order_id": order["id"], "amount": order["amount"]})
    except ToolError as e:
        yield ("release_inventory", {"reservation": res})
        return {"status": "payment_failed", "error": str(e)}
    tracking = yield ("create_shipment", {"order_id": order["id"], "reservation": res})
    yield ("send_email", {"to": order["email"], "template": "shipped", "tracking": tracking})
    return {"status": "shipped", "charge": charge, "tracking": tracking}


def order_v2(order):
    """A later deploy: a confirmation email is sent before shipping."""
    res = yield ("reserve_inventory", {"order_id": order["id"], "sku": order["sku"]})
    try:
        charge = yield ("charge_card", {"order_id": order["id"], "amount": order["amount"]})
    except ToolError as e:
        yield ("release_inventory", {"reservation": res})
        return {"status": "payment_failed", "error": str(e)}
    yield ("send_email", {"to": order["email"], "template": "confirmed", "tracking": None})
    tracking = yield ("create_shipment", {"order_id": order["id"], "reservation": res})
    yield ("send_email", {"to": order["email"], "template": "shipped", "tracking": tracking})
    return {"status": "shipped", "charge": charge, "tracking": tracking}


def order_no_email(order):
    """A later deploy that dropped the shipping email."""
    res = yield ("reserve_inventory", {"order_id": order["id"], "sku": order["sku"]})
    try:
        charge = yield ("charge_card", {"order_id": order["id"], "amount": order["amount"]})
    except ToolError as e:
        yield ("release_inventory", {"reservation": res})
        return {"status": "payment_failed", "error": str(e)}
    tracking = yield ("create_shipment", {"order_id": order["id"], "reservation": res})
    return {"status": "shipped", "charge": charge, "tracking": tracking}


WORKFLOWS = {"order_v1": order_v1, "order_v2": order_v2, "order_no_email": order_no_email}


def run(ns, order, history, runs):
    """Run the workflow once per entry in `runs` against one durable history store.
    A run with crash_at=k dies when it is about to make its k-th live activity call."""
    store = copy.deepcopy(history)
    report = []
    for spec in runs:
        calls = []

        def act(name, fn, spec=spec, calls=calls):
            def call(**kwargs):
                if spec.get("crash_at") == len(calls) + 1:
                    raise WorkerCrash("worker died before %s" % name)
                calls.append([name, kwargs])
                return fn(**kwargs)
            return call

        def charge(order_id, amount):
            if amount > order["card_limit"]:
                raise ToolError("card_declined: insufficient funds")
            return "ch_" + order_id

        activities = {
            "reserve_inventory": act("reserve_inventory", lambda order_id, sku: "res_" + order_id),
            "charge_card": act("charge_card", charge),
            "release_inventory": act("release_inventory", lambda reservation: "released " + reservation),
            "create_shipment": act("create_shipment", lambda order_id, reservation: "1Z" + order_id),
            "send_email": act("send_email", lambda to, template, tracking: "sent " + template),
        }
        entry = {"workflow": spec["workflow"]}
        try:
            entry["result"] = ns["run_workflow"](WORKFLOWS[spec["workflow"]], order, store, activities)
            entry["outcome"] = "returned"
        except Exception as e:
            entry["result"] = None
            entry["outcome"] = type(e).__name__
        entry["activity_calls"] = calls
        report.append(entry)
    return {"runs": report, "history": store}
