import os

import redis
import git
from flask import Blueprint, jsonify

api = Blueprint("api", __name__)

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"),
                                    decode_responses=True)


@api.route("/status")
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
