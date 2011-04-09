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
import prefetch
import helper

from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification

#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

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
    if session.has_key('register_error'):
      register_error = session.pop('register_error')
    if session.has_key('login_error'):
      login_error = session.pop('login_error')
    if session.has_key('login_error_nickname'):
      login_error_nickname = session.pop('login_error_nickname')

    if session.has_key('user'):
      user = session['user']
      self.redirect('/logout')
    else:
      self.response.out.write(template.render('templates/login.html', locals()))

  def post(self):
    session = get_current_session()
    nickname = helper.sanitizeHtml(self.request.get('nickname'))
    password = helper.sanitizeHtml(self.request.get('password'))
    password = User.slow_hash(password);

    user = User.all().filter('lowercase_nickname =',nickname.lower()).filter('password =',password).fetch(1)
    if len(user) == 1:
      if session.is_active():
        session.terminate()
      session.regenerate_id()
      session['user'] = user[0]
      self.redirect('/')
    else:
      session['login_error'] = "Usuario y password incorrectos"
      session['login_error_nickname'] = nickname
      self.redirect('/login')

class RegisterHandler(webapp.RequestHandler):
  def post(self):
    session = get_current_session()
    nickname = helper.sanitizeHtml(self.request.get('nickname'))
    password = helper.sanitizeHtml(self.request.get('password'))
    
    if len(nickname) > 1 and len(password) > 1:
      password = User.slow_hash(password);
      already = User.all().filter("lowercase_nickname =",nickname.lower()).fetch(1)
      if len(already) == 0:
        user = User(nickname=nickname, lowercase_nickname=nickname.lower(),password=password, about="")
        user.put()
        if session.is_active():
          session.terminate()
        session.regenerate_id()
        session['user'] = user
        self.redirect('/')
      else:
        session['register_error'] = "Ya existe alguien con ese nombre de usuario " + nickname
        self.redirect('/login')
    else:
      session['register_error'] = "Porfavor escribe un username y un password"
      self.redirect('/login')

