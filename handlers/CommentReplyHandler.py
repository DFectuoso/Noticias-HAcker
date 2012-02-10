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


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self,comment_id):
    session = get_current_session()
    if hasattr(keys, 'comment_key'):
      comment_key = keys.comment_key
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
      key = self.request.get('comment_key')
      if len(message) > 0 and key == keys.comment_key:
        try:
          parentComment = db.get(comment_id)
          comment = Comment(message=message,user=user,post=parentComment.post, father=parentComment)
          comment.put()
          helper.killmetrics("Comment","Child", "posted", session, "",self)
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


