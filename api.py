import os

import redis
import git
from flask import Blueprint, jsonify, request, abort
from flask_cors import CORS, cross_origin

api = Blueprint("api", __name__)
CORS(api)

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"),
                                    decode_responses=True)


class Item:
    @property
    def redis_key(self):
        return f"items:{self.uuid}"

    @staticmethod
    def from_redis(redis, uuid):
        item = Item()
        item.uuid = uuid

        item.name = redis.hget(item.redis_key, "name")
        item.guild = int(redis.hget(item.redis_key, "guild") or "0")
        item.owner = int(redis.hget(item.redis_key, "owner") or "0")
        item.desc = redis.hget(item.redis_key, "desc")
        item.wearable = redis.hget(item.redis_key, "wearable") or "0"
        return item


@api.route("/status")
@cross_origin()
def status():
    server_count = redis_client.scard("guild:list")
    user_count = redis_client.scard("user:list")
    testing_server_size = redis_client.scard(
        f"guild:member:{os.getenv('CONFIG_GUILD')}")
    commands_run = redis_client.get("commands:total_run")

    return jsonify({
        "server_count": server_count,
        "user_count": user_count,
        "testing_server_size": testing_server_size,
        "commands_run": commands_run,
        "git_hash": git_hash
    })


@api.route("/guild")
@cross_origin()
def guild():
    guild_id = request.args.get("id")

    if not guild_id:
        return abort(404)

    website_enabled = int(redis_client.hget(f"guild:{guild_id}", "website"))
    if not website_enabled:
        return []

    guild_name = redis_client.hget(f"guild:{guild_id}", "name")
    member_count = redis_client.scard(f"guild:member:{guild_id}")

    return jsonify({
        "name": guild_name,
        "member_count": member_count
    })


@api.route("/richest")
@cross_origin()
def richest():
    guild_id = request.args.get("id")

    if not guild_id:
        return abort(404)

    website_enabled = int(redis_client.hget(f"guild:{guild_id}", "website"))
    if not website_enabled:
        return []

    balances = []

    guild_members = redis_client.smembers(f"guild:member:{guild_id}")
    for member_id in guild_members:
        balance = int(redis_client.get(
            f"currency:balance:{guild_id}:{member_id}") or 0)
        member_name = redis_client.get(f"user:name:{guild_id}:{member_id}")
        balances.append({
            "balance": balance,
            "name": member_name,
            "id": member_id
        })

    richest_members = sorted(
        balances, key=lambda a: a["balance"], reverse=True)

    return jsonify(richest_members)


@api.route("/shop")
@cross_origin()
def shop():
    guild_id = request.args.get("id")

    if not guild_id:
        return abort(404)

    website_enabled = int(redis_client.hget(f"guild:{guild_id}", "website"))
    if not website_enabled:
        return []

    shop_item_ids = redis_client.smembers(f"shop:items:{guild_id}")

    shop_items = []

    for item_id in shop_item_ids:
        price = int(redis_client.get(f"shop:prices:{guild_id}:{item_id}"))
        item = Item.from_redis(redis_client, item_id)
        item.price = price
        shop_items.append(vars(item))

    return jsonify(shop_items)


@api.route("/profile")
@cross_origin()
def profile():
    member_id = request.args.get("id")
    guild_id = request.args.get("guild_id")

    website_enabled = int(redis_client.hget(f"guild:{guild_id}", "website"))
    if not website_enabled:
        return abort(404)

    guild_name = redis_client.hget(f"guild:{guild_id}", "name")
    user_name = redis_client.get(f"user:name:{guild_id}:{member_id}")

    guild_size = redis_client.scard(f"guild:member:{guild_id}")

    if not user_name:
        return abort(404)

    user_name = redis_client.get(f"user:name:{guild_id}:{member_id}")

    profile_desc = redis_client.hget(
        f"profile:{guild_id}:{member_id}", "desc")
    profile_bg = redis_client.hget(
        f"profile:{guild_id}:{member_id}", "bg")
    profile_pfp = redis_client.hget(
        f"profile:{guild_id}:{member_id}", "pfp")

    balance = int(
        redis_client.get(f"currency:balance:{guild_id}:{member_id}") or 0)

    inventory = redis_client.hgetall(f"inventory:{guild_id}:{member_id}")

    amounts = []
    for item_name, amount in inventory.items():
        item = Item.from_redis(redis_client, item_name)
        item.quantity = amount
        if int(amount) > 0:
            amounts.append(vars(item))

    wearing = [vars(Item.from_redis(redis_client, uuid))
               for uuid
               in redis_client.smembers(f"wear:{guild_id}:{member_id}")]

    return jsonify({
        "name": user_name,
        "id": member_id,
        "guild_name": guild_name,
        "guild_id": guild_id,
        "guild_size": guild_size,
        "desc": profile_desc,
        "bg": profile_bg,
        "pfp": profile_pfp,
        "balance": balance,
        "inventory": amounts,
        "outfit": wearing
    })
