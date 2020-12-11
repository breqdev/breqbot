import aiocron

from discord.ext import commands


class Watchable:
    async def check_target(self, target):
        "Verify that a target represents a valid resource."
        return True

    async def get_state(self, target):
        "Returns some object representing the state of the resource"
        pass

    async def get_hash(self, state):
        "Returns a string which will change if the resource changes"
        return str(state)

    async def get_response(self, state):
        "Returns content, files, embed from the resource"
        return "", [], None

    async def human_targets(self, targets):
        "Convert machine-readable targets to human-readable ones"
        return targets


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
        if not await self.cog.check_target(target):
            raise commands.CommandError(f"Invalid target: {target}")

        if not await self.redis.sismember(
                f"watch:{self.name}:targets", target):
            state = await self.cog.get_state(target)
            hash = await self.cog.get_hash(state)
            await self.redis.set(f"watch:{self.name}:hash:{target}", hash)

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

    async def is_registered(self, channel, target):
        return await self.redis.sismember(
            f"watch:{self.name}:target:{target}", channel.id)

    async def get_targets(self, channel):
        return await self.redis.smembers(
            f"watch:{self.name}:channel:{channel.id}")

    async def human_targets(self, channel):
        targets = await self.get_targets(channel)
        return await self.cog.human_targets(targets)

    async def watch(self):
        for target in await self.redis.smembers(f"watch:{self.name}:targets"):
            state = await self.cog.get_state(target)
            new_hash = await self.cog.get_hash(state)

            old_hash = await self.redis.get(f"watch:{self.name}:hash:{target}")
            if old_hash != new_hash:
                response = await self.cog.get_response(state)

                await self.redis.set(
                    f"watch:{self.name}:hash:{target}", new_hash)

                for channel_id in await self.redis.smembers(
                        f"watch:{self.name}:target:{target}"):
                    channel = self.bot.get_channel(int(channel_id))
                    await response.send_to(channel)


class MessageWatch(Watch):
    def start_listeners(self):
        @self.bot.listen()
        async def on_raw_message_delete(payload):
            await self.unregister(payload.message_id)

    async def register(self, channel, target):
        state = await self.cog.get_state(target)
        response = await self.cog.get_response(state)
        message = await response.send_to(channel)

        if not await self.redis.sismember(
                f"watch:{self.name}:targets", target):
            hash = await self.cog.get_hash(state)
            await self.redis.set(f"watch:{self.name}:hash:{target}", hash)

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
                response = await self.cog.get_response(state)

                await self.redis.set(
                    f"watch:{self.name}:hash:{target}", new_hash)

                for message_id in await self.redis.smembers(
                        f"watch:{self.name}:target:{target}"):
                    channel_id = await self.redis.get(
                        f"watch:{self.name}:message:{message_id}:channel")

                    channel = self.bot.get_channel(int(channel_id))
                    message = await channel.fetch_message(int(message_id))

                    await response.send_to(message)
