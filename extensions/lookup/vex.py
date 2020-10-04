import typing
import requests

import discord
from discord.ext import commands

from ..base import run_in_executor
from .. import publisher


class Vex(publisher.PublisherCog):
    "Information about the VEX Robotics Competition"
    watch_params = ("team", "sku")
    scan_interval = 1

    SEASON = "Tower Takeover"

    async def get_team_overview(self, team):
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

        awards = "**Awards:**\n" + awards

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

        rankings = "**Rankings:**\n" + rankings

        embed.description = awards + "\n" + rankings

        return None, [], embed

    @run_in_executor
    def get_meet_data(self, team, sku):
        team = requests.get(
            "https://api.vexdb.io/v1/get_teams",
            params={"team": team}
        ).json()["result"][0]

        event = requests.get(
            "https://api.vexdb.io/v1/get_events",
            params={"sku": sku}
        ).json()["result"][0]

        matches = requests.get(
            "https://api.vexdb.io/v1/get_matches",
            params={"sku": sku, "team": team["number"],
                    "scored": 1}
        ).json()["result"]

        driver_skills = requests.get(
            "https://api.vexdb.io/v1/get_skills",
            params={"sku": sku, "team": team["number"], "type": 0}
        ).json()["result"][0]

        programming_skills = requests.get(
            "https://api.vexdb.io/v1/get_skills",
            params={"sku": sku, "team": team["number"], "type": 1}
        ).json()["result"][0]

        ranking = requests.get(
            "https://api.vexdb.io/v1/get_rankings",
            params={"sku": sku, "team": team["number"]}
        ).json()["result"][0]

        return team, event, matches, driver_skills, programming_skills, ranking

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

    async def get_meet_overview(self, team, sku):
        team, event, matches, driver_skills, programming_skills, ranking \
            = await self.get_meet_data(team, sku)

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
            content, files, embed = await self.get_meet_overview(team, sku)
        else:
            content, files, embed = await self.get_team_overview(team)

        await ctx.send(embed=embed)

    async def get_hash(self, team, sku):
        team, event, matches, driver_skills, programming_skills, ranking \
            = await self.get_meet_data(team, sku)

        return (f"{len(matches)}:{driver_skills['attempts']}:"
                f"{programming_skills['attempts']}")

    async def get_update(self, team, sku):
        return await self.get_meet_overview(team, sku)


def setup(bot):
    bot.add_cog(Vex(bot))
