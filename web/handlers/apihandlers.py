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
from web.models.models import Appliance, LogTracking


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
		
		# build paramter list
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


class APIPublicHandler(BaseHandler):
	def get(self, public_method = None):
		
		if public_method == "version":
			query_version = self.request.get("ver")
			logging.info("value is: %s" % query_version)
			params = {
				'query_version': query_version,
			}

			# return all versions as good for now
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/versions.json', **params)
				
		elif public_method == "flavors":
			query_version = self.request.get("ver")
			logging.info("version is: %s" % query_version)

			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/flavors.json')

		elif public_method == "images":
			query_version = self.request.get("ver")
			logging.info("version is: %s" % query_version)

			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/images.json')