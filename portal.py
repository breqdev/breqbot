import os
import json
import time

import socketio


sio = socketio.Client()

@sio.on("connect")
def on_connect():
    print("Connected")
    time.sleep(1)
    sio.emit("portal_register",
                     {"portal": "echo", "name": "Echo", "desc": "A Breqbot Portal"})
    print("Registered!")

@sio.on("portal_query")
def on_query(sid, data):
    print("Query received")
    job = data["job"]
    result = {
        "title": "Hi",
        "description": "Hello"
    }
    result = json.dumps(result)
    sio.emit("portal_completed", {"job": job, "result": result})
    print("Response sent")

def run(url):
    sio.connect(url)
    sio.wait()

run("http://localhost:5000")
