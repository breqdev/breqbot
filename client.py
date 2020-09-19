import os
import urllib

import requests

class Breqbot:
    def __init__(self, root_url="", token=os.getenv("API_TOKEN")):
        self.root_url = f"{root_url}/api"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_items(self):
        return self.session.get(f"{self.root_url}/items").json()

    def get_item(self, uuid=None, name=None):
        if uuid:
            return self.session.get(f"{self.root_url}/items/{uuid}").json()
        # Get by name
        result = self.session.get(f"{self.root_url}/items/by_name/{urllib.parse.quote_plus(name)}")
        if result.status_code >= 400:
            return None
        return result.json()


    def modify_item(self, uuid, name=None, desc=None):
        current = self.get_item(uuid)
        name = name or current["name"]
        desc = desc or current["desc"]
        self.session.put(f"{self.root_url}/items/{uuid}", data={"name": name, "desc": desc})

    def delete_item(self, uuid):
        current = self.get_item(uuid)
        if current is None:
            raise ValueError("Item does not exist")

        self.session.delete(f"{self.root_url}/items/{uuid}")

    def create_item(self, name, desc):
        current = self.get_item(name=name)
        if current is not None:
            raise ValueError("Item with name exists")
        return self.session.post(f"{self.root_url}/items/new", data={"name": name, "desc": desc}).json()

    def get_shop(self, guild_id):
        return Shop(self.session, self.root_url, guild_id)

class Shop:
    def __init__(self, session, root_url, guild_id):
        self.session = session
        self.id = guild_id
        self.root_url = f"{root_url}/shop/{guild_id}"

    def get(self):
        return self.session.get(self.root_url).json()

    def list(self, uuid, price):
        self.session.post(f"{self.root_url}/list", data={"uuid": uuid, "price": price})

    def delist(self, uuid, price):
        self.session.post(f"{self.root_url}/delist", data={"uuid": uuid})
