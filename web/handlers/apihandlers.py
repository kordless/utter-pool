# standard library imports
import logging, os
import urllib, urllib2, httplib2
import hashlib, json
from datetime import datetime

from google.appengine.ext import ndb

# related webapp2 imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

# local application/library specific imports
import config
from web.basehandler import BaseHandler
from web.models.models import Appliance, Wisp, Instance, Image, Flavor, LogTracking


# appliance token validation
# http://0.0.0.0/api/v1/authorization/ via POST
class TokenValidate(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		# paramters, assume failure, response type
		params = {}
		params['response'] = "fail"
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


# instance callback handler to handle pool_instance() calls from utter-va
# http://0.0.0.0/api/v1/instances/smi-xxxxxxxxx/ via POST
class InstancesHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self, instance_name):
		# paramters, assume failure, response type
		params = {}
		params['response'] = "fail"
		self.response.headers['Content-Type'] = "application/json"

		# get appliance variables
		try:
			packet = json.loads(self.request.body)
			apitoken = packet['appliance']['apitoken']
		except:
			params['message'] = "You must submit a valid JSON object with a token."
			self.response.set_status(401)
			return self.render_template('api/response.json', **params)	
		
		print "******************************************"
		print "instance %s has a state of: %s" % (packet['instance']['name'], packet['instance']['state'])
		print "******************************************"

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

		# pull out the appliance's instance
		appliance_instance = packet['instance']

		if not appliance_instance:
			params['response'] = "fail"
			params['result'] = "JSON instance data not found."
			self.response.set_status(404)
			return self.render_template('api/response.json', **params)
		
		# grab the instance info
		name = appliance_instance['name']
		if instance_name != name:
			# not valid
			params['response'] = "fail"
			params['result'] = "JSON instance name doesn't match resource URI."
			self.response.set_status(401)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/response.json', **params)			

		# grab the rest of appliance POST data
		flavor = appliance_instance['flavor']
		ask = appliance_instance['ask']
		expires = datetime.fromtimestamp(appliance_instance['expires'])
		address = appliance_instance['address'] # bitcoin address

		# look up the pool's version of this instance
		instance = Instance.get_by_name_appliance(name, appliance.key)

		# not having the instance sucks
		if not instance:
			params['response'] = "fail"
			params['result'] = "Instance not found."
			self.response.set_status(404)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/response.json', **params)	
		
		# grab the instance's wisp
		if instance.wisp:
			wisp = Wisp.get_by_id(instance.wisp)
		else:
			# try default wisp for appliance/instance owner
			wisp = Wisp.get_user_default(instance.owner)

		# get the value or return None if not present
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
		return self.render_template('api/instances.json', **params)

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
		params['response'] = "fail"
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
