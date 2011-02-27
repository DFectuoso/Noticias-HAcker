from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template

from google.appengine.ext.webapp.util import run_wsgi_app
from gaesessions import get_current_session

from urlparse import urlparse
import hashlib

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

class Post(db.Model):
  title   = db.StringProperty(required=True)
  url     = db.LinkProperty(required=False)
  message = db.TextProperty()  
  user    = db.ReferenceProperty(User, collection_name='posts')

class Comment(db.Model):
  message = db.TextProperty()  
  user    = db.ReferenceProperty(User, collection_name='comments')
  post    = db.ReferenceProperty(Post, collection_name='comments')
  father  = db.SelfReferenceProperty(collection_name='childs')

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

  def post(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      message = self.request.get('message')
      user = session['user']
      if len(message) > 0:
        try:
          post = db.get(post_id)
          comment = Comment(message=message,user=user,post=post)
          comment.put()
          self.redirect('/noticia/' + post_id)
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/noticia/' + post_id)
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


# Front page
class MainHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'): 
      user = session['user']
    posts = Post.all().fetch(20)
    self.response.out.write(template.render('templates/main.html', locals()))

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/agregar', SubmitNewStoryHandler),
      ('/perfil/(.+)', ProfileHandler),
      ('/noticia/(.+)', PostHandler),
      ('/login', LoginHandler),
      ('/logout', LogoutHandler),
      ('/register', RegisterHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
