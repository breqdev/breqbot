import os
import json
import queue

from flask import Flask, render_template, abort
from flask_sockets import Sockets
import gevent
import redis

from cogs.items import Item

app = Flask(__name__)
sockets = Sockets(app)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.route("/server/<int:id>")
def server(id):
    website_enabled = int(redis_client.hget(f"guild:{id}", "website"))
    if not website_enabled:
        return abort(404)

    guild_name = redis_client.hget(f"guild:{id}", "name")
    guild_members = redis_client.smembers(f"guild:member:{id}")

    balances = []

    for member in guild_members:
        balance = int(redis_client.get(f"currency:balance:{id}:{member}") or 0)
        member_name = redis_client.get(f"user:name:{member}")
        balances.append((balance, member_name))

    richest_members = sorted(balances, key=lambda a: a[0], reverse=True)

    shop_item_ids = redis_client.smembers(f"shop:items:{id}")

    shop_items = []

    for item_id in shop_item_ids:
        price = int(redis_client.get(f"shop:prices:{id}:{item_id}"))
        name = redis_client.hget(f"items:{item_id}", "name")
        shop_items.append((price, name))

    return render_template("server.html", server=guild_name,
                           richest_members=richest_members,
                           shop_items=shop_items)

@app.route("/user/<int:guild_id>/<int:user_id>")
def user(guild_id, user_id):
    website_enabled = int(redis_client.hget(f"guild:{guild_id}", "website"))
    if not website_enabled:
        return abort(404)

    guild_name = redis_client.hget(f"guild:{guild_id}", "name")
    user_name = redis_client.get(f"user:name:{user_id}")

    if not user_name:
        return abort(404)

    balance = int(redis_client.get(f"currency:balance:{guild_id}:{user_id}") or 0)

    inventory = redis_client.hgetall(f"inventory:{guild_id}:{user_id}")

    amounts = {Item.from_redis(redis_client, item): int(amount)
               for item, amount in inventory.items() if int(amount) > 0}

    wearing = [Item.from_redis(redis_client, uuid) for uuid in redis_client.smembers(f"wear:{guild_id}:{user_id}")]

    return render_template("user.html", server=guild_name, user=user_name,
                           balance=balance, inventory=amounts.items(), wearing=wearing)


class ThingBackend():
    def __init__(self):
        self.clients = {}
        self.pubsub = redis_client.pubsub()
        self.pubsub.psubscribe("things:*")

    def register(self, channel, client):
        if channel not in self.clients:
            self.clients[channel] = set()
        self.clients[channel].add(client)

    def unregister(self, channel, client):
        self.clients[channel].remove(client)

        if not self.clients[channel]:
            del self.clients[channel]

    def send(self, client, thing, data, job):
        message = {"job": job, "data": data}
        try:
            client.send(json.dumps(message))
        except Exception:
            print("Send failed")
            return

        response = json.loads(client.receive())
        if response["job"] != job:
            # TODO: prevent race condition
            print("Warning: job UUID mismatch")

        message = json.dumps({"type": "response",
                              "data": response["data"]})

        print(f"Publishing {message} to things:{thing}:{job}")
        redis_client.publish(f"things:{thing}:{job}", message)


    def iter_data(self):
        for message in self.pubsub.listen():
            if message["type"] in ("pmessage", "message"):
                channel = message.get("channel")
                _, thing, job = channel.split(":")

                data = message.get("data")
                data = json.loads(data)
                if data["type"] == "query":
                    yield thing, data["data"], job

    def run(self):
        for thing, data, job in self.iter_data():
            print(thing, data, job)
            if thing not in self.clients:
                print("skipping")
                continue
            for client in self.clients[thing]:
                gevent.spawn(self.send, client, thing, data, job)

    def start(self):
        gevent.spawn(self.run)

thing_backend = ThingBackend()
thing_backend.start()

@sockets.route("/things")
def things(ws):
    channel = ws.receive()
    thing_backend.register(channel, ws)

    while not ws.closed:
        gevent.sleep(0.1)

    thing_backend.unregister(channel, ws)

if __name__ == "__main__":
    app.run("0.0.0.0")
