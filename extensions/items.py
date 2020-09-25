from uuid import uuid4

class Item():
    def __init__(self, name=None, desc=None, wearable=0, *, uuid=None):
        self.uuid = uuid or str(uuid4())
        self.name = name
        self.desc = desc
        self.wearable = wearable

    def __str__(self):
        return f"{self.name}: {self.desc} {'(wearable)' if int(self.wearable or 0) else ''} ({self.uuid})"

    @property
    def redis_key(self):
        return f"items:{self.uuid}"

    @staticmethod
    def from_redis(redis, uuid):
        exists = redis.sismember("items:list", uuid)
        if not exists:
            raise ValueError("Item does not exist")

        item = Item()
        item.uuid = uuid

        item.name = redis.hget(item.redis_key, "name")
        item.desc = redis.hget(item.redis_key, "desc")
        item.wearable = redis.hget(item.redis_key, "wearable") or "0"
        return item

    @staticmethod
    def from_name(redis, name):
        uuid = redis.get(f"items:from_name:{name.lower()}")
        if not uuid:
            raise ValueError("Item does not exist")
        return Item.from_redis(redis, uuid)

    @staticmethod
    def check_name(redis, name):
        "Ensure the name is not in use."
        uuid = redis.get(f"items:from_name:{name.lower()}")
        return (uuid is None)

    def to_redis(self, redis):
        redis.sadd("items:list", self.uuid)

        redis.hset(self.redis_key, "name", self.name)
        redis.hset(self.redis_key, "desc", self.desc)
        redis.hset(self.redis_key, "wearable", self.wearable)

        redis.set(f"items:from_name:{self.name.lower()}", self.uuid)

    def rename(self, redis, newname):
        redis.delete(f"items:from_name:{self.name.lower()}")
        self.name = newname
        redis.hset(self.redis_key, "name", self.name)
        redis.set(f"items:from_name:{self.name.lower()}", self.uuid)

    def delete(self, redis):
        redis.srem("items:list", self.uuid)
        redis.delete(f"items:from_name:{self.name.lower()}")
        redis.delete(self.redis_key)

    @property
    def dict(self):
        return {"uuid": self.uuid,
                "name": self.name,
                "desc": self.desc,
                "wearable": self.wearable}
