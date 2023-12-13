from flask import Flask, request
import bot_app

app = Flask(__name__)


@app.route("/register", methods=['POST'])
def register():
    data = request.get_json()
    bot_app.register_confirm(data)

    resp = {'message': 'Success'}
    return resp, 200


def run():
    while True:
        try:
            app.run(port=8081)
        except Exception as ex:
            print(ex)

