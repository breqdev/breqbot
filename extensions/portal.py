import uuid
import json
import time
import asyncio

import discord
from discord.ext import commands

from .items import Item
from .utils import *

class Portal(BaseCog):
    "Interface with real-world things"

    @commands.command()
    @passfail
    async def makeportal(self, ctx, id: str, name: str = None, desc: str = None):
        "Register a new Portal"

        name = name or id
        desc = desc or "A Breqbot portal"

        token = str(uuid.uuid4())

        if self.redis.hget(f"portal:{id}", "id"):
            raise Fail(f"A portal with id {id} exists.")

        self.redis.hset(f"portal:{id}", mapping={
            "id": id,
            "name": name,
            "desc": desc,
            "owner": ctx.author.id,
            "token": token,
            "status": "0",
        })

        self.redis.sadd("portal:list", id)

        embed = discord.Embed(title=f"Portal: {name}")
        embed.description = "Thank you for registering a Breqbot portal!"

        embed.add_field(name=name, value=desc, inline=False)
        embed.add_field(name="Portal ID", value=id, inline=False)
        embed.add_field(name="Portal Token (keep this secret!)", value=f"||{token}||", inline=False)

        await ctx.author.send(embed=embed)

    @commands.command()
    @passfail
    async def delportal(self, ctx, id: str):
        "Delete an existing Portal"

        portal = self.redis.hgetall(f"portal:id")
        if not portal:
            raise Fail(f"Portal {id} does not exist.")

        if portal["owner"] != ctx.author.id:
            raise Fail(f"You do not own the portal {id}.")

        self.redis.srem("portal:list", id)
        self.redis.delete(f"portal:{id}")

    @staticmethod
    def portal_status_to_emoji(status):
        if status == 0:
            return ":x:" # Disconnected
        elif status == 1:
            return ":orange_circle:" # Connected, Not Ready
        elif status == 2:
            return ":green_circle:" # Connected, Ready

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
                "desc": self.redis.hget(f"portal:{id}", "desc"),
                "status": int(self.redis.hget(f"portal:{id}", "status"))
            }
            portals.append(portal)

        embed.description = "\n".join(f"{self.portal_status_to_emoji(portal['status'])} `{portal['id']}`: {portal['name']}, {portal['desc']}"
                                      for portal in portals)
        return embed

    @commands.command()
    @passfail
    async def portal(self, ctx, portal: str, *, command: str = ""):
        "Send a command to a connected portal"
        job_id = str(uuid.uuid4())

        pubsub = self.redis.pubsub()
        pubsub.subscribe(f"portal:{portal}:{job_id}")

        message = json.dumps({"type": "query",
                              "job": job_id,
                              "portal": portal,
                              "data": command})

        self.redis.publish(f"portal:{portal}:{job_id}", message)

        message = None
        ts = time.time()
        while message is None or json.loads(message["data"])["type"] != "response":
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0)
            if time.time() - ts > 10:
                raise Fail("Connection to Portal timed out")
            await asyncio.sleep(0.2)

        data = json.loads(message["data"])["data"]

        embed = discord.Embed()
        if "title" in data:
            embed.title = data["title"]
        if "description" in data:
            embed.description = data["description"]

        portal_name = self.redis.hget(f"portal:{portal}", "name")
        embed.set_footer(text=f"Connected to Portal: {portal_name}")
        return embed



def setup(bot):
    bot.add_cog(Portal(bot))
