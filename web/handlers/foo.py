# standard library imports					# standard library imports
import logging, os, md5						import logging, os, md5
import hashlib, json						import hashlib, json
import simplejson						import simplejson
import time							import time
from datetime import datetime					from datetime import datetime
from HTMLParser import HTMLParser				from HTMLParser import HTMLParser

# google							# google
from google.appengine.ext import ndb				from google.appengine.ext import ndb
from google.appengine.api import urlfetch			from google.appengine.api import urlfetch
from google.appengine.api import channel			from google.appengine.api import channel

# related webapp2 imports					# related webapp2 imports
import webapp2							import webapp2
from webapp2_extras import security				from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPa	from webapp2_extras.auth import InvalidAuthIdError, InvalidPa
from webapp2_extras.appengine.auth.models import Unique		from webapp2_extras.appengine.auth.models import Unique

# local application/library specific imports			# local application/library specific imports
import config							import config
from lib.utils import generate_token				from lib.utils import generate_token
							      >	from lib.apishims import InstanceApiShim
from web.basehandler import BaseHandler				from web.basehandler import BaseHandler

# note User is not used except to send to channel		# note User is not used except to send to channel
from web.models.models import User, Appliance, Wisp, Cloud, I	from web.models.models import User, Appliance, Wisp, Cloud, I

							      >	from utter_libs.schemas import schemas
							      >	from utter_libs.schemas.helpers import ApiSchemaHelper
							      >
