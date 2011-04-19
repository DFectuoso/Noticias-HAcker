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
import keys

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime

# Models
class User(db.Model):
  lowercase_nickname  = db.StringProperty(required=True)
  nickname            = db.StringProperty(required=True)
  password            = db.StringProperty(required=True)
  created             = db.DateTimeProperty(auto_now_add=True)
  about               = db.TextProperty(required=False)
  hnuser              = db.StringProperty(required=False, default="")
  github              = db.StringProperty(required=False, default="")
  location            = db.StringProperty(required=False, default="")
  twitter             = db.StringProperty(required=False, default="")
  email               = db.EmailProperty(required=False)
  url                 = db.LinkProperty(required=False)
  admin               = db.BooleanProperty(default=False)
  karma               = db.IntegerProperty(required=False)

  @staticmethod
  def slow_hash(password, iterations=1000):
    h = hashlib.sha1()
    h.update(unicode(password).encode("utf-8"))
    h.update(keys.salt_key)
    for x in range(iterations):
      h.update(h.digest())
    return h.hexdigest()

  def average_karma(self):
    delta = (datetime.now() - self.created)
    days = delta.days
    votes = self.karma
    if votes is None:
      votes = 0
    if days > 0:
      return votes/float(days)
    else:
      return votes

  def sum_votes(self):
    val = memcache.get("u_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = Vote.all().filter("user !=",self).filter("target_user =",self).count()
      self.karma = val
      self.put()
      memcache.add("u_" + str(self.key()), val, 3600)
      return val

  def remove_from_memcache(self):
    memcache.delete("u_" + str(self.key()))

  def has_notifications(self):
    count_notificationes = memcache.get("user_notification_" + str(self.key()))
    if count_notificationes is not None:
      return count_notificationes > 0 
    else:
      count_notificationes = Notification.all().filter("target_user =",self).filter("read =", False).count()
      memcache.add("user_notification_" + str(self.key()), count_notificationes, 3600)
      return count_notificationes > 0 

  def remove_notifications_from_memcache(self):
    memcache.delete("user_notification_" + str(self.key()))

class Post(db.Model):
  title     = db.StringProperty(required=True)
  url       = db.LinkProperty(required=False)
  message   = db.TextProperty()
  user      = db.ReferenceProperty(User, collection_name='posts')
  created   = db.DateTimeProperty(auto_now_add=True)
  karma     = db.FloatProperty()
  edited    = db.BooleanProperty(default=False)
  twittered = db.BooleanProperty(default=False)

  def to_json(self):
    return {
      'id':str(self.key()),
      'title':self.title,
      'message':self.message,
      'created':self.created.strftime("%s"),
      'user':self.user.nickname,
      'comment_count':self.cached_comment_count,
      'url':self.url,	  
      'votes':self.prefetched_sum_votes}

  def url_netloc(self):
    return urlparse(self.url).netloc

  def can_edit(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      if self.user.key() == user.key() or user.admin:
        return True
    return False

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def sum_votes(self):
    val = memcache.get("p_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = self.votes.count()
      memcache.add("p_" + str(self.key()), val, 3600)
      return val

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def already_voted(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      # hit memcache for this
      memValue = memcache.get("vp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return memValue == 1
      else:
        vote = Vote.all().filter("user =", user).filter("post =", self).fetch(1)
        memcache.add("vp_" + str(self.key()) + "_" + str(user.key()), len(vote), 3600)
        return len(vote) == 1
    else:
      return False

  def remove_from_memcache(self):
    memcache.delete("pc_" + str(self.key()))
    memcache.delete("p_" + str(self.key()))
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      user.remove_from_memcache()
      memcache.delete("vp_" + str(self.key()) + "_" + str(user.key()))
    self.calculate_karma()

  def calculate_karma(self):
    delta = (datetime.now() - self.created)
    seconds = delta.seconds + delta.days*86400
    hours = seconds / 3600 + 1
    votes = self.sum_votes() 
    gravity = 1.8
    karma = (votes - 1) / pow((hours + 2), gravity)
    self.karma = karma 
    self.put()

  @staticmethod
  def remove_cached_count_from_memcache():
    memcache.delete("Post_count")

  @staticmethod
  def get_cached_count():
    memValue = memcache.get("Post_count")
    if memValue is not None:
      return memValue
    else:
      count = Post.all().count()
      memcache.add("Post_count",count,3600)
      return count

class Comment(db.Model):
  message = db.TextProperty()
  user    = db.ReferenceProperty(User, collection_name='comments')
  post    = db.ReferenceProperty(Post, collection_name='comments')
  father  = db.SelfReferenceProperty(collection_name='childs')
  created = db.DateTimeProperty(auto_now_add=True)
  karma   = db.FloatProperty()
  edited  = db.BooleanProperty(default=False)

  def father_ref(self):
    return Comment.father.get_value_for_datastore(self)

  def to_json(self):
    childs_json = map(lambda u: u.to_json(), self.processed_child)
    return {
      'message':self.message,
      'created':self.created.strftime("%s"),
      'user':self.user.nickname,
      'votes':self.prefetched_sum_votes,
      'comments': childs_json}

  def can_edit(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      if self.user.key() == user.key() or user.admin:
        return True
    return False

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def sum_votes(self):
    val = memcache.get("c_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = self.votes.count()
      memcache.add("c_" + str(self.key()), val, 3600)
      return val

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def already_voted(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      # hit memcache for this
      memValue = memcache.get("cp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return memValue == 1
      else:
        vote = Vote.all().filter("user =", user).filter("comment =", self).fetch(1)
        memcache.add("cp_" + str(self.key()) + "_" + str(user.key()), len(vote), 3600)
        return len(vote) == 1
    else:
      return False

  def remove_from_memcache(self):
    memcache.delete("c_" + str(self.key()))
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      user.remove_from_memcache()
      memcache.delete("cp_" + str(self.key()) + "_" + str(user.key()))
    self.calculate_karma()

  def calculate_karma(self):
    delta = (datetime.now() - self.created)
    seconds = delta.seconds + delta.days*86400
    hours = seconds / 3600 + 1
    votes = self.sum_votes() 
    gravity = 1.8
    karma = (votes - 1) / pow((hours + 2), gravity)
    self.karma = karma 
    self.put()

class Vote(db.Model):
  user        = db.ReferenceProperty(User, collection_name='votes')
  target_user = db.ReferenceProperty(User, collection_name='received_votes')
  post        = db.ReferenceProperty(Post, collection_name='votes')
  comment     = db.ReferenceProperty(Comment, collection_name='votes')
  created     = db.DateTimeProperty(auto_now_add=True)

class Notification(db.Model):
  target_user = db.ReferenceProperty(User, collection_name='notifications')
  sender_user = db.ReferenceProperty(User, collection_name='send_notifications')
  post        = db.ReferenceProperty(Post)
  comment     = db.ReferenceProperty(Comment)
  created     = db.DateTimeProperty(auto_now_add=True)
  read        = db.BooleanProperty(default=False)

  @staticmethod
  def create_notification_for_comment_and_user(comment,target_user):
    notification = Notification(target_user=target_user,post=comment.post,comment=comment,sender_user=comment.user)
    notification.put()
    target_user.remove_notifications_from_memcache()
    return notification

class Ticket(db.Model):
  user        = db.ReferenceProperty(User, collection_name='tickets')
  is_active   = db.BooleanProperty(default=True)
  code        = db.StringProperty(required=True)
  created     = db.DateTimeProperty(auto_now_add=True)
  
  @staticmethod
  def create_code(seed, iterations=1000):
    h = hashlib.sha1()
    h.update(unicode(seed).encode("utf-8"))
    h.update(keys.salt_key)
    for x in range(iterations):
      h.update(h.digest())
    return h.hexdigest()
  
  @staticmethod
  def deactivate_others(user):
    tickets = Ticket.all()
    print (tickets)
    for ticket in tickets:
      ticket.is_active = False
      ticket.put()
      
  
