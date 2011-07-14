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
    posts = Post.all().order('-created').fetch(20)
    prefetch.prefetch_posts_list(posts)

    items = []
    for post in posts:
      if len(post.message) == 0:
        rss_poster = '<a href="'+post.url+'">'+post.url+'</a>'
      else:
        rss_poster = post.message
      rss_poster += ' por <a href="'+helper.base_url(self)+'/perfil/'+post.user.nickname+'">'+post.user.nickname+'</a>'

      link = helper.base_url(self)+'/noticia/' + str(post.key())
      if post.nice_url:
        link = helper.base_url(self)+'/noticia/' + str(post.nice_url)

      items.append(PyRSS2Gen.RSSItem(
          title = post.title,
          link = link,
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



