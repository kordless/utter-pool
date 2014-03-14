import logging

import urllib
import httplib2
import simplejson
import yaml

import config
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb


# user model
class User(User):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    last_login = ndb.DateTimeProperty()
    uid = ndb.StringProperty()
    email = ndb.StringProperty()
    tfkey = ndb.StringProperty()
    tfenabled = ndb.BooleanProperty(default=False)
    username = ndb.StringProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    company = ndb.StringProperty()
    gravatar_url = ndb.StringProperty()
    activated = ndb.BooleanProperty(default=False)
    admin = ndb.BooleanProperty(default=False)

    @classmethod
    def get_by_email(cls, email):
        return cls.query(cls.email == email).get()

    @classmethod
    def get_by_uid(cls, uid):
        return cls.query(cls.uid == uid).get()


# blog posts and pages
class Article(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    owner = ndb.KeyProperty(kind=User)
    title = ndb.StringProperty()
    summary = ndb.StringProperty()
    filename = ndb.StringProperty()
    url = ndb.StringProperty()
    slug = ndb.StringProperty()
    article_type = ndb.StringProperty()
    draft = ndb.BooleanProperty(default=True)
    
    @classmethod
    def delete_by_user(cls, user):
        article_query = cls.query().filter(cls.owner == user)
        articles = article_query.fetch()
        keys = []
        for x in articles:
            keys.append(x.key)
        return ndb.delete_multi(keys)

    @classmethod
    def get_all(cls):
        article_query = cls.query().filter().order(-cls.created)
        gists = article_query.fetch()
        return gists

    @classmethod
    def get_blog_posts(cls, num_articles=1):
        article_query = cls.query().filter(cls.article_type == 'post', cls.draft == False).order(-cls.created)
        gists = article_query.fetch(limit=num_articles)
        return gists

    @classmethod
    def get_by_user(cls, user):
        article_query = cls.query().filter(cls.owner == user).order(-Article.created)
        gists = article_query.fetch()
        return gists

    @classmethod
    def get_by_user_and_type(cls, user, article_type):
        article_query = cls.query().filter(cls.owner == user, cls.article_type == article_type).order(-Article.created)
        gists = article_query.fetch()
        return gists

    @classmethod
    def get_by_user_and_slug(cls, user, slug):
        article_query = cls.query().filter(cls.owner == user, cls.slug == slug)
        gist = article_query.get()
        return gist


# log visits
class LogVisit(ndb.Model):
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    user = ndb.KeyProperty(kind=User)
    message = ndb.StringProperty()
    uastring = ndb.StringProperty()
    ip = ndb.StringProperty()


# log outgoing emails
class LogEmail(ndb.Model):
    sender = ndb.StringProperty(
        required=True)
    to = ndb.StringProperty(
        required=True)
    subject = ndb.StringProperty(
        required=True)
    body = ndb.TextProperty()
    when = ndb.DateTimeProperty()

