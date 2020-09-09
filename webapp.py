from flask import Flask

app = Flask(__name__)

@app.route("/")
def index(self):
    return "Hello World from Breqbot! :&gt;"

if __name__ == "__main__":
    app.run()
