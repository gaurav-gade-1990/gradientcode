class ApprovalRun:
    def __init__(self, policy, ttl, clock, execute, log):
        # Write your code here
        pass

    @property
    def state(self):
        pass

    def call(self, call_id, tool, args):
        pass

    def approve(self, call_id, approver):
        pass

    def reject(self, call_id, approver):
        pass

    def tick(self):
        pass
