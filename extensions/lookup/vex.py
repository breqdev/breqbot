import typing
import json

import aiohttp
import aiocron
import discord
from discord.ext import commands

from ..base import BaseCog


class Vex(BaseCog):
    "Information about the VEX Robotics Competition"

    SEASON = "Tower Takeover"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()

        @aiocron.crontab("*/1 * * * *")
        async def watch_task():
            for pair in await self.redis.smembers("vex:watch:list"):
                data = await self.get_meet_data(*(pair.split(":")))
                new_hash = json.dumps(data)
                old_hash = await self.redis.get(f"vex:hash:{pair}")
                if old_hash != new_hash:
                    await self.redis.set(f"vex:hash:{pair}", new_hash)

                    embed = self.get_meet_overview(*data)

                    for channel_id in \
                            await self.redis.smembers(f"vex:watch:{pair}"):
                        channel = self.bot.get_channel(int(channel_id))

                        await channel.send(embed=embed)

    async def get_json(self, url, params={}):
        async with self.session.get(url, params=params) as response:
            return await response.json()

    async def get_team_overview(self, team):
        team = (await self.get_json(
            "https://api.vexdb.io/v1/get_teams",
            params={"team": team})
        )["result"][0]

        embed = discord.Embed(
            title=f"{team['program']} team {team['number']}: "
            f"{team['team_name']}")

        awards_raw = (await self.get_json(
            "https://api.vexdb.io/v1/get_awards",
            params={"team": team["number"], "season": self.SEASON})
        )["result"]

        awards = []
        for award_raw in awards_raw:
            award_name = award_raw["name"]

            event_raw = (await self.get_json(
                "https://api.vexdb.io/v1/get_events",
                params={"sku": award_raw["sku"]})
            )["result"][0]
            event_name = event_raw["name"]
            awards.append((award_name, event_name))

        awards = "\n".join(f"• **{award}** | {event}"
                           for award, event in awards)
        if not awards:
            awards = "This team has not won any awards."

        awards = "**Awards:**\n" + awards

        rankings_raw = (await self.get_json(
            "https://api.vexdb.io/v1/get_rankings",
            params={"team": team["number"], "season": self.SEASON})
        )["result"]

        rankings = []
        for ranking_raw in rankings_raw:
            ranking = ranking_raw["rank"]

            teams_count = (await self.get_json(
                "https://api.vexdb.io/v1/get_teams",
                params={"sku": ranking_raw["sku"], "nodata": "true"})
            )["size"]

            event_raw = (await self.get_json(
                "https://api.vexdb.io/v1/get_events",
                params={"sku": ranking_raw["sku"]})
            )["result"][0]
            event_name = event_raw["name"]

            rankings.append((ranking, teams_count, event_name))

        rankings = "\n".join(f"• **{rank}**/{teams} | {event}"
                             for rank, teams, event in rankings)
        if not rankings:
            rankings = "This team has not competed."

        rankings = "**Rankings:**\n" + rankings

        embed.description = awards + "\n" + rankings

        return None, [], embed

    async def get_meet_data(self, team, sku):
        team = (await self.get_json(
            "https://api.vexdb.io/v1/get_teams",
            params={"team": team})
        )["result"][0]

        event = (await self.get_json(
            "https://api.vexdb.io/v1/get_events",
            params={"sku": sku})
        )["result"][0]

        matches = (await self.get_json(
            "https://api.vexdb.io/v1/get_matches",
            params={"sku": sku, "team": team["number"], "scored": 1})
        )["result"]

        driver_skills = (await self.get_json(
            "https://api.vexdb.io/v1/get_skills",
            params={"sku": sku, "team": team["number"], "type": 0})
        )["result"][0]

        programming_skills = (await self.get_json(
            "https://api.vexdb.io/v1/get_skills",
            params={"sku": sku, "team": team["number"], "type": 1})
        )["result"][0]

        ranking = (await self.get_json(
            "https://api.vexdb.io/v1/get_rankings",
            params={"sku": sku, "team": team["number"]})
        )["result"][0]

        return team, event, matches, driver_skills, programming_skills, ranking

    async def get_hash(self, team, sku):
        data = await self.get_meet_data(team, sku)
        return json.dumps(data)

    def matchnum(self, match):
        if match["round"] == 1:  # Practice
            return f"P{match['matchnum']}"
        if match["round"] == 2:  # Qualification
            return f"Q{match['matchnum']}"
        if match["round"] == 3:  # QuarterFinals
            return f"QF{match['matchnum']}-{match['instance']}"
        if match["round"] == 4:  # SemiFinals
            return f"SF{match['matchnum']}-{match['instance']}"
        if match["round"] == 5:  # Finals
            return f"Final {match['instance']}"

    def matchstr(self, match, team=None):
        team = team["number"]
        num = self.matchnum(match)

        teams = [match[key] for key in ("red1", "red2", "blue1", "blue2")]

        redteams = " ".join((f"**{t}**" if t == team else t)
                            for t in teams[:2])
        blueteams = " ".join((f"**{t}**" if t == team else t)
                             for t in teams[2:])

        if team in teams[:2]:  # Team On Red
            score = f" **{match['redscore']}** - *{match['bluescore']}* "
        else:  # Team On Blue
            score = f" *{match['redscore']}* - **{match['bluescore']}** "

        if match["redscore"] > match["bluescore"]:
            # Red win
            score = f"🟥{score}⬛"
            if team in teams[:2]:
                result = "✅"
            else:
                result = "❌"

        elif match["bluescore"] > match["redscore"]:
            # Blue win
            score = f"⬛{score}🟦"
            if team in teams[2:]:
                result = "✅"
            else:
                result = "❌"
        else:
            # Tie
            score = f"🟪{score}🟪"
            result = "🔸"

        return f"{num}\t-\t{redteams}\t{score}\t{blueteams}\t-\t{result}"

    def get_meet_overview(self, team, event, matches,
                          driver_skills, programming_skills, ranking):

        embed = discord.Embed(
            title=f"**{team['number']}**: *{team['team_name']}* at"
            f"*{event['name']}*")

        matches_str = "\n".join(f"{self.matchstr(match, team)}"
                                for match in matches)

        skills_str = (f"Driver: {driver_skills['score']} "
                      f"*({driver_skills['attempts']} attempts)*\n"
                      f"Programming: {programming_skills['score']} "
                      f"*({programming_skills['attempts']} attempts)*")

        rankings_str = (f"**{ranking['rank']}** "
                        f"({ranking['wins']}-{ranking['losses']}-"
                        f"{ranking['ties']})")

        embed.add_field(name="Matches", value=matches_str, inline=False)
        embed.add_field(name="Skills", value=skills_str, inline=False)
        embed.add_field(name="Rankings", value=rankings_str, inline=False)

        return None, [], embed

    @commands.command()
    async def vex(self, ctx, team: str, sku: typing.Optional[str] = None):
        ":mag: :robot: Get info about a Vex team :video_game:"
        if sku:
            content, files, embed = self.get_meet_overview(
                *(await self.get_meet_data(team, sku)))
        else:
            content, files, embed = await self.get_team_overview(team)

        await ctx.send(embed=embed)

    @commands.command()
    async def watchteam(self, ctx, team: str, sku: str):
        "Subscribe to updates from a Vex team!"

        if ctx.guild:
            if not ctx.channel.permissions_for(ctx.author).administrator:
                raise commands.UserInputError(
                    "To prevent spam, "
                    "only administrators can watch VEX teams.")

        team = team.upper()
        sku = sku.upper()

        hash = await self.get_hash(team, sku)

        await self.redis.set(f"vex:hash:{team}:{sku}", hash)
        await self.redis.sadd(f"vex:watch:{team}:{sku}", ctx.channel.id)
        await self.redis.sadd(f"vex:channel:{ctx.channel.id}", f"{team}:{sku}")
        await self.redis.sadd("vex:watch:list", f"{team}:{sku}")

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def unwatchteam(self, ctx, team: str, sku: str):
        "Unsubscribe from updates about a team."

        if ctx.guild:
            if not ctx.channel.permissions_for(ctx.author).administrator:
                raise commands.UserInputError(
                    "To prevent spam, "
                    "only administrators can unwatch VEX teams.")

        team = team.upper()
        sku = sku.upper()

        await self.redis.srem(f"vex:watch:{team}:{sku}", ctx.channel.id)
        await self.redis.srem(f"vex:channel:{ctx.channel.id}", f"{team}:{sku}")
        if (await self.redis.scard(f"vex:watch:{team}:{sku}")) == 0:
            await self.redis.srem("vex:watch:list", f"{team}:{sku}")

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def watchingteams(self, ctx):
        "List VEX teams and events being watched"

        embed = discord.Embed(title=f"#{ctx.channel.name} is watching...")

        embed.description = ""
        pairs = await self.redis.smembers(f"vex:channel:{ctx.channel.id}")
        for pair in pairs:
            team, sku = pair.split(":")
            embed.description += f"**{team}** | *{sku}*\n"

        if not embed.description:
            embed.description = "None"

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Vex(bot))
