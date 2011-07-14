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

# User Handlers
class Handler(webapp.RequestHandler):
  def get(self,nickname):
    nickname = helper.parse_post_id(nickname)
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
      if helper.is_json(self.request.url):
        if(self.request.get('callback')):
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'nickname':profiledUser.nickname, 'karma':profiledUser.karma,'twitter':profiledUser.twitter,'github':profiledUser.github,'hn':profiledUser.hnuser})+')')
        else:
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(simplejson.dumps({'nickname':profiledUser.nickname,'twitter':profiledUser.twitter, 'karma':profiledUser.karma, 'github':profiledUser.github,'hn':profiledUser.hnuser}))
      else:
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
        if len(User.all().filter("email",email).fetch(1)) == 0:
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

