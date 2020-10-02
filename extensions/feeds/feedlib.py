class Feed:
    desc = "A Breqbot Feed"

    async def has_update(self, oldstate):
        """Checks to see if the Feed has been updated since the last
        version/state. If it has, return the new version/state identifier."""
        return False

    async def get_latest(self):
        return None

    async def get_random(self):
        return None

    async def get_number(self, number):
        return None
