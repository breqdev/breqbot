import os
import json
import time

import websocket


class Portal:
    def __init__(self, url, id, token):
        self.id = id
        self.token = token

        self.socket = websocket.WebSocketApp(f"{url}portal")

        def on_open(ws):
            self.on_open()

        def on_message(ws, message):
            self.handle_request(message)

        def on_error(ws, error="Closed"):
            print(f"Error: {error}")

        self.socket.on_open = on_open
        self.socket.on_message = on_message
        self.socket.on_error = self.socket.on_close = on_error

        self.request_callback = lambda self, message: None

    def on_open(self):
        self.auth()
        self.set_status(2)

    def auth(self):
        message = json.dumps({
            "type": "auth",
            "id": self.id,
            "token": self.token
        })
        self.socket.send(message)

    def set_status(self, status):
        message = json.dumps({
            "type": "status",
            "status": status
        })
        self.socket.send(message)

    def handle_request(self, message):
        message = json.loads(message)

        if message["type"] == "ping":
            return
        elif message["type"] != "query":
            return

        result = self.request_callback(message["data"])

        response = json.dumps({
            "type": "response",
            "job": message["job"],
            "data": result
        })
        self.socket.send(response)

    def on_request(self):
        def decorator(func):
            self.request_callback = func
            return func
        return decorator

    def run(self):
        self.socket.run_forever()


portal = Portal(os.getenv("PORTAL_URL"), os.getenv("PORTAL_ID"), os.getenv("PORTAL_TOKEN"))


@portal.on_request()
def on_request(data):
    print(data)
    time.sleep(20)
    return {"title": data,
            "description": "Echo portal, made with <3 by breq!"}


portal.run()
