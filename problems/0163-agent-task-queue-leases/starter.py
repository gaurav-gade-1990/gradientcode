class TaskQueue:
    def __init__(self, clock, log, visibility_timeout=30.0, max_deliveries=3):
        # Write your code here
        pass

    def enqueue(self, task_id, priority, payload):
        pass

    def lease(self, worker):
        pass

    def heartbeat(self, lease_id):
        pass

    def ack(self, lease_id):
        pass

    def nack(self, lease_id):
        pass

    def sweep(self):
        pass

    def dead_letters(self):
        pass
