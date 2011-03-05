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
  about               = db.TextProperty()  

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
      memcache.add("u_" + str(self.key()), val, 360) 
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

  def url_netloc(self):
    return urlparse(self.url).netloc

  def cached_comment_count(self):
    val = memcache.get("pc_" + str(self.key())) 
    if val is not None:
      return str(val)
    else:
      val = self.comments.count() 
      memcache.add("pc_" + str(self.key()), val, 360) 
      return str(val) 

  def sum_votes(self):
    val = memcache.get("p_" + str(self.key())) 
    if val is not None:
      return val
    else:
      val = self.votes.count() 
      memcache.add("p_" + str(self.key()), val, 360) 
      return val 

  def already_voted(self):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
      # hit memcache for this
      memValue = data = memcache.get("vp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return True
      else:
        vote = [v for v in self.votes if v.user.key() == user.key()]
        if len(vote) == 0:
          return False
        else:
          memcache.add("vp_" + str(self.key()) + "_" + str(user.key()), 1, 360)
          return True 
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
    self.karma = float(self.sum_votes() / hours)
    self.karma = self.karma * self.karma
    self.put()

class Comment(db.Model):
  message = db.TextProperty()  
  user    = db.ReferenceProperty(User, collection_name='comments')
  post    = db.ReferenceProperty(Post, collection_name='comments')
  father  = db.SelfReferenceProperty(collection_name='childs')
  created = db.DateTimeProperty(auto_now_add=True)
  karma   = db.FloatProperty()

  def sum_votes(self):
    val = memcache.get("c_" + str(self.key())) 
    if val is not None:
      return val
    else:
      val = self.votes.count() 
      memcache.add("c_" + str(self.key()), val, 360) 
      return val 

  def already_voted(self):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
      # hit memcache for this
      memValue = data = memcache.get("cp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return True
      else:
        vote = [v for v in self.votes if v.user.key() == user.key()]
        if len(vote) == 0:
          return False
        else:
          memcache.add("cp_" + str(self.key()) + "_" + str(user.key()), 1, 360)
          return True 
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


