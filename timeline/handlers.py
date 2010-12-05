import os
import sys
import logging
import datetime
import json

import tornado.web
from tornado.web import authenticated
from tornado.escape import xhtml_escape

from timeline import db
import timeline.poll

ch = logging.StreamHandler(sys.stderr)
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
ch.setFormatter(formatter)

logging.getLogger('').setLevel(logging.WARNING)

all_handlers = []

class HandlerMeta(type(tornado.web.RequestHandler)):

    def __init__(cls, name, bases, cls_dict):
        super(HandlerMeta, cls).__init__(name, bases, cls_dict)
        if not cls_dict.get('abstract', False):
            all_handlers.append((cls.path, cls))

class RequestHandler(tornado.web.RequestHandler):
    """Customized RequestHandler instance for timeline."""

    __metaclass__ = HandlerMeta
    abstract = True

    log = logging.getLogger('timeline')

    def initialize(self):
        super(RequestHandler, self).initialize()
        self.log.info('%s %s' % (self.request.method, self.request.path))
        self.env = {'show_flash': self.show_flash}

    def get_current_user(self):
        user_id = self.get_secure_cookie('s')
        if user_id:
            return db.User.by_id(int(user_id))

    def render(self, template, **kw):
        self.env.update(kw)
        super(RequestHandler, self).render(template, **self.env)
       
    def save_error(self, msg):
        self.set_secure_cookie('e', msg)
    
    def save_info(self, msg):
        self.set_secure_cookie('i', msg)
    
    def show_flash(self):
        err = self.get_secure_cookie('e')
        info = self.get_secure_cookie('i')

        s = ''
        if err:
            s += '<div class="error">%s</div>' % (xhtml_escape(err),)
            self.clear_cookie('e')
        if info:
            s += '<div class="info">%s</div>' % (xhtml_escape(info),)
            self.clear_cookie('i')
        return s

    def render_json(self, obj):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(obj))

RequestHandler.log.setLevel(logging.DEBUG)
RequestHandler.log.addHandler(ch)

def get_application(**extra):
    settings = {
        'cookie_secret': 'gQbwoaY24zeYadFUK4L+ZjXDZwAQeeNC4NGPxmZ7rVUV4UYCU3MG2bIY7IllluWt',
        'login_url': '/login',
        'xsrf_cookies': True
        }
    base_path = None
    try:
        base_path = extra.pop('base_path')
    except KeyError:
        pass
    if base_path:
        settings['static_path'] = os.path.join(base_path, 'static')
        settings['template_path'] = os.path.join(base_path, 'templates')
    settings.update(extra)
    return tornado.web.Application(all_handlers, **settings)

########################
#  REQUEST HANDLERS
########################

class HomeHandler(RequestHandler):

    path = '/'
    def initialize(self):
        super(HomeHandler, self).initialize()
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        self.env['events_list'] = db.Event.list_by_minute(start_time=one_hour_ago, end_time=datetime.datetime.now())

    def get(self):
        self.render('home.html')

class LoginHandler(RequestHandler):

    path = '/login'

    def get(self):
        timeline.poll.notify_all()
        self.render('login.html')

    def post(self):
        username = self.get_argument('username', None)
        password = self.get_argument('password', None)
        if not (username and password):
            self.redirect('/login')
            return
        username = str(username)
        user = db.User.authenticate(username, password)
        if user:
            self.set_secure_cookie('s', '%d' % (user.id,))
            self.redirect('/')
            return
        # user does not exist, or the password was wrong
        user = db.User.create(username, password)
        if user:
            self.set_secure_cookie('s', '%d' % (user.id,))
            self.redirect('/')
            return

        self.save_error('wrong password')

        # wrong password was entered!
        self.redirect('/')

class LogoutHandler(RequestHandler):

    path = '/logout'

    def get(self):
        self.clear_cookie('s')
        self.redirect('/')

class EventCreateHandler(RequestHandler):
    path = '/event/new'

    def get(self):
        self.render('event.html')

    def post(self):
        event_name = xhtml_escape(self.get_argument('event_name', None))
        timestamp = self.get_argument('timestamp', datetime.datetime.now())
        details = xhtml_escape(self.get_argument('details', None))
        db.Event.create(event_name, timestamp, details)
        self.redirect('/')

class TagCreateHandler(RequestHandler):
    path = '/tag/new'

    def get(self):
        self.render('tag.html')

    def post(self):
        tag_name = self.get_argument('tag_name')
        db.Tag.create(tag_name)
        self.redirect('/')

class AddTagToEventHandler(RequestHandler):
    path = '/tag/add'

    def get(self):
        self.render('add_tag.html')

    def post(self):
        tag_id = self.get_argument('tag_id', None)
        event_id = self.get_argument('event_id', None)
        db.Event.by_id(event_id).tags.append(db.Tag.by_id(tag_id))
        self.redirect('/')
