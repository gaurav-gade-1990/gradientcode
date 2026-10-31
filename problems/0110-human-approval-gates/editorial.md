## Approach

There are two states, one pending slot and one FIFO queue. Every entry point first applies the *lazy* expiry, since nothing wakes up on its own in a request-driven service:

```python
def _expire(self):
    if self.pending and self.clock.now() >= self.pending["expires_at"]:
        self.log.append("expired", id=self.pending["id"])
        self.pending = None
        self._drain()

def _process(self, c):                  # one policy path for new and queued calls
    if c["tool"] in self.blocked:         log denied
    elif c["tool"] in self.needs_approval: set pending, log approval_requested
    else:                                 execute, log executed

def _drain(self):
    while self.pending is None and self.queue:
        self._process(self.queue.pop(0))
```

`approve` and `reject` check that the id is the call pending *right now* and that the approver is authorized. Only then do they clear the slot, execute or discard the call, and drain. Since a decided call is no longer pending, a second click is ignored for free.

## Common mistakes

- **No expiry.** An approval request from last week gets clicked by someone who has lost the context. Approvals must be fresh.
- **`>` at the boundary.** The deadline is exclusive for approvals: at `now == expires_at` the request is gone.
- **Draining around the policy.** Executing queued calls directly lets a refund queued during a pause skip its gate. This is the agent version of a TOCTOU bug.
- **Approving from a table of all requests.** A double-click or a retried Slack webhook executes the refund twice.
- **No approver check.** The agent's own service account can approve its own actions.

## Production notes

- LangGraph implements this with `interrupt()` plus a checkpointer, the OpenAI Agents SDK has tool approval hooks, and MCP clients ask the user before running a tool. In each case the run's state must be persisted, because the human answers minutes or hours later, often on a different server (problem 111, durable-workflow-replay).
- Deliver approvals through signed, idempotent callbacks (problem 167, signed-webhook-delivery). Treat a decision as an event keyed by call id, not as a command.
- Show the approver the exact arguments that will run, and hash them into the approval. If the agent changes the amount, the approval no longer matches.
- Feed the policy from a real policy engine (problem 160) and log the full trail to a tamper-evident audit log (problem 161).
