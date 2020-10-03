from .base import BaseCog


class PublisherCog(BaseCog):
    "A Breqbot Publisher"
    watch_params = tuple()
    scan_interval = 15

    def __init__(self, bot):
        super().__init__(bot)
