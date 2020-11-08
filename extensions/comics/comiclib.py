class Comic:
    async def get_url(self, url, type="text", headers={}):
        async with self.session.get(url, headers=headers) as response:
            if type == "text":
                return await response.text()
            elif type == "bin":
                return await response.read()
            elif type == "json":
                return await response.json()
