import hashlib
import hmac
import json


def sign(secret, timestamp, body):
    # Write your code here
    pass


def verify(secret, header, body, now, tolerance=300):
    pass


class Receiver:
    def __init__(self, secret, tolerance=300):
        self.processed = []

    def handle(self, header, body, now):
        pass


def deliver(event, secret, send, clock, schedule):
    pass
