# -*- coding: utf-8 -*-
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

register = webapp.template.create_template_register()
def hacetiempo(value):
  value = value.replace("year", "año")
  value = value.replace("week", "semana")
  value = value.replace("day", "dia")
  value = value.replace("hour", "hora")
  value = value.replace("minute", "minuto")
  return value

register.filter(hacetiempo)


