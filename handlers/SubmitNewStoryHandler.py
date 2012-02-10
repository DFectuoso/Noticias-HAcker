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
    session = get_current_session()
    if session.has_key('post_error'):
      post_error = session.pop('post_error')

    if session.has_key('user'):
      if hasattr(keys, 'comment_key'):
        comment_key = keys.comment_key
      user = session['user']
      #### Killmetrics test
      killmetrics_session_id = helper.get_session_id(session)
      killmetrics_key = ''
      if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
        killmetrics_key = keys.killmetrics_dev
      if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and (helper.base_url(self) == keys.base_url or helper.base_url(self) == keys.base_url_custom_url):
        killmetrics_key = keys.killmetrics_prod
      #### Killmetrics test



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
    nice_url = helper.sluglify(title)
    key = self.request.get('comment_key')
 
    if session.has_key('user') and key == keys.comment_key:
      if len(nice_url) > 0:
        user = session['user']
        if len(message) == 0: #is it a post or a message?
          #Check that we don't have the same URL within the last 'check_days'
          since_date = date.today() - timedelta(days=7)
          q = Post.all().filter("created >", since_date).filter("url =", url).count()
          url_exists = q > 0
          q = Post.all().filter("nice_url", nice_url).count()
          nice_url_exist = q > 0
          try:
            if not url_exists:
              if not nice_url_exist:
                post = Post(url=url,title=title,message=message, user=user, nice_url=nice_url)
                post.put()
                helper.killmetrics("Submit","Link", "do", session, "",self)
                vote = Vote(user=user, post=post, target_user=post.user)
                vote.put()
                Post.remove_cached_count_from_memcache()
 	
                #index with indextank
                helper.indextank_document( helper.base_url(self), post)
                
                self.redirect('/noticia/' + str(post.nice_url));
              else:
                session['post_error'] = "Este titulo ha sido usado en una noticia anterior"
                self.redirect('/agregar')
            else:
              session['post_error'] = "Este link ha sido entregado en los ultimo 7 dias"
              self.redirect('/agregar')
          except db.BadValueError:
            session['post_error'] = "El formato del link no es valido"
            self.redirect('/agregar')
        else:
          q = Post.all().filter("nice_url", nice_url).count()
          nice_url_exist = q > 0
          if not nice_url_exist:
            post = Post(title=title,message=message, user=user, nice_url=nice_url)
            post.put()
            helper.killmetrics("Submit","Post", "do", session, "",self)
            post.url = helper.base_url(self) + "/noticia/" + post.nice_url
            post.put()
            Post.remove_cached_count_from_memcache()
            vote = Vote(user=user, post=post, target_user=post.user)
            vote.put()

	    #index with indextank
	    helper.indextank_document( helper.base_url(self), post)
            
	    self.redirect('/noticia/' + post.nice_url);
          else:
            session['post_error'] = "Este titulo ha sido usado en una noticia anterior"
            self.redirect('/agregar')
      else:
        session['post_error'] = "Necesitas agregar un titulo"
        self.redirect('/agregar')
    else:
      self.redirect('/login')
