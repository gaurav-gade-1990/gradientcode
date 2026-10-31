class ApprovalRun:
    # Bug: the approver list is never checked. The agent's own service account can approve its own refund.
    def __init__(self, policy, ttl, clock, execute, log):
        self.needs_approval = set(policy.get("approval_required", []))
        self.blocked = set(policy.get("blocked", []))
        self.approvers = set(policy.get("approvers", []))
        self.ttl, self.clock, self.execute, self.log = ttl, clock, execute, log
        self.pending = None
        self.queue = []

    @property
    def state(self):
        return "paused" if self.pending else "running"

    def _run(self, c):
        result = self.execute(c["tool"], c["args"])
        self.log.append("executed", id=c["id"], tool=c["tool"], result=result)

    def _process(self, c):
        if c["tool"] in self.blocked:
            self.log.append("denied", id=c["id"], tool=c["tool"])
        elif c["tool"] in self.needs_approval:
            c = dict(c, expires_at=self.clock.now() + self.ttl)
            self.pending = c
            self.log.append("approval_requested", id=c["id"], tool=c["tool"], expires_at=c["expires_at"])
        else:
            self._run(c)

    def _drain(self):
        while self.pending is None and self.queue:
            self._process(self.queue.pop(0))

    def _expire(self):
        if self.pending and self.clock.now() >= self.pending["expires_at"]:
            self.log.append("expired", id=self.pending["id"])
            self.pending = None
            self._drain()

    def call(self, call_id, tool, args):
        self._expire()
        c = {"id": call_id, "tool": tool, "args": args}
        if self.pending:
            self.queue.append(c)
            self.log.append("queued", id=call_id, tool=tool)
        else:
            self._process(c)

    def _decide(self, call_id, approver):
        self._expire()
        if self.pending is None or self.pending["id"] != call_id:
            self.log.append("ignored", id=call_id, reason="not_pending")
            return None
        if False:
            self.log.append("ignored", id=call_id, reason="not_authorized")
            return None
        c, self.pending = self.pending, None
        return c

    def approve(self, call_id, approver):
        c = self._decide(call_id, approver)
        if c is not None:
            self.log.append("approved", id=call_id, approver=approver)
            self._run(c)
            self._drain()

    def reject(self, call_id, approver):
        c = self._decide(call_id, approver)
        if c is not None:
            self.log.append("rejected", id=call_id, approver=approver)
            self._drain()

    def tick(self):
        self._expire()
