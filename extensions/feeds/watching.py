import discord
from discord.ext import commands

from .. import base
from .. import watch


class Watching(base.BaseCog):

    category = "Feeds"

    async def get_watching(self, channel):
        watching = {}

        for name, watch_instance in self.bot.watches.items():
            watching[name] = await watch_instance.human_targets(channel)

        return watching

    @commands.command()
    async def watching(self, ctx):
        "List the Feeds that this channel is subscribed to"

        if ctx.guild:
            name = f"#{ctx.channel.name}"
        else:
            name = f"@{ctx.author.display_name}"

        embed = discord.Embed(title=f"{name} is watching...")

        watching = await self.get_watching(ctx.channel)

        for name, targets in watching.items():
            if targets:
                embed.add_field(
                    name=name, value=", ".join(targets), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def messagewatches(self, ctx):
        "List the currently active MessageWatches"

        targets = {}

        for name, watch_instance in self.bot.watches.items():
            if isinstance(watch_instance, watch.MessageWatch):
                targets[name] = await watch_instance.human_targets(ctx.guild)

        embed = discord.Embed(title=f"{ctx.guild.name} is watching...")

        for name, each_targets in targets.items():
            if each_targets:
                for target in each_targets:
                    target["channel"] = self.bot.get_channel(
                        int(target["channel_id"]))
                    target["message"] = await target["channel"].fetch_message(
                        int(target["message_id"]))

                embed.add_field(
                    name=name, value=", ".join(
                        f"[{target['target']}]({target['message'].jump_url})"
                        for target in each_targets))

        await ctx.send(embed=embed)

    @commands.command()
    @commands.dm_only()
    async def rmwatch(self, ctx, *, message: discord.Message):
        "Remove a MessageWatch"
        for watch_instance in self.bot.watches.values():
            if isinstance(watch_instance, watch.MessageWatch):
                await watch.unregister(message.channel.id, message.id)

        await message.delete()

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Watching(bot))
