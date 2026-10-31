class AuthClient:
    def __init__(self, loop, token, refresh, send):
        self.loop = loop
        self.token = token
        self.refresh = refresh
        self.send = send

    def call(self, request):
        # Write your code here
        pass
