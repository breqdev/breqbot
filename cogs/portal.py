import uuid
import json
import asyncio

import discord
from discord.ext import commands

from .items import Item
from .breqcog import *

class Portal(Breqcog):
    "Interface with real-world things"

    @commands.command()
    @passfail
    async def portal(self, ctx, portal: str, *, command: str = ""):
        "Send a command to a connected portal"
        job_id = str(uuid.uuid4())

        pubsub = self.redis.pubsub()
        pubsub.subscribe(f"portal:{portal}:{job_id}")

        message = json.dumps({"portal": portal,
                              "job": job_id,
                              "data": command})

        self.redis.publish("portal:query", message)

        message = None
        while message is None or json.loads(message["data"])["type"] != "response":
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0)
            await asyncio.sleep(0.5)

        data = json.loads(message["data"])

        embed = discord.Embed()
        if "title" in data:
            embed.title = data["title"]
        if "description" in data:
            embed.description = data["description"]

        portal_name = self.redis.hget(f"portal:{portal}", "name")
        embed.set_footer(text=f"Connected to Portal: {portal_name}")
        return embed

    @commands.command()
    @passfail
    async def portals(self, ctx):
        "List connected portals"
        portal_ids = self.redis.smembers("portal:list")

        embed = discord.Embed(title="Connected Portals")

        portals = []
        for id in portal_ids:
            portal = {
                "id": self.redis.hget(f"portal:{id}", "id"),
                "name": self.redis.hget(f"portal:{id}", "name"),
                "desc": self.redis.hget(f"portal:{id}", "desc")
            }
            portals.append(portal)

        embed.description = "\n".join(f"• `{portal['id']}`: {portal['name']}, {portal['desc']}"
                                      for portal in portals)
        return embed



def setup(bot):
    bot.add_cog(Portal(bot))
