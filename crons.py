#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import cgi

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime
from gaesessions import delete_expired_sessions

from models import User, Post, Comment, Vote
from random import choice

class TopHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-karma').fetch(50)
    post = choice(posts)
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
