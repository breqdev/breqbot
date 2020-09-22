import uuid
import json
import asyncio

import discord
from discord.ext import commands

from .items import Item
from .breqcog import *

class Things(Breqcog):
    "Interface with real-world things"

    @commands.command()
    @passfail
    async def thing(self, ctx, thing: str, command: str):
        "Send a command to a real-world thing"
        job_id = uuid.uuid4()

        pubsub = self.redis.pubsub()
        pubsub.subscribe(f"things:{thing}:{job_id}")

        message = json.dumps({"type": "query",
                              "data": command})

        self.redis.publish(f"things:{thing}:{job_id}", message)

        message = None
        while message is None or message["type"] != "response":
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0)
            await asyncio.sleep(0.5)
        return message



def setup(bot):
    bot.add_cog(Things(bot))
