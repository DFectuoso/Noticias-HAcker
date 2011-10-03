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
import cgi
import keys
import sys
import urllib

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime
from gaesessions import delete_expired_sessions

from models import User, Post, Comment, Vote
from random import choice

from libs import bitly
sys.path.insert(0, 'libs/tweepy.zip')
import tweepy
import helper


class TopHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-karma').fetch(50)
    post = choice(posts)
    post.calculate_karma()
    self.response.out.write("ok")

def sendMessageToTwitter(self, post):
  bitlyApi = bitly.Api(login=keys.bitly_login, apikey=keys.bitly_apikey) 
  auth = tweepy.OAuthHandler(keys.consumer_key, keys.consumer_secret)
  auth.set_access_token(keys.access_token, keys.access_token_secret)
  twitterapi = tweepy.API(auth)
  url =  keys.base_url_custom_url + "/noticia/" + str(post.key())
  if post.nice_url:
    url =  keys.base_url_custom_url + "/noticia/" + str(post.nice_url)

  shortUrl = bitlyApi.shorten(url)
  title = post.title[:115]
  message = title + "... " + shortUrl
  twitterapi.update_status(message)
  return message

class TwitterHandler(webapp.RequestHandler):
  def get(self):
    if hasattr(keys,'consumer_key') and hasattr(keys,'consumer_secret') and hasattr(keys,'access_token') and hasattr(keys,'access_token_secret') and hasattr(keys,'bitly_login') and hasattr(keys,'bitly_apikey') and hasattr(keys,'base_url') and helper.base_url(self) == keys.base_url:
      posts = Post.all().order('-karma').fetch(20)
      for post in posts:
        if not post.twittered:
          post.twittered = True
          post.put()
          out = sendMessageToTwitter(self,post)
          self.response.out.write("Printed:" + out)  
          return
      self.response.out.write("No more message")
    else:
      self.response.out.write("No keys")

class SessionsHandler(webapp.RequestHandler):
  def get(self):
    while not delete_expired_sessions():
      pass
    self.response.out.write("ok")

class SendToKillmetricsHandler(webapp.RequestHandler):
  def get(self):
    killmetrics_key = ''
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and helper.base_url(self) == keys.base_url:
      killmetrics_key = keys.killmetrics_prod
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
      killmetrics_key = keys.killmetrics_dev

    if killmetrics_key == '':
      return

    killmetrics_base_url = "http://alertify.appspot.com/"

    userUID     = urllib.quote(self.request.get("userUID"))
    sessionUID  = urllib.quote(self.request.get("sessionUID"))
    category    = urllib.quote(self.request.get("category"))
    subcategory = urllib.quote(self.request.get("subcategory"))
    verb        = urllib.quote(self.request.get("verb"))

    url = killmetrics_base_url + '/data-point/'+killmetrics_key+'?userUID='+userUID+'&sessionUID='+sessionUID+'&category='+category+'&subcategory='+subcategory+'&verb='+verb
    result = urlfetch.fetch(url)

  def post(self):
    self.get() 

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/tasks/update_top_karma', TopHandler),
      ('/tasks/send_top_to_twitter', TwitterHandler),
      ('/tasks/cleanup_sessions', SessionsHandler),
      ('/tasks/send_to_killmetrics', SendToKillmetricsHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
