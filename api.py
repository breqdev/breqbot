import os

import redis
from flask import Blueprint, jsonify, request, abort
from flask_httpauth import HTTPTokenAuth

from items import Item

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

app = Blueprint("items", __name__)
auth = HTTPTokenAuth(scheme="Bearer")

api_token = os.getenv("API_TOKEN")

@auth.verify_token
def check_token(token):
    if token == api_token:
        return {"name": "Breq"}

@app.route("/api/items")
@auth.login_required
def items_list():
    items = [Item.from_redis(redis_client, uuid).dict for uuid in redis_client.smembers("items:list")]
    return jsonify(items)

@app.route("/api/items/<string:uuid>", methods=["GET", "PUT", "DELETE"])
@auth.login_required
def items(uuid):
    item = Item.from_redis(redis_client, uuid)

    if request.method == "GET":
        return jsonify(item.dict)

    if request.method == "DELETE":
        item.del_redis(redis_client)
        return ""

    if request.method == "PUT":
        item.name = request.form["name"]
        item.desc = request.form["desc"]
        item.to_redis(redis_client)
        return ""

@app.route("/api/items/by_name/<string:name>")
@auth.login_required
def items_by_name(name):
    item = Item.from_name(redis_client, name)
    return jsonify(item)

@app.route("/api/items/new", methods=["POST"])
@auth.login_required
def new_item():
    name = request.form["name"]
    desc = request.form["desc"]

    item = Item(name, desc)
    item.to_redis(redis_client)

    return jsonify(item.dict)

@app.route("/api/shop/<int:guild_id>")
@auth.login_required
def shop_index(guild_id):
    items = [Item.from_redis(redis_client, uuid).dict for uuid in redis_client.smembers(f"shop:items:{guild_id}")]
    for item in items:
        price = redis_client.get(f"shop:prices:{guild_id}:{item['uuid']}")
        item["price"] = price
    return jsonify(items)

@app.route("/api/shop/<int:guild_id>/list", methods=["POST"])
@auth.login_required
def shop_list(guild_id):
    uuid = request.form["uuid"]
    price = request.form["price"]

    redis_client.sadd(f"shop:items:{guild_id}", uuid)
    redis_client.set(f"shop:prices:{guild_id}:{uuid}", price)

    return ""

@app.route("/api/shop/<int:guild_id>/delist", methods=["POST"])
@auth.login_required
def shop_delist(guild_id):
    uuid = request.form["uuid"]

    redis_client.srem(f"shop:items:{guild_id}", uuid)
    redis_client.delete(f"shop:prices:{guild_id}:{uuid}")
