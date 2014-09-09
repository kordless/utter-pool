# standard library imports
import logging, os, md5
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
from web.basehandler import BaseHandler

# note User is not used except to send to channel
from web.models.models import User, Appliance, Wisp, Cloud, Instance, InstanceBid, Image, Flavor, LogTracking

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

		if instancebid:
			# load the payment address
			if instancebid.instance:
				instancebid.address = instancebid.instance.get().address
			else:
				# we should have an instance assosciated, so bail on this one
				instancebid.key.delete()
				return error_response(self, "Deleting bid because no instance was associated.", 403, params)

			# IP has a unmatched bid, so deny creating new one
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
		if 'flavor_id' in request:
			flavor_id = request['flavor_id']
			flavor = Flavor.get_by_id(long(flavor_id))

			# check if flavor was found
			if not flavor:
				return error_response(self, "Flavor ID not found.", 403, params)

		else:
			return error_response(self, "Flavor ID is required.", 403, params)

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
			if wisp.image == None and wisp.dynamic_image_url == None:
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
# http://0.0.0.0/api/v1/bids/xxxxxxxx/
class BidsDetailHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def get(self, token=None):
		params = {}

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
# http://0.0.0.0/api/v1/instances/smi-xxxxxxxxx/ via POST
class InstanceDetailHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	#################################################
	# API FOR INSTANCE DETAIL POST FROM APPLIANCE   #
	# 1. parse instance JSON data from appliance    #
	# 2. authenticate and validate JSON             #
	# 3. locate or create new instance              #
	# 4. update local instance with appliance data  #
	# 5. send update information to channel         #
	# 6. build response packet                      #
	# 7a. proxy 1st callback URL's JSON to appliance#
	# or...                                         #
	# 7b. build JSON response for appliance         #
	#################################################
	
	def post(self, instance_name):
		# paramters, assume failure, response type
		params = {}
		params['response'] = "error"
		self.response.headers['Content-Type'] = "application/json"

		# request basics
		ip = self.request.remote_addr

		##############################################
		# 1. parse instance JSON data from appliance #
		##############################################
		
		try:
			packet = json.loads(self.request.body)
			apitoken = packet['appliance']['apitoken']
		except:
			logging.error("%s submitted an invalid JSON instance object." % ip)
			return error_response(self, "A valid JSON object could not be loaded from the request.", 401, params)

		#####################################
		# 2. authenticate and validate JSON #
		#####################################

		# check the appliance
		appliance = Appliance.get_by_token(apitoken)
		if not appliance:
			logging.error("%s is using an invalid token(%s)." % (ip, apitoken))
			return error_response(self, "Token is not valid.", 401, params)

		if appliance.activated == False:
			# appliance not activated
			logging.error("%s is running a disabled appliance." % ip)
			return error_response(self, "This appliance has been disabled by pool controller.", 409, params)

		# pull out the appliance's instance
		try:
			appliance_instance = packet['instance']
		except:
			logging.error("%s sent data without instance key." % ip)
			return error_response(self, "Instance data not found.", 404, params)
		
		# grab the instance name and check the url
		try:
			name = appliance_instance['name']
			# same name?
			if instance_name != name:
				raise Exception
		except:
			logging.error("%s submitted mismatched instance data." % ip)
			return error_response(self, "Submitted instance name needs to match resource URI.", 401, params)

		# grab the rest of the instance info
		try:
			# grab the rest of appliance POST data
			flavor_name = appliance_instance['flavor']
			ask = appliance_instance['ask']
			expires = datetime.fromtimestamp(appliance_instance['expires'])
			address = appliance_instance['address'] # bitcoin address
			state = appliance_instance['state']
			ipv4_address = appliance_instance['ipv4_address']
			ipv6_address = appliance_instance['ipv6_address']
			ipv4_private_address = appliance_instance['ipv4_private_address']
			console_output = appliance_instance['console_output']
		except:
			logging.error("%s submitted data without required keys." % ip)
			return error_response(self, "Flavor, ask, expires, address, state, ip addresses and console output must be included in POST data.", 401, params)

		####################################
		# 3. locate or create new instance #
		####################################
		
		# look up the pool's version of this instance
		instance = Instance.get_by_name_appliance(name, appliance.key)

		# create a new instance for this appliance because we've never seen it
		if not instance:
			instance = Instance().push(appliance_instance, appliance)
			instance.address = address
			instance.ask = ask
			# add wisp to new instance
			wisp = Wisp.get_user_default(appliance.owner)
			if wisp:
				instance.wisp = wisp.key
			else:
				wisp = Wisp.get_system_default()
				instance.wisp = wisp.key

			# add flavor to new instance, or return error
			flavor = Flavor.get_by_name(flavor_name)
			if flavor:
				instance.flavor = flavor.key
			else:
				logging.error("%s submitted an unknown flavor." % ip)
				return error_response(self, "Flavor name not found.", 401, params)

		#########################################################
		# 4. update local instance with appliance instance data #
		#########################################################

		# update start time if instance state changed from being 1 to anything else
		if instance.state == 1 and state > 1:
			instance.started = datetime.utcnow()
		# load state and ips into local instance
		instance.state = state
		instance.expires = expires
		instance.ipv4_private_address = ipv4_private_address
		instance.ipv4_address = ipv4_address
		instance.ipv6_address = ipv6_address
		

		# load console output into local instance
		h = HTMLParser()
		console = ""
		for line in console_output:
			console += "%s\n" % h.unescape(line)

		instance.console_output = console

		# update local instance
		instance.put()

		# sleep for dev
		if config.debug:
			time.sleep(1)

		#########################################
		# 5. send update information to channel #
		#########################################
		
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

		############################
		# 6. build response packet #
		############################
		
		# check if there is an instance bid reservation on this instance
		instancebid = InstanceBid.get_by_instance(instance.key)
		if instancebid:
			# load up callback URL
			if instancebid.callback_url > "":
				# load for later + stuff it in instance for page reference purposes
				callback_url = instancebid.callback_url
				instance.callback_url = instancebid.callback_url
				instance.put()
			else:
				# using a wisp, so we don't need it for displaying
				callback_url = instancebid.wisp.get().callback_url

			"""
			BEGIN CODE CALLOUT
			"""
			# August 24, 2014
			#
			# The following code retrieves content from a remote server and proxies it to 
			# an appliance for starting an instance. It is at this point an anonymous user's
			# callback pattern is most venerable to being monitored and manipulated by a 
			# government agency.
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
			# agency to intercept and monitor instances using a custom callback.
			#
			# Kord Campbell
			#
			if callback_url:
				try:
					result = urlfetch.fetch(callback_url, deadline=5)
				except Exception as ex:
					logging.error("Error fetching callback URL content.")
					instance.console_output = "Error fetching callback url=(%s)'s' content. %s" % (callback_url, ex)
					instance.put()
					channel.send_message(instance.token, "reload")
					return error_response(self, "Error fetching callback URL content.", 401, params)

				############################################
				# 7a. proxy callback URL JSON to appliance #
				############################################
		
				# return content retrieved from callback URL if the JSON returned by this method includes
				# a callback_url in the data, the appliance will follow the URL and will not call this API 
				# again during the life of the instance.
				self.response.headers['Content-Type'] = 'application/json'
				self.response.write(json.dumps(json.loads(result.content), sort_keys=True, indent=2))

				# delete the instance reservation
				instancebid.key.delete()
				
				return	
			else:
				# assign the instance the registered user's bid wisp
				instance.wisp = instancebid.wisp
				instance.owner = instancebid.wisp.get().owner
				instance.cloud = instancebid.cloud
				instance.put()

				# delete the instance reservation
				instancebid.key.delete()

			"""
			END CODE CALLOUT
			"""

		# at this point we have one of two scenarios:
		# 1. an external instance start (registered user with appliance, sans instancebid)
		# 2. registered user using a wisp WITHOUT a callback_url (with instancebid)

		# grab the instance's wisp
		if instance.wisp:
			# used if registered user is using a wisp
			wisp = Wisp.get_by_id(instance.wisp.id())
		else:
			wisp = Wisp.get_user_default(instance.owner)

		# deliver default system wisp if none (external instance start)
		if not wisp:
			wisp = Wisp.get_system_default()

		# get the follow values or return None if not present
		dynamic_image_url = wisp.dynamic_image_url if wisp.dynamic_image_url > "" else None
		callback_url = wisp.callback_url if wisp.callback_url > "" else None
		image = wisp.image.get().name if wisp.image else None

		# pop the ssh_key script into an array
		if wisp.ssh_key:
			ssh_key = []
			for line in iter(wisp.ssh_key.splitlines()):
				ssh_key.append(line)
		else:
			ssh_key = [""]

		# pop the post creation script into an array
		if wisp.post_creation:
			post_creation = []
			for line in iter(wisp.post_creation.splitlines()):
				post_creation.append(line)
		else:
			post_creation = [""]

		# load the instance info back into the response
		params = {
			'response': "success",
			'instance_name': name,
			'image': image,
			'dynamic_image_url': dynamic_image_url,
			'callback_url': callback_url,
			'ssh_key': ssh_key,
			'post_creation': post_creation 
		}

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

		params = {}
		params['response'] = "success"
		
		self.response.headers['Content-Type'] = 'application/json'
		
		return self.render_template('api/instance.json', **params)


# accept sale of multiple instances from provider
# http://0.0.0.0/api/v1/instances/broker/ via POST
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


# NO AUTHENTICATION
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

	def post(self):
		# get current flavors
		flavors = Flavor().get_all()
		
		# build parameter list
		params = {
			'flavors': flavors
		}

		# return images via template
		self.response.headers['Content-Type'] = 'application/json'
		return self.render_template('api/flavors.json', **params)

	def get(self):
		return self.post()


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

