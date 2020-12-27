import json
import asyncio
import os

import aioredis
from quart import Blueprint, websocket
from quart import current_app as app


portal_server = Blueprint("portal", __name__)


async def auth_portal(auth_info):
    id = auth_info["id"]
    user_token = auth_info["token"]

    portal_token = await app.redis.hget(f"portal:{id}", "token")
    if portal_token is None:
        return False  # Portal does not exist

    if user_token != portal_token:
        return False  # Invalid token

    return await app.redis.hgetall(f"portal:{id}")


async def receive_portal(portal):
    id = portal["id"]

    while True:
        message = await websocket.receive()
        message = json.loads(message)
        if message["type"] == "response":
            job = message["job"]
            message["portal"] = id

            await app.redis.publish_json(f"portal:{id}:{job}", message)

        elif message["type"] == "status":
            status = message["status"]
            await app.redis.hset(f"portal:{id}", "status", status)


async def send_portal(portal):
    sub_conn = await aioredis.create_redis(
        os.getenv("REDIS_URL"), encoding="utf-8")
    channel = (await sub_conn.psubscribe(f"portal:{portal['id']}:*"))[0]
    async for _, message in channel.iter(decoder=json.loads):
        if message["type"] == "query":
            await websocket.send(json.dumps(message))


async def maintain_ping(portal):
    while True:
        await websocket.send(json.dumps({
            "type": "ping"
        }))
        await asyncio.sleep(1)


@portal_server.websocket("/portal")
async def portal_requests():
    global clients
    portal_auth_info = json.loads(await websocket.receive())

    portal = await auth_portal(portal_auth_info)
    if not portal:
        websocket.close()
        return

    receive = receive_portal(portal)
    send = send_portal(portal)
    ping = maintain_ping(portal)

    try:
        await asyncio.gather(receive, send, ping)
    except asyncio.CancelledError:
        await app.redis.hset(f"portal:{portal['id']}", "status", "0")
        raise
