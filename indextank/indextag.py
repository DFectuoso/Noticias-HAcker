from google.appengine.ext import webapp
from django import template as django_template

import os
DEV = os.environ['SERVER_SOFTWARE'].startswith('Development')

import keys

register = webapp.template.create_template_register()

class StringNode(django_template.Node):
  def __init__(self, string):
    self.string = string
  def render(self, context):
	  return self.string
	
def indexkey(parser, token):
    return StringNode(keys.indextank_public_key)
def indexname(parser, token):
    if DEV:
      return StringNode(keys.indextank_name_key) 
    else:
      return StringNode(keys.indextank_name_key_prod) 

register.tag(indexkey)
register.tag(indexname)
