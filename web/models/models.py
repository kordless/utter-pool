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

from utter_libs.schemas import schemas
from utter_libs.schemas.model_mixin import ModelSchemaMixin


# user model - extends webapp2 User model
class User(User):
	uid = ndb.StringProperty()
	username = ndb.StringProperty()
	email = ndb.StringProperty()
	name = ndb.StringProperty()
	timezone = ndb.StringProperty()
	country = ndb.StringProperty()
	company = ndb.StringProperty()
	provider = ndb.BooleanProperty(default=False) 
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
	def get_all(cls):
		return cls.query().fetch

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
	def keys_with_instances_on_sale(cls):
		appliances = set()
		for instance in Instance.get_all_offered():
			appliances.add(instance.appliance)
		return list(appliances)

	@classmethod
	def appliances_with_instances_on_sale(cls):
		return [
			appliance_key.get()
			for appliance_key in cls.keys_with_instances_on_sale()]

	@classmethod
	def get_geopoints(cls):
		# fetch public appliances
		appliances = cls.query().filter(
			cls.group == None,
			cls.updated >= datetime.now() - timedelta(seconds=900)).fetch()
		
		# geopoint array
		geopoints = []

		# loop through the appliances
		for appliance in appliances:
			if appliance.location:
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


# flavor model
class Flavor(ndb.Model, ModelSchemaMixin):
	name = ndb.StringProperty()
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
	# active defines if the flavor should be sent to appliances or not
	active = ndb.BooleanProperty(default=False)
	appliances = ndb.KeyProperty(kind=Appliance, repeated=True)

	# criteria based on which we decide if another flavor is same or not
	comparison_criteria = [
		{'key': 'memory', 'name': 'm'},
		{'key': 'vpus', 'name': 'v'},
		{'key': 'disk', 'name': 'd'},
		{'key': 'network_up', 'name': 'e'},  # e = egress
		{'key': 'network_down', 'name': 'i'}]  # i = ingress

	object_schema = schemas['FlavorSchema']
	object_list_schema = schemas['FlavorListSchema']

	@property
	def ask(self):
		return 0

	@property
	def flags(self):
		if self.active:
			return 1
		return 8

	# see if another flavor that's equal already exists
	@classmethod
	def find_match(cls, *args, **kwargs):
		qry = cls.query()
		for crit in [crit_full['key'] for crit_full in cls.comparison_criteria]:
			qry = qry.filter(getattr(cls, crit) == kwargs[crit])
		return qry.get()

	# method to generate flavor name based on it's specs
	@classmethod
	def flavor_name(cls, specs):
		return '.'.join([
			key_name['name'] + str(specs[key_name['key']])
			for key_name in cls.comparison_criteria])

	# generate flavor name based on it's specs
	@property
	def description(self):
		# format string
		name_format = '{memory}MB RAM, {vpus} VPUs, {disk}GB Disk'

		# add network if set
		if self.network_down > 0:
			name_format += ', {network_down} Mbps Ingress'
		if self.network_up > 0:
			name_format += ', {network_up} Mbps Egress'
		if self.network_down == 0 and self.network_up == 0:
			name_format += ', Unlimited Ingress/Egress'

		# populate from keys
		return name_format.format(**dict([
			(crit['key'], getattr(self, crit['key']))
			for crit in self.comparison_criteria]))

	# used to retreive a flavor by merging it's specs. if the searched specs
	# don't exist yet, it creates a new auto-generated merge-flavor.
	@classmethod
	def get_by_merge(cls, *args, **kwargs):
		criteria = dict(
			(crit_key, kwargs[crit_key])
			for crit_key in [
					crit_full['key']
					for crit_full in cls.comparison_criteria])

		# search for flavor that matches the criteria from cls.comparison_criteria
		flavor = cls.find_match(**criteria)
		if not flavor:
			flavor = Flavor(
				name=cls.flavor_name(criteria),
				hot=2, # because we feel like 2 is a good number
				rate=kwargs['ask'] if kwargs.has_key('ask') else 0,
				launches=0,
				active=True,
			)
			for key in criteria.keys():
				setattr(flavor, key, criteria[key])
			flavor.put()
			# because in dev put() seems to behave asynchronous
			if config.debug:
				time.sleep(2)
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

	@classmethod
	def keys_with_instances_on_sale(cls):
		flavors = set()
		for instance in Instance.get_all_offered():
			flavors.add(instance.flavor)

		return list(flavors)

	@classmethod
	def flavors_with_instances_on_sale(cls):
		return [
			flavor_key.get()
			for flavor_key in cls.keys_with_instances_on_sale()]

	@classmethod
	def keys_with_instances_by_appliance_on_sale(cls, appliance):
		flavors = set()
		for instance in Instance.get_all_offered():
			if instance.appliance == appliance:
				flavors.add(instance.flavor)

		return list(flavors)

	@classmethod
	def flavors_with_min_specs_by_appliance_on_sale(cls, specs, appliance):
		flavors = [
			flavor_key.get()
			for flavor_key in cls.keys_with_instances_by_appliance_on_sale(appliance)]

		results = []
		for flavor in flavors:
			if flavor.vpus < specs['vpus']:
				continue
			if flavor.memory < specs['memory']:
				continue
			if flavor.disk < specs['disk']:
				continue
			results.append(flavor)

		return sorted(results, key=lambda flavor: flavor.memory)

	def ask_prices(self):
		return [
			instance.ask
			for instance in Instance.query(Instance.flavor == self.key)]


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


# project model
class Project(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	repo_name = ndb.StringProperty()
	url = ndb.StringProperty()
	description = ndb.StringProperty()
	address = ndb.StringProperty()
	amount = ndb.IntegerProperty()
	vpus = ndb.IntegerProperty()
	memory = ndb.IntegerProperty()
	disk = ndb.IntegerProperty()
	image = ndb.KeyProperty(kind=Image)
	dynamic_image_name = ndb.StringProperty()
	dynamic_image_url = ndb.StringProperty()
	readme_url = ndb.StringProperty()
	readme_link = ndb.StringProperty()
	json_url = ndb.StringProperty()
	json_link = ndb.StringProperty()
	install_url = ndb.StringProperty()
	install_link = ndb.StringProperty()
	icon_url = ndb.StringProperty()
	icon_link = ndb.StringProperty()
	port = ndb.IntegerProperty()
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
	def get_by_url(cls, url):
		query = cls.query().filter(cls.url == url)
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

	def is_configured(self):
		if not self.readme_url:
			return False
		if not self.install_url:
			return False
		if not self.icon_url:
			return False

		return True

	@property
	def use_dynamic_image(self):
		if self.dynamic_image_url is not None and self.dynamic_image_url != "":
			return True
			
	# generate and return a dynamic image
	def get_dynamic_image(self):
		class dynamic_image(object):
			def __init__(self, project):
				self.url = project.dynamic_image_url
				self.name = project.dynamic_image_name
				self.container_format = "bare"
				self.disk_format = "qcow2"

		return dynamic_image(self)


# wisp model
class Wisp(ndb.Model):
	name = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	image = ndb.KeyProperty(kind=Image)
	ssh_key = ndb.TextProperty()
	ssh_key_hash = ndb.StringProperty()
	post_creation = ndb.TextProperty()
	dynamic_image_url = ndb.StringProperty()
	image_disk_format = ndb.StringProperty()
	image_container_format = ndb.StringProperty()
	callback_url = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	bid = ndb.IntegerProperty()
	amount = ndb.IntegerProperty()
	default = ndb.BooleanProperty(default=False)
	token = ndb.StringProperty()
	remote_ip = ndb.StringProperty()
	project = ndb.KeyProperty(kind=Project)

	@classmethod
	def get_by_remote_ip(cls, remote_ip):
		query = cls.query().filter(cls.remote_ip == remote_ip, cls.status != 1)
		wisp = query.get()

		if wisp:
			return wisp
		else:
			return False

	@property
	def use_dynamic_image(self):
		if self.dynamic_image_url is not None and self.dynamic_image_url != "":
			return True

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
	def patch_to_stock(cls, project):
		# get all the wisps using this project
		query = cls.query().filter(cls.project == project)
		wisps = query.fetch()
		
		# loop through list of wisps using this project
		for wisp in wisps:
			# patch the image
			project = wisp.project.get()
			if project.image:
				wisp.image = project.image
			elif project.dynamic_image_url:
				wisp.dynamic_image_url = project.dynamic_image_url
				wisp.image_disk_format = "qcow2"
				wisp.image_container_format = "bare"

			# get the rendered json config from ourselves
			if project.json_url:
				content = json.loads(
					urlfetch.fetch(
						'%s/projects/%s/files/utterio.json' % (
							config.website_url.strip('/'),
							project.key.id()
						)
					).content
				)
				
				post_creation = ""
				# grab out the post_create lines
				for line in content['post_create']:
					post_creation = post_creation + '%s\n' % line

				# add the wisps cloud-config stuff
				wisp.post_creation = post_creation	
			
			# remove project
			wisp.project = None

			# update
			wisp.put()


	@classmethod
	def get_system_default(cls):
		# try to get default
		wisp_query = cls.query().filter(cls.owner == None, cls.default == True, cls.name == "System Default")
		wisp = wisp_query.get()

		# create it if we don't have it
		if not wisp:
			wisp = Wisp()
			wisp.name = "default"
			wisp.dynamic_image_url = "http://download.cirros-cloud.net/0.3.3/cirros-0.3.3-x86_64-disk.img"
			wisp.image_container_format = "bare"
			wisp.image_disk_format = "qcow2"
			wisp.default = True
			wisp.put()

		# return whatever we did
		return wisp

	@classmethod
	def from_project(
		cls,
		ssh_key,
		project,
		owner
	):
		# calculate the hash of the ssh_key+project.key.id()
		import hashlib
		m = hashlib.md5()
		m.update(ssh_key)
		m.update(str(project.key.id()))
		ssh_key_hash = m.hexdigest()

		# do we have this wisp already?
		if not owner:		
			entry = cls.query().filter(
				cls.ssh_key_hash == ssh_key_hash
			).get()
		else:
			entry = cls.query().filter(
				cls.ssh_key_hash == ssh_key_hash, 
				cls.owner == owner.key
			).get()
		
		# create if we didn't find it
		if not entry:
			# generate new token and create new entry 
			token = "%s" % generate_token(size=16, caselimit=True)
			entry = Wisp(
				name = project.name,
				ssh_key = ssh_key,
				ssh_key_hash = ssh_key_hash,
				token = token,
				project = project.key,
				owner = owner.key
			)
			entry.put()

		return entry

	@classmethod
	def from_stock(
		cls,
		ssh_key,
		post_creation,
		dynamic_image_url,
		image_disk_format,
		image_container_format,
		owner
	):
		# calculate the hash of the ssh_key+post_creation+dynamic_image_url
		import hashlib
		m = hashlib.md5()
		m.update(ssh_key)
		m.update(post_creation)
		m.update(dynamic_image_url)
		ssh_key_hash = m.hexdigest()

		# do we have this wisp already?
		if not owner:		
			entry = cls.query().filter(
				cls.ssh_key_hash == ssh_key_hash
			).get()
		else:
			entry = cls.query().filter(
				cls.ssh_key_hash == ssh_key_hash, 
				cls.owner == owner.key
			).get()
		
		# create if we didn't find it
		if not entry:
			# generate new token and create new entry 
			token = "%s" % generate_token(size=16, caselimit=True)
			entry = Wisp(
				name = 'anonymous',
				ssh_key = ssh_key,
				ssh_key_hash = ssh_key_hash,
				post_creation = post_creation,
				dynamic_image_url = dynamic_image_url,
				image_disk_format = image_disk_format,
				image_container_format = image_container_format,
				token = token,
				owner = owner.key
			)
			entry.put()

		return entry

	@classmethod
	def get_expired_anonymous(cls):
		# grab anonymous wisps older than a day
		epoch_time = int(time.time())
		expires = datetime.fromtimestamp(epoch_time-86400)
		query = cls.query().filter(cls.created < expires, cls.name == 'anonymous', cls.owner == None)
		wisps = query.fetch()

		return wisps

	@classmethod
	def get_by_token(cls, token):
		query = cls.query(cls.token == token).get()
		return query

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

	# generate and return a dynamic image
	def get_dynamic_image(self):
		class dynamic_image(object):
			def __init__(self, wisp):
				self.url = wisp.dynamic_image_url
				self.name = 'dynamic'
				self.container_format = wisp.image_container_format
				self.disk_format = wisp.image_disk_format

		return dynamic_image(self)


# instance model
class Instance(ndb.Model, ModelSchemaMixin):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	expires = ndb.IntegerProperty()
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
	image_url = ndb.StringProperty()
	image_name = ndb.StringProperty()
	state = ndb.IntegerProperty()
	reserved = ndb.BooleanProperty(default=False)
	token = ndb.StringProperty()
	console_output = ndb.TextProperty()
	meta = ndb.TextProperty()

	object_schema = schemas['InstanceSchema']

	def __setattr__(self, k, v):
		if k == "state" and self.state == 1 and v > 1:
				self.set_started_datetime()
		super(Instance, self).__setattr__(k, v)

	def set_started_datetime(self):
		self.started = datetime.utcnow()

	@classmethod
	def get_all(cls):
		return cls.query().fetch

	@classmethod
	def get_all_offered(cls, seconds=900):
		delta = datetime.now() - timedelta(seconds=seconds)
		return cls.query().filter(cls.state == 1, cls.updated > delta).order().fetch()

	@classmethod
	def get_by_name_appliance(cls, name, appliance):
		query = cls.query().filter(cls.name == name, cls.appliance == appliance)
		result = query.get()
		return result

	@classmethod
	def get_by_token(cls, token):
		query = cls.query(cls.token == token).get()
		return query

	@classmethod
	def get_by_name(cls, name):
		query = cls.query().filter(cls.name == name)
		result = query.get()
		return result

	@classmethod
	def get_by_group(cls, group):
		query = cls.query().filter(cls.group == group)
		results = query.fetch()
		return results

	@classmethod
	def get_by_appliance(cls, appliance):
		query = cls.query().filter(cls.appliance == appliance)
		results = query.fetch()
		return results

	@classmethod
	def get_by_cloud(cls, cloud):
		query = cls.query().filter(cls.cloud == cloud)
		results = query.fetch()
		return results

	@classmethod
	def get_count_by_cloud(cls, cloud):
		query = cls.query().filter(cls.cloud == cloud)
		count = query.count()
		return count

	# feteches instances older than delta many seconds
	@classmethod
	def get_older_than(cls, seconds):
		delta = datetime.now() - timedelta(seconds=seconds)
		query = cls.query().filter(cls.updated < delta)
		results = query.fetch()
		return results

	# insert or update instance
	# note that appliance is an object, not a dict
	@classmethod
	def push(cls, appliance_instance, appliance):
		# check if we have it
		instance = cls.query().filter(cls.name == appliance_instance['name']).get()

		if not instance:
			# lookup flavor info
			flavor = Flavor().get_by_merge(**appliance_instance['flavor'])

			# create new entry
			instance = Instance()
			instance.name = appliance_instance['name']
			instance.address = appliance_instance['address']
			instance.ask = appliance_instance['flavor']['ask']
			instance.state = appliance_instance['state']
			instance.expires = appliance_instance['expires']
			instance.flavor = flavor.key
			instance.appliance = appliance.key
			instance.group = appliance.group
			instance.owner = appliance.owner
			instance.put()
		else:
			# update ask
			instance.ask = appliance_instance['flavor']['ask']
			instance.state = appliance_instance['state']
			instance.appliance = appliance.key
			instance.group = appliance.group
			instance.owner = appliance.owner
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
	def delete_by_wisp(cls, wisp):
		query = cls.query().filter(cls.wisp == wisp)
		bid = query.get()
		if bid:
			instance = bid.instance.get()
			instance.reserved == False
			instance.token == None
			bid.key.delete()
		return

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