# easy button for error response				# easy button for error response
def error_response(handler, message, code, params):		def error_response(handler, message, code, params):
	params['response'] = "error"					params['response'] = "error"
	params['message'] = message					params['message'] = message
	handler.response.set_status(code)				handler.response.set_status(code)
	return handler.render_template('api/response.json', *		return handler.render_template('api/response.json', *

# appliance token validation					# appliance token validation
# http://0.0.0.0/api/v1/authorization/ via POST			# http://0.0.0.0/api/v1/authorization/ via POST
class TokenValidate(BaseHandler):				class TokenValidate(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	def post(self):							def post(self):
		# paramters, assume failure, response type			# paramters, assume failure, response type
		params = {}							params = {}
		params['response'] = "error"					params['response'] = "error"
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl

		# get appliance variables					# get appliance variables
		try:								try:
			packet = json.loads(self.request.body				packet = json.loads(self.request.body
			apitoken = packet['appliance']['apito				apitoken = packet['appliance']['apito
		except:								except:
			params['message'] = "You must submit 				params['message'] = "You must submit 
			self.response.set_status(401)					self.response.set_status(401)
			return self.render_template('api/resp				return self.render_template('api/resp
										
		# load the appliance						# load the appliance
		appliance = Appliance.get_by_token(apitoken)			appliance = Appliance.get_by_token(apitoken)

		if not appliance:						if not appliance:
			params['message'] = "Token is not val				params['message'] = "Token is not val
			self.response.set_status(401)					self.response.set_status(401)
			return self.render_template('api/resp				return self.render_template('api/resp

		if appliance.activated == False:				if appliance.activated == False:
			# appliance not activated					# appliance not activated
			params['message'] = "Appliance has be				params['message'] = "Appliance has be
			self.response.set_status(409)					self.response.set_status(409)
			return self.render_template('api/resp				return self.render_template('api/resp

		# update appliance info						# update appliance info
		latitude = float(packet['appliance']['locatio			latitude = float(packet['appliance']['locatio
		longitude = float(packet['appliance']['locati			longitude = float(packet['appliance']['locati
		appliance.location = ndb.GeoPt(latitude, long			appliance.location = ndb.GeoPt(latitude, long
		appliance.dynamicimages = bool(packet['applia			appliance.dynamicimages = bool(packet['applia
		appliance.put()							appliance.put()

		# respond with success						# respond with success
		params['response'] = "success"					params['response'] = "success"
		params['message'] = "Appliance token authenti			params['message'] = "Appliance token authenti
		return self.render_template('api/response.jso			return self.render_template('api/response.jso

	def get(self):							def get(self):
		return self.post()						return self.post()


# bids creation							# bids creation
# http://0.0.0.0/api/v1/bids/					# http://0.0.0.0/api/v1/bids/
class BidsHandler(BaseHandler):					class BidsHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	# creation of a bid						# creation of a bid
	def post(self):							def post(self):
		# request basics						# request basics
		ip = self.request.remote_addr					ip = self.request.remote_addr

		# response, type, cross posting					# response, type, cross posting
		params = {}							params = {}
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl
		self.response.headers['Access-Control-Allow-O			self.response.headers['Access-Control-Allow-O

		# check if this IP has any other bids open			# check if this IP has any other bids open
		instancebid = InstanceBid.get_incomplete_by_i			instancebid = InstanceBid.get_incomplete_by_i

		if instancebid:							if instancebid:
			# load the payment address					# load the payment address
			if instancebid.instance:					if instancebid.instance:
				instancebid.address = instanc					instancebid.address = instanc
				instancebid.ask = instancebid <
			else:								else:
				# we should have an instance 					# we should have an instance 
				instancebid.key.delete()					instancebid.key.delete()
				return error_response(self, "					return error_response(self, "

							      >				# IP has a unmatched bid, so deny cre
			params['response'] = "error"					params['response'] = "error"
			params['message'] = "The calling IP a				params['message'] = "The calling IP a
			params['instancebid'] = instancebid				params['instancebid'] = instancebid
			self.response.set_status(403)					self.response.set_status(403)
			return self.render_template('api/bid.				return self.render_template('api/bid.

		# load POSTed JSON						# load POSTed JSON
		try:								try:
			request = json.loads(self.request.bod				request = json.loads(self.request.bod
		except Exception as ex:						except Exception as ex:
			return error_response(self, "Failure 				return error_response(self, "Failure 

		# load optional values or defaults				# load optional values or defaults
		# ipv4 (allow default)						# ipv4 (allow default)
		if 'requires_ipv4' in request:					if 'requires_ipv4' in request:
			requires_ipv4 = request['requires_ipv				requires_ipv4 = request['requires_ipv
		else:								else:
			requires_ipv4 = 0						requires_ipv4 = 0
										
		# ipv6 (allow default)						# ipv6 (allow default)
		if 'requires_ipv6' in request:					if 'requires_ipv6' in request:
			requires_ipv6 = request['requires_ipv				requires_ipv6 = request['requires_ipv
		else:								else:
			requires_ipv6 = 0						requires_ipv6 = 0

		# providers (allow default)					# providers (allow default)
		if 'providers' in request:					if 'providers' in request:
			providers = request['providers']				providers = request['providers']
		else:								else:
			providers = [{u'id': 1, u'name': u'Al				providers = [{u'id': 1, u'name': u'Al

		# flavors (required)						# flavors (required)
		if 'flavor_id' in request:					if 'flavor_id' in request:
			flavor_id = request['flavor_id']				flavor_id = request['flavor_id']
			flavor = Flavor.get_by_id(long(flavor				flavor = Flavor.get_by_id(long(flavor

			# check if flavor was found					# check if flavor was found
			if not flavor:							if not flavor:
				return error_response(self, "					return error_response(self, "

		else:								else:
			return error_response(self, "Flavor I				return error_response(self, "Flavor I

		# cloud (optional)						# cloud (optional)
		if 'cloud_id' in request:					if 'cloud_id' in request:
			cloud_id = request['cloud_id']					cloud_id = request['cloud_id']
			cloud = Cloud.get_by_id(long(cloud_id				cloud = Cloud.get_by_id(long(cloud_id

			# check if cloud was found					# check if cloud was found
			if not cloud:							if not cloud:
				return error_response(self, "					return error_response(self, "
		else:								else:
			cloud = None							cloud = None

		# disallow both a wisp and a callback_url			# disallow both a wisp and a callback_url
		if 'wisp_id' in request and 'callback_url' in			if 'wisp_id' in request and 'callback_url' in
			return error_response(self, "A wisp a				return error_response(self, "A wisp a

		# require either a wisp or a callback_url			# require either a wisp or a callback_url
		if 'wisp_id' not in request and 'callback_url			if 'wisp_id' not in request and 'callback_url
			return error_response(self, "A valid 				return error_response(self, "A valid 

		# load the wisp, if there is one				# load the wisp, if there is one
		if 'wisp_id' in request:					if 'wisp_id' in request:
			wisp_id = request['wisp_id']					wisp_id = request['wisp_id']
			wisp = Wisp.get_by_id(long(wisp_id))				wisp = Wisp.get_by_id(long(wisp_id))
		else:								else:
			wisp = None							wisp = None
										
		# load the callback URL, if there is one			# load the callback URL, if there is one
		if 'callback_url' in request:					if 'callback_url' in request:
			callback_url = request['callback_url'				callback_url = request['callback_url'
		elif wisp:							elif wisp:
			callback_url = wisp.callback_url				callback_url = wisp.callback_url
		else:								else:
			callback_url = ""						callback_url = ""

		# test we have a callback_url or a valid imag			# test we have a callback_url or a valid imag
		if callback_url > "":						if callback_url > "":
			try:								try:
				result = urlfetch.fetch(callb					result = urlfetch.fetch(callb
				if result.status_code > 399:					if result.status_code > 399:
					return error_response						return error_response
				# test result's image URL					# test result's image URL
			except Exception as ex:						except Exception as ex:
				return error_response(self, "					return error_response(self, "
		elif wisp:							elif wisp:
			if wisp.image == None and wisp.dynami				if wisp.image == None and wisp.dynami
				return error_response(self, "					return error_response(self, "

		# grab a new bid hash to use for the new bid			# grab a new bid hash to use for the new bid
		token = generate_token(size=16)					token = generate_token(size=16)
		name = "smr-%s" % generate_token(size=8)			name = "smr-%s" % generate_token(size=8)

		# create a new bid						# create a new bid
		instancebid = InstanceBid()					instancebid = InstanceBid()
		instancebid.token = token					instancebid.token = token
		instancebid.name = name						instancebid.name = name
		instancebid.need_ipv4_address = bool(requires			instancebid.need_ipv4_address = bool(requires
		instancebid.need_ipv6_address = bool(requires			instancebid.need_ipv6_address = bool(requires
		instancebid.flavor = flavor.key					instancebid.flavor = flavor.key
		instancebid.remote_ip = ip					instancebid.remote_ip = ip
		instancebid.appliances = providers # provider			instancebid.appliances = providers # provider
		instancebid.status = 0						instancebid.status = 0
		instancebid.callback_url = callback_url				instancebid.callback_url = callback_url

		# expires in 5 minutes						# expires in 5 minutes
		epoch_time = int(time.time())					epoch_time = int(time.time())
		instancebid.expires = datetime.fromtimestamp(			instancebid.expires = datetime.fromtimestamp(

		# add wisp, if present						# add wisp, if present
		if wisp:							if wisp:
			instancebid.wisp = wisp.key					instancebid.wisp = wisp.key
										
		# add cloud, if present						# add cloud, if present
		if cloud:							if cloud:
			instancebid.cloud = cloud.key					instancebid.cloud = cloud.key

		# update							# update
		instancebid.put()						instancebid.put()

		# sleep for dev							# sleep for dev
		if config.debug:						if config.debug:
			time.sleep(2)							time.sleep(2)

		# reserve the instance						# reserve the instance
		InstanceBid.reserve_instance_by_token(instanc			InstanceBid.reserve_instance_by_token(instanc

		# get the address, if you got an instance			# get the address, if you got an instance
		if instancebid.instance:					if instancebid.instance:
			address = instancebid.instance.get().				address = instancebid.instance.get().
			ask = instancebid.instance.get().ask				ask = instancebid.instance.get().ask
		else:								else:
			# no instance was reserved					# no instance was reserved
			instancebid.key.delete()					instancebid.key.delete()
			return error_response(self, "No valid				return error_response(self, "No valid
											
		# hack address and ask into instancebid objec			# hack address and ask into instancebid objec
		instancebid.address = address					instancebid.address = address
		instancebid.ask = ask						instancebid.ask = ask

		# build out the response					# build out the response
		params['response'] = "success"					params['response'] = "success"
		params['message'] = "A new instance bid has b			params['message'] = "A new instance bid has b
		params['instancebid'] = instancebid				params['instancebid'] = instancebid

		# return response and include cross site POST			# return response and include cross site POST
		self.response.set_status(201)					self.response.set_status(201)

		return self.render_template('api/bid.json', *			return self.render_template('api/bid.json', *


	def get(self):							def get(self):
		return self.post()						return self.post()

	def options(self):						def options(self):
		self.response.headers['Access-Control-Allow-O			self.response.headers['Access-Control-Allow-O
		self.response.headers['Access-Control-Allow-H			self.response.headers['Access-Control-Allow-H
		self.response.headers['Access-Control-Allow-M			self.response.headers['Access-Control-Allow-M
		return								return


# bids detail							# bids detail
# http://0.0.0.0/api/v1/bids/xxxxxxxx/				# http://0.0.0.0/api/v1/bids/xxxxxxxx/
class BidsDetailHandler(BaseHandler):				class BidsDetailHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	def get(self, token=None):					def get(self, token=None):
		# response, type, cross posting		      <
		params = {}							params = {}
		self.response.headers['Content-Type'] = "appl <
		self.response.headers['Access-Control-Allow-O <

		# look for instance bid first					# look for instance bid first
		bid = InstanceBid.get_by_token(token)				bid = InstanceBid.get_by_token(token)

		if bid:								if bid:
			# build out the response					# build out the response
			params['response'] = "success"					params['response'] = "success"
			params['message'] = "Reservation foun				params['message'] = "Reservation foun
			params['instancebid'] = bid					params['instancebid'] = bid

			# return response						# return response
			self.response.set_status(201)					self.response.set_status(201)
			return self.render_template('api/bid.				return self.render_template('api/bid.

		else:								else:
			# look for instance						# look for instance
			instance = Instance.get_by_token(toke				instance = Instance.get_by_token(toke
											
			if instance:							if instance:
				# build out the response					# build out the response
				params['response'] = "success					params['response'] = "success
				params['message'] = "Instance					params['message'] = "Instance
				params['instance'] = instance					params['instance'] = instance

				# return response						# return response
				self.response.set_status(201)					self.response.set_status(201)
				return self.render_template('					return self.render_template('
											
			else:								else:
				# build out the error respons					# build out the error respons
				params['response'] = "error"					params['response'] = "error"
				params['message'] = "No resou					params['message'] = "No resou
							      <
				return self.render_template('					return self.render_template('

	def delete(self, token=None):					def delete(self, token=None):
		bid = InstanceBid.get_by_token(token)				bid = InstanceBid.get_by_token(token)

		# delete the bid						# delete the bid
		if bid:								if bid:
			bid.key.delete()						bid.key.delete()

		# patch up the respective instance if it's no			# patch up the respective instance if it's no
		instance = Instance.get_by_token(token)				instance = Instance.get_by_token(token)

		if instance:							if instance:
			# only patch instance if it's not bee				# only patch instance if it's not bee
			if instance.state <= 1:						if instance.state <= 1:
					instance.reserved = F						instance.reserved = F
					instance.token = None						instance.token = None
					instance.put()							instance.put()

		return								return

	def options(self):				      <
		self.response.headers['Access-Control-Allow-O <
		self.response.headers['Access-Control-Allow-H <
		self.response.headers['Access-Control-Allow-M <
		return					      <

# list of all available instances for sale			# list of all available instances for sale
# http://0.0.0.0/api/v1/instances/				# http://0.0.0.0/api/v1/instances/
class InstancesHandler(BaseHandler):				class InstancesHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	def post(self):							def post(self):
		# request basics						# request basics
		ip = self.request.remote_addr					ip = self.request.remote_addr
		offset = self.request.get("offset")				offset = self.request.get("offset")
		limit = self.request.get("limit")				limit = self.request.get("limit")

		instances = Instance().get_all_offered()			instances = Instance().get_all_offered()
										
		# add gravatar URLs						# add gravatar URLs
		for instance in instances:					for instance in instances:
			email = instance.appliance.get().owne				email = instance.appliance.get().owne
			gravatar_hash = md5.new(email.lower()				gravatar_hash = md5.new(email.lower()
			instance.gravatar_url = "https://www.				instance.gravatar_url = "https://www.

		# build parameter list						# build parameter list
		params = {							params = {
			'remote_ip': ip,						'remote_ip': ip,
			'instances': instances						'instances': instances
		}								}

		# return images via template					# return images via template
		self.response.headers['Content-Type'] = 'appl			self.response.headers['Content-Type'] = 'appl
		return self.render_template('api/instances.js			return self.render_template('api/instances.js

	def get(self):							def get(self):
		return self.post()						return self.post()


# instance callback handler to handle pool_instance() calls f	# instance callback handler to handle pool_instance() calls f
# http://0.0.0.0/api/v1/instances/smi-xxxxxxxxx/ via POST	# http://0.0.0.0/api/v1/instances/smi-xxxxxxxxx/ via POST
class InstanceDetailHandler(BaseHandler):			class InstanceDetailHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	#################################################		#################################################
	# API FOR INSTANCE DETAIL POST FROM APPLIANCE   #		# API FOR INSTANCE DETAIL POST FROM APPLIANCE   #
	# 1. parse instance JSON data from appliance    #		# 1. parse instance JSON data from appliance    #
	# 2. authenticate and validate JSON             #		# 2. authenticate and validate JSON             #
	# 3. locate or create new instance              #		# 3. locate or create new instance              #
	# 4. update local instance with appliance data  #		# 4. update local instance with appliance data  #
	# 5. send update information to channel         #		# 5. send update information to channel         #
	# 6. build response packet                      #		# 6. build response packet                      #
	# 7a. proxy 1st callback URL's JSON to appliance#		# 7a. proxy 1st callback URL's JSON to appliance#
	# or...                                         #		# or...                                         #
	# 7b. build JSON response for appliance         #		# 7b. build JSON response for appliance         #
	#################################################		#################################################
									
	def post(self, instance_name):					def post(self, instance_name):
		# paramters, assume failure, response type			# paramters, assume failure, response type
		params = {}							params = {}
		params['response'] = "error"					params['response'] = "error"
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl

		# request basics						# request basics
		ip = self.request.remote_addr					ip = self.request.remote_addr

		############################################# <
		# 1. parse instance JSON data from appliance  <
		############################################# <
							      <
		try:								try:
			packet = json.loads(self.request.body |				body = json.loads(self.request.body)
			apitoken = packet['appliance']['apito |				instance_schema = schemas['InstanceSc
		except:					      |				appliance_schema = schemas['Appliance
			logging.error("%s submitted an invali |
			return error_response(self, "A valid  |				# try to authenticate appliance
							      |				if not Appliance.authenticate(applian
		#####################################	      |					logging.error("%s is using an
		# 2. authenticate and validate JSON #	      |						% (ip, appliance_sche
		#####################################	      |					return error_response(self, "
							      |
		# check the appliance			      |				# fetch appliance and instance
		appliance = Appliance.get_by_token(apitoken)  |				appliance = Appliance.get_by_token(ap
		if not appliance:			      |				instance = Instance.get_by_name_appli
			logging.error("%s is using an invalid |					instance_schema.name.as_dict(
			return error_response(self, "Token is |
							      |				# if instance doesn't already exist, 
		if appliance.activated == False:	      |				if not instance:
			# appliance not activated	      |					wisp = Wisp.get_user_default(
			logging.error("%s is running a disabl |					if not wisp:
			return error_response(self, "This app |						wisp = Wisp.get_syste
							      |					instance = Instance(wisp=wisp
		# pull out the appliance's instance	      |
		try:					      |				# wrap instance into api shim in orde
			appliance_instance = packet['instance |				# of api to structure of model. I hop
		except:					      |				# models are similar enough so we can
			logging.error("%s sent data without i |				instance_shim = InstanceApiShim(insta
			return error_response(self, "Instance |				# update instance with values from po
							      |				ApiSchemaHelper.fill_object_from_sche
		# grab the instance name and check the url    |					instance_schema, instance_shi
		try:					      |
			name = appliance_instance['name']     |				# associate instance with it's applia
			# same name?			      |				instance_shim.appliance = appliance
			if instance_name != name:	      |			except Exception as e:
				raise Exception		      |				print("Error in creating or updating 
		except:					      |							"with message
			logging.error("%s submitted mismatche <
			return error_response(self, "Submitte <
							      <
		# grab the rest of the instance info	      <
		try:					      <
			# grab the rest of appliance POST dat <
			flavor_name = appliance_instance['fla <
			ask = appliance_instance['ask']	      <
			expires = datetime.fromtimestamp(appl <
			address = appliance_instance['address <
			state = appliance_instance['state']   <
			ipv4_address = appliance_instance['ip <
			ipv6_address = appliance_instance['ip <
			ipv4_private_address = appliance_inst <
			console_output = appliance_instance[' <
		except:					      <
			logging.error("%s submitted data with <
			return error_response(self, "Flavor,  <
							      <
		####################################	      <
		# 3. locate or create new instance #	      <
		####################################	      <
							      <
		# look up the pool's version of this instance <
		instance = Instance.get_by_name_appliance(nam <
							      <
		# create a new instance for this appliance be <
		if not instance:			      <
			instance = Instance().push(appliance_ <
			instance.address = address	      <
			instance.ask = ask		      <
			# add wisp to new instance	      <
			wisp = Wisp.get_user_default(applianc <
			if wisp:			      <
				instance.wisp = wisp.key      <
			else:				      <
				wisp = Wisp.get_system_defaul <
				instance.wisp = wisp.key      <
							      <
			# add flavor to new instance, or retu <
			flavor = Flavor.get_by_name(flavor_na <
			if flavor:			      <
				instance.flavor = flavor.key  <
			else:				      <
				logging.error("%s submitted a <
				return error_response(self, " <
							      <
		############################################# <
		# 4. update local instance with appliance ins <
		############################################# <
							      <
		# update start time if instance state changed <
		if instance.state == 1 and state > 1:	      <
			instance.started = datetime.utcnow()  <
							      <
		# load state and ips into local instance      <
		instance.state = state			      <
		instance.expires = expires		      <
		instance.ipv4_private_address = ipv4_private_ <
		instance.ipv4_address = ipv4_address	      <
		instance.ipv6_address = ipv6_address	      <
							      <
							      <
		# load console output into local instance     <
		h = HTMLParser()			      <
		console = ""				      <
		for line in console_output:		      <
			console += "%s\n" % h.unescape(line)  <
							      <
		instance.console_output = console	      <

		# update local instance						# update local instance
		instance.put()							instance.put()

		# sleep for dev							# sleep for dev
		if config.debug:						if config.debug:
			time.sleep(1)							time.sleep(1)

		#########################################			#########################################
		# 5. send update information to channel #			# 5. send update information to channel #
		#########################################			#########################################
										
		if instance.token:						if instance.token:
			output = {							output = {
				"name": instance.name,						"name": instance.name,
				"token": instance.token,					"token": instance.token,
				"state": instance.state,					"state": instance.state,
			}								}
			channel.send_message(instance.token, 				channel.send_message(instance.token, 

		# pop a reload just in case user is on their 			# pop a reload just in case user is on their 
		if instance.owner:						if instance.owner:
			user_info = User.get_by_id(long(insta				user_info = User.get_by_id(long(insta
			channel.send_message(user_info.key.ur				channel.send_message(user_info.key.ur

		##############################		      |			############################
		# 6. convert bid to instance #		      |			# 6. build response packet #
		##############################		      |			############################
										
		# check if there is an instance bid reservati			# check if there is an instance bid reservati
		instancebid = InstanceBid.get_by_instance(ins			instancebid = InstanceBid.get_by_instance(ins
		if instancebid:							if instancebid:
			# check for a bid callback_url (enter |				# load up callback URL
			if instancebid.callback_url > "":				if instancebid.callback_url > "":
				# put the callback into the i |					# load for later + stuff it i
							      >					callback_url = instancebid.ca
				instance.callback_url = insta					instance.callback_url = insta
							      >					instance.put()
			else:								else:
				# assuming we have a wisp, tr |					# using a wisp, so we don't n
				# maybe add a check to see if <
				callback_url = instancebid.wi					callback_url = instancebid.wi
							      <
				# if the wisp has an empty ca <
				if callback_url == "" or call <
					instance.wisp = insta <
					instance.owner = inst <
					instance.cloud = inst <
				else:			      <
					# we have a custom ca <
					instance.callback_url <

			# update the instance		      |				"""
			instance.put()			      |				BEGIN CODE CALLOUT
							      |				"""
			# delete the instance reservation     |				# August 24, 2014
			instancebid.key.delete()	      |				#
							      >				# The following code retrieves conten
							      >				# an appliance for starting an instan
							      >				# callback pattern is most venerable 
							      >				# government agency.
							      >				# 
							      >				# The author of this software issues 
							      >				# should appear on the 1st of each mo
							      >				# having been issued to StackMonkey, 
							      >				#
							      >				# Please monitor the code block betwe
							      >				# if the canary tweet does not appear
							      >				# file's retrieval patterns if the ca
							      >				# Please report any findings to the c
							      >				#
							      >				# Remember, the code is Open Source. 
							      >				# 
							      >				# The warrant canary will likely be y
							      >				# taken place to the system.  These c
							      >				# agency to intercept and monitor ins
							      >				#
							      >				# Kord Campbell
							      >				#
							      >				if callback_url:
							      >					try:
							      >						result = urlfetch.fet
							      >					except Exception as ex:
							      >						logging.error("Error 
							      >						instance.console_outp
							      >						instance.put()
							      >						channel.send_message(
							      >						return error_response

							      >					#############################
							      >					# 7a. proxy callback URL JSON
							      >					#############################
							      >			
							      >					# return content retrieved fr
							      >					# a callback_url in the data,
							      >					# again during the life of th
							      >					self.response.headers['Conten
							      >					self.response.write(json.dump

		#############################		      |					# delete the instance reserva
		# 7a. proxy custom callback #		      |					instancebid.key.delete()
		#############################		      |					
							      |					return	
		"""					      |				else:
		BEGIN CODE CALLOUT			      |					# assign the instance the reg
		"""					      |					instance.wisp = instancebid.w
		# August 24, 2014			      |					instance.owner = instancebid.
		#					      |					instance.cloud = instancebid.
		# The following code retrieves content from a <
		# an appliance for starting an instance. It i <
		# callback pattern is most venerable to being <
		# government agency.			      <
		# 					      <
		# The author of this software issues a warran <
		# should appear on the 1st of each month indi <
		# having been issued to StackMonkey, Utter.io <
		#					      <
		# Please monitor the code block between BEGIN <
		# if the canary tweet does not appear on sche <
		# file's retrieval patterns if the canary twe <
		# Please report any findings to the community <
		#					      <
		# Remember, the code is Open Source. Use that <
		# 					      <
		# The warrant canary will likely be your only <
		# taken place to the system.  These changes m <
		# agency to intercept and monitor instances u <
		#					      <
		# Kord Campbell				      <
		#					      <
		if instance.callback_url:		      <
			try:				      <
				result = urlfetch.fetch(insta <
			except Exception as ex:		      <
				logging.error("Error fetching <
				instance.console_output = "Er <
				instance.put()							instance.put()
				channel.send_message(instance <
				return error_response(self, " <

			##################################### |					# delete the instance reserva
			# 7a. proxy callback URL JSON to appl |					instancebid.key.delete()
			##################################### <
							      <
			# return content retrieved from callb <
			# a callback_url in the data, the app <
			# again during the life of the instan <
			self.response.headers['Content-Type'] <
			self.response.write(json.dumps(json.l <
							      <
			# return from here		      <
			return				      <

			"""								"""
			END CODE CALLOUT						END CODE CALLOUT
			"""								"""

		# at this point we have one of two scenarios:			# at this point we have one of two scenarios:
		# 1. an external instance start (registered u			# 1. an external instance start (registered u
		# 2. registered user using a normal wisp WITH |			# 2. registered user using a wisp WITHOUT a c

		# grab the instance's wisp					# grab the instance's wisp
		if instance.wisp:						if instance.wisp:
			# used if registered user is using a 				# used if registered user is using a 
			wisp = Wisp.get_by_id(instance.wisp.i				wisp = Wisp.get_by_id(instance.wisp.i
		else:								else:
			wisp = Wisp.get_user_default(instance				wisp = Wisp.get_user_default(instance

		# deliver default system wisp if none (extern			# deliver default system wisp if none (extern
		if not wisp:							if not wisp:
			wisp = Wisp.get_system_default()				wisp = Wisp.get_system_default()

		# get the follow values or return None if not			# get the follow values or return None if not
		dynamic_image_url = wisp.dynamic_image_url if			dynamic_image_url = wisp.dynamic_image_url if
		callback_url = wisp.callback_url if wisp.call			callback_url = wisp.callback_url if wisp.call
		image = wisp.image.get().name if wisp.image e			image = wisp.image.get().name if wisp.image e

		# pop the ssh_key script into an array				# pop the ssh_key script into an array
		if wisp.ssh_key:						if wisp.ssh_key:
			ssh_key = []							ssh_key = []
			for line in iter(wisp.ssh_key.splitli				for line in iter(wisp.ssh_key.splitli
				ssh_key.append(line)						ssh_key.append(line)
		else:								else:
			ssh_key = [""]							ssh_key = [""]

		# pop the post creation script into an array			# pop the post creation script into an array
		if wisp.post_creation:						if wisp.post_creation:
			post_creation = []						post_creation = []
			for line in iter(wisp.post_creation.s				for line in iter(wisp.post_creation.s
				post_creation.append(line)					post_creation.append(line)
		else:								else:
			post_creation = [""]						post_creation = [""]

		# load the instance info back into the respon			# load the instance info back into the respon
		params = {							params = {
			'response': "success",						'response': "success",
			'instance_name': name,		      |				'instance_name': instance.name,
			'image': image,							'image': image,
			'dynamic_image_url': dynamic_image_ur				'dynamic_image_url': dynamic_image_ur
			'callback_url': callback_url,					'callback_url': callback_url,
			'ssh_key': ssh_key,						'ssh_key': ssh_key,
			'post_creation': post_creation 					'post_creation': post_creation 
		}								}

		self.response.headers['Content-Type'] = 'appl			self.response.headers['Content-Type'] = 'appl
		return self.render_template('api/instance.jso			return self.render_template('api/instance.jso

	# unauthenticated endpoint					# unauthenticated endpoint
	def get(self, instance_name = None):				def get(self, instance_name = None):

		# get the instance, build the response type			# get the instance, build the response type
		instance = Instance.get_by_name(instance_name			instance = Instance.get_by_name(instance_name
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl

		# if no instance, then show error				# if no instance, then show error
		if not instance:						if not instance:
			params['message'] = "Instance not fou				params['message'] = "Instance not fou
			self.response.set_status(404)					self.response.set_status(404)
			return self.render_template('api/resp				return self.render_template('api/resp

		params = {}							params = {}
		params['response'] = "success"					params['response'] = "success"
										
		self.response.headers['Content-Type'] = 'appl			self.response.headers['Content-Type'] = 'appl
										
		return self.render_template('api/instance.jso			return self.render_template('api/instance.jso


# accept sale of multiple instances from provider		# accept sale of multiple instances from provider
# http://0.0.0.0/api/v1/instances/broker/ via POST		# http://0.0.0.0/api/v1/instances/broker/ via POST
class BrokerHandler(BaseHandler):				class BrokerHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	def post(self):							def post(self):
		# paramters, assume failure, response type			# paramters, assume failure, response type
		params = {}							params = {}
		params['response'] = "error"					params['response'] = "error"
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl

		# get appliance variables					# get appliance variables
		try:								try:
			packet = json.loads(self.request.body				packet = json.loads(self.request.body
			apitoken = packet['appliance']['apito				apitoken = packet['appliance']['apito
		except:								except:
			params['message'] = "You must submit 				params['message'] = "You must submit 
			self.response.set_status(401)					self.response.set_status(401)
			return self.render_template('api/resp				return self.render_template('api/resp
										
		# load the appliance						# load the appliance
		appliance = Appliance.get_by_token(apitoken)			appliance = Appliance.get_by_token(apitoken)

		if not appliance:						if not appliance:
			params['message'] = "Token is not val				params['message'] = "Token is not val
			self.response.set_status(401)					self.response.set_status(401)
			return self.render_template('api/resp				return self.render_template('api/resp

		if appliance.activated == False:				if appliance.activated == False:
			# appliance not activated					# appliance not activated
			params['message'] = "Appliance has be				params['message'] = "Appliance has be
			self.response.set_status(409)					self.response.set_status(409)
			return self.render_template('api/resp				return self.render_template('api/resp

		# update appliance info						# update appliance info
		latitude = float(packet['appliance']['locatio			latitude = float(packet['appliance']['locatio
		longitude = float(packet['appliance']['locati			longitude = float(packet['appliance']['locati
		appliance.location = ndb.GeoPt(latitude, long			appliance.location = ndb.GeoPt(latitude, long
		appliance.dynamicimages = bool(packet['applia			appliance.dynamicimages = bool(packet['applia
		appliance.put()							appliance.put()

		# loop through instances being advertised for			# loop through instances being advertised for
		for appliance_instance in packet['instances']			for appliance_instance in packet['instances']
			# pass in appliance_instance and appl				# pass in appliance_instance and appl
			#logging.info("instance: %s" % applia				#logging.info("instance: %s" % applia
			instance = Instance.push(appliance_in				instance = Instance.push(appliance_in

		# build parameter list						# build parameter list
		params = {}							params = {}
		params['response'] = "success"					params['response'] = "success"
		params['message'] = "Instances accepted for s			params['message'] = "Instances accepted for s
		self.response.headers['Content-Type'] = 'appl			self.response.headers['Content-Type'] = 'appl
										
		return self.render_template('api/response.jso			return self.render_template('api/response.jso
										
	def get(self):							def get(self):
		return self.post()						return self.post()


# NO AUTHENTICATION						# NO AUTHENTICATION
# images list							# images list
# http://0.0.0.0/api/v1/images/ GET or POST			# http://0.0.0.0/api/v1/images/ GET or POST
class ImagesHandler(BaseHandler):				class ImagesHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	def post(self):							def post(self):
		images = Image().get_all()					images = Image().get_all()
										
		# build parameter list						# build parameter list
		params = {							params = {
			'images': images						'images': images
		}								}

		# return images via template					# return images via template
		self.response.headers['Content-Type'] = 'appl			self.response.headers['Content-Type'] = 'appl
		return self.render_template('api/images.json'			return self.render_template('api/images.json'

	def get(self):							def get(self):
		return self.post()						return self.post()


# flavors list							# flavors list
# http://0.0.0.0/api/v1/flavors/ GET or POST			# http://0.0.0.0/api/v1/flavors/ GET or POST
class FlavorsHandler(BaseHandler):				class FlavorsHandler(BaseHandler):
	# disable csrf check in basehandler				# disable csrf check in basehandler
	csrf_exempt = True						csrf_exempt = True

	def post(self):					      |		def post(self, action):
		# get current flavors			      <
		flavors = Flavor().get_all()		      <
							      <
		# build parameter list			      <
		params = {				      <
			'flavors': flavors		      <
		}					      <
							      <
		# return images via template		      <
		self.response.headers['Content-Type'] = 'appl			self.response.headers['Content-Type'] = 'appl
		return self.render_template('api/flavors.json |			self.response.set_status(200)
							      >			# write dictionary as json string
							      >			self.response.out.write(json.dumps(
							      >					# retrieve flavors as schema 
							      >					Flavor.as_schema_list(
							      >						# pass get_all method
							      >						Flavor.get_all).as_di

	def get(self):					      |		def get(self, action):
		return self.post()			      |			return self.post(action)


# used to log whatever we want to track				# used to log whatever we want to track
# http://0.0.0.0/api/v1/track/ via GET				# http://0.0.0.0/api/v1/track/ via GET
class TrackingPingHandler(BaseHandler):				class TrackingPingHandler(BaseHandler):
	def get(self):							def get(self):
		# get ip address						# get ip address
		ip = self.request.remote_addr					ip = self.request.remote_addr
		message = self.request.get("message")				message = self.request.get("message")

		# update db							# update db
		track = LogTracking()						track = LogTracking()
		track.ip = ip							track.ip = ip
		if message:							if message:
			track.message = message						track.message = message
		else:								else:
			track.message = "Simple tracking requ				track.message = "Simple tracking requ
		track.put()							track.put()

		# return JSON response						# return JSON response
		params = {}							params = {}
		params['response'] = "success"					params['response'] = "success"
		params['result'] = "ping recorded for %s" % i			params['result'] = "ping recorded for %s" % i
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl
		return self.render_template('api/response.jso			return self.render_template('api/response.jso


# generate list of geopoints for appliances			# generate list of geopoints for appliances
# http://0.0.0.0/api/v1/appliances/geopoints/ GET		# http://0.0.0.0/api/v1/appliances/geopoints/ GET
class ApplianceGeoPoints(BaseHandler):				class ApplianceGeoPoints(BaseHandler):
	def get(self):							def get(self):
		geopoints = Appliance().get_geopoints()				geopoints = Appliance().get_geopoints()

		# return JSON response						# return JSON response
		params = {							params = {
			'geopoints': geopoints						'geopoints': geopoints
		}								}
		self.response.headers['Content-Type'] = "appl			self.response.headers['Content-Type'] = "appl
		return self.render_template('api/geopoints.js			return self.render_template('api/geopoints.js

