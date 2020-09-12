import os
import asyncio

import threading

import discord
from flask import Flask, render_template

app = Flask(__name__)

client = discord.Client()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/<int:id>")
def server(id):
    server = client.get_guild(id)
    print(server)
    return render_template("server.html", server=server)

def start_discord():
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(client.start(os.getenv("DISCORD_TOKEN")))
    except KeyboardInterrupt:
        loop.run_until_complete(client.logout())
        # cancel all tasks lingering
    finally:
        loop.close()

threading.Thread(target=start_discord).start()

if __name__ == "__main__":
    app.run()
