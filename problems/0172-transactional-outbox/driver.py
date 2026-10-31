import copy


class Crash(BaseException):
    """The process died. BaseException, so `except Exception` in user code does not swallow it."""


class World:
    """Counts step boundaries and kills the process just before boundary number `crash_at`."""

    def __init__(self, crash_at=None):
        self.crash_at = crash_at
        self.steps = 0
        self.dead = False
        self.crashed_before = None
        self.context = ""
        self.generation = 0

    def step(self, label):
        if self.dead:
            raise Crash("process is dead")
        i = self.steps
        self.steps += 1
        if i == self.crash_at:
            self.dead = True
            self.crashed_before = "%s: before %s" % (self.context, label)
            raise Crash(label)

    def restart(self):
        self.dead = False
        self.crash_at = None
        self.generation += 1


class Txn:
    def __init__(self, db):
        self._db, self._gen = db, db.world.generation
        self._writes = {}
        self._open = True

    def _check(self):
        if not self._open:
            raise RuntimeError("transaction already finished")
        if self._gen != self._db.world.generation:
            raise RuntimeError("transaction from before the restart")

    def get(self, table, key):
        self._check()
        if (table, key) in self._writes:
            return copy.deepcopy(self._writes[(table, key)])
        return copy.deepcopy(self._db.tables.get(table, {}).get(key))

    def scan(self, table):
        self._check()
        merged = dict(self._db.tables.get(table, {}))
        for (t, k), v in self._writes.items():
            if t == table:
                merged[k] = v
        return [(k, copy.deepcopy(merged[k])) for k in sorted(merged)]

    def put(self, table, key, value):
        self._check()
        self._db.world.step("%s.put %s/%s" % (self._db.name, table, key))
        self._writes[(table, key)] = copy.deepcopy(value)

    def commit(self):
        self._check()
        self._db.world.step("%s.commit" % self._db.name)
        for (t, k), v in self._writes.items():
            self._db.tables.setdefault(t, {})[k] = v
        self._open = False

    def rollback(self):
        self._open = False


class FakeDB:
    def __init__(self, world, name):
        self.world, self.name = world, name
        self.tables = {}          # committed, durable state

    def begin(self):
        self.world.step("%s.begin" % self.name)
        return Txn(self)


class Broker:
    def __init__(self, world):
        self.world = world
        self.log = []             # (topic, message), durable

    def publish(self, topic, message):
        self.world.step("broker.publish %s" % message.get("event_id"))
        self.log.append((topic, copy.deepcopy(message)))


def _scenario(ns, world, orders, redeliver):
    """Run the system once with at most one crash. After a crash, restart from durable state only:
    the client retries the order it was sending, the relay starts over, and the consumer is rebuilt
    and resumes at the broker's committed offset (messages are acked after handle() returns)."""
    db, store, broker = FakeDB(world, "orders_db"), FakeDB(world, "consumer_db"), Broker(world)
    prog = {"orders": 0, "relay": False, "offset": 0, "redelivered": set()}
    clean = {"responses": [], "published": None, "consumer": []}
    while True:
        try:
            while prog["orders"] < len(orders):
                order = orders[prog["orders"]]
                world.context = "place_order %s" % order["order_id"]
                r = ns["place_order"](db, copy.deepcopy(order))
                world.step("response to client")
                clean["responses"].append(r)
                prog["orders"] += 1
            if not prog["relay"]:
                world.context = "relay"
                n = ns["relay"](db, broker)
                world.step("relay returns")
                clean["published"] = n
                prog["relay"] = True
            consumer = ns["RevenueConsumer"](store)
            while prog["offset"] < len(broker.log):
                off = prog["offset"]
                topic, msg = broker.log[off]
                world.context = "consumer offset %d (%s)" % (off, msg.get("event_id"))
                r = consumer.handle(copy.deepcopy(msg))
                clean["consumer"].append(r)
                if off in redeliver and off not in prog["redelivered"]:
                    world.step("ack lost for offset %d" % off)
                    prog["redelivered"].add(off)
                    continue
                world.step("ack offset %d" % off)
                prog["offset"] += 1
            if world.dead:
                raise RuntimeError("your code caught the simulated crash; let it propagate")
            return db, store, broker, clean
        except Crash:
            if world.crash_at is None and not world.dead:
                raise
            world.restart()


def _violations(orders, db, store, broker):
    expected = {}
    for o in orders:
        expected.setdefault(o["order_id"], o)
    want_rev = {}
    for o in expected.values():
        want_rev[o["tenant"]] = want_rev.get(o["tenant"], 0) + o["total_cents"]
    v = set()
    stored = db.tables.get("orders", {})
    if set(stored) != set(expected):
        v.add("order_lost")
    outbox = db.tables.get("outbox", {})
    ids = [row.get("event_id") for _, row in sorted(outbox.items())]
    if len(ids) != len(set(ids)):
        v.add("duplicate_outbox_row")
    if set(ids) != {"evt_" + k for k in expected}:
        v.add("event_missing_from_outbox")
    if any(not row.get("published") for row in outbox.values()):
        v.add("outbox_not_drained")
    sent = [m.get("event_id") for _, m in broker.log]
    if not set(ids) <= set(sent):
        v.add("event_never_published")
    if not set(sent) <= set(ids):
        v.add("phantom_event")
    seen, firsts = set(), []
    for m in sent:
        if m not in seen:
            seen.add(m)
            firsts.append(m)
    known = set(ids)
    if [m for m in firsts if m in known] != [i for i in ids if i in seen]:
        v.add("published_out_of_order")
    rev = store.tables.get("revenue", {})
    for t in set(want_rev) | set(rev):
        got, want = rev.get(t, 0), want_rev.get(t, 0)
        if got > want:
            v.add("revenue_double_counted")
        elif got < want:
            v.add("revenue_missing")
    return sorted(v)


def run(ns, orders, redeliver=()):
    redeliver = set(redeliver)
    world = World()
    db, store, broker, clean = _scenario(ns, world, orders, redeliver)
    total = world.steps
    out = {"clean": {
        "responses": clean["responses"],
        "published": clean["published"],
        "consumer": clean["consumer"],
        "broker_log": [[topic, m.get("seq"), m.get("event_id")] for topic, m in broker.log],
        "outbox": [[k, row.get("event_id"), row.get("published")] for k, row in sorted(db.tables.get("outbox", {}).items())],
        "revenue": dict(sorted(store.tables.get("revenue", {}).items())),
        "violations": _violations(orders, db, store, broker),
    }}
    # Kill the process before every step boundary of the clean run, recover, and check the invariants.
    union, first = set(), None
    for k in range(total):
        w = World(crash_at=k)
        db, store, broker, _ = _scenario(ns, w, orders, redeliver)
        v = _violations(orders, db, store, broker)
        if v:
            union |= set(v)
            if first is None:
                first = {"crashed": w.crashed_before, "violations": v}
    out["crash_recovery"] = {"violations": sorted(union), "first_violation": first}
    return out
