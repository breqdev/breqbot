import aiocron

from . import base


class Watchable:
    async def get_state(self, target):
        "Returns some object representing the state of the resource"
        pass

    async def get_hash(self, state):
        "Returns a string which will change if the resource changes"
        return str(state)

    async def get_pack(self, state):
        "Returns content, files, embed from the resource"
        return "", [], None


class Watch:
    def __init__(self, cog, crontab="*/1 * * * *"):
        self.name = cog.qualified_name
        self.cog = cog
        self.bot = self.cog.bot
        self.redis = self.bot.redis
        self.crontab = crontab

        self.start_listeners()

        self.cron = aiocron.crontab(self.crontab, func=self.watch, start=False)

        @self.bot.listen()
        async def on_ready():
            self.cron.start()


class ChannelWatch(Watch):
    def start_listeners(self):
        pass

    async def register(self, channel, target):

        # todo: if its the first with this target, pre-fill the 'hash'

        await self.redis.sadd(f"watch:{self.name}:targets", target)
        await self.redis.sadd(f"watch:{self.name}:target:{target}", channel.id)

        await self.redis.sadd(
            f"watch:{self.name}:channel:{channel.id}", target)

    async def unregister(self, channel, target):
        await self.redis.srem(f"watch:{self.name}:target:{target}", channel.id)

        card = await self.redis.scard(f"watch:{self.name}:target:{target}")
        if int(card) < 1:
            await self.redis.srem(f"watch:{self.name}:targets", target)

        await self.redis.srem(
            f"watch:{self.name}:channel:{channel.id}", target)

    async def watch(self):
        for target in await self.redis.smembers(f"watch:{self.name}:targets"):
            state = await self.cog.get_state(target)
            new_hash = await self.cog.get_hash(state)

            old_hash = await self.redis.get(f"watch:{self.name}:hash:{target}")
            if old_hash != new_hash:
                pack = await self.cog.get_pack(state)

                await self.redis.set(
                    f"watch:{self.name}:hash:{target}", new_hash)

                for channel_id in await self.redis.smembers(
                        f"watch:{self.name}:target:{target}"):
                    channel = self.bot.get_channel(int(channel_id))
                    await base.BaseCog.pack_send(channel, *pack)


class MessageWatch(Watch):
    def start_listeners(self):
        @self.bot.listen()
        async def on_raw_message_delete(payload):
            await self.unregister(payload.message_id)

    async def register(self, channel, target):
        state = await self.cog.get_state(target)
        pack = await self.cog.get_pack(state)
        message = await base.BaseCog.pack_send(channel, *pack)

        await self.redis.sadd(f"watch:{self.name}:targets", target)
        await self.redis.sadd(f"watch:{self.name}:messages", message.id)
        await self.redis.sadd(f"watch:{self.name}:target:{target}", message.id)
        await self.redis.set(
            f"watch:{self.name}:message:{message.id}:target", target)
        await self.redis.set(
            f"watch:{self.name}:message:{message.id}:channel", channel.id)

    async def unregister(self, message_id):
        if not await self.redis.sismember(
                f"watch:{self.name}:messages", message_id):
            return

        target = await self.redis.get(
            f"watch:{self.name}:message:{message_id}:target")

        await self.redis.srem(f"watch:{self.name}:target:{target}", message_id)

        card = await self.redis.scard(f"watch:{self.name}:target:{target}")
        if int(card) < 1:
            await self.redis.srem(f"watch:{self.name}:targets", target)
            await self.redis.delete(f"watch:{self.name}:hash:{target}")

        await self.redis.delete(
            f"watch:{self.name}:message:{message_id}:target")
        await self.redis.delete(
            f"watch:{self.name}:message:{message_id}:channel")

    async def watch(self):
        for target in await self.redis.smembers(f"watch:{self.name}:targets"):
            state = await self.cog.get_state(target)
            new_hash = await self.cog.get_hash(state)

            old_hash = await self.redis.get(f"watch:{self.name}:hash:{target}")
            if old_hash != new_hash:
                pack = await self.cog.get_pack(state)

                await self.redis.set(
                    f"watch:{self.name}:hash:{target}", new_hash)

                for message_id in await self.redis.smembers(
                        f"watch:{self.name}:target:{target}"):
                    channel_id = await self.redis.get(
                        f"watch:{self.name}:message:{message_id}:channel")

                    channel = self.bot.get_channel(int(channel_id))
                    message = await channel.fetch_message(int(message_id))

                    await base.BaseCog.pack_send(message, *pack)