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
      helper.killmetrics("Pageview","New", "view", session, "",self)
      self.response.out.write(template.render('templates/main.html', locals()))

