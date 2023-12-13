import threading
import time
from time import sleep

import bot_app
import flask_app

import tracemalloc

tracemalloc.start()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_app.run)
    bot_thread.daemon = True
    bot_thread.start()

    app_thread = threading.Thread(target=flask_app.run)
    app_thread.daemon = True
    app_thread.start()

    # Костыль, чтобы иметь возможность прерывать приложение по [Ctrl] + [C]
    while True:
        try:
            sleep(1)
        except KeyboardInterrupt:
            break
