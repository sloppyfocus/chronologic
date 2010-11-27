import tornado.websocket

alive = []

class PollHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        alive.append(self)

    def on_close(self):
        try:
            alive.remove(self)
        except ValueError:
            pass

def notify_all():
    for handler in alive:
        handler.write_message('x')

