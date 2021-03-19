import typing
import calendar

import aiocron
import timestring
import discord
from discord.ext import commands

from bot import base


class Birthdays(base.BaseCog):
    "Breqbot can remember your birthday and wish you happy birthday!"

    category = "Profile"

    @commands.Cog.listener()
    async def on_ready(self):
        @aiocron.crontab("0 0 * * *")
        async def birthday_reminders():
            date = timestring.Date("now")

            for channel in self.bot.get_all_channels():
                for member_id in (await self.redis.smembers(
                        f"birthdays:channel:{channel.id}")):

                    birthday = await self.redis.hgetall(
                        f"birthdays:user:{member_id}")

                    if not birthday:
                        continue

                    if not (birthday["month"] == str(date.month)
                            and birthday["day"] == str(date.day)):
                        continue

                    member = self.bot.get_user(int(member_id))

                    message = (f"It's {member.mention}'s birthday! "
                               ":partying_face:")
                    await channel.send(message)

    @commands.group(invoke_without_command=True)
    async def birthday(self, ctx, *, user: typing.Optional[base.FuzzyMember]):
        "Who's birthday is it today? Or, specify a user to get their birthday."

        if user:
            month, day = await self.redis.hmget(
                f"birthdays:user:{user.id}", "month", "day")

            if month is None or day is None:
                await ctx.send(
                    f"{user.display_name} has not set a birthday. "
                    f"`{self.bot.main_prefix}birthday set`?")
            else:
                await ctx.send(f"{user.display_name}'s birthday is "
                               f"**{calendar.month_name[int(month)]} {day}**")

        else:
            date = timestring.Date("now")

            embed = discord.Embed(title="Birthdays today :partying_face:")

            birthdays = []

            for member in ctx.channel.members:
                birthday = await self.redis.hgetall(
                    f"birthdays:user:{member.id}")
                if not birthday:
                    continue  # user has not yet set their birthday
                if (birthday["month"] == str(date.month)
                        and birthday["day"] == str(date.day)):
                    birthdays.append(member)

            if birthdays:
                embed.description = "\n".join(
                    member.mention for member in birthdays)
            else:
                embed.description = "Nobody's birthday is today :("

            await ctx.send(embed=embed)

    @birthday.command()
    async def set(self, ctx, *, date: str):
        "Tell Breqbot when your birthday is"
        date = timestring.Date(date)

        await self.redis.hmset_dict(f"birthdays:user:{ctx.author.id}", {
            "month": date.month,
            "day": date.day
        })

        await ctx.send(
            f"Set {ctx.author.display_name}'s birthday to "
            f"**{calendar.month_name[int(date.month)]} {date.day}** ✅")

    @birthday.command()
    async def clear(self, ctx):
        "Clear your set birthday"
        await self.redis.delete(f"birthdays:user:{ctx.author.id}")
        await ctx.message.add_reaction("✅")

    @birthday.command()
    async def remind(self, ctx, user: typing.Optional[discord.User] = None):
        "Tell Breqbot to remind you of your or someone else's birthday"
        if user is None:
            user = ctx.author

        await self.redis.sadd(f"birthdays:channel:{ctx.channel.id}", user.id)

        await ctx.message.add_reaction("✅")

    @birthday.command()
    async def noremind(self, ctx):
        "Tell Breqbot to stop remind you about your birthday, if you hate fun."

        await self.redis.srem(
            f"birthdays:channel:{ctx.channel.id}", ctx.author.id)

        await ctx.message.add_reaction("✅")

    @birthday.command()
    async def reminders(self, ctx):
        "List the users for which Breqbot will send out a birthday reminder"

        members = await self.redis.smembers(
            f"birthdays:channel:{ctx.channel.id}")

        embed = discord.Embed(
            title=f"Birthday reminders on #{ctx.channel.name}")

        embed.description = "\n".join(
            self.bot.get_user(int(member_id)).mention for member_id in members)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Birthdays(bot))
