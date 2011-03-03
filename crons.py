import logging
import hashlib

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime
from gaesessions import delete_expired_sessions

from models import User, Post, Comment, Vote

class TopHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-karma').fetch(100)
    for post in posts:
      post.calculate_karma()
    self.response.out.write("ok")

class SessionsHandler(webapp.RequestHandler):
  def get(self):
    while not delete_expired_sessions():
      pass
    self.response.out.write("ok")

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/tasks/update_top_karma', TopHandler),
      ('/tasks/cleanup_sessions', SessionsHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
