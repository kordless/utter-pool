import json
import md5
import time
import logging

from google.appengine.api import urlfetch
from google.appengine.api import channel
from web.basehandler import BaseHandler

from utter_libs.schemas import schemas
from utter_libs.schemas.helpers import ApiSchemaHelper

import config

from web.models.models import Instance
from web.models.models import InstanceBid
from web.models.models import Wisp
from web.models.models import User
from lib.apishims import InstanceApiShim
from web.handlers.api.helpers import authenticate_appliance
from web.handlers.apihandlers import error_response


# class full of helper functions for instances handler
class InstancesBaseHandler(BaseHandler):
	# disable csrf check in basehandler
	csrf_exempt = True

	# get the wisp for an instance, implements multiple fallbacks
	def _get_instance_wisp(self, instance):
		# grab the instance's wisp
		if instance.wisp:
			# used if registered user is using a wisp
			wisp = Wisp.get_by_id(instance.wisp.id())
		else:
			wisp = Wisp.get_user_default(instance.owner)

		# deliver default system wisp if none (external instance start)
		if not wisp:
			wisp = Wisp.get_system_default()
		return wisp

	# aggregate all startup parameters for a given instance
	def _get_instance_startup_parameters(self, instance):
		wisp = self._get_instance_wisp(instance)

		if wisp.dynamic_image_url == "":
			image = wisp.image.get()
			image_url = image.url
			image_name = image.name
		else:
			image_url = wisp.dynamic_image_url
			image_name = "dynamic"

		ssh_keys = wisp.get_ssh_key_lines()
		post_creation_lines = wisp.get_post_creation_lines()

		return {
			'image_url': image_url,
			'image_name': image_name,
			'callback_url': wisp.callback_url if wisp.callback_url else "",
			'ssh_keys': ssh_keys,
			'post_create': post_creation_lines}

	def _convert_bid_to_instance(self, instance):
		# convert bid to instance
		# check if there is an instance bid reservation on this instance
		instancebid = InstanceBid.get_by_instance(instance.key)
		if instancebid:
			# check for a bid callback_url
			# (entered in the callback field on the launcher)
			if instancebid.callback_url > "":
				# put the callback into the instance
				instance.callback_url = instancebid.callback_url
			else:
				# assuming we have a wisp, try to get the wisp's callback URL
				# maybe add a check to see if we have a wisp here...
				callback_url = instancebid.wisp.get().callback_url

				# if the wisp has an empty callback URL, populate the instance with the
				# wisp's bid details
				if callback_url == "" or callback_url is None:
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

	# update an instance, using the data from the passed instance_schema
	def _update_instance_info(self, instance, instance_schema, appliance):

		# if instance doesn't already exist, create it
		if not instance:
			instance = Instance()
			instance.wisp = self._get_instance_wisp(instance).key

		# wrap instance into api shim in order to translate values from structure
		# of api to structure of model. I hope at some point in the future the two
		# models are similar enough so we can entirely drop this shim
		instance_shim = InstanceApiShim(instance)

		try:
			# update instance with values from post
			ApiSchemaHelper.fill_object_from_schema(
				instance_schema, instance_shim)

			# associate instance with it's appliance
			instance_shim.appliance = appliance
		except Exception as e:
			return error_response(
				self,
				'Error in creating or updating instance from '
				'post data, with message {0}'.format(str(e)), 500, {})

		# update local instance
		instance.put()

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

		return instance

		#############################################################################
		# August 24, 2014
		#
		# The following code retrieves content from a remote server and proxies it to
		# an appliance for starting an instance. It is at this point an anonymous
		# user's callback pattern is most venerable to being monitored and
		# manipulated by a government agency.
		#
		# The author of this software issues a warrant canary tweet to @stackape
		# which should appear on the 1st of each month indicating the absence of a
		# gag order having been issued to StackMonkey, Utter.io, or Kord Campbell.
		#
		# Please monitor the code block between BEGIN CODE CALLOUT and END CODE
		# CALLOUT if the canary tweet does not appear on schedule. Please monitor
		# any callback file's retrieval patterns if the canary tweet does not appear
		# on schedule. Please report any findings to the community sections of the
		# project/site.
		#
		# Remember, the code is Open Source. Use that fact to the community's
		# advantage.
		#
		# The warrant canary will likely be your only indication a change has
		# possibly taken place to the system.  These changes may or may not enable
		# a government agency to intercept and monitor instances using a custom URL
		# callback.
		#
		# Kord Campbell
		#
		#############################################################################
		"""
		BEGIN CODE CALLOUT
		"""
		def _proxy_to_callback(self, instance):
			try:
				result = urlfetch.fetch(instance.callback_url, deadline=5)
			except Exception as ex:
				logging.error("Error fetching callback URL content.")
				instance.console_output = \
					"Error fetching callback url=({0})'s' content. {1}".format(
						instance.callback_url, ex)
				instance.put()
				channel.send_message(instance.token, "reload")
				return error_response(
					self, "Error fetching callback URL content.", 401, {})

			# return content retrieved from callback URL if the JSON returned by this
			# method includes a callback_url in the data, the appliance will follow
			# the URL and will not call this API again during the life of the instance.
			self.response.headers['Content-Type'] = 'application/json'
			self.response.write(
				json.dumps(
					json.loads(result.content),
					sort_keys=True,
					indent=2))
		"""
		END CODE CALLOUT
		"""


# list the offered instances
class InstancesListHandler(InstancesBaseHandler):

	def post(self):
		# request basics
		ip = self.request.remote_addr

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

	# disable csrf check in basehandler
	csrf_exempt = True


class InstanceInfoHandler(InstancesBaseHandler):

	def post(self):
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


class InstanceStartupParamsHandler(InstancesBaseHandler):

	def post(self):
		# extract instance name from request body
		instance_name = schemas['InstanceStartupParametersRequestSchema'](
			**json.loads(self.request.body)).as_dict()['name']

		instance = Instance.get_by_name(instance_name)
		if not instance:
			self.response.set_status(404)
			self.response.write("Instance '{0}' not found.".format(instance_name))
			return

		if instance.callback_url:
			return self._proxy_to_callback(instance.callback_url)

		start_params = schemas['InstanceStartupParametersResponseSchema'](
			**self._get_instance_startup_parameters(instance))

		self.response.set_status(200)
		self.response.headers['Content-Type'] = 'application/json'
		# write dictionary as json string
		self.response.out.write(
			json.dumps(
				# retrieve dict from schema
				start_params.as_dict()))


# do updates on lists of instances
class InstancesUpdateHandler(InstancesBaseHandler):

	@authenticate_appliance
	def post(self, *args, **kwargs):
		self.response.headers['Content-Type'] = "application/json"

		instances_schema = schemas['InstanceListSchema'](
			**json.loads(self.request.body))

		for instance_schema in instances_schema.items:
			instance = Instance.get_by_name_appliance(
				instance_schema.name.as_dict(), kwargs['appliance'].key)
			self._convert_bid_to_instance(
				self._update_instance_info(
					instance, instance_schema, kwargs['appliance']))