# User Handlers
class ProfileHandler(webapp.RequestHandler):
  def get(self,nickname):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    if session.has_key('profile_saved'):
      profile_saved = session.pop('profile_saved')
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
        about = helper.sanitizeHtml(self.request.get('about'))
        hnuser = helper.sanitizeHtml(self.request.get('hnuser'))
        location = helper.sanitizeHtml(self.request.get('location'))
        github = helper.sanitizeHtml(self.request.get('github'))
        twitter = helper.sanitizeHtml(self.request.get('twitter'))
        email = helper.sanitizeHtml(self.request.get('email'))
        url = helper.sanitizeHtml(self.request.get('url'))

        user.about = about
        user.location = location
        user.github = github
        user.hnuser = hnuser
        user.twitter = twitter
        try:
          user.email = email
        except db.BadValueError:
          pass
        try:
          user.url = url
        except db.BadValueError:
          pass
        user.put()
        my_profile = True
        session['profile_saved'] = True 
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
      post = db.get(helper.parse_post_id(post_id))
      comments = Comment.all().filter("post =", post.key()).order("-karma").fetch(1000)
      comments = helper.order_comment_list_in_memory(comments)
      prefetch.prefetch_comment_list(comments)
      display_post_title = True
      prefetch.prefetch_posts_list([post])
      if helper.is_json(post_id):
        comments_json = [c.to_json() for c in comments if not c.father_ref()] 
        if(self.request.get('callback')):
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'post':post.to_json(),'comments':comments_json})+')')
        else:
          self.response.headers['Content-Type'] = "application/json"
          self.response.out.write(simplejson.dumps({'post':post.to_json(),'comments':comments_json}))
      else:
        self.response.out.write(template.render('templates/post.html', locals()))
    except db.BadKeyError:
      self.redirect('/')

  # This adds root level comments
  def post(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      message = helper.sanitizeHtml(self.request.get('message'))
      user = session['user']
      if len(message) > 0:
        try:
          post = db.get(post_id)
          post.remove_from_memcache()
          comment = Comment(message=message,user=user,post=post)
          comment.put()
          vote = Vote(user=user, comment=comment, target_user=user)
          vote.put()
          Notification.create_notification_for_comment_and_user(comment,post.user)
          self.redirect('/noticia/' + post_id)
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/noticia/' + post_id)
    else:
      self.redirect('/login')

class EditPostHandler(webapp.RequestHandler):
  def get(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        post = db.get(helper.parse_post_id(post_id))
        if post.can_edit():
          self.response.out.write(template.render('templates/edit-post.html', locals()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')
    else:
      self.redirect('/')

  def post(self, post_id):
    session = get_current_session()
    title = helper.sanitizeHtml(self.request.get('title'))
    message = helper.sanitizeHtml(self.request.get('message'))

    if session.has_key('user'):
      user = session['user']
      try:
        post = db.get(helper.parse_post_id(post_id))
        if post.can_edit():
          if len(title) > 0:
            post.title = title
          if post.message is not None and message is not None:
            post.message = message
          post.edited = True
          post.put()
          self.redirect('/noticia/' + str(post.key()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')  
    else:
      self.redirect('/')

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
      message = helper.sanitizeHtml(self.request.get('message'))
      user = session['user']
      if len(message) > 0:
        try:
          parentComment = db.get(comment_id)
          comment = Comment(message=message,user=user,post=parentComment.post, father=parentComment)
          comment.put()
          comment.post.remove_from_memcache()
          vote = Vote(user=user, comment=comment, target_user=user)
          vote.put()
          Notification.create_notification_for_comment_and_user(comment,parentComment.user)
          self.redirect('/noticia/' + str(parentComment.post.key()))
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/responder/' + comment_id)
    else:
      self.redirect('/login')

class EditCommentHandler(webapp.RequestHandler):
  def get(self, comment_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        comment = db.get(helper.parse_post_id(comment_id))
        if comment.can_edit():
          self.response.out.write(template.render('templates/edit-comment.html', locals()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')
    else:
      self.redirect('/')

  def post(self, comment_id):
    session = get_current_session()
    message = helper.sanitizeHtml(self.request.get('message'))

    if session.has_key('user'):
      user = session['user']
      try:
        comment = db.get(helper.parse_post_id(comment_id))
        if comment.can_edit():
          if message is not None:
            comment.message = message
          comment.edited = True
          comment.put()
          self.redirect('/noticia/' + str(comment.post.key()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')  
    else:
      self.redirect('/')

class SubmitNewStoryHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('post_error'):
      post_error = session.pop('post_error')

    if session.has_key('user'):
      user = session['user']
      get_url = helper.sanitizeHtml(self.request.get('url_bookmarklet'))
      get_title = helper.sanitizeHtml(self.request.get('title_bookmarklet'))
      self.response.out.write(template.render('templates/submit.html', locals()))
    else:
      self.redirect('/login')

  def post(self):
    session = get_current_session()
    url = self.request.get('url')
    title = helper.sanitizeHtml(self.request.get('title'))
    message = helper.sanitizeHtml(self.request.get('message'))

    if session.has_key('user'):
      if len(title) > 0:
        user = session['user']
        if len(message) == 0: #is it a post or a message?
          #Check that we don't have the same URL within the last 'check_days'
          since_date = date.today() - timedelta(days=7)
          q = Post.all().filter("created >", since_date).filter("url =", url).count()
          url_exists = q > 0
          try:
            if not url_exists:
              post = Post(url=url,title=title,message=message, user=user)
              post.put()
              vote = Vote(user=user, post=post, target_user=post.user)
              vote.put()
              Post.remove_cached_count_from_memcache()
              self.redirect('/noticia/' + str(post.key()));
            else:
              session['post_error'] = "Este link ha sido entregado en los ultimo 7 dias"
              self.redirect('/agregar')
          except db.BadValueError:
            session['post_error'] = "El formato del link no es valido"
            self.redirect('/agregar')
        else:
          post = Post(title=title,message=message, user=user)
          post.put()
          post.url = helper.base_url(self) + "/noticia/" + str(post.key())
          post.put()
          Post.remove_cached_count_from_memcache()
          vote = Vote(user=user, post=post, target_user=post.user)
          vote.put()
          self.redirect('/noticia/' + str(post.key()));
      else:
        session['post_error'] = "Necesitas agregar un titulo"
        self.redirect('/agregar')
    else:
      self.redirect('/login')

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
    page = helper.sanitizeHtml(self.request.get('pagina'))
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
    prefetch.prefetch_posts_list(posts)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    if helper.is_json(self.request.url):
      posts_json = [p.to_json() for p in posts]
      if(self.request.get('callback')):
        self.response.headers['Content-Type'] = "application/javascript"
        self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'posts':posts_json})+');')
      else:
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(simplejson.dumps({'posts':posts_json}))
    else:
      self.response.out.write(template.render('templates/main.html', locals()))

class ThreadsHandler(webapp.RequestHandler):
  def get(self,nickname):
    page = helper.sanitizeHtml(self.request.get('pagina'))
    perPage = 6
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage
    # this is used to tell the template to include the topic
    threads = True

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    thread_user = User.all().filter('lowercase_nickname =',nickname.lower()).fetch(1)
    if len(thread_user) > 0:
      thread_user = thread_user[0]
      user_comments = Comment.all().filter('user =',thread_user).order('-created').fetch(perPage, realPage * perPage)
      comments = helper.filter_user_comments(user_comments, thread_user)
      if (page * perPage) < Comment.all().filter('user =', thread_user).count():
        nextPage = page + 1
      self.response.out.write(template.render('templates/threads.html', locals()))
    else:
      self.redirect('/')

class NewHandler(webapp.RequestHandler):
  def get(self):
    page = helper.sanitizeHtml(self.request.get('pagina'))
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
    prefetch.prefetch_posts_list(posts)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    if helper.is_json(self.request.url):
      posts_json = [p.to_json() for p in posts]
      if(self.request.get('callback')):
        self.response.headers['Content-Type'] = "application/javascript"
        self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'posts':posts_json})+');')
      else:
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(simplejson.dumps({'posts':posts_json}))
    else:
      self.response.out.write(template.render('templates/main.html', locals()))

class UserPostsHandler(webapp.RequestHandler):
  def get(self, user):
    page = helper.sanitizeHtml(self.request.get('pagina'))
    target_user_str= helper.sanitizeHtml(helper.parse_post_id(user))
    perPage = 20
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    target_user = User.all().filter('lowercase_nickname =', target_user_str).fetch(1)
    if len(target_user) > 0:
      posts = Post.all().filter('user =',target_user[0]).order('-created').fetch(perPage,perPage * realPage)
      if (page * perPage) < Post.all().filter('user =',target_user[0]).order('-created').count():
        nextPage = page + 1
      prefetch.prefetch_posts_list(posts)
      i = perPage * realPage + 1
      for post in posts:
        post.number = i
        i = i + 1
      if helper.is_json(self.request.url):
        posts_json = [p.to_json() for p in posts]
        if(self.request.get('callback')):
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'posts':posts_json})+');')
        else:
          self.response.headers['Content-Type'] = "application/json"
          self.response.out.write(simplejson.dumps({'posts':posts_json}))
      else:
        self.response.out.write(template.render('templates/main.html', locals()))
    else:
      self.redirect('/')

class GuidelinesHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/guidelines.html', locals()))

class FAQHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/faq.html', locals()))

class LeaderHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']

    users = User.all().order("-karma").fetch(50)
    i = 1
    for u in users:
      u.pos = i
      i = i + 1
    self.response.out.write(template.render('templates/leaders.html', locals()))

class RssHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-created').fetch(20)
    prefetch.prefetch_posts_list(posts)

    items = []
    for post in posts:
      if len(post.message) == 0:
          rss_poster = '<a href="'+post.url+'">'+post.url+'</a>'
      else:
          rss_poster = post.message
      rss_poster += ' por <a href="'+helper.base_url(self)+'/perfil/'+post.user.nickname+'">'+post.user.nickname+'</a>'
      items.append(PyRSS2Gen.RSSItem(
          title = post.title,
          link = helper.base_url(self)+'/noticia/' + str(post.key()),
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

class NotificationsMarkAsReadHandler(webapp.RequestHandler):
  def get(self,notification_key):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        notification = db.get(helper.sanitizeHtml(notification_key))
        if str(notification.target_user.key()) == str(user.key()):
          notification.read = True
          notification.put()
          user.remove_notifications_from_memcache()
          self.response.out.write('Ok')
        else:
          self.response.out.write('Bad')
      except db.BadKeyError:
        self.response.out.write('Bad')
    else:
      self.response.out.write('Bad')

# Notifications
class NotificationsInboxHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      page = helper.sanitizeHtml(self.request.get('pagina'))
      perPage = 10
      page = int(page) if page else 1
      realPage = page - 1
      inbox = True
      if realPage > 0:
        prevPage = realPage
      if (page * perPage) < Notification.all().filter("target_user =",user).filter("read =",False).count():
        nextPage = page + 1
 
      notifications = Notification.all().filter("target_user =",user).filter("read =",False).order("-created").fetch(perPage,perPage * realPage)
      prefetch.prefetch_refprops(notifications,Notification.post,Notification.comment,Notification.sender_user)
      self.response.out.write(template.render('templates/notifications.html', locals()))
    else:
      self.redirect('/login')

# Notifications
class NotificationsInboxAllHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      page = helper.sanitizeHtml(self.request.get('pagina'))
      perPage = 10
      page = int(page) if page else 1
      realPage = page - 1
      inboxAll = True
      if realPage > 0:
        prevPage = realPage
      if (page * perPage) < Notification.all().filter("target_user =",user).count():
        nextPage = page + 1
 
      notifications = Notification.all().filter("target_user =",user).order("-created").fetch(perPage,perPage * realPage)
      prefetch.prefetch_refprops(notifications,Notification.post,Notification.comment,Notification.sender_user)
      self.response.out.write(template.render('templates/notifications.html', locals()))
    else:
      self.redirect('/login')

class APIGitHubHandler(webapp.RequestHandler):
  def get(self):
    json = memcache.get("api_github")
    if json is None:
      users = User.all().filter("github !=", "").fetch(1000)
      github_user_string = [{u.nickname:u.github} for u in users]
      json = simplejson.dumps({'github_users':github_user_string})
      memcache.add("api_github",json,3600)

    if(self.request.get('callback')):
      self.response.headers['Content-Type'] = "application/javascript"
      self.response.out.write(self.request.get('callback')+'(' + json + ')')
    else:
      self.response.headers['Content-Type'] = "application/json"
      self.response.out.write(json)

class APITwitterHandler(webapp.RequestHandler):
  def get(self):
    json = memcache.get("api_twitter")
    if json is None:
      users = User.all().filter("twitter !=", "").fetch(1000)
      twitter_user_string = [{u.nickname:u.twitter} for u in users]
      json = simplejson.dumps({'twitter_users':twitter_user_string})
      memcache.add("api_twitter",json,3600)

    if(self.request.get('callback')):
      self.response.headers['Content-Type'] = "application/javascript"
      self.response.out.write(self.request.get('callback')+'(' + json + ')')
    else:
      self.response.headers['Content-Type'] = "application/json"
      self.response.out.write(json)

class APIHackerNewsHandler(webapp.RequestHandler):
  def get(self):
    json = memcache.get("api_hackernews")
    if json is None:
      users = User.all().filter("hnuser !=", "").fetch(1000)
      hackernews_user_string = [{u.nickname:u.hnuser} for u in users]
      json = simplejson.dumps({'hackernews_users':hackernews_user_string})
      memcache.add("api_hackernews",json,3600)

    if(self.request.get('callback')):
      self.response.headers['Content-Type'] = "application/javascript"
      self.response.out.write(self.request.get('callback')+'(' + json + ')')
    else:
      self.response.headers['Content-Type'] = "application/json"
      self.response.out.write(json)

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/.json', MainHandler),
      ('/conversaciones/(.+)', ThreadsHandler),
      ('/directrices', GuidelinesHandler),
      ('/preguntas-frecuentes', FAQHandler),
      ('/nuevo', NewHandler),
      ('/nuevo.json', NewHandler),
      ('/noticias-usuario/(.+)', UserPostsHandler),
      ('/agregar', SubmitNewStoryHandler),
      ('/upvote/(.+)', UpVoteHandler),
      ('/upvote_comment/(.+)', UpVoteCommentHandler),
      ('/perfil/(.+)', ProfileHandler),
      ('/noticia/(.+)', PostHandler),
      ('/editar-noticia/(.+)', EditPostHandler),
      ('/responder/(.+)', CommentReplyHandler),
      ('/editar-comentario/(.+)', EditCommentHandler),
      ('/inbox', NotificationsInboxHandler),
      ('/inbox/all', NotificationsInboxAllHandler),
      ('/inbox/marcar-como-leido/(.+)', NotificationsMarkAsReadHandler),
      ('/lideres', LeaderHandler),
      ('/login', LoginHandler),
      ('/logout', LogoutHandler),
      ('/register', RegisterHandler),
      ('/rss', RssHandler),
      ('/api/usuarios/github', APIGitHubHandler),
      ('/api/usuarios/twitter', APITwitterHandler),
      ('/api/usuarios/hackernews', APIHackerNewsHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
