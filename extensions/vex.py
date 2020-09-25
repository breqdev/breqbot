import requests

import discord
from discord.ext import commands

from .utils import *


class Vex(BaseCog):
    "Information about the VEX Robotics Competition"

    SEASON = "Tower Takeover"

    @commands.command()
    @passfail
    async def vex(self, ctx, team: str):
        ":mag: :robot: Get info about a Vex team :video_game:"

        async with ctx.channel.typing():
            team = requests.get("https://api.vexdb.io/v1/get_teams",
                                params={"team": team}).json()["result"][0]

            embed = discord.Embed(
                title=f"{team['program']} team {team['number']}: "
                f"{team['team_name']}")

            awards_raw = requests.get(
                "https://api.vexdb.io/v1/get_awards",
                params={"team": team["number"], "season": self.SEASON}
            ).json()["result"]

            awards = []
            for award_raw in awards_raw:
                award_name = award_raw["name"]

                event_raw = requests.get(
                    "https://api.vexdb.io/v1/get_events",
                    params={"sku": award_raw["sku"]}).json()["result"][0]
                event_name = event_raw["name"]
                awards.append((award_name, event_name))

            awards = "\n".join(f"• **{award}** | {event}"
                               for award, event in awards)
            if not awards:
                awards = "This team has not won any awards."

            embed.add_field(name="Awards", value=awards, inline=False)

            rankings_raw = requests.get(
                "https://api.vexdb.io/v1/get_rankings",
                params={"team": team["number"], "season": self.SEASON}
            ).json()["result"]

            rankings = []
            for ranking_raw in rankings_raw:
                ranking = ranking_raw["rank"]

                teams_count = requests.get(
                    "https://api.vexdb.io/v1/get_teams",
                    params={"sku": ranking_raw["sku"], "nodata": "true"}
                ).json()["size"]

                event_raw = requests.get(
                    "https://api.vexdb.io/v1/get_events",
                    params={"sku": ranking_raw["sku"]}).json()["result"][0]
                event_name = event_raw["name"]

                rankings.append((ranking, teams_count, event_name))

            rankings = "\n".join(f"• **{rank}**/{teams} | {event}"
                                 for rank, teams, event in rankings)
            if not rankings:
                rankings = "This team has not competed."

            embed.add_field(name="Rankings", value=rankings, inline=False)
        return embed


def setup(bot):
    bot.add_cog(Vex(bot))
