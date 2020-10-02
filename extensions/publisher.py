from discord.ext import tasks

from .base import BaseCog


class PublisherCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.cogname = self.__class__.__name__
        self.handle_publish.start()

    async def has_update(self, param):
        oldhash = self.redis.get(
            f"publisher:hash:{self.cogname}:{param}")
        newhash = await self.get_hash(param)

        if newhash != oldhash:
            self.redis.set(
                f"publisher:hash:{self.cogname}:{param}", newhash)
            return True
        return False

    async def register_channel(self, param, channel_id):
        self.redis.sadd(f"publisher:watching:{self.cogname}", param)
        self.redis.sadd(
            f"publisher:channels:{self.cogname}:{param}", channel_id)

    async def unregister_channel(self, param, channel_id):
        self.redis.srem(
            f"publisher:channels:{self.cogname}:{param}", channel_id)
        if self.redis.scard(f"publisher:channels:{self.cogname}:{param}") == 0:
            self.redis.srem(f"publisher:watching:{self.cogname}", param)
            self.redis.delete(f"publisher:channels:{self.cogname}:{param}")

    async def get_watching(self, ichannel_id):
        params = []
        for param in self.redis.smembers(f"publisher:watching:{self.cogname}"):
            for channel_id in self.redis.smembers(
                    f"publisher:channels:{self.cogname}:{param}"):
                if channel_id == str(ichannel_id):
                    params.append(param)

        return params

    @tasks.loop(seconds=30)
    async def handle_publish(self):
        await self.bot.wait_until_ready()
        for param in self.redis.smembers(f"publisher:watching:{self.cogname}"):
            if not await self.has_update(param):
                continue

            update = await self.get_update(param)

            for channel_id in self.redis.smembers(
                    f"publisher:channels:{self.cogname}:{param}"):
                channel = self.bot.get_channel(int(channel_id))
                await channel.send(embed=update)
