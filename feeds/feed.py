import aiohttp


class Feed:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def get_url(self, url, type="text", headers={}):
        async with self.session.get(url, headers=headers) as response:
            if type == "text":
                return await response.text()
            elif type == "bin":
                return await response.read()
            elif type == "json":
                return await response.json()


class FeedResponse:
    def __init__(self, content="", files=[], embed=None):
        self.content = content
        self.files = files
        self.embed = embed

    async def send_to(self, dest):
        await dest.send(self.content, files=self.files, embed=self.embed)


class FeedLookupError(ValueError):
    pass
