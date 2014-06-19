# -*- coding: utf-8 -*-

"""
API Handlers
"""
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

class AuthError(Exception):
    """Base class for exceptions in this module."""
    pass

# used to log installs of openstack and whatever else we want to track
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


class TokenValidate(BaseHandler):
	def get(self):
		# look up the appliance
		apitoken = self.request.get("apitoken")
		appliance = Appliance.get_by_token(apitoken)
		
		# build parameter list
		params = {}

		# check if appliance is activated
		try:
			if appliance.activated == True:
				params['response'] = "success"
				params['result'] = "token authenticated"
				self.response.headers['Content-Type'] = "application/json"
				return self.render_template('api/response.json', **params)

		except:	
			pass
		
		# not active
		params['response'] = "fail"
		params['result'] = "token is not valid"
		self.response.set_status(401)
		self.response.headers['Content-Type'] = 'application/json'
		return self.render_template('api/response.json', **params)


class InstancesHandler(BaseHandler):
	def get(self):
		pass

class InstanceDetailHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def get(self, instance_name):
		# build parameter list
		params = {}
		params['response'] = "success"
		params['result'] = ""
		return self.render_template('api/instances.json', **params)

	def post(self, instance_name):
		# build parameter list
		instance = json.loads(self.request.body)

		name = instance['name']
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


# accept sale of instances from provider
class BrokerHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	def post(self):
		# look up the appliance
		apitoken = self.request.get("apitoken")
		appliance = Appliance.get_by_token(apitoken)
		
		# grab the packet
		packet = json.loads(self.request.body)

		try:
			# test if appliance is activated and apitoken is the same in the JSON body
			if (appliance.activated != True) or (apitoken != packet["appliance"]["apitoken"]):
				# wrong apitokens in use
				raise AuthError
		
			# update appliance info
			latitude = float(packet['appliance']['location']['latitude'])
			longitude = float(packet['appliance']['location']['longitude'])
			appliance.location = ndb.GeoPt(latitude, longitude)
			appliance.dynamicimages = bool(packet['appliance']['dynamicimages'])			
			appliance.put()

			# loop through instances being advertised for sale
			for appliance_instance in packet['instances']:
				instance = Instance.get_by_name_appliance(appliance_instance['name'], appliance)

				# didn't find this instance
				if not instance:
					instance = Instance.add(appliance_instance, appliance)

			# build parameter list
			params = {}
			params['response'] = "success"
			params['message'] = "Instances accepted for sale."
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/response.json', **params)
		
		except AuthError:
			self.response.set_status(401)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/error.json')		
		except Exception as ex:
			print ex
			self.response.set_status(500)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/error.json')				

class ImagesHandler(BaseHandler):
	def get(self):
		images = Image().get_all()
		
		# build parameter list
		params = {
			'images': images
		}

		# return images via template
		self.response.headers['Content-Type'] = 'application/json'
		return self.render_template('api/images.json', **params)


class FlavorsHandler(BaseHandler):
	def get(self):
		# get current flavors
		flavors = Flavor().get_all()
		
		# build parameter list
		params = {
			'flavors': flavors
		}

		# return images via template
		self.response.headers['Content-Type'] = 'application/json'
		return self.render_template('api/flavors.json', **params)

# get the current results for an instance bid
class InstanceBidResults(BaseHandler):
	pass