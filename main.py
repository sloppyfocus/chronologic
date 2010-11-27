import os
import optparse

import tornado.ioloop
import tornado.httpserver

import timeline.db
import timeline.handlers

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('--no-debug', dest='debug', default=True, action='store_false', help='Do not run in debug mode')
    parser.add_option('-p', '--port', type='int', default=8080, help='What port to run on')
    opts, args = parser.parse_args()

    base_path = os.path.abspath(os.path.dirname(__file__) or '.')
    application = timeline.handlers.get_application(base_path=base_path, debug=opts.debug)

    timeline.db.connect()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(opts.port)
    tornado.ioloop.IOLoop.instance().start()

