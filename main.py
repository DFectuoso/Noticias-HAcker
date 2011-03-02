import logging
import hashlib

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime

template.register_template_library('CustomFilters') 

# Helpers
def slow_hash(password, iterations=1000):
        h = hashlib.sha1()
        h.update(password)
        h.update('trezAwuZuQadruDef5Uh4cErABE4hAcheKusestEbrE6UjEqachuSteweJaspefU')
        for x in range(iterations):
            h.update(h.digest())
        return h.hexdigest() 

# Models
class User(db.Model):
  nickname  = db.StringProperty(required=True)
  password  = db.StringProperty(required=True) 
  created = db.DateTimeProperty(auto_now_add=True)

  def sum_votes(self):
    val = memcache.get("u_" + str(self.key())) 
    if val is not None:
      return val
    else:
      val = sum([i.value for i in self.received_votes])
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
      val = sum([i.value for i in self.votes])
      memcache.add("p_" + str(self.key()), val, 360) 
      return val 

  def already_voted(self, value):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
      # hit memcache for this
      memValue = data = memcache.get("vp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return memValue == value
      else:
        # Decidir si es 0, 1 o -1 y ponerlo en memcache
        vote = [v for v in self.votes if v.user.key() == user.key()]
        if len(vote) == 0:
          memcache.add("vp_" + str(self.key()) + "_" + str(user.key()), 0, 360)
          return False
        else:
          memcache.add("vp_" + str(self.key()) + "_" + str(user.key()), vote[0].value, 360)
          return vote[0].value == value 
    else:
      return False

  def already_voted_up(self):
    return self.already_voted(1)

  def already_voted_down(self):
    return self.already_voted(-1)

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
    hours = (datetime.now() - self.created).seconds / 60 / 60 + 1
    self.karma = float(self.sum_votes() / hours)
    self.karma = self.karma * self.karma
    self.put()

class Comment(db.Model):
  message = db.TextProperty()  
  user    = db.ReferenceProperty(User, collection_name='comments')
  post    = db.ReferenceProperty(Post, collection_name='comments')
  father  = db.SelfReferenceProperty(collection_name='childs')
  created = db.DateTimeProperty(auto_now_add=True)

class Vote(db.Model):
  user        = db.ReferenceProperty(User, collection_name='votes')
  target_user = db.ReferenceProperty(User, collection_name='received_votes')
  post        = db.ReferenceProperty(Post, collection_name='votes')
  comment     = db.ReferenceProperty(Comment, collection_name='votes')
  created     = db.DateTimeProperty(auto_now_add=True)
  value       = db.IntegerProperty(required=True)

# User Mgt Handlers
class LogoutHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.is_active():
      session.terminate()
    session.regenerate_id()
    self.redirect('/') 

class LoginHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/login.html', locals()))

  def post(self):
    # TODO: Future; allow the session to store if we got here redirected and redirect back there
    nickname = self.request.get('nickname')
    password = self.request.get('password')
    password = slow_hash(password);

    user = User.all().filter('nickname =',nickname).filter('password =',password).fetch(1)
    if len(user) == 1:
      session = get_current_session()
      if session.is_active():
        session.terminate()
      session.regenerate_id()
      session['user'] = user[0]
      self.redirect('/')
    else:
      self.redirect('/login')

class RegisterHandler(webapp.RequestHandler):
  def post(self):
    # TODO: Check if the nickname is used and display an error
    # TODO: Check for empty name and empty password
    # TODO: Future; allow the session to store if we got here redirected and redirect back there
    session = get_current_session()
    nickname = self.request.get('nickname')
    password = self.request.get('password')
    password = slow_hash(password);
    
    user = User(nickname=nickname,password=password)
    user.put()
    if session.is_active():
      session.terminate()
    session.regenerate_id()
    session['user'] = user
    self.redirect('/')

# User Handlers
class ProfileHandler(webapp.RequestHandler):
  def get(self,nickname):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    profiledUser = User.all().filter('nickname =',nickname).fetch(1)
    if len(profiledUser) == 1:
      profiledUser = profiledUser[0]
      self.response.out.write(template.render('templates/profile.html', locals()))
    else:
      self.redirect('/')
 
# News Handlers
class PostHandler(webapp.RequestHandler):
  def get(self,post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    try:
      post = db.get(post_id) 
      self.response.out.write(template.render('templates/post.html', locals()))
    except db.BadKeyError:
      self.redirect('/')

  # This adds root level comments
  def post(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      message = self.request.get('message')
      user = session['user']
      if len(message) > 0:
        try:
          post = db.get(post_id)
          post.remove_from_memcache()
          comment = Comment(message=message,user=user,post=post)
          comment.put()
          self.redirect('/noticia/' + post_id)
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/noticia/' + post_id)
    else:
      self.redirect('/login')

class CommentReplyHandler(webapp.RequestHandler):
  def get(self,comment_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    try:
      comment = db.get(comment_id) 
      self.response.out.write(template.render('templates/comment.html', locals()))
    except db.BadKeyError:
      self.redirect('/')


  def post(self,comment_id):
    session = get_current_session()
    if session.has_key('user'):
      message = self.request.get('message')
      user = session['user']
      if len(message) > 0:
        try:
          parentComment = db.get(comment_id)
          comment = Comment(message=message,user=user,post=parentComment.post, father=parentComment)
          comment.put()
          comment.post.remove_from_memcache()
          self.redirect('/noticia/' + str(parentComment.post.key()))
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/responder/' + comment_id)
    else:
      self.redirect('/login')

class SubmitNewStoryHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      self.response.out.write(template.render('templates/submit.html', locals()))
    else:
      self.redirect('/login')

  def post(self):
    url = self.request.get('url')
    title = self.request.get('title')
    message = self.request.get('message')
 
    session = get_current_session()
    if session.has_key('user') and len(title) > 0:
      user = session['user']
      # decide if its a message or a link, if its a link we need a try/catch around the save, the link might be invalid
      if len(message) == 0:
        try:
          # TODO: Make this redirect to the comment page
          post = Post(url=url,title=title,message=message, user=user)
          post.put()
          self.redirect('/');
        except db.BadValueError:
          self.redirect('/agregar')
      else:
        # TODO: Make this redirect to the comment page
        post = Post(title=title,message=message, user=user)
        post.put()
        post.url = "http://" + urlparse(self.request.url).netloc + "/noticia/" + str(post.key())
        post.put()
        self.redirect('/');
    else:
      self.refirect('/')    

# vote handlers
def handleVote(self,post_id,value):
  session = get_current_session()
  if session.has_key('user'): 
    user = session['user']
    try:
      post = db.get(post_id)
      if not post.already_voted_up() and not post.already_voted_down():
        vote = Vote(user=user, post=post, value=value, target_user=post.user)
        vote.put()
        post.remove_from_memcache()
        self.response.out.write('Ok')
      else:
        self.response.out.write('No')
    except db.BadValueError:
      self.response.out.write('Bad')
  else:
    self.response.out.write('Bad')


class UpVoteHandler(webapp.RequestHandler):
  def get(self,post_id):
    handleVote(self, post_id,1)

class DownVoteHandler(webapp.RequestHandler):
  def get(self,post_id):
    handleVote(self,post_id,-1)

# Front page
class MainHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
    posts = Post.all().order('-karma').fetch(20)
    self.response.out.write(template.render('templates/main.html', locals()))

class NewHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
    posts = Post.all().order('-created').fetch(20)
    self.response.out.write(template.render('templates/main.html', locals()))

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/nuevo', NewHandler),
      ('/agregar', SubmitNewStoryHandler),
      ('/downvote/(.+)', DownVoteHandler),
      ('/upvote/(.+)', UpVoteHandler),
      ('/perfil/(.+)', ProfileHandler),
      ('/noticia/(.+)', PostHandler),
      ('/responder/(.+)', CommentReplyHandler),
      ('/login', LoginHandler),
      ('/logout', LogoutHandler),
      ('/register', RegisterHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
