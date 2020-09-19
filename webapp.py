import os
import queue

from flask import Flask, render_template

import redis

app = Flask(__name__)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/server/<int:id>")
def server(id):
    guild_name = redis_client.get(f"guild:name:{id}")
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


if __name__ == "__main__":
    app.run()
