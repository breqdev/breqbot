import os

import aioredis
from quart import Quart, redirect

from api.api import api
from api.portal import portal_server


app = Quart(__name__)


@app.before_serving
async def create_redis_client():
    app.redis = await aioredis.create_redis_pool(
        os.getenv("REDIS_URL"), encoding="utf-8")


@app.route("/")
async def index():
    return redirect("https://bot.breq.dev/")


@app.route("/guild")
async def guild():
    return redirect(os.getenv("TESTING_DISCORD"))


@app.route("/bugs")
async def bugs():
    return redirect(os.getenv("BUG_REPORT"))


@app.route("/invite")
async def invite():
    return redirect(os.getenv("BOT_INVITE"))


@app.route("/github")
async def github():
    return redirect(os.getenv("GITHUB_URL"))


@app.route("/status")
async def status():
    return redirect("https://bot.breq.dev/")


app.register_blueprint(api, url_prefix="/api")
app.register_blueprint(portal_server)


if __name__ == "__main__":
    app.run()
