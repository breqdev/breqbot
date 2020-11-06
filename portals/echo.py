import os

from portal import Portal


portal = Portal(
    os.getenv("PORTAL_URL"),
    os.getenv("PORTAL_ID_ECHO"),
    os.getenv("PORTAL_TOKEN_ECHO")
)


@portal.on_request()
def on_request(data):
    print(data)
    # time.sleep(20)
    return {"title": data,
            "description": "Echo portal, made with <3 by breq!"}


portal.run()
