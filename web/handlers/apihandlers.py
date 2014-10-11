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

from utter_libs.schemas import schemas
from utter_libs.schemas.helpers import ApiSchemaHelper

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

	def post(self, action):
		self.response.headers['Content-Type'] = 'application/json'
		self.response.set_status(200)
		# write dictionary as json string
		self.response.out.write(json.dumps(
				# retrieve flavors as schema and convert schema to dict
				ApiSchemaHelper.build_schema_list(
					Flavor.query(),
					schemas['FlavorListSchema'],
					schemas['FlavorSchema']).as_dict()))

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

