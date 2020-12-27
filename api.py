import os

import git
from quart import Blueprint, jsonify, request, abort
from quart import current_app as app
from quart_cors import cors

api = Blueprint("api", __name__)
api = cors(api)

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha


class Item:
    @property
    def redis_key(self):
        return f"items:{self.uuid}"

    @staticmethod
    async def from_redis(redis, uuid):
        item = Item()
        item.uuid = uuid

        item.name = await redis.hget(item.redis_key, "name")
        item.guild = int(await redis.hget(item.redis_key, "guild") or "0")
        item.owner = int(await redis.hget(item.redis_key, "owner") or "0")
        item.desc = await redis.hget(item.redis_key, "desc")
        item.wearable = await redis.hget(item.redis_key, "wearable") or "0"
        return item


@api.route("/status")
async def status():
    server_count = await app.redis.scard("guild:list")
    user_count = await app.redis.scard("user:list")
    testing_server_size = await app.redis.scard(
        f"guild:member:{os.getenv('CONFIG_GUILD')}")
    commands_run = await app.redis.get("commands:total_run")

    return jsonify({
        "server_count": server_count,
        "user_count": user_count,
        "testing_server_size": testing_server_size,
        "commands_run": commands_run,
        "git_hash": git_hash
    })


@api.route("/guild")
async def guild():
    guild_id = request.args.get("id")

    if not guild_id:
        return abort(404)

    website_enabled = int(await app.redis.hget(
        f"guild:{guild_id}", "website"))
    if not website_enabled:
        return []

    guild_name = await app.redis.hget(f"guild:{guild_id}", "name")
    member_count = await app.redis.scard(f"guild:member:{guild_id}")

    return jsonify({
        "name": guild_name,
        "member_count": member_count
    })


@api.route("/richest")
async def richest():
    guild_id = request.args.get("id")

    if not guild_id:
        return abort(404)

    website_enabled = int(await app.redis.hget(
        f"guild:{guild_id}", "website"))
    if not website_enabled:
        return []

    balances = []

    guild_members = await app.redis.smembers(f"guild:member:{guild_id}")
    for member_id in guild_members:
        balance = int(await app.redis.get(
            f"currency:balance:{guild_id}:{member_id}") or 0)
        member_name = await app.redis.get(
            f"user:name:{guild_id}:{member_id}")
        balances.append({
            "balance": balance,
            "name": member_name,
            "id": member_id
        })

    richest_members = sorted(
        balances, key=lambda a: a["balance"], reverse=True)

    return jsonify(richest_members)


@api.route("/shop")
async def shop():
    guild_id = request.args.get("id")

    if not guild_id:
        return abort(404)

    website_enabled = int(await app.redis.hget(
        f"guild:{guild_id}", "website"))
    if not website_enabled:
        return []

    shop_item_ids = await app.redis.smembers(f"shop:items:{guild_id}")

    shop_items = []

    for item_id in shop_item_ids:
        price = int(await app.redis.get(
            f"shop:prices:{guild_id}:{item_id}"))
        item = await Item.from_redis(app.redis, item_id)
        item.price = price
        shop_items.append(vars(item))

    return jsonify(shop_items)


@api.route("/profile")
async def profile():
    member_id = request.args.get("id")
    guild_id = request.args.get("guild_id")

    website_enabled = int(await app.redis.hget(
        f"guild:{guild_id}", "website"))
    if not website_enabled:
        return abort(404)

    guild_name = await app.redis.hget(f"guild:{guild_id}", "name")
    user_name = await app.redis.get(f"user:name:{guild_id}:{member_id}")

    guild_size = await app.redis.scard(f"guild:member:{guild_id}")

    if not user_name:
        return abort(404)

    user_name = await app.redis.get(f"user:name:{guild_id}:{member_id}")

    profile_desc = await app.redis.hget(
        f"profile:{guild_id}:{member_id}", "desc")
    profile_bg = await app.redis.hget(
        f"profile:{guild_id}:{member_id}", "bg")
    profile_pfp = await app.redis.hget(
        f"profile:{guild_id}:{member_id}", "pfp")

    balance = int(
        await app.redis.get(
            f"currency:balance:{guild_id}:{member_id}") or 0)

    inventory = await app.redis.hgetall(f"inventory:{guild_id}:{member_id}")

    amounts = []
    for item_name, amount in inventory.items():
        item = await Item.from_redis(app.redis, item_name)
        item.quantity = amount
        if int(amount) > 0:
            amounts.append(vars(item))

    wearing = [vars(await Item.from_redis(app.redis, uuid))
               for uuid
               in await app.redis.smembers(f"wear:{guild_id}:{member_id}")]

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


@api.route("/card")
async def card():
    member_id = request.args.get("id")
    guild_id = request.args.get("guild_id")

    defaults = {
        "bio": "",
        "background": "https://breq.dev/assets/images/pansexual.png",
        "template": "light-profile"
    }

    params = {
        field:
            (await app.redis.hget(f"profile:{guild_id}:{member_id}", field)
             or defaults[field])
        for field in defaults
    }

    params["name"] = await app.redis.get(
        f"user:name:{guild_id}:{member_id}")
    params["avatar"] = await app.redis.hget(
        f"profile:{guild_id}:{member_id}", "pfp")

    return jsonify(params)
