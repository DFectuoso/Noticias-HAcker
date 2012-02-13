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
import keys
import sys

from google.appengine.ext.db import ReferencePropertyResolveError
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache, taskqueue
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime
from gaesessions import delete_expired_sessions

from models import User, Post, Comment, Vote, Notification 
from random import choice

from libs import bitly
sys.path.insert(0, 'libs/tweepy.zip')
import tweepy
import helper


class ReIndexTankHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().fetch(10000)
    base_url = helper.base_url(self) 
    for post in posts:
      taskqueue.add(url='/admin/re-index-tank-task', params={'post_key': str(post.key()), 'base_url': base_url})
    self.response.out.write("ok")

class ReIndexTankTaskHandler(webapp.RequestHandler):
  def post(self):
    post = db.get(self.request.get('post_key'))
    base_url = self.request.get('base_url')
    helper.indextank_document(base_url, post) 

class DeleteNotificationsOfDeletedHandler(webapp.RequestHandler):
  def get(self):
    notifications = Notification.all().fetch(2000)
    for notification in notifications:
      taskqueue.add(url='/admin/delete-notification-of-deleted-comments', params={'notification_key': str(notification.key())})

  def post(self):
    notification = db.get(self.request.get("notification_key"))
    try:
      post = notification.post
      comment = notification.comment
    except ReferencePropertyResolveError:
      logging.info("WE HAVE A NOTIFICATION That failed")
      notification.target_user.remove_notifications_from_memcache()
      notification.delete()

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/admin/re-index-tank', ReIndexTankHandler),
      ('/admin/re-index-tank-task', ReIndexTankTaskHandler),
      ('/admin/delete-notification-of-deleted-comments', DeleteNotificationsOfDeletedHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
