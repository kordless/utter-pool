# standard library imports
import logging, os
import urllib, urllib2, httplib2
import hashlib, json

from google.appengine.ext import ndb

# related webapp2 imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

# local application/library specific imports
import config
from web.basehandler import BaseHandler
from web.models.models import Appliance, Instance, Image, Flavor, LogTracking


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


# instance callback handler
# http://0.0.0.0/api/v1/instances/smi-xxxxxxxxx/ via POST
class InstancesHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def get(self, instance_name = None):
		# build parameter list
		params = {}
		params['response'] = "success"
		params['result'] = ""
		return self.render_template('api/instances.json', **params)

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

		# pull out the instance
		instance = packet['instance']

		if not instance:
			params['response'] = "fail"
			params['result'] = "Instance not found."
			self.response.set_status(404)
			return self.render_template('api/response.json', **params)
		
		try:
			# grab the instance info
			name = instance['name']
			if instance_name != name:
				# not valid
				params['response'] = "fail"
				params['result'] = "JSON instance name doesn't match resource URI."
				self.response.set_status(401)
				self.response.headers['Content-Type'] = 'application/json'
				return self.render_template('api/response.json', **params)			

			image = instance['image']
			flavor = instance['flavor']
			ask = instance['ask']
			address = instance['address']
			state = instance['state']

			# load the instance back into the response
			response = "success"
			params = {
				'response': response,
				'instance_name': name,
				'image': image,
				'flavor': flavor,
				'ask': ask,
				'address': address
			}

			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/instances.json', **params)
		
		except:
				params['response'] = "fail"
				params['result'] = "JSON data missing some fields.  No dice, buddy."
				self.response.set_status(401)
				self.response.headers['Content-Type'] = 'application/json'
				return self.render_template('api/response.json', **params)			


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
