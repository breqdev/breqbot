import os
import json
import time

import websocket

class Portal:
    def __init__(self, url, portal, name=None, desc=None):
        self.portal = portal
        self.name = name or portal
        self.desc = desc or "A Breqbot Portal"

        self.requests = websocket.WebSocketApp(f"{url}/portal/requests")

        def on_open(ws):
            message = json.dumps({
                "id": self.portal,
                "name": self.name,
                "desc": self.desc
            })
            ws.send(message)
        def on_message(ws, message):
            self.handle_request(message)
        def on_error(ws, error="Closed"):
            print(f"Error: {error}")

        self.requests.on_open = on_open
        self.requests.on_message = on_message
        self.requests.on_error = self.requests.on_close = on_error

        self.responses = websocket.WebSocket()
        self.responses.connect(f"{url}/portal/responses")

        self.request_callback = lambda self, message: None

    def handle_request(self, message):
        message = json.loads(message)

        if message["type"] == "ping":
            return
        elif message["type"] != "query":
            return

        result = self.request_callback(message["data"])

        response = json.dumps({"job": message["job"],
                               "portal": message["portal"],
                               "data": result})
        self.responses.send(response)

    def on_request(self):
        def decorator(func):
            self.request_callback = func
            return func
        return decorator

    def run(self):
        self.requests.run_forever()

portal = Portal("ws://localhost:8000", "echo", "Echo", "Demo portal by Breq")

@portal.on_request()
def on_request(data):
    print(data)
    time.sleep(10)
    return {"title": data,
            "description": "Echo portal, made with <3 by breq!"}

portal.run()
