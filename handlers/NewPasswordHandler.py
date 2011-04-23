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
    if session.has_key('forgotten_password_error'):
      forgotten_password_error = session.pop('forgotten_password_error')
    if session.has_key('forgotten_password_ok'):
      forgotten_password_ok = session.pop('forgotten_password_ok')
    
    if session.has_key('user'):
      user = session['user']
      self.redirect('/logout')
    else:
      self.response.out.write(template.render('templates/forgotten-password.html', locals()))

  def post(self):
    session = get_current_session()
    email = helper.sanitizeHtml(self.request.get('email'))
    if len(email) > 1:      
      users = User.all().filter("email =", email).fetch(1)
      if len(users) == 1:
        if session.is_active():
          session.terminate()
        user = users[0]
        Ticket.deactivate_others(user)
        ticket = Ticket(user=user,code=Ticket.create_code(user.password + user.nickname + str(random.random())))
        ticket.put()
        code = ticket.code
        host = self.request.url.replace(self.request.path,'',1)
       
        mail.send_mail(sender="NoticiasHacker <dfectuoso@noticiashacker.com>",
          to=user.nickname + "<"+user.email+">",
          subject="Liga para restablecer password",
          html=template.render('templates/mail/forgotten-password-email.html', locals()),
          body=template.render('templates/mail/forgotten-password-email-plain.html', locals()))
      
        session['forgotten_password_ok'] = "Se ha enviado un correo electrónico a tu bandeja de entrada con las instrucciones"
      else:
        session['forgotten_password_error'] = "El correo electronico <strong>"+ email +"</strong> no existe en nuestra base de datos"
    else:
      session['forgotten_password_error'] = "Debes especificar tu correo electrónico"
     
    self.redirect('/olvide-el-password')


