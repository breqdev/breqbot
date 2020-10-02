from .base import BaseCog


class PublisherCog(BaseCog):
    "A Breqbot Publisher"
    watch_params = tuple()

    def __init__(self, bot):
        super().__init__(bot)
