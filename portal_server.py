import os
import json

import redis
import gevent
import geventwebsocket
from flask import Blueprint

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL"), decode_responses=True)

portal_server = Blueprint("portal", __name__)


class PortalBackend():
    def __init__(self):
        self.clients = {}
        self.pubsub = redis_client.pubsub()
        self.pubsub.psubscribe("portal:*")

    def register(self, portal, client):
        channel = portal["id"]
        if channel not in self.clients:
            self.clients[channel] = set()
        self.clients[channel].add(client)

    def unregister(self, portal, client):
        channel = portal["id"]
        self.clients[channel].remove(client)

        if not self.clients[channel]:
            del self.clients[channel]

    def send(self, client, message):
        try:
            client.send(json.dumps(message))
        except geventwebsocket.exceptions.WebSocketError:
            return

    def iter_data(self):
        for message in self.pubsub.listen():
            if message["type"] in ("pmessage", "message"):
                channel = message.get("channel")
                _, portal, job = channel.split(":")

                message = message.get("data")
                message = json.loads(message)
                if message["type"] == "query":
                    yield message

    def run(self):
        for message in self.iter_data():
            if message["portal"] not in self.clients:
                continue
            for client in self.clients[message["portal"]]:
                gevent.spawn(self.send, client, message)

    def start(self):
        gevent.spawn(self.run)


portal_backend = PortalBackend()
portal_backend.start()


def auth_portal(auth_info):
    id = auth_info["id"]
    user_token = auth_info["token"]

    portal_token = redis_client.hget(f"portal:{id}", "token")
    if portal_token is None:
        return False  # Portal does not exist

    if user_token != portal_token:
        return False  # Invalid token

    return redis_client.hgetall(f"portal:{id}")


@portal_server.route("/portal")
def portal_requests(ws):
    portal_auth_info = json.loads(ws.receive())

    portal = auth_portal(portal_auth_info)
    if not portal:
        ws.close()
        return

    id = portal["id"]

    portal_backend.register(portal, ws)

    while not ws.closed:
        # Be nice to other processes
        gevent.sleep(0.1)
        # Get responses
        message = None
        with gevent.Timeout(0.1, False):
            message = ws.receive()

        if message:
            message = json.loads(message)

            if message["type"] == "response":
                job = message["job"]
                message["portal"] = id

                redis_client.publish(f"portal:{id}:{job}", json.dumps(message))

            elif message["type"] == "status":
                status = message["status"]
                redis_client.hset(f"portal:{id}", "status", status)

        # Send ping to ensure connection
        try:
            ws.send(json.dumps({"type": "ping"}))
        except geventwebsocket.exceptions.WebSocketError:
            break

    redis_client.hset(f"portal:{id}", "status", "0")
    portal_backend.unregister(portal, ws)
