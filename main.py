#!/usr/local/bin/python
# -*- coding: utf-8 -*-
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
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket

from handlers import ( MainHandler, ThreadsHandler, GuidelinesHandler, FAQHandler,
                       NewHandler, UserPostsHandler, SubmitNewStoryHandler, UpVoteHandler,
                       UpVoteCommentHandler, ProfileHandler, PostHandler, EditPostHandler,
                       CommentReplyHandler, EditCommentHandler, NotificationsInboxHandler,
                       NotificationsInboxAllHandler, NotificationsMarkAsReadHandler,
                       LeaderHandler, LoginHandler, LogoutHandler, RegisterHandler, 
                       NewPasswordHandler, RecoveryHandler, RssHandler, APIGitHubHandler,
                       APITwitterHandler, APIHackerNewsHandler )


# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler.Handler),
      ('/.json', MainHandler.Handler),
      ('/conversaciones/(.+)', ThreadsHandler.Handler),
      ('/directrices', GuidelinesHandler.Handler),
      ('/preguntas-frecuentes', FAQHandler.Handler),
      ('/nuevo', NewHandler.Handler),
      ('/nuevo.json', NewHandler.Handler),
      ('/noticias-usuario/(.+)', UserPostsHandler.Handler),
      ('/agregar', SubmitNewStoryHandler.Handler),
      ('/upvote/(.+)', UpVoteHandler.Handler),
      ('/upvote_comment/(.+)', UpVoteCommentHandler.Handler),
      ('/perfil/(.+)', ProfileHandler.Handler),
      ('/noticia/(.+)', PostHandler.Handler),
      ('/editar-noticia/(.+)', EditPostHandler.Handler),
      ('/responder/(.+)', CommentReplyHandler.Handler),
      ('/editar-comentario/(.+)', EditCommentHandler.Handler),
      ('/inbox', NotificationsInboxHandler.Handler),
      ('/inbox/all', NotificationsInboxAllHandler.Handler),
      ('/inbox/marcar-como-leido/(.+)', NotificationsMarkAsReadHandler.Handler),
      ('/lideres', LeaderHandler.Handler),
      ('/login', LoginHandler.Handler),
      ('/logout', LogoutHandler.Handler),
      ('/register', RegisterHandler.Handler),
      ('/olvide-el-password', NewPasswordHandler.Handler),
      ('/recovery/(.+)?', RecoveryHandler.Handler),
      ('/rss', RssHandler.Handler),
      ('/api/usuarios/github', APIGitHubHandler.Handler),
      ('/api/usuarios/twitter', APITwitterHandler.Handler),
      ('/api/usuarios/hackernews', APIHackerNewsHandler.Handler),
  ], debug=True)
  util.run_wsgi_app(application)

webapp.template.register_template_library('indextank.indextag')

if __name__ == '__main__':
  main()
