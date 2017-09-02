import logging

import urllib
import httplib2
import simplejson
import yaml
import json
import random
import time

from datetime import datetime
from datetime import timedelta

import config
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb
from google.appengine.api import urlfetch

from lib.utils import generate_token
from lib.github import github


# user model - extends webapp2 User model
class User(User):
	uid = ndb.StringProperty()
	username = ndb.StringProperty()
	email = ndb.StringProperty()
	name = ndb.StringProperty()
	timezone = ndb.StringProperty()
	country = ndb.StringProperty()
	company = ndb.StringProperty()
	blogger = ndb.BooleanProperty(default=False)
	activated = ndb.BooleanProperty(default=False)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	last_login = ndb.DateTimeProperty()
	tfsecret = ndb.StringProperty()
	tfenabled = ndb.BooleanProperty(default=False)

	@classmethod
	def get_by_email(cls, email):
		return cls.query(cls.email == email).get()

	@classmethod
	def get_by_uid(cls, uid):
		return cls.query(cls.uid == uid).get()

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(-cls.created).fetch()


# image model
class Image(ndb.Model):
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	url = ndb.StringProperty()
	disk_format = ndb.StringProperty()
	container_format = ndb.StringProperty()
	active = ndb.BooleanProperty(default=False)
	dynamic = ndb.BooleanProperty(default=False)

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(cls.created).fetch()

	@classmethod
	def get_by_name(cls, name):
		image_query = cls.query().filter(cls.name == name)
		image = image_query.get()
		return image


# cloud model
class API(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)

	@classmethod
	def get_by_user(cls, user):
		api_query = cls.query().filter(cls.owner == user).order(-cls.created)
		apis = api_query.fetch()
		return apis

	@classmethod
	def get_by_user_name(cls, user, name):
		api_query = cls.query().filter(cls.owner == user, cls.name == name)
		apis = api_query.get()
		return apis

	@classmethod
	def create_default(cls, userkey, name="Default"):
		api = API()
		api.name = name
		api.description = "Auto generated default."
		api.owner = userkey
		api.put()
		return api


# project model
class Repo(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	public = ndb.BooleanProperty(default=False)

	@classmethod
	def get_by_user(cls, user):
		query = cls.query().filter(cls.owner == user).order(-cls.created)
		results = query.fetch()
		return results

	@classmethod
	def get_by_user_name(cls, user, name):
		query = cls.query().filter(cls.owner == user, cls.name == name)
		result = query.get()
		return result

	@classmethod
	def get_public(cls):
		query = cls.query().filter(cls.public == True)
		results = query.fetch()
		return results

	@classmethod
	def get_available(cls, user):
		query = cls.query().filter(cls.public == True)
		results = query.fetch()
		query = cls.query().filter(cls.public != True, cls.owner == user)
		for result in query.fetch():
			results.append(result)
		return results

	def sync(self):
		message = github.repo_sync_contents(self)
		return message


# blog posts and pages
class Article(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	owner = ndb.KeyProperty(kind=User)
	title = ndb.StringProperty()
	summary = ndb.StringProperty()
	filename = ndb.StringProperty()
	slug = ndb.StringProperty()
	article_type = ndb.StringProperty()
	draft = ndb.BooleanProperty(default=True)
	
	@classmethod
	def get_all(cls):
		article_query = cls.query().filter().order(-cls.created)
		articles = article_query.fetch()
		return articles

	@classmethod
	def get_blog_posts(cls, num_articles=1, offset=0):
		article_query = cls.query().filter(cls.article_type == 'post', cls.draft == False).order(-cls.created)
		articles = article_query.fetch(limit=num_articles)
		return articles

	@classmethod
	def get_by_user(cls, user):
		article_query = cls.query().filter(cls.owner == user).order(-Article.created)
		articles = article_query.fetch()
		return articles

	@classmethod
	def get_by_type(cls, article_type):
		article_query = cls.query().filter(cls.article_type == article_type).order(-Article.created)
		articles = article_query.fetch()
		return articles

	@classmethod
	def get_by_slug(cls, slug):
		article_query = cls.query().filter(cls.slug == slug)
		article = article_query.get()
		return article


# log tracking pings
class LogTracking(ndb.Model):
	timestamp = ndb.DateTimeProperty(auto_now_add=True)
	message = ndb.StringProperty()
	ip = ndb.StringProperty()    


# log visits
class LogVisit(ndb.Model):
	timestamp = ndb.DateTimeProperty(auto_now_add=True)
	user = ndb.KeyProperty(kind=User)
	message = ndb.StringProperty()
	uastring = ndb.StringProperty()
	ip = ndb.StringProperty()


# log outgoing emails
class LogEmail(ndb.Model):
	sender = ndb.StringProperty(required=True)
	to = ndb.StringProperty(required=True)
	subject = ndb.StringProperty(required=True)
	body = ndb.TextProperty()
	when = ndb.DateTimeProperty()

