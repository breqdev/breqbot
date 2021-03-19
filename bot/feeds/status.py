import os

import aiohttp
import aiocron
import discord
from discord.ext import commands

from bot import base
from bot import watch

UPTIMEROBOT_KEY = os.getenv("UPTIMEROBOT_KEY")


class Status(base.BaseCog, watch.Watchable):
    description = "Subscribe to status updates for Breq's services"
    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)

        self.session = aiohttp.ClientSession()
        self.watch = watch.MessageWatch(self)
        self.bot.watches["Status"] = self.watch
        self.services = {}

    @commands.Cog.listener()
    async def on_ready(self):
        await self.fetch_services_list()

        @aiocron.crontab("*/1 * * * *")
        async def fetch_task():
            await self.fetch_services_list()

    async def fetch_services_list(self):
        "Fetch the list of services"

        async with self.session.post(
                "https://api.uptimerobot.com/v2/getMonitors",
                data={
                    "api_key": UPTIMEROBOT_KEY,
                    "format": "json",
                }) as response:
            response = await response.json()

        self.services = {}
        for monitor in response["monitors"]:
            self.services[monitor["friendly_name"]] = monitor

    async def get_state_by_ids(self, monitor_ids):
        async with self.session.post(
                "https://api.uptimerobot.com/v2/getMonitors",
                data={
                    "api_key": UPTIMEROBOT_KEY,
                    "format": "json",
                    "monitors": monitor_ids,
                    "custom_uptime_ratios": 30
                }) as response:
            response = await response.json()

        return response

    @commands.group(invoke_without_command=True)
    async def status(self, ctx, *service_names: str):
        "Get the status of one of Breq's services"

        if len(service_names) == 0:
            service_names = self.services.keys()

        monitor_ids = "-".join(
            str(self.services[name]["id"])
            for name in service_names if name in self.services)

        response = await self.get_state_by_ids(monitor_ids)

        embed = discord.Embed(
            title="Breq Services Status", url="https://status.breq.dev")

        status_emojis = {
            0: "📴",  # Paused
            1: "📴",  # Not checked yet
            2: "🟢",  # Up
            8: "🔴",  # Seems Down
            9: "🔴",  # Down
        }

        embed.description = "\n".join(
            f"{status_emojis[service['status']]} {service['friendly_name']}: "
            f"{service['custom_uptime_ratio']}%"
            for service in response["monitors"])

        await ctx.send(embed=embed)

    @status.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx, service_name: str):
        "Watch the status of one of Breq's services"

        await self.watch.register(ctx.channel, service_name)

    async def check_target(self, target):
        return target in self.services

    async def get_state(self, target):
        monitor_id = self.services[target]["id"]
        return (await self.get_state_by_ids(monitor_id))["monitors"][0]

    async def get_response(self, state):
        embed = discord.Embed(
            title="Breq Services Status", url="https://status.breq.dev")

        status_emojis = {
            0: "📴",  # Paused
            1: "📴",  # Not checked yet
            2: "🟢",  # Up
            8: "🔴",  # Seems Down
            9: "🔴",  # Down
        }

        embed.description = (
            f"{status_emojis[state['status']]} {state['friendly_name']}: "
            f"{state['custom_uptime_ratio']}%")

        return base.Response("", {}, embed)


def setup(bot):
    bot.add_cog(Status(bot))
