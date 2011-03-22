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

import cgi
import prefetch
from models import User, Post, Comment, Vote 

def sanitizeHtml(value):
  return cgi.escape(value)

def is_json(value):
  if value.find('.json') >= 0:
    return True
  else:
    return False

def parse_post_id(value):
  if is_json(value):
    return value.split('.')[0]
  else:
    return value

def add_childs_to_comment(comment):
  """We need to add the childs of each post because we want to render them in the
     same way we render the Post view. So we need to find all the "preprocessed_childs"
     Now, we also want to hold a reference to them to be able to pre_fetch them
  """
  comment.processed_child = []
  total_childs = []
  for child in comment.childs:
    comment.processed_child.append(child)
    total_childs.append(child)
    total_childs.extend(add_childs_to_comment(child))
  return total_childs

def filter_user_comments(all_comments, user):
  """ This function removes comments that belong to a thread
  which had a comment by the same user as a parent """
  res_comments = []
  for user_comment in all_comments: ### Cycle all the comments and find the ones we care
    linked_comment = user_comment
    while(True):
      if Comment.father.get_value_for_datastore(linked_comment) is None:
        if not [c for c in res_comments if c.key() == user_comment.key()]:
          res_comments.append(user_comment) # we care about the ones that are topmost
        break
      if linked_comment.father.user.key() == user.key():
        if not [c for c in res_comments if c.key() == linked_comment.father.key()]:
          res_comments.append(linked_comment.father) # But we also want to append the "father" ones to avoid having pages with 0 comments
        break
      linked_comment = linked_comment.father
  # Add Childs here
  child_list = []
  for comment in res_comments:
    comment.is_top_most = True
    child_list.extend(add_childs_to_comment(comment))
  prefetch.prefetch_comment_list(res_comments + child_list) #Finally we prefetch everything, 1 super call to memcache
  return res_comments

def get_comment_from_list(comment_key,comments):
  return [comment for comment in comments if comment.key() ==  comment_key]

def order_comment_list_in_memory(comments):
  # order childs for display
  for comment in comments:
    comment.processed_child = []
  for comment in comments:
    father_key = Comment.father.get_value_for_datastore(comment)
    if father_key is not None:
      father_comment = get_comment_from_list(father_key,comments)
      if len(father_comment) == 1:
        father_comment[0].processed_child.append(comment)
  return comments

