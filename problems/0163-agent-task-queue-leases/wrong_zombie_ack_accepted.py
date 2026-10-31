class TaskQueue:
    def __init__(self, clock, log, visibility_timeout=30.0, max_deliveries=3):
        self.clock, self.log = clock, log
        self.vt, self.max = visibility_timeout, max_deliveries
        self.tasks = {}   # id -> record
        self.seq = 0
        self.dlq = []

    # ------------------------------------------------------------ helpers
    def _sweep(self):
        now = self.clock.now()
        due = [t for t in self.tasks.values() if t["state"] == "leased" and t["deadline"] <= now]
        for t in sorted(due, key=lambda t: (t["deadline"], t["seq"])):
            self.log.append("expired", task=t["id"], worker=t["worker"], delivery=t["deliveries"])
            self._release(t)

    def _release(self, t):
        t["lease"] = t["worker"] = t["deadline"] = None
        if t["deliveries"] >= self.max:
            t["state"] = "dead"
            self.dlq.append(t["id"])
            self.log.append("dead_lettered", task=t["id"], reason="max_deliveries")
        else:
            t["state"] = "ready"

    def _current(self, lease_id):
        task_id = lease_id.rsplit("#", 1)[0]
        t = self.tasks.get(task_id)
        if t is not None and t["state"] == "leased" and t["lease"] == lease_id:
            return t
        return None

    # ------------------------------------------------------------ API
    def enqueue(self, task_id, priority, payload):
        self._sweep()
        if task_id in self.tasks:
            return False
        self.seq += 1
        self.tasks[task_id] = {"id": task_id, "priority": priority, "payload": payload, "seq": self.seq, "state": "ready",
                               "deliveries": 0, "lease": None, "worker": None, "deadline": None}
        self.log.append("enqueued", task=task_id, priority=priority)
        return True

    def lease(self, worker):
        self._sweep()
        ready = [t for t in self.tasks.values() if t["state"] == "ready"]
        if not ready:
            return None
        t = min(ready, key=lambda t: (t["priority"], t["seq"]))
        t["deliveries"] += 1
        t["state"], t["worker"] = "leased", worker
        t["lease"] = "%s#%d" % (t["id"], t["deliveries"])
        t["deadline"] = self.clock.now() + self.vt
        self.log.append("leased", task=t["id"], worker=worker, delivery=t["deliveries"], until=t["deadline"])
        return {"task": t["id"], "lease_id": t["lease"], "delivery": t["deliveries"], "payload": t["payload"]}

    def heartbeat(self, lease_id):
        self._sweep()
        t = self._current(lease_id)
        if t is None:
            return False
        t["deadline"] = self.clock.now() + self.vt
        self.log.append("extended", task=t["id"], until=t["deadline"])
        return True

    def ack(self, lease_id):
        self._sweep()
        t = self.tasks.get(lease_id.rsplit("#", 1)[0])
        if t is not None and t["state"] == "done":
            return "duplicate"
        if t is None or t["deliveries"] == 0:
            return "stale"
        self.log.append("acked", task=t["id"], worker=t["worker"])
        t["state"], t["lease"], t["worker"], t["deadline"] = "done", None, None, None
        return "acked"

    def nack(self, lease_id):
        self._sweep()
        t = self._current(lease_id)
        if t is None:
            return "stale"
        self.log.append("nacked", task=t["id"], worker=t["worker"])
        self._release(t)
        return "dead_lettered" if t["state"] == "dead" else "requeued"

    def sweep(self):
        self._sweep()

    def dead_letters(self):
        return list(self.dlq)
