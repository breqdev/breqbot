import uuid
import json
import time
import asyncio

import discord
from discord.ext import commands

from ..base import BaseCog, UserError


class Portal(BaseCog):
    "Interface with real-world things"

    async def get_portal(self, id, user_id=None):
        portal = self.redis.hgetall(f"portal:{id}")
        if not portal:
            raise UserError(f"Portal {id} does not exist.")

        if user_id and int(portal["owner"]) != user_id:
            raise UserError(f"You do not own the portal {id}.")

        return portal

    async def set_portal(self, portal):
        id = portal["id"]
        self.redis.hset(f"portal:{id}", mapping=portal)

        self.redis.sadd("portal:list", id)
        self.redis.sadd(f"portal:from_owner:{portal['owner']}", id)

    # WORK WITH THE UNDERLYING PORTAL OBJECTS

    @commands.command()
    async def makeportal(self, ctx):
        "Register a new Portal"

        id = str(uuid.uuid4())
        token = str(uuid.uuid4())

        portal = {
            "id": id,
            "name": "A Breqbot Portal",
            "desc": "Example Description",
            "owner": ctx.author.id,
            "token": token,
            "status": "0",
        }
        await self.set_portal(portal)

        embed = discord.Embed(title="Portal")
        embed.description = "Thank you for registering a Breqbot portal!"

        embed.add_field(name="Portal ID", value=id, inline=False)
        embed.add_field(name="Portal Token (keep this secret!)",
                        value=f"||{token}||", inline=False)

        await ctx.author.send(embed=embed)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def modifyportal(self, ctx, id: str, field: str, *, value: str):
        "Modify an existing Portal"

        portal = await self.get_portal(id, ctx.author.id)

        if field == "name":
            portal["name"] = value
        elif field == "desc":
            portal["desc"] = value
        else:
            raise UserError(f"Invalid field {field}")

        await self.set_portal(portal)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def delportal(self, ctx, id: str):
        "Delete an existing Portal"

        await self.get_portal(id, ctx.author.id)

        self.redis.srem("portal:list", id)
        self.redis.srem(f"portal:from_owner:{ctx.author.id}", id)
        self.redis.delete(f"portal:{id}")

        guild_ids = self.redis.smembers(f"portal:guilds:{id}")
        for gid in guild_ids:
            await self.remove_portal(id, gid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def myportals(self, ctx):
        "List your registered Portals"

        portal_ids = self.redis.smembers(f"portal:from_owner:{ctx.author.id}")

        embed = discord.Embed(title=f"{ctx.author.display_name}'s Portals")

        portals = []
        for id in portal_ids:
            portal = await self.get_portal(id)
            portals.append(portal)

        embed.description = "\n".join(
            f"{self.portal_status_to_emoji(portal['status'])} "
            f"`{portal['id']}`: {portal['name']}, {portal['desc']}"
            for portal in portals)

        await ctx.send(embed=embed)

    # MAKE THE PORTAL OBJECTS AVAILABLE USING ALIASES IN GUILDS

    @commands.command()
    async def portalguilds(self, ctx, id: str):
        "List the servers that a Portal is connected to"

        await self.get_portal(id, ctx.author.id)

        guild_ids = self.redis.smembers(f"portal:guilds:{id}")

        embed = discord.Embed(title="Connected Guilds")

        guilds = []
        for id in guild_ids:
            guild = self.bot.get_guild(int(id))
            guilds.append(guild)

        embed.description = "\n".join(
            f"`{guild.id}`: {guild.name}" for guild in guilds)

        await ctx.send(embed=embed)

    def check_name(self, name, guild_id):
        existing_id = self.redis.get(f"portal:from_name:{guild_id}:{name}")
        if not existing_id:
            return True

        if not self.redis.exists(f"portal:{existing_id}"):
            self.redis.delete(f"portal:from_name:{guild_id}:{name}")
            return True

        return False

    @commands.command()
    async def addportal(self, ctx, id: str, name: str):
        "Add a portal to a server"

        portal = await self.get_portal(id, ctx.author.id)

        if not self.check_name(name, ctx.guild.id):
            raise UserError(f"A portal with the name {name} already exists.")

        if self.redis.sismember(f"portal:list:{ctx.guild.id}", portal["id"]):
            raise UserError("That portal already exists in this server.")

        self.redis.sadd(f"portal:list:{ctx.guild.id}", portal["id"])
        self.redis.sadd(f"portal:guilds:{portal['id']}", ctx.guild.id)
        self.redis.set(f"portal:from_name:{ctx.guild.id}:{name}", portal["id"])
        self.redis.set(f"portal:from_id:{ctx.guild.id}:{portal['id']}", name)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def remportal(self, ctx, name: str):
        "Remove a portal from a server"

        portal_id = self.redis.get(f"portal:from_name:{ctx.guild.id}:{name}")
        if not portal_id:
            raise UserError(f"The portal {name} does not exist.")

        portal = await self.get_portal(portal_id, ctx.author.id)

        await self.remove_portal(portal["id"], ctx.guild.id)
        await ctx.message.add_reaction("✅")

    async def remove_portal(self, id, guild_id):
        name = self.redis.get(f"portal:from_id:{guild_id}:{id}")

        self.redis.srem(f"portal:list:{guild_id}", id)
        self.redis.srem(f"portal:guilds:{id}", guild_id)
        self.redis.delete(f"portal:from_name:{guild_id}:{name}")
        self.redis.delete(f"portal:from_id:{guild_id}:{id}")

    @staticmethod
    def portal_status_to_emoji(status):
        status = int(status)
        if status == 0:
            return ":x:"  # Disconnected
        elif status == 1:
            return ":orange_circle:"  # Connected, Not Ready
        elif status == 2:
            return ":green_circle:"  # Connected, Ready

    @commands.command()
    async def portals(self, ctx):
        "List connected portals"
        portal_ids = self.redis.smembers(f"portal:list:{ctx.guild.id}")

        embed = discord.Embed(title="Connected Portals")

        portals = []
        for id in portal_ids:
            portal = await self.get_portal(id)
            portal["alias"] = self.redis.get(
                f"portal:from_id:{ctx.guild.id}:{id}")
            portals.append(portal)

        embed.description = "\n".join(
            f"{self.portal_status_to_emoji(portal['status'])} "
            f"`{portal['alias']}`: {portal['name']}, "
            f"{portal['desc']} ({portal['id']})"
            for portal in portals)

        await ctx.send(embed=embed)

    @commands.command()
    async def portal(self, ctx, name: str, *, command: str = ""):
        "Send a command to a connected portal"
        job_id = str(uuid.uuid4())

        portal_id = self.redis.get(f"portal:from_name:{ctx.guild.id}:{name}")
        if not portal_id:
            raise UserError(f"Portal {name} does not exist!")

        portal_name = self.redis.hget(f"portal:{portal_id}", "name")

        pubsub = self.redis.pubsub()
        pubsub.subscribe(f"portal:{portal_id}:{job_id}")

        message = json.dumps({
            "type": "query",
            "job": job_id,
            "portal": portal_id,
            "data": command
        })

        clocks = "🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"

        embed = discord.Embed(title="Waiting for response...")

        dismsg = await ctx.send(embed=embed)

        self.redis.publish(f"portal:{portal_id}:{job_id}", message)

        message = None
        ts = time.time()
        frame = 0

        while (message is None
               or json.loads(message["data"])["type"] != "response"):
            if time.time() - ts > 30:
                # Connection timed out
                embed.title = "Timed Out"
                embed.description = (f"Portal {portal_name} "
                                     "did not respond in time.")
                await dismsg.edit(embed=embed)
                return

            if frame % 5 == 0:
                clock_index = (frame // 5) % len(clocks)
                clock = clocks[clock_index]
                embed.description = clock
                await dismsg.edit(embed=embed)

            message = pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0)

            frame += 1

            await asyncio.sleep(0.2)

        data = json.loads(message["data"])["data"]

        embed = discord.Embed()
        if "title" in data:
            embed.title = data["title"]
        if "description" in data:
            embed.description = data["description"]

        embed.set_footer(text=f"Connected to Portal: {portal_name}")

        await dismsg.edit(embed=embed)


def setup(bot):
    bot.add_cog(Portal(bot))
