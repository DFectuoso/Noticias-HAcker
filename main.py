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

from models import User, Post, Comment, Vote

template.register_template_library('CustomFilters') 

def sanitizeHtml(value):                                                                 
  return cgi.escape(value)

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
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      self.redirect('/logout')
    else:
      self.response.out.write(template.render('templates/login.html', locals()))

  def post(self):
    # TODO: Future; allow the session to store if we got here redirected and redirect back there
    nickname = sanitizeHtml(self.request.get('nickname'))
    password = sanitizeHtml(self.request.get('password'))
    password = User.slow_hash(password);

    user = User.all().filter('lowercase_nickname =',nickname.lower()).filter('password =',password).fetch(1)
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
    nickname = sanitizeHtml(self.request.get('nickname'))
    password = sanitizeHtml(self.request.get('password'))
    password = User.slow_hash(password);
    
    already = User.all().filter("nickname =",nickname).fetch(1)
    if len(already) == 0:
      user = User(nickname=nickname, lowercase_nickname=nickname.lower(),password=password)
      user.put()
      if session.is_active():
        session.terminate()
      session.regenerate_id()
      session['user'] = user
      self.redirect('/')
    else:
      self.redirect('/login')

# User Handlers
class ProfileHandler(webapp.RequestHandler):
  def get(self,nickname):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    profiledUser = User.all().filter('nickname =',nickname).fetch(1)
    if len(profiledUser) == 1:
      profiledUser = profiledUser[0]
      #TODO fix this horrible way of testing for the user
      if session.has_key('user') and user.key() == profiledUser.key():
        my_profile = True
      self.response.out.write(template.render('templates/profile.html', locals()))
    else:
      self.redirect('/')

  def post(self,nickname):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      profiledUser = User.all().filter('nickname =',nickname).fetch(1)
      if len(profiledUser) == 1:
        profiledUser = profiledUser[0]
      if user.key() == profiledUser.key():
        about = sanitizeHtml(self.request.get('about'))
        user.about = about
        user.put() 
        my_profile = True
        self.redirect('/perfil/' + user.nickname)
      else:
        self.redirect('/')
    else:
      self.redirect('/login')

 
 
# News Handlers
class PostHandler(webapp.RequestHandler):
  def get(self,post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    try:
      post = db.get(post_id) 
      comments = Comment.all().filter("post =", post.key()).order("-karma").fetch(1000)
      self.response.out.write(template.render('templates/post.html', locals()))
    except db.BadKeyError:
      self.redirect('/')

  # This adds root level comments
  def post(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      message = sanitizeHtml(self.request.get('message'))
      user = session['user']
      if len(message) > 0:
        try:
          post = db.get(post_id)
          post.remove_from_memcache()
          comment = Comment(message=message,user=user,post=post)
          comment.put()
          vote = Vote(user=user, comment=comment, target_user=user)
          vote.put()
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
      message = sanitizeHtml(self.request.get('message'))
      user = session['user']
      if len(message) > 0:
        try:
          parentComment = db.get(comment_id)
          comment = Comment(message=message,user=user,post=parentComment.post, father=parentComment)
          comment.put()
          comment.post.remove_from_memcache()
          vote = Vote(user=user, comment=comment, target_user=user)
          vote.put()
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
    title = sanitizeHtml(self.request.get('title'))
    message = sanitizeHtml(self.request.get('message'))
 
    session = get_current_session()
    if session.has_key('user') and len(title) > 0:
      user = session['user']
      # decide if its a message or a link, if its a link we need a try/catch around the save, the link might be invalid
      if len(message) == 0:
        try:
          post = Post(url=url,title=title,message=message, user=user)
          post.put()
          vote = Vote(user=user, post=post, target_user=post.user)
          vote.put()
          self.redirect('/noticia/' + str(post.key()));
        except db.BadValueError:
          self.redirect('/agregar')
      else:
        post = Post(title=title,message=message, user=user)
        post.put()
        post.url = "http://" + urlparse(self.request.url).netloc + "/noticia/" + str(post.key())
        post.put()
        vote = Vote(user=user, post=post, target_user=post.user)
        vote.put()
        self.redirect('/noticia/' + str(post.key()));
    else:
      self.redirect('/')    

# vote handlers
class UpVoteHandler(webapp.RequestHandler):
  def get(self,post_id):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
      try:
        post = db.get(post_id)
        if not post.already_voted():
          vote = Vote(user=user, post=post, target_user=post.user)
          vote.put()
          post.remove_from_memcache()
          post.user.remove_from_memcache()
          self.response.out.write('Ok')
        else:
          self.response.out.write('No')
      except db.BadValueError:
        self.response.out.write('Bad')
    else:
      self.response.out.write('Bad')

class UpVoteCommentHandler(webapp.RequestHandler):
  def get(self,comment_id):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
      try:
        comment = db.get(comment_id)
        if not comment.already_voted():
          vote = Vote(user=user, comment=comment, target_user=comment.user)
          vote.put()
          comment.remove_from_memcache()
          comment.user.remove_from_memcache()
          self.response.out.write('Ok')
        else:
          self.response.out.write('No')
      except db.BadValueError:
        self.response.out.write('Bad')
    else:
      self.response.out.write('Bad')

# Front page
class MainHandler(webapp.RequestHandler):
  def get(self):
    page = sanitizeHtml(self.request.get('pagina'))
    if not page:
      page = 1
    else: 
      page = int(page)
    nextPage = page + 1
    realPage = page - 1
    perPage = 20
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
    posts = Post.all().order('-karma').fetch(perPage, realPage * perPage)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    self.response.out.write(template.render('templates/main.html', locals()))

class NewHandler(webapp.RequestHandler):
  def get(self):
    page = sanitizeHtml(self.request.get('pagina'))
    if not page:
      page = 1
    else: 
      page = int(page)
    nextPage = page + 1
    realPage = page - 1
    perPage = 20
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
    posts = Post.all().order('-created').fetch(perPage,perPage * realPage)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    self.response.out.write(template.render('templates/main.html', locals()))

class GuidelinesHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/guidelines.html', locals()))

class FAQHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/faq.html', locals()))

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/lineamientos', GuidelinesHandler),
      ('/preguntas-frecuentes', FAQHandler),
      ('/nuevo', NewHandler),
      ('/agregar', SubmitNewStoryHandler),
      ('/upvote/(.+)', UpVoteHandler),
      ('/upvote_comment/(.+)', UpVoteCommentHandler),
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
