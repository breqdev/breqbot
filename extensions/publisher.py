from .base import BaseCog


class PublisherCog(BaseCog):
    "A Breqbot Publisher"
    watch_params = tuple()
    scan_interval = 30

    def __init__(self, bot):
        super().__init__(bot)
