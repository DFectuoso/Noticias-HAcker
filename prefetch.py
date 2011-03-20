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

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime

from models import User, Post, Comment, Vote 

def prefetch_refprops(entities, *props):
  fields = [(entity, prop) for entity in entities for prop in props]
  ref_keys = [prop.get_value_for_datastore(x) for x, prop in fields]
  ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
  for (entity, prop), ref_key in zip(fields, ref_keys):
    if ref_entities[ref_key]:
      prop.__set__(entity, ref_entities[ref_key])
  return entities

def prefetch_comment_list(comments):
  prefetch_refprops(comments, Comment.user, Comment.post)

  # call all the memcache information
  # starting by the already_voted area
  comment_keys = [str(comment.key()) for comment in comments]
  session = get_current_session()
  if session.has_key('user'):
    user = session['user']
    memcache_voted_keys = ["cp_" + comment_key + "_" + str(user.key()) for comment_key in comment_keys]
    memcache_voted = memcache.get_multi(memcache_voted_keys)
    memcache_to_add = {}
    for comment in comments:
      vote_value = memcache_voted.get("cp_" + str(comment.key()) + "_" +str(user.key()))
      if vote_value is not None:
        comment.prefetched_already_voted = vote_value == 1
      else:
        vote = Vote.all().filter("user =", user).filter("comment =", comment).fetch(1)
        memcache_to_add["cp_" + str(comment.key()) + "_" + str(user.key())] = len(vote)
        comment.prefetched_already_voted = len(vote) == 1
    if memcache_to_add.keys():
      memcache.add_multi(memcache_to_add, 3600)
  else:
    for comment in comments:
      comment.prefetched_already_voted = False
  # now the sum_votes
  memcache_sum_votes_keys = ["c_" + comment_key for comment_key in comment_keys]
  memcache_sum_votes = memcache.get_multi(memcache_sum_votes_keys)
  memcache_to_add = {}
  for comment in comments:
    sum_votes_value = memcache_sum_votes.get("c_" + str(comment.key()))
    if sum_votes_value is not None:
      comment.prefetched_sum_votes = sum_votes_value
    else:
      sum_votes = Vote.all().filter("comment =", comment).count()
      memcache_to_add["c_" + str(comment.key())] = sum_votes
      comment.prefetched_sum_votes =sum_votes
  if memcache_to_add.keys():
    memcache.add_multi(memcache_to_add, 3600)

def prefetch_posts_list(posts):
  prefetch_refprops(posts, Post.user)
  posts_keys = [str(post.key()) for post in posts]

  # get user, if no user, all already_voted = no
  session = get_current_session()
  if session.has_key('user'):
    user = session['user']
    memcache_voted_keys = ["vp_" + post_key + "_" + str(user.key()) for post_key in posts_keys]
    memcache_voted = memcache.get_multi(memcache_voted_keys)
    memcache_to_add = {}
    for post in posts:
      vote_value = memcache_voted.get("vp_" + str(post.key()) + "_" +str(user.key()))
      if vote_value is not None:
        post.prefetched_already_voted = vote_value == 1
      else:
        vote = Vote.all().filter("user =", user).filter("post =", post).fetch(1)
        memcache_to_add["vp_" + str(post.key()) + "_" + str(user.key())] = len(vote)
        post.prefetched_already_voted = len(vote) == 1
    if memcache_to_add.keys():
      memcache.add_multi(memcache_to_add, 3600)
  else:
    for post in posts:
      post.prefetched_already_voted = False
  # for voted in memcache_voted:

  # TODO get comment count, change template and json
  # TODO get already voted



