import asyncio

import aiohttp


class Portal:
    def __init__(self, url, id, token):
        self.url = url
        self.id = id
        self.token = token

    async def connect(self):
        self.session = aiohttp.ClientSession()
        self.socket = await self.session.ws_connect(f"{self.url}portal")

        await self.auth()
        await self.set_status(2)

    async def handle(self):
        await self.connect()
        while True:
            message = await self.socket.receive_json()
            await self.handle_request(message)

    async def auth(self):
        message = {
            "type": "auth",
            "id": self.id,
            "token": self.token
        }
        await self.socket.send_json(message)

    async def set_status(self, status):
        message = {
            "type": "status",
            "status": status
        }
        await self.socket.send_json(message)

    async def handle_request(self, message):
        if message["type"] == "ping":
            return
        elif message["type"] != "query":
            return

        result = self.request_callback(message["data"])

        response = {
            "type": "response",
            "job": message["job"],
            "data": result
        }
        await self.socket.send_json(response)

    def on_request(self):
        def decorator(func):
            self.request_callback = func
            return func
        return decorator

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.handle())
