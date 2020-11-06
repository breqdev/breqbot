import os
import subprocess
import uuid
import shutil
import time

import requests

from portal import Portal

portal = Portal(
    os.getenv("PORTAL_URL"),
    os.getenv("PORTAL_ID_MATRIX"),
    os.getenv("PORTAL_TOKEN_MATRIX")
)


CAMERA_WAKE = 2


@portal.on_request()
def on_request(data):

    ffmpeg = subprocess.Popen([
        "ffmpeg",
        "-i", "/dev/video0",
        "-video_size", "1280x720",
        "matrix/recording.mkv"
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(CAMERA_WAKE)

    print("Recording started")

    requests.get("http://raspberrypi.local/",
                 params={"text": data, "color": "128,128,128"})

    print("Scrolling finished")

    ffmpeg.communicate(b"q\n")

    print("Recording finished")

    subprocess.run([
        "ffmpeg",
        "-i", "matrix/recording.mkv",
        "-ss", str(CAMERA_WAKE),
        "-vf", ("fps=10,scale=320:-1:flags=lanczos,split[s0][s1];"
                "[s0]palettegen[p];[s1][p]paletteuse"),
        "-loop", "0",
        "matrix/output.gif"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("Conversion finished")

    os.remove("matrix/recording.mkv")

    filename = f"{str(uuid.uuid4())}.gif"
    shutil.move("matrix/output.gif", f"/keybase/public/breq/matrix/{filename}")

    time.sleep(10)

    return {"title": f"https://breq.keybase.pub/matrix/{filename}",
            "image": f"https://breq.keybase.pub/matrix/{filename}",
            "description": "Matrix portal | captured by Breq <3"}


portal.run()
