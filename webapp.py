import os

from flask import Flask, redirect

from api import api
from portal_server import portal_server
from flask_sockets import Sockets


app = Flask(__name__)
sockets = Sockets(app)


@app.route("/")
def index():
    return redirect("https://breq.dev/apps/breqbot")


@app.route("/guild")
def guild():
    return redirect(os.getenv("TESTING_DISCORD"))


@app.route("/bugs")
def bugs():
    return redirect(os.getenv("BUG_REPORT"))


@app.route("/invite")
def invite():
    return redirect(os.getenv("BOT_INVITE"))


@app.route("/github")
def github():
    return redirect(os.getenv("GITHUB_URL"))


app.register_blueprint(api, url_prefix="/api")
sockets.register_blueprint(portal_server)


if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 8000), app, handler_class=WebSocketHandler)
    server.serve_forever()
