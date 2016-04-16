import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class SetupHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Setting up!")


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/setup", SetupHandler)
    ])

if __name__ == "__main__":
    app = make_app()
    for port in range(8870,8881):
    	app.listen(port)
    tornado.ioloop.IOLoop.current().start()