# standard library imports
import logging, os, md5, sys
import hashlib, json
import simplejson
import time
from datetime import datetime
from HTMLParser import HTMLParser

# google
from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.api import channel

# related webapp2 imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

# local application/library specific imports
import config
from lib.utils import generate_token
from lib.apishims import InstanceApiShim
from web.basehandler import BaseHandler

# note User is not used except to send to channel
from web.models.models import User, Appliance, Wisp, Cloud, Instance, Project, InstanceBid, Image, Flavor, LogTracking

from utter_libs.schemas import schemas
from utter_libs.schemas.helpers import ApiSchemaHelper

# easy button for error response
def error_response(handler, message, code, params):
	params['response'] = "error"
	params['message'] = message
	handler.response.set_status(code)
	return handler.render_template('api/response.json', **params)

# appliance token validation
# http://0.0.0.0/api/v1/authorization/ via POST
class TokenValidate(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		# paramters, assume failure, response type
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"

		# get appliance variables
		try:
			packet = json.loads(self.request.body)
			apitoken = packet['appliance']['apitoken']
		except:
			params['message'] = "You must submit a valid JSON object with a token."
			self.response.set_status(401)
			return self.render_template('api/response.json', **params)	
		
		# load the appliance
		appliance = Appliance.get_by_token(apitoken)

		if not appliance:
			params['message'] = "Token is not valid."
			self.response.set_status(401)
			return self.render_template('api/response.json', **params)

		if appliance.activated == False:
			# appliance not activated
			params['message'] = "Appliance has been disabled by pool controller. Please contact support."
			self.response.set_status(409)
			return self.render_template('api/response.json', **params)

		# update appliance info
		latitude = float(packet['appliance']['location']['latitude'])
		longitude = float(packet['appliance']['location']['longitude'])
		appliance.location = ndb.GeoPt(latitude, longitude)
		appliance.dynamicimages = bool(packet['appliance']['dynamicimages'])			
		appliance.put()

		# respond with success
		params['response'] = "success"
		params['message'] = "Appliance token authenticated."
		return self.render_template('api/response.json', **params)

	def get(self):
		return self.post()


# bids creation
# http://0.0.0.0/api/v1/bids/
class BidsHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	# creation of a bid
	def post(self):
		# request basics
		ip = self.request.remote_addr

		# response, type, cross posting
		params = {}
		self.response.headers['Content-Type'] = "application/json"
		self.response.headers['Access-Control-Allow-Origin'] = '*'

		# check if this IP has any other bids open
		instancebid = InstanceBid.get_incomplete_by_ip(ip)


		# check we have an instancebid already
		if instancebid:
			# validate wisp
			if instancebid.wisp == None:
				instancebid.key.delete()
				return error_response(self, "Deleting bid because no wisp was associated.", 403, params)

			# load the payment address
			if instancebid.instance:
				instancebid.address = instancebid.instance.get().address
				instancebid.ask = instancebid.instance.get().ask
			else:
				# we should have an instance assosciated, so bail on this one
				instancebid.key.delete()
				return error_response(self, "Deleting bid because no instance was associated.", 403, params)

			params['response'] = "error"
			params['message'] = "The calling IP address already has an instance reservation in progress."
			params['instancebid'] = instancebid
			self.response.set_status(403)
			return self.render_template('api/bid.json', **params)	

		# load POSTed JSON
		try:
			request = json.loads(self.request.body)
		except Exception as ex:
			return error_response(self, "Failure in parsing request JSON.", 403, params)

		# load optional values or defaults
		# ipv4 (allow default)
		if 'requires_ipv4' in request:
			requires_ipv4 = request['requires_ipv4']
		else:
			requires_ipv4 = 0
		
		# ipv6 (allow default)
		if 'requires_ipv6' in request:
			requires_ipv6 = request['requires_ipv6']
		else:
			requires_ipv6 = 0

		# providers (allow default)
		if 'providers' in request:
			providers = request['providers']
		else:
			providers = [{u'id': 1, u'name': u'All Providers'}]		

		# flavors (required)
		if 'flavor' in request:
			flavor_name = request['flavor']
			flavor = Flavor.get_by_name(flavor_name)

			# check if flavor was found
			if not flavor:
				return error_response(self, "Flavor not found.", 403, params)

		else:
			return error_response(self, "Flavor name is required.", 403, params)

		# cloud (optional)
		if 'cloud_id' in request:
			cloud_id = request['cloud_id']
			cloud = Cloud.get_by_id(long(cloud_id))

			# check if cloud was found
			if not cloud:
				return error_response(self, "Cloud ID not found.", 403, params)
		else:
			cloud = None

		# disallow both a wisp and a callback_url
		if 'wisp_id' in request and 'callback_url' in request:
			return error_response(self, "A wisp and a callback URL may not be used together.", 403, params)

		# require either a wisp or a callback_url
		if 'wisp_id' not in request and 'callback_url' not in request:
			return error_response(self, "A valid wisp or a callback URL is required.", 403, params)

		# load the wisp, if there is one
		if 'wisp_id' in request:
			wisp_id = request['wisp_id']
			wisp = Wisp.get_by_id(long(wisp_id))
		else:
			wisp = None
		
		# load the callback URL, if there is one
		if 'callback_url' in request:
			callback_url = request['callback_url']
		elif wisp:
			callback_url = wisp.callback_url
		else:
			callback_url = ""

		# test we have a callback_url or a valid image in the wisp
		if callback_url > "":
			try:
				result = urlfetch.fetch(callback_url, deadline=5)
				if result.status_code > 399:
					return error_response(self, "The callback URL is unreachable.", 403, params)
				# test result's image URL
			except Exception as ex:
				return error_response(self, "The callback URL is unreachable.", 403, params)
		elif wisp:
			if wisp.image == None and wisp.dynamic_image_url == None and wisp.project == None:
				return error_response(self, "A valid wisp or a callback URL is required.", 403, params)

		# grab a new bid hash to use for the new bid
		token = generate_token(size=16)
		name = "smr-%s" % generate_token(size=8)

		# create a new bid
		instancebid = InstanceBid()
		instancebid.token = token
		instancebid.name = name
		instancebid.need_ipv4_address = bool(requires_ipv4)
		instancebid.need_ipv6_address = bool(requires_ipv6)
		instancebid.flavor = flavor.key
		instancebid.remote_ip = ip
		instancebid.appliances = providers # providers is already JSON
		instancebid.status = 0
		instancebid.callback_url = callback_url

		# expires in 5 minutes
		epoch_time = int(time.time())
		instancebid.expires = datetime.fromtimestamp(epoch_time+300)

		# add wisp, if present
		if wisp:
			instancebid.wisp = wisp.key
		
		# add cloud, if present
		if cloud:
			instancebid.cloud = cloud.key

		# update
		instancebid.put()

		# sleep for dev
		if config.debug:
			time.sleep(2)

		# reserve the instance
		InstanceBid.reserve_instance_by_token(instancebid.token)

		# get the address, if you got an instance
		if instancebid.instance:
			address = instancebid.instance.get().address
			ask = instancebid.instance.get().ask
		else:
			# no instance was reserved
			instancebid.key.delete()
			return error_response(self, "No valid instances were returned.", 403, params)
			
		# hack address and ask into instancebid object for template (not stored)
		instancebid.address = address
		instancebid.ask = ask

		# build out the response
		params['response'] = "success"
		params['message'] = "A new instance bid has been created."	
		params['instancebid'] = instancebid

		# return response and include cross site POST headers
		self.response.set_status(201)

		return self.render_template('api/bid.json', **params)


	def get(self):
		return self.post()

	def options(self):
		self.response.headers['Access-Control-Allow-Origin'] = '*'
		self.response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'
		self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
		return


# bids detail
# http://0.0.0.0/api/v1/bids/<token>/
class BidsDetailHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def get(self, token=None):
		# response, type, cross posting
		params = {}
		self.response.headers['Content-Type'] = "application/json"
		self.response.headers['Access-Control-Allow-Origin'] = '*'

		# look for instance bid first
		bid = InstanceBid.get_by_token(token)

		if bid:
			# build out the response
			params['response'] = "success"
			params['message'] = "Reservation found by token."	
			params['instancebid'] = bid

			# return response
			self.response.set_status(201)
			return self.render_template('api/bid.json', **params)

		else:
			# look for instance
			instance = Instance.get_by_token(token)
			
			if instance:
				# build out the response
				params['response'] = "success"
				params['message'] = "Instance found by token."	
				params['instance'] = instance

				# return response
				self.response.set_status(201)
				return self.render_template('api/instancedetail.json', **params)
			
			else:
				# build out the error response
				params['response'] = "error"
				params['message'] = "No resources found by token."

				return self.render_template('api/response.json', **params)

	def delete(self, token=None):
		bid = InstanceBid.get_by_token(token)

		# delete the bid
		if bid:
			bid.key.delete()

		# patch up the respective instance if it's not been started
		instance = Instance.get_by_token(token)

		if instance:
			# only patch instance if it's not been started
			if instance.state <= 1:
					instance.reserved = False
					instance.token = None
					instance.put()

		return

	def options(self):
		self.response.headers['Access-Control-Allow-Origin'] = '*'
		self.response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'
		self.response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
		return


# list of all available instances for sale
# http://0.0.0.0/api/v1/instances/
class InstancesHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		# request basics
		ip = self.request.remote_addr
		offset = self.request.get("offset")
		limit = self.request.get("limit")

		instances = Instance().get_all_offered()
		
		# add gravatar URLs
		for instance in instances:
			email = instance.appliance.get().owner.get().email
			gravatar_hash = md5.new(email.lower().strip()).hexdigest()
			instance.gravatar_url = "https://www.gravatar.com/avatar/%s" % gravatar_hash

		# build parameter list
		params = {
			'remote_ip': ip,
			'instances': instances
		}

		# return images via template
		self.response.headers['Content-Type'] = 'application/json'
		return self.render_template('api/instances.json', **params)

	def get(self):
		return self.post()


# instance callback handler to handle pool_instance() calls from utter-va
# http://0.0.0.0/api/v1/instances/<instance_name>/ via POST, PUT, GET
class InstanceDetailHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True
	
	def post(self, instance_name):
		# paramters, assume failure, response type
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"

		# request basics
		ip = self.request.remote_addr

		try:
			body = json.loads(self.request.body)
			instance_schema = schemas['InstanceSchema'](**body['instance'])
			appliance_schema = schemas['ApplianceSchema'](**body['appliance'])

			# try to authenticate appliance
			if not Appliance.authenticate(appliance_schema.apitoken.as_dict()):
				logging.error("%s is using an invalid token(%s) or appliance deactivated."
					% (ip, appliance_schema.apitoken.as_dict()))
				return error_response(self, "Token is not valid.", 401, params)

			# fetch appliance and instance
			appliance = Appliance.get_by_token(appliance_schema.apitoken.as_dict())

			instance = Instance.get_by_name_appliance(
				instance_schema.name.as_dict(), 
				appliance.key
			)

			# if instance doesn't already exist, create it
			if not instance:
				wisp = Wisp.get_user_default(appliance.owner)
				if not wisp:
					wisp = Wisp.get_system_default()
				instance = Instance(wisp=wisp.key)

			# wrap instance into api shim in order to translate values from structure
			# of api to structure of model. I hope at some point in the future the two
			# models are similar enough so we can entirely drop this shim
			instance_shim = InstanceApiShim(instance)

			# update instance with values from post
			ApiSchemaHelper.fill_object_from_schema(
				instance_schema, instance_shim)

			# associate instance with it's appliance
			instance_shim.appliance = appliance

		except Exception as e:
			return error_response(self, 'Error in creating or updating instance from '
				'post data, with message {0}'.format(str(e)), 500, {})


		# update local instance
		instance.put()

		# update appliance ip address hint
		if instance.state > 3 and instance.ipv4_address:
			appliance.ipv4enabled = True
		if instance.state > 3 and instance.ipv6_address:
			appliance.ipv6enabled = True
		appliance.put()

		# sleep for dev
		if config.debug:
			time.sleep(1)

		# send update information to channel
		if instance.token:

			output = {
				"name": instance.name,
				"token": instance.token,
				"state": instance.state,
			}
			channel.send_message(instance.token, json.dumps(output))		

		# pop a reload just in case user is on their cloud page
		if instance.owner:
			user_info = User.get_by_id(long(instance.owner.id()))
			channel.send_message(user_info.key.urlsafe(), "reload")

		# convert bid to instance
		# check if there is an instance bid reservation on this instance
		instancebid = InstanceBid.get_by_instance(instance.key)
		if instancebid:
			# check for a bid callback_url (entered in the callback field on the launcher)
			if instancebid.callback_url > "":
				# put the callback into the instance
				instance.callback_url = instancebid.callback_url
			
			elif instancebid.wisp:
				# otherwise, get the wisp's callback URL	
				callback_url = instancebid.wisp.get().callback_url
			
				# if the wisp has an empty callback URL, populate the instance with the wisp's bid details
				if callback_url == "" or callback_url == None:
					instance.wisp = instancebid.wisp
					instance.owner = instancebid.wisp.get().owner
					instance.cloud = instancebid.cloud
				else:
					# we have a custom callback in the wisp itself, so move to instance
					instance.callback_url = callback_url

			# update the instance
			instance.put()

			# delete the instance reservation
			instancebid.key.delete()

		# proxy custom callback
	
		"""
		BEGIN CODE CALLOUT
		"""
		# August 24, 2014
		#
		# The following code retrieves content from a remote server and proxies it to 
		# an appliance for starting an instance. It is at this point an anonymous user's
		# callback pattern is most venerable to being monitored and manipulated.
		# 
		# The author of this software issues a warrant canary tweet to @stackape which 
		# should appear on the 1st of each month indicating the absence of a gag order
		# having been issued to StackMonkey, Utter.io, or Kord Campbell.
		#
		# Please monitor the code block between BEGIN CODE CALLOUT and END CODE CALLOUT 
		# if the canary tweet does not appear on schedule. Please monitor any callback
		# file's retrieval patterns if the canary tweet does not appear on schedule.
		# Please report any findings to the community sections of the project/site.
		#
		# Remember, the code is Open Source. Use that fact to the community's advantage.
		# 
		# The warrant canary will likely be your only indication a change has possibly
		# taken place to the system.  These changes may or may not enable a government 
		# agency to intercept and monitor instances using a custom URL callback.
		#
		# Kord Campbell
		#
		if instance.callback_url:
			try:
				result = urlfetch.fetch(instance.callback_url, deadline=5)
			except Exception as ex:
				logging.error("Error fetching callback URL content.")
				instance.console_output = "Error fetching callback url=(%s)'s' content. %s" % (instance.callback_url, ex)
				instance.put()

				# user may be sitting on an instance reservation here, so reload the page
				# this will force the handler to redirect the user to the instance page
				channel.send_message(instance.token, "reload")
				return error_response(self, "Error fetching callback URL content.", 401, params)

			# return content retrieved from callback URL if the JSON returned by this method includes
			# a callback_url in the data, the appliance will follow the URL and will not call this API 
			# again during the life of the instance.
			self.response.headers['Content-Type'] = 'application/json'
			self.response.write(json.dumps(json.loads(result.content), sort_keys=True, indent=2))
			
			# return from here	
			return

		"""
		END CODE CALLOUT
		"""

		# at this point we have one of two scenarios:
		# 1. an external instance start (registered user with appliance, sans instancebid)
		# 2. registered user using a normal wisp WITHOUT a callback_url

		# grab the instance's wisp
		if instance.wisp:
			# if instance is using a wisp
			wisp = Wisp.get_by_id(instance.wisp.id())
		else:
			# no wisp on instance
			wisp = Wisp.get_user_default(instance.owner)

		# deliver default system wisp if none (external instance start)
		if not wisp:
			wisp = Wisp.get_system_default()

		# load wisp image
		if not wisp.use_dynamic_image:
			image = wisp.image.get()
		else:
			image = wisp.get_dynamic_image()

		# pop the ssh_key into an array
		if wisp.ssh_key:
			ssh_keys = []
			for line in iter(wisp.ssh_key.splitlines()):
				ssh_keys.append(line)
		else:
			ssh_keys = [""]

		# 
		# pop the post creation script into an array
		if wisp.post_creation:
			post_creation = []
			for line in iter(wisp.post_creation.splitlines()):
				post_creation.append(line)
		else:
			post_creation = [""]

		# some of replay's magic - need docs on this
		start_params = schemas['InstanceStartParametersSchema']()
		data = {
			'image': image,
			'callback_url': wisp.callback_url if wisp.callback_url else "",
			'ssh_keys': ssh_keys,
			'post_create': post_creation}
		ApiSchemaHelper.fill_schema_from_object(start_params, data)

		self.response.set_status(200)
		self.response.headers['Content-Type'] = 'application/json'

		# write dictionary as json string
		self.response.out.write(json.dumps(
				# retrieve dict from schema
				start_params.as_dict()))

	# unauthenticated put for meta data
	def put(self, instance_name = None):
		# disable csrf check in basehandler
		csrf_exempt = True

		# paramters, assume failure, response type
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"

		# get the instance, build the response type
		instance = Instance.get_by_name(instance_name)
		self.response.headers['Content-Type'] = "application/json"		

		# if no instance, then show error
		if not instance:
			params['message'] = "Instance not found."
			self.response.set_status(404)
			return self.render_template('api/response.json', **params)
		else:
			# load the instance's meta data, if any
			if instance.meta:
				meta = json.loads(instance.meta)
			else:
				meta = json.loads('{}')

		# load the json from the call
		try:
			body = json.loads(self.request.body)

			# loop through key space and set meta data
			for key in body:
				meta[key] = body[key]

			# dump back into the db
			instance.meta = json.dumps(meta)
			instance.put()

		except Exception as e:
			params['message'] = "An error was encountered with parsing meta key values: %s." % str(e)
			self.response.set_status(500)
			return self.render_template('api/response.json', **params)

		# send update information to channel
		if instance.token:
			output = {
				"name": instance.name,
				"token": instance.token,
				"state": instance.state,
				"meta": meta
			}
			channel.send_message(instance.token, json.dumps(output))	

		# build response
		params = {
			"instance": instance,
			"meta": json.loads(instance.meta)
		}
		params['response'] = "success"
		self.response.headers['Content-Type'] = 'application/json'
		
		return self.render_template('api/instance.json', **params)


	# unauthenticated endpoint
	def get(self, instance_name = None):

		# get the instance, build the response type
		instance = Instance.get_by_name(instance_name)
		self.response.headers['Content-Type'] = "application/json"

		# if no instance, then show error
		if not instance:
			params['message'] = "Instance not found."
			self.response.set_status(404)
			return self.render_template('api/response.json', **params)

		# load the instance's meta data, if any
		if instance.meta:
			meta = json.loads(instance.meta)
		else:
			meta = json.loads('{}')

		# build response
		params = {
			"instance": instance,
			"meta": meta
		}

		params['response'] = "success"
		self.response.headers['Content-Type'] = 'application/json'
		
		return self.render_template('api/instance.json', **params)


# accept sale of multiple instances from provider
# http://0.0.0.0/api/v1/broker/ via POST
class BrokerHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		# paramters, assume failure, response type
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"

		# get appliance variables
		try:
			packet = json.loads(self.request.body)
			apitoken = packet['appliance']['apitoken']
		except:
			params['message'] = "You must submit a valid JSON object with a token."
			self.response.set_status(401)
			return self.render_template('api/response.json', **params)	
		
		# load the appliance
		appliance = Appliance.get_by_token(apitoken)

		if not appliance:
			params['message'] = "Token is not valid."
			self.response.set_status(401)
			return self.render_template('api/response.json', **params)

		if appliance.activated == False:
			# appliance not activated
			params['message'] = "Appliance has been disabled by pool controller. Please contact support."
			self.response.set_status(409)
			return self.render_template('api/response.json', **params)

		# update appliance info
		latitude = float(packet['appliance']['location']['latitude'])
		longitude = float(packet['appliance']['location']['longitude'])
		appliance.location = ndb.GeoPt(latitude, longitude)
		appliance.dynamicimages = bool(packet['appliance']['dynamicimages'])			
		appliance.put()

		# loop through instances being advertised for sale
		for appliance_instance in packet['instances']:
			# pass in appliance_instance and appliance object
			#logging.info("instance: %s" % appliance_instance['name'])
			instance = Instance.push(appliance_instance, appliance)

		# build parameter list
		params = {}
		params['response'] = "success"
		params['message'] = "Instances accepted for sale."
		self.response.headers['Content-Type'] = 'application/json'
		
		return self.render_template('api/response.json', **params)
		
	def get(self):
		return self.post()


# images list
# http://0.0.0.0/api/v1/images/ GET or POST
class ImagesHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		images = Image().get_all()
		
		# build parameter list
		params = {
			'images': images
		}

		# return images via template
		self.response.headers['Content-Type'] = 'application/json'
		return self.render_template('api/images.json', **params)

	def get(self):
		return self.post()


# flavors list
# http://0.0.0.0/api/v1/flavors/ GET or POST
class FlavorsHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self, action):
		self.response.headers['Content-Type'] = 'application/json'
		self.response.set_status(200)
		# write dictionary as json string
		self.response.out.write(json.dumps(
				# retrieve flavors as schema and convert schema to dict
				Flavor.as_schema_list(
					# pass get_all method as query object
					Flavor.query()).as_dict()))

	def get(self, action):
		return self.post(action)


# used to log whatever we want to track
# http://0.0.0.0/api/v1/track/ via GET
class TrackingPingHandler(BaseHandler):
	def get(self):
		# get ip address
		ip = self.request.remote_addr
		message = self.request.get("message")

		# update db
		track = LogTracking()
		track.ip = ip
		if message:
			track.message = message
		else:
			track.message = "Simple tracking request."
		track.put()

		# return JSON response
		params = {}
		params['response'] = "success"
		params['result'] = "ping recorded for %s" % ip
		self.response.headers['Content-Type'] = "application/json"
		return self.render_template('api/response.json', **params)


# create wisps, anonymously if needed
# http://0.0.0.0/api/v1/wisp/ via GET, POST
class WispHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		# try to pull get user info from a browser based session
		if self.user_id:
			user_info = User.get_by_id(long(self.user_id))
		else:
			user_info = None

		# paramters, assume failure, response type
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"

		# response headers
		self.response.headers['Content-Type'] = "application/json"
		self.response.headers['Access-Control-Allow-Origin'] = '*'

		# load various variables
		body = json.loads(self.request.body)
		
		# SSH key (not required)
		try:
			ssh_key = body['ssh_key']
		except:
			ssh_key = ""

		# load project if we have it
		try:
			project_id = body['project_id']
			project = Project.get_by_id(long(project_id))
		except:
			project = None

		# handle project wisps differently
		if project:
			wisp = Wisp().from_project(
				ssh_key,
				project,
				user_info
			)
		else:
			try:
				post_creation = body['post_creation']
			except:
				post_creation = ""

			try:
				image_id = body['image_id']
				image = Image.get_by_id(long(image_id))
			except:
				try:
					dynamic_image_url = body['dynamic_image_url']
				except:
					# we don't have an image or a URL, so nothing can do
					params['message'] = "Wisps require an image to boot."
					self.response.set_status(401)
					return self.render_template('api/response.json', **params)

			# disk and container formats if they were sent (usually qcow/bare)
			try:
				image_disk_format = body['image_disk_format']
			except:
				image_disk_format = "qcow2"
			try:
				image_container_format = body['image_container_format']
			except:
				image_container_format = "bare"

			# create an anonymous wisp if we don't have it already
			wisp = Wisp().from_stock(
				ssh_key, 
				post_creation, 
				dynamic_image_url, 
				image_disk_format, 
				image_container_format,
				user_info
			)

		if wisp:	
			# return JSON response
			params['response'] = "success"
			params['wisp'] = wisp
			
			return self.render_template('api/wisp.json', **params)
		else:
			params['message'] = "Wisp creation failed."
			self.response.set_status(401)
			return self.render_template('api/response.json', **params)
	
	def get(self):
		return self.post()

