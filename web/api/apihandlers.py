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

		elif public_method == "validate":
			api_token = self.request.get("apitoken")
			if api_token == "gYZ9FFpal7zrUBcyllVJtJEMxCQm1FJ39xfLQ8LHwfFIkwEv8Npua9mgpugnRf8f":
				# return token as good
				self.response.headers['Content-Type'] = 'application/json'
				return self.render_template('response.json', result="valid")
			else:
				self.response.headers['Content-Type'] = 'application/json'
				return self.render_template('response.json', result="valid")
				
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