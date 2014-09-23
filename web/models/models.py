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

from lib.utils import generate_token
from utter_apiobjects import schemes
from utter_apiobjects.model_mixin import ModelSchemaMixin


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


# appliance group model
class Group(ndb.Model):
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	owner = ndb.KeyProperty(kind=User)

	@classmethod
	def get_by_name(cls, name):
		return cls.query(cls.name == name).get()

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(-cls.created).fetch()

	@classmethod
	def get_by_owner(cls, owner):
		return cls.query(cls.owner == owner).order(-cls.created).fetch()


# class for group membership
class GroupMembers(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	group = ndb.KeyProperty(kind=Group)    
	email = ndb.StringProperty()
	member = ndb.KeyProperty(kind=User)
	invitor = ndb.KeyProperty(kind=User)
	token = ndb.StringProperty()
	active = ndb.BooleanProperty(default=False)

	@classmethod
	def invite(cls, email, group, invitor):
		# do we have this combo already?
		entry = cls.query().filter(cls.email == email, cls.group == group).get()
		
		if not entry:
			# generate new token and create new entry 
			token = "%s" % generate_token(size=16, caselimit=True)
			entry = GroupMembers(
				group = group,
				email = email,
				invitor = invitor,
				token = token,
				active = False
			)
			entry.put()

		return entry

	@classmethod
	def get_group_user_count(cls, group):
		return cls.query().filter(cls.group == group, cls.active == True).count()

	@classmethod
	def get_by_token(cls, token):
		return cls.query().filter(cls.token == token).fetch()

	@classmethod
	def get_by_userid_groupid(cls, user, group):
		return cls.query().filter(cls.member == user, cls.group == group).get()

	@classmethod
	def get_new_owner(cls, user, group):
		return cls.query().filter(cls.group == group, cls.member != user).get()

	@classmethod
	def get_user_groups(cls, user):
		groups = []
		entries = cls.query(cls.member == user).fetch()
		for entry in entries:
			group = Group.get_by_id(entry.group.id())
			groups.append(group)
		return groups

	@classmethod
	def get_group_users(cls, group):
		users = []
		entries = cls.query().filter(cls.group == group, cls.active == True).fetch()
		for entry in entries:
			stuff = entry.member
			user = User.get_by_id(entry.member.id())
			users.append(user)
		return users

	@classmethod
	def is_member(cls, user, group):
		entry = cls.query().filter(cls.member == user, cls.group == group).get()
		if entry:
			return True
		else:
			return False


# appliance model
class Appliance(ndb.Model):
	activated = ndb.BooleanProperty(default=True)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	token = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	group = ndb.KeyProperty(kind=Group)
	dynamicimages = ndb.BooleanProperty(default=True)
	location = ndb.GeoPtProperty()
	ipv4enabled = ndb.BooleanProperty(default=False)
	ipv6enabled = ndb.BooleanProperty(default=False)
	ipv4_address = ndb.StringProperty()

	@classmethod
	def get_by_token(cls, token):
		return cls.query(cls.token == token).get()

	@classmethod
	def get_by_user(cls, user):
		return cls.query().filter(cls.owner == user).order(-cls.created).fetch()

	@classmethod
	def get_by_group(cls, group):
		return cls.query().filter(cls.group == group).fetch()

	@classmethod
	def get_by_user_group(cls, user, group):
		return cls.query().filter(cls.owner == user, cls.group == group).fetch()

	@classmethod
	def get_appliance_count_by_user_group(cls, user, group):
		return cls.query().filter(cls.owner == user, cls.group == group).count()

	@classmethod
	def get_geopoints(cls):
		# fetch public appliances
		appliances = cls.query().filter(cls.group == None).fetch()
		
		# geopoint array
		geopoints = []

		# loop through the appliances
		for appliance in appliances:
			geopoints.append({
				"latitude": appliance.location.lat, 
				"longitude": appliance.location.lon, 
				"name": appliance.name,
				"id": appliance.key.id()
			})

		return geopoints

	@classmethod
	def authenticate(cls, apitoken):
		appliance = cls.get_by_token(apitoken)
		if not (appliance and appliance.activated):
			return False
		return True


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


# flavor model
class Flavor(ndb.Model, ModelSchemaMixin):
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	vpus = ndb.IntegerProperty()
	memory = ndb.IntegerProperty()
	disk = ndb.IntegerProperty()
	network_up = ndb.IntegerProperty()
	network_down = ndb.IntegerProperty()
	rate = ndb.IntegerProperty() # current market rate
	hot = ndb.IntegerProperty() # number hot
	launches = ndb.IntegerProperty() # number of launches
	active = ndb.BooleanProperty(default=False)
	# specifies where the flavor originated from
	# 0 - originated from pool
	# 1 - originated from an appliance
	# 2 - merge generated in pool
	locality = ndb.IntegerProperty(default=0)
	appliances = ndb.KeyProperty(kind=Appliance, repeated=True)

	# criteria based on which we decide if another flavor is same or not
	comparison_criteria = [
		'vpus',
		'memory',
		'disk',
		'network_up',
		'network_down']

	object_schema = schemes['FlavorSchema']
	object_list_schema = schemes['FlavorListSchema']

	@property
	def flags(self):
		if self.active:
			return 1
		return 8

	# see if another flavor that's equal already exists
	@classmethod
	def find_match(cls, *args, **kwargs):
		qry = cls.query()
		for crit in cls.comparison_criteria:
			qry = qry.filter(getattr(cls, crit) == kwargs[crit])
		return qry.get()

	# used to retreive a flavor by merging it's specs. if the searched specs
	# don't exist yet, it creates a new auto-generated merge-flavor.
	@classmethod
	def get_by_merge(cls, *args, **kwargs):
		criteria = dict((x, kwargs[x]) for x in cls.comparison_criteria)

		# search for flavor that matches the criteria from cls.comparison_criteria
		flavor = cls.find_match(**criteria)
		if not flavor:
			flavor = Flavor(
				# create a name that includes all specs of flavor
				name='Merge flavor ' + ' '.join([
					str(criteria[key]) for key in sorted(criteria.keys())
				]),
				#[x[key] for key in sorted(x.keys())]
				description='This is a flavor that was autogenerated by the flavor-merge',
				locality=2, # merge generated in pool
				hot=2, # because we feel like 2 is a good number
				launches=0,
				active=True,
				rate=0 # it's a manual number for now
			)
			for key in criteria.keys():
				setattr(flavor, key, criteria[key])
			flavor.put()
		return flavor

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(-cls.rate).fetch()

	@classmethod
	def get_all_active(cls):
		return cls.query().filter(cls.active == True).order(-cls.rate).fetch()

	@classmethod
	def get_by_name(cls, name):
		flavor_query = cls.query().filter(cls.name == name)
		flavor = flavor_query.get()
		return flavor


# address model
class Address(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	address = ndb.StringProperty()


# cloud model
class Cloud(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	address = ndb.StringProperty()

	@classmethod
	def get_by_user(cls, user):
		cloud_query = cls.query().filter(cls.owner == user).order(-cls.created)
		clouds = cloud_query.fetch()
		return clouds

	@classmethod
	def get_by_user_name(cls, user, name):
		cloud_query = cls.query().filter(cls.owner == user, cls.name == name)
		cloud = cloud_query.get()
		return cloud

	@classmethod
	def create_default(cls, userkey, name="Default"):
		cloud = Cloud()
		cloud.name = name
		cloud.description = "Auto generated default cloud."
		cloud.owner = userkey
		cloud.put()
		return cloud

# callback model
class Callback(ndb.Model):
	name = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	json_content = ndb.StringProperty()


# wisp model
class Wisp(ndb.Model):
	name = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	image = ndb.KeyProperty(kind=Image)
	ssh_key = ndb.StringProperty()
	post_creation = ndb.StringProperty()
	dynamic_image_url = ndb.StringProperty()
	callback_url = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	bid = ndb.IntegerProperty()
	amount = ndb.IntegerProperty()
	default = ndb.BooleanProperty(default=False)

	@classmethod
	def get_by_user(cls, user):
		wisp_query = cls.query().filter(cls.owner == user).order(cls.name)
		wisps = wisp_query.fetch()
		return wisps

	@classmethod
	def get_by_user_name(cls, user, name):
		wisp_query = cls.query().filter(cls.owner == user, cls.name == name)
		wisp = wisp_query.get()
		return wisp

	@classmethod
	def get_user_default(cls, user):
		wisp_query = cls.query().filter(cls.owner == user, cls.default == True)
		wisp = wisp_query.get()
		return wisp

	@classmethod
	def get_system_default(cls):
		# try to get default
		wisp_query = cls.query().filter(cls.owner == None, cls.default == True, cls.name == "System Default")
		wisp = wisp_query.get()

		# create it if we don't have it
		if not wisp:
			wisp = Wisp()
			wisp.name = "System Default"
			wisp.dynamic_image_url = "http://download.cirros-cloud.net/0.3.2/cirros-0.3.2-x86_64-disk.img"
			wisp.default = True
			wisp.put()

		# return whatever we did
		return wisp

	@classmethod
	def set_default(cls, wisp):
		# find the owner of this wisp
		owner = wisp.owner
	
		# get all wisps by this owner
		wisp_query = cls.query().filter(cls.owner == owner)
		wisps = wisp_query.fetch()

		# all other wisps not default wisp
		for wispr in wisps:
			wispr.default = False
			wispr.put()

		# this wisp is default
		wisp.default = True
		wisp.put()
	
		return wisp


# instance model
class Instance(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	expires = ndb.DateTimeProperty()
	started = ndb.DateTimeProperty()
	name = ndb.StringProperty()
	address = ndb.StringProperty() # bitcoin
	owner = ndb.KeyProperty(kind=User)
	appliance = ndb.KeyProperty(kind=Appliance)
	group = ndb.KeyProperty(kind=Group)
	cloud = ndb.KeyProperty(kind=Cloud)
	flavor = ndb.KeyProperty(kind=Flavor)
	ask = ndb.IntegerProperty()
	wisp = ndb.KeyProperty(kind=Wisp)
	callback_url = ndb.StringProperty()
	ipv4_private_address = ndb.StringProperty()
	ipv4_address = ndb.StringProperty()
	ipv6_address = ndb.StringProperty()
	state = ndb.IntegerProperty()
	reserved = ndb.BooleanProperty(default=False)
	token = ndb.StringProperty()
	console_output = ndb.TextProperty()

	def __setattr__(self, k, v):
		if k == "state" and self.state == 1 and v > 1:
				self.set_started_datetime()
		super(Instance, self).__setattr__(k, v)

	def set_started_datetime(self):
		self.started = datetime.utcnow()

	@classmethod
	def get_all_offered(cls, seconds=900):
		delta = datetime.now() - timedelta(seconds=seconds)
		return cls.query().filter(cls.state == 1, cls.updated > delta).order().fetch()

	@classmethod
	def get_by_name_appliance(cls, name, appliance):
		instance_query = cls.query().filter(cls.name == name, cls.appliance == appliance)
		instance = instance_query.get()
		return instance

	@classmethod
	def get_by_token(cls, token):
		query = cls.query(cls.token == token).get()
		return query

	@classmethod
	def get_by_name(cls, name):
		instance_query = cls.query().filter(cls.name == name)
		instance = instance_query.get()
		return instance

	@classmethod
	def get_by_appliance(cls, appliance):
		instance_query = cls.query().filter(cls.appliance == appliance)
		instances = instance_query.fetch()
		return instances

	@classmethod
	def get_by_cloud(cls, cloud):
		instance_query = cls.query().filter(cls.cloud == cloud)
		instances = instance_query.fetch()
		return instances

	@classmethod
	def get_count_by_cloud(cls, cloud):
		instance_query = cls.query().filter(cls.cloud == cloud)
		count = instance_query.count()
		return count

	# feteches instances older than delta many seconds
	@classmethod
	def get_older_than(cls, seconds):
		delta = datetime.now() - timedelta(seconds=seconds)
		instance_query = cls.query().filter(cls.updated < delta)
		instances = instance_query.fetch()
		return instances

	# insert or update instance
	# note that appliance is an object, not a dict
	@classmethod
	def push(cls, appliance_instance, appliance):
		# check if we have it
		instance = cls.query().filter(cls.name == appliance_instance['name']).get()

		if not instance:
			# lookup image and flavor info
			image = Image().get_by_name(appliance_instance['image'])
			flavor = Flavor().get_by_name(appliance_instance['flavor'])

			# create new entry
			instance = Instance()
			instance.name = appliance_instance['name']
			instance.address = appliance_instance['address']
			instance.ask = appliance_instance['ask']
			instance.state = appliance_instance['state']
			instance.expires = datetime.fromtimestamp(long(appliance_instance['expires']))
			instance.flavor = flavor.key
			instance.image = image.key
			instance.appliance = appliance.key
			instance.group = appliance.group
			instance.owner = appliance.owner
			instance.put()
		else:
			# update ask
			instance.ask = appliance_instance['ask']
			instance.put()

		return instance


# instance bid model (instance reservation)
class InstanceBid(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	expires = ndb.DateTimeProperty()
	name = ndb.StringProperty()
	token = ndb.StringProperty()
	instance = ndb.KeyProperty(kind=Instance)
	cloud = ndb.KeyProperty(kind=Cloud)
	flavor = ndb.KeyProperty(kind=Flavor)
	bid = ndb.IntegerProperty()
	group = ndb.KeyProperty(kind=Group)
	wisp = ndb.KeyProperty(kind=Wisp)
	callback_url = ndb.StringProperty()
	address = ndb.StringProperty()
	appliances = ndb.JsonProperty()
	need_ipv4_address = ndb.BooleanProperty()
	need_ipv6_address = ndb.BooleanProperty()
	remote_ip = ndb.StringProperty()
	status = ndb.IntegerProperty() # 0 - not filled, 1 - filled

	@classmethod
	def get_by_token(cls, token):
		query = cls.query(cls.token == token).get()
		return query

	@classmethod
	def get_incomplete_by_ip(cls, remote_ip):
		query = cls.query().filter(cls.remote_ip == remote_ip, cls.status != 1)
		bid = query.get()

		if bid:
			return bid
		else:
			return False

	@classmethod
	def get_by_instance(cls, instance):
		query = cls.query().filter(cls.instance == instance)
		bid = query.get()

		return bid

	@classmethod
	def get_expired(cls):
		epoch_time = int(time.time())
		expires = datetime.fromtimestamp(epoch_time)
		query = cls.query().filter(cls.expires < expires)
		bids = query.fetch()

		return bids
	
	@classmethod
	def reserve_instance_by_token(cls, token):
		query = cls.query().filter(cls.token == token)
		bid = query.get()

		# get list of provider ids
		appliance_ids = []
		for appliance in bid.appliances:
			appliance_ids.append(appliance['id'])

		# check if we should use all providers, or a subset
		if 1 in appliance_ids:
			# randomly select the oldest non-reserved instance and reserve it
			query = Instance.query().filter(
				Instance.reserved != True, 
				Instance.flavor == bid.flavor,
				Instance.state == 1,
				Instance.group == None
			).order(Instance.reserved, Instance.created)
			
			# grab an instance
			instance = query.get()
			
			# return if we didn't find one
			if not instance:
				logging.info("Search returned no results for instance reservation.")
				return False
		
			# reserve the instance and link it to the bid
			instance.reserved = True
			instance.token = token
			instance.put()
		
			# sleep for dev
			if config.debug:
				time.sleep(1)

			bid.instance = instance.key
			bid.put()

			# sleep for dev
			if config.debug:
				time.sleep(1)
		
		else:
			# grab a random appliance and then get an instance from it
			appliance = Appliance.get_by_id(long(random.choice(appliance_ids)))

			# randomly select the oldest non-reserved active instance by this appliance and reserve it
			query = Instance.query().filter(
				Instance.reserved != True,
				Instance.flavor == bid.flavor,
				Instance.appliance == appliance.key,
				Instance.state == 1
			).order(Instance.reserved, Instance.created)
			
			# grab an instance, return if none
			instance = query.get()
			if not instance:
				return False

			instance.reserved = True
			instance.token = token
			instance.put()

			# sleep for dev
			if config.debug:
				time.sleep(1)

			bid.instance = instance.key
			bid.put()

			# sleep for dev
			if config.debug:
				time.sleep(1)

		return instance

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