# create anonymous wisp
# http://0.0.0.0/api/v1/wisp/<token>/ via GET, POST
class WispViewHandler(BaseHandler):
	def get(self, token=None):
		# paramters, assume failure, response type
		# response, type, cross posting
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"
		self.response.headers['Access-Control-Allow-Origin'] = '*'

		# look for instance bid first
		wisp = Wisp.get_by_token(token)
		
		# if no instance, then show error
		if not wisp:
			params['message'] = "Wisp not found."
			self.response.set_status(404)
			return self.render_template('api/response.json', **params)
		else:
			params['respose'] = "success"
			params['wisp'] = wisp
			
		return self.render_template('api/wisp.json', **params)


# generate list of appliances
# http://0.0.0.0/api/v1/appliances/ GET
class ApplianceListHandler(BaseHandler):
	def get(self):
		appliances = Appliance().appliances_with_instances_on_sale()

		# add gravatar URLs
		for appliance in appliances:
			email = appliance.owner.get().email
			gravatar_hash = md5.new(email.lower().strip()).hexdigest()
			appliance.gravatar_url = "https://www.gravatar.com/avatar/%s" % gravatar_hash

		# return JSON response
		params = {
			'appliances': appliances,
			'message': "This is a list of all active appliances with instances for sale."
		}
		self.response.headers['Content-Type'] = "application/json"
		return self.render_template('api/appliances.json', **params)


# generate list of geopoints for appliances
# http://0.0.0.0/api/v1/appliances/geopoints/ GET
class ApplianceGeoPoints(BaseHandler):
	def get(self):
		geopoints = Appliance().get_geopoints()

		# return JSON response
		params = {
			'geopoints': geopoints
		}
		self.response.headers['Content-Type'] = "application/json"
		return self.render_template('api/geopoints.json', **params)

