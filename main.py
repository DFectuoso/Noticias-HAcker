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

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime

from models import User, Post, Comment, Vote, prefetch_posts_list
from models import prefetch_and_order_childs_for_comment_list, prefetch_refprops
from libs import PyRSS2Gen

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
    # TODO: Check for empty name and empty password
    # TODO: Future; allow the session to store if we got here redirected and redirect back there
    session = get_current_session()
    nickname = sanitizeHtml(self.request.get('nickname'))
    password = sanitizeHtml(self.request.get('password'))
    password = User.slow_hash(password);

    already = User.all().filter("lowercase_nickname =",nickname.lower()).fetch(1)
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
      prefetch_and_order_childs_for_comment_list(comments)
      display_post_title = True
      prefetch_posts_list([post])
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
          Post.remove_cached_count_from_memcache()
          self.redirect('/noticia/' + str(post.key()));
        except db.BadValueError:
          self.redirect('/agregar')
      else:
        post = Post(title=title,message=message, user=user)
        post.put()
        post.url = "http://" + urlparse(self.request.url).netloc + "/noticia/" + str(post.key())
        post.put()
        Post.remove_cached_count_from_memcache()
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
    perPage = 20
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage
    if (page * perPage) < Post.get_cached_count():
      nextPage = page + 1

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    posts = Post.all().order('-karma').fetch(perPage, realPage * perPage)
    prefetch_posts_list(posts)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    self.response.out.write(template.render('templates/main.html', locals()))



def filter_user_comments(all_comments, user):
  """ This function removes comments that belong to a thread 
  which had a comment by the same user as a parent """
  res_comments = []
  for user_comment in all_comments:
    linked_comment = user_comment
    while(True):
      if Comment.father.get_value_for_datastore(linked_comment) is None:
        res_comments.append(user_comment)
        break
      if linked_comment.father.user == user:
        break
      linked_comment = linked_comment.father
  return res_comments

class ThreadsHandler(webapp.RequestHandler):
  def get(self,nickname):
    page = sanitizeHtml(self.request.get('pagina'))
    perPage = 5
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    thread_user = User.all().filter('lowercase_nickname =',nickname.lower()).fetch(1)
    if len(thread_user) > 0:
      thread_user = thread_user[0]
      user_comments = Comment.all().filter('user =',thread_user).order('-created').fetch(perPage, realPage * perPage)
      comments = filter_user_comments(user_comments, thread_user)
      prefetch_and_order_childs_for_comment_list(comments)
      if (page * perPage) < Comment.all().filter('user =', thread_user).count():
        nextPage = page + 1
      self.response.out.write(template.render('templates/threads.html', locals()))
    else:
      self.redirect('/')

class NewHandler(webapp.RequestHandler):
  def get(self):
    page = sanitizeHtml(self.request.get('pagina'))
    perPage = 20
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage
    if (page * perPage) < Post.get_cached_count():
      nextPage = page + 1

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    posts = Post.all().order('-created').fetch(perPage,perPage * realPage)
    prefetch_posts_list(posts)
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

class RssHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-created').fetch(20)
    prefetch_posts_list(posts)

    items = []
    for post in posts:
       if len(post.message) == 0:
          rss_poster = post.url
      else:
          rss_poster = post.message
      items.append(PyRSS2Gen.RSSItem(
          title = post.title,
          link = "http://noticiashacker.com/noticia/" + str(post.key()),
          description = rss_poster,
          guid = PyRSS2Gen.Guid("guid1"),
          pubDate = post.created
      ))

    rss = PyRSS2Gen.RSS2(
            title = "Noticias Hacker",
            link = "http://noticiashacker.com/",
            description = "Noticias Hacker",
            lastBuildDate = datetime.now(),
            items = items
          )
    print 'Content-Type: text/xml'
    self.response.out.write(rss.to_xml('utf-8'))

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/conversaciones/(.+)', ThreadsHandler),
      ('/directrices', GuidelinesHandler),
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
      ('/rss', RssHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
