import os
import json

from flask import Flask, render_template, abort, redirect
from flask_sockets import Sockets

import gevent
import geventwebsocket
import redis
import git

from extensions.economy.itemlib import Item

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha

app = Flask(__name__)
sockets = Sockets(app)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"),
                                    decode_responses=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.route("/<int:id>")
def server(id):
    website_enabled = int(redis_client.hget(f"guild:{id}", "website"))
    if not website_enabled:
        return abort(404)

    guild_name = redis_client.hget(f"guild:{id}", "name")
    guild_members = redis_client.smembers(f"guild:member:{id}")

    balances = []

    for member in guild_members:
        balance = int(redis_client.get(f"currency:balance:{id}:{member}") or 0)
        member_name = redis_client.get(f"user:name:{id}:{member}")
        balances.append((balance, member_name, member))

    richest_members = sorted(balances, key=lambda a: a[0], reverse=True)

    shop_item_ids = redis_client.smembers(f"shop:items:{id}")

    shop_items = []

    for item_id in shop_item_ids:
        price = int(redis_client.get(f"shop:prices:{id}:{item_id}"))
        name = Item.from_redis(redis_client, item_id)
        shop_items.append((price, name))

    return render_template("server.html", server=guild_name,
                           server_id=id, server_size=len(guild_members),
                           richest_members=richest_members,
                           shop_items=shop_items)


@app.route("/<int:guild_id>/<int:user_id>")
def user(guild_id, user_id):
    website_enabled = int(redis_client.hget(f"guild:{guild_id}", "website"))
    if not website_enabled:
        return abort(404)

    guild_name = redis_client.hget(f"guild:{guild_id}", "name")
    user_name = redis_client.get(f"user:name:{guild_id}:{user_id}")

    guild_size = redis_client.scard(f"guild:member:{guild_id}")

    if not user_name:
        return abort(404)

    balance = int(
        redis_client.get(f"currency:balance:{guild_id}:{user_id}") or 0)

    inventory = redis_client.hgetall(f"inventory:{guild_id}:{user_id}")

    amounts = {Item.from_redis(redis_client, item): int(amount)
               for item, amount in inventory.items() if int(amount) > 0}

    wearing = [Item.from_redis(redis_client, uuid)
               for uuid in redis_client.smembers(f"wear:{guild_id}:{user_id}")]

    profile_desc = redis_client.hget(
        f"profile:{guild_id}:{user_id}", "desc") or ""
    profile_bg = (
        redis_client.hget(f"profile:{guild_id}:{user_id}", "bg")
        or "https://breq.dev/assets/images/logo/white_wireframe.jpg")
    profile_pfp = (
        redis_client.hget(f"profile:{guild_id}:{user_id}", "pfp")
        or "https://breq.dev/assets/images/logo/white_wireframe.jpg")

    return render_template("user.html", server=guild_name, server_id=guild_id,
                           server_size=guild_size, user=user_name,
                           balance=balance, inventory=amounts.items(),
                           wearing=wearing, profile_desc=profile_desc,
                           profile_bg=profile_bg, profile_pfp=profile_pfp)


@app.route("/guild")
def guild():
    return redirect(os.getenv("TESTING_DISCORD"))


@app.route("/bugs")
def bugs():
    return redirect(os.getenv("BUG_REPORT"))


@app.route("/invite")
def invite():
    return redirect(os.getenv("BOT_INVITE"))


@app.route("/status")
def status():
    server_count = redis_client.scard("guild:list")
    user_count = redis_client.scard("user:list")
    testing_server_size = redis_client.scard(
        f"guild:member:{os.getenv('CONFIG_GUILD')}")
    commands_run = redis_client.get("commands:total_run")

    return render_template(
        "status.html",
        server_count=server_count,
        user_count=user_count,
        git_hash=git_hash[:7],
        testing_server_size=testing_server_size,
        commands_run=commands_run
    )


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


@sockets.route("/portal")
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


if __name__ == "__main__":
    app.run("0.0.0.0")
