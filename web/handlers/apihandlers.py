# -*- coding: utf-8 -*-

"""
API Handlers
"""
# standard library imports
import logging, os
import urllib, urllib2, httplib2
import hashlib, json

# related webapp2 imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique


# local application/library specific imports
import config
from web.basehandler import BaseHandler
from web.models.models import Appliance, Image, Flavor, LogTracking


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


