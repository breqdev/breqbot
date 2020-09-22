import os
import json

import websocket

responses = websocket.WebSocket()
responses.connect("ws://localhost:8000/things/responses")

def on_message(ws, message):
    message = json.loads(message)
    print(f"New message> {message['data']}")
    response = input("Response> ")
    response = json.dumps({"job": message["job"],
                           "thing": message["thing"],
                           "data": response})
    responses.send(response)

def on_close(ws):
    print("Closed")

def on_error(ws, error):
    print(f"Error: {error}")

def on_open(ws):
    channel = input("Channel> ")
    ws.send(channel)

ws = websocket.WebSocketApp(f"ws://localhost:8000/things/requests",
                            on_message=on_message, on_close=on_close, on_error=on_error)
ws.on_open = on_open

ws.run_forever()
