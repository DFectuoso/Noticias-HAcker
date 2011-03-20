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

def get_comment_from_list(comment_key,comments):
  return [comment for comment in comments if comment.key() ==  comment_key]

def order_comment_list_in_memory(comments):
  # order childs for display
  for comment in comments:
    comment.processed_child = []
  for comment in comments:
    father_key = Comment.father.get_value_for_datastore(comment)
    if father_key is not None:
      father_comment = get_comment_from_list(father_key,comments)
      if len(father_comment) == 1:
        father_comment[0].processed_child.append(comment)
  return comments

# Models
class User(db.Model):
  lowercase_nickname  = db.StringProperty(required=True)
  nickname            = db.StringProperty(required=True)
  password            = db.StringProperty(required=True)
  created             = db.DateTimeProperty(auto_now_add=True)
  about               = db.TextProperty(required=False)
  hnuser              = db.StringProperty(required=False, default="")
  twitter             = db.StringProperty(required=False, default="")
  email               = db.EmailProperty(required=False)
  url                 = db.LinkProperty(required=False)

  @staticmethod
  def slow_hash(password, iterations=1000):
    h = hashlib.sha1()
    h.update(password)
    h.update(keys.salt_key)
    for x in range(iterations):
      h.update(h.digest())
    return h.hexdigest()

  def sum_votes(self):
    val = memcache.get("u_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = Vote.all().filter("user !=",self).filter("target_user =",self).count()
      memcache.add("u_" + str(self.key()), val, 3600)
      return val

  def remove_from_memcache(self):
    memcache.delete("u_" + str(self.key()))

class Post(db.Model):
  title   = db.StringProperty(required=True)
  url     = db.LinkProperty(required=False)
  message = db.TextProperty()
  user    = db.ReferenceProperty(User, collection_name='posts')
  created = db.DateTimeProperty(auto_now_add=True)
  karma   = db.FloatProperty()

  def to_json(self):
    return {
      'id':str(self.key()),
      'title':self.title,
      'message':self.message,
      'created':self.created.strftime("%s"),
      'user':self.user.nickname,
      'comment_count':self.cached_comment_count(),
      'votes':self.sum_votes()}

  def url_netloc(self):
    return urlparse(self.url).netloc

  def cached_comment_count(self):
    val = memcache.get("pc_" + str(self.key()))
    if val is not None:
      return str(val)
    else:
      val = self.comments.count()
      memcache.add("pc_" + str(self.key()), val, 3600)
      return str(val)

  def sum_votes(self):
    val = memcache.get("p_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = self.votes.count()
      memcache.add("p_" + str(self.key()), val, 3600)
      return val

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
    self.karma = self.sum_votes() / float(hours)
    self.karma = self.karma * self.karma
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

  def sum_votes(self):
    val = memcache.get("c_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = self.votes.count()
      memcache.add("c_" + str(self.key()), val, 3600)
      return val

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
    self.karma = float(self.sum_votes() / hours)
    self.karma = self.karma * self.karma
    self.put()

class Vote(db.Model):
  user        = db.ReferenceProperty(User, collection_name='votes')
  target_user = db.ReferenceProperty(User, collection_name='received_votes')
  post        = db.ReferenceProperty(Post, collection_name='votes')
  comment     = db.ReferenceProperty(Comment, collection_name='votes')
  created     = db.DateTimeProperty(auto_now_add=True)


