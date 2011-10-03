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

# News Handlers
class Handler(webapp.RequestHandler):
  def get(self,post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    

    try:
      post = Post.all().filter('nice_url =', helper.parse_post_id( post_id ) ).get()
      if  post  == None: #If for some reason the post doesn't have a nice url, we try the id. This is also the case of all old stories
        post = db.get( helper.parse_post_id( post_id ) ) 

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
        helper.killmetrics("Pageview","Post", "view", session, "")
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
          post = Post.all().filter('nice_url =', helper.parse_post_id( post_id ) ).get()
          if post  == None: #If for some reason the post doesn't have a nice url, we try the id. This is also the case of all old stories
            post = db.get( helper.parse_post_id( post_id ) ) 

          post.remove_from_memcache()
          comment = Comment(message=message,user=user,post=post)
          comment.put()
          helper.killmetrics("Comment","Root", "posted", session, "")
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



