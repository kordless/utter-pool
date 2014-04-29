import logging

import urllib
import httplib2
import simplejson
import yaml

import config
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb


# appliance group model
class Group(ndb.Model):
    name = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    owner = ndb.KeyProperty(kind=User)
    public = ndb.BooleanProperty(default=False)

    @classmethod
    def get_by_name(cls, groupname):
        return cls.query(cls.groupname == groupname).get()

    @classmethod
    def get_all(cls):
        return cls.query().filter().order(-cls.created).fetch()

    @classmethod
    def get_by_owner_private(cls, owner):
        return cls.query(cls.owner == owner, cls.public == False).order(cls.created).fetch()
    
    @classmethod
    def get_public(cls):
        return cls.query(cls.public == True).order(cls.created).fetch()


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

    # group membership
    groups = ndb.StructuredProperty(Group, repeated=True)

    @classmethod
    def get_by_email(cls, email):
        return cls.query(cls.email == email).get()

    @classmethod
    def get_by_uid(cls, uid):
        return cls.query(cls.uid == uid).get()

    @classmethod
    def get_all(cls):
        return cls.query().filter().order(-cls.created).fetch()


# appliance model
class Appliance(ndb.Model):
    name = ndb.StringProperty()
    token = ndb.StringProperty()
    activated = ndb.BooleanProperty(default=True)
    ssluri = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    last_active = ndb.DateTimeProperty()
    owner = ndb.KeyProperty(kind=User)
    group = ndb.KeyProperty(kind=Group)
    ipv4enabled = ndb.BooleanProperty(default=False)
    ipv6enabled = ndb.BooleanProperty(default=False)
    ipv4net = ndb.StringProperty()
    ipv6net = ndb.StringProperty()

    @classmethod
    def get_by_token(cls, token):
        return cls.query(cls.token == token).get()

    @classmethod
    def get_by_user(cls, user):
        return cls.query().filter(cls.owner == user).order(-cls.created).fetch()


# image model
class Image(ndb.Model):
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    url = ndb.StringProperty()
    size = ndb.IntegerProperty()
    diskformat = ndb.StringProperty()
    containerformat = ndb.StringProperty()
    active = ndb.BooleanProperty(default=True)

    @classmethod
    def get_all(cls):
        return cls.query().filter().order(cls.created).fetch()


# flavor model
class Flavor(ndb.Model):
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    vpus = ndb.IntegerProperty()
    memory = ndb.IntegerProperty()
    disk = ndb.IntegerProperty()
    network = ndb.IntegerProperty()
    rate = ndb.IntegerProperty() # current market rate
    launches = ndb.IntegerProperty() # number of launches
    active = ndb.BooleanProperty(default=False)

    @classmethod
    def get_all(cls):
        return cls.query().filter().order(cls.created).fetch()


# address model
class Address(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)


# cloud model
class Cloud(ndb.Model):
    name = ndb.StringProperty()
    group = ndb.KeyProperty(kind=Group)
    owner = ndb.KeyProperty(kind=User)
    address = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)


# instance model
class Instance(ndb.Model):
    name = ndb.StringProperty()
    provider = ndb.KeyProperty(kind=User)
    appliance = ndb.KeyProperty(kind=Appliance)
    cloud = ndb.KeyProperty(kind=Cloud)
    address = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    flavor = ndb.KeyProperty(kind=Flavor)
    image = ndb.KeyProperty(kind=Image)
    ipv4_private_address = ndb.StringProperty()
    ipv4_address = ndb.StringProperty()
    ipv6_address = ndb.StringProperty()


# bid model
class Bid(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    callback = ndb.StringProperty()
    address = ndb.KeyProperty(kind=Address)
    flavor = ndb.KeyProperty(kind=Flavor)
    amount = ndb.IntegerProperty()
    price = ndb.IntegerProperty()


# ask model
class Ask(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    appliance = ndb.KeyProperty(kind=Appliance)
    flavor = ndb.KeyProperty(kind=Flavor)
    price = ndb.IntegerProperty()


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
    sender = ndb.StringProperty(
        required=True)
    to = ndb.StringProperty(
        required=True)
    subject = ndb.StringProperty(
        required=True)
    body = ndb.TextProperty()
    when = ndb.DateTimeProperty()

