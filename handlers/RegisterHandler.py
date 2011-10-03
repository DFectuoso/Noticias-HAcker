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
        helper.killmetrics("Register",nickname, "do", session, "")
        random_id = helper.get_session_id(session) 
        if session.is_active():
          session.terminate()
        session.regenerate_id()
        session['random_id'] = random_id
        session['user'] = user
        self.redirect('/')
      else:
        session['register_error'] = "Ya existe alguien con ese nombre de usuario <strong>" + nickname + "</strong>"
        self.redirect('/login')
    else:
      session['register_error'] = "Porfavor escribe un username y un password"
      self.redirect('/login')



