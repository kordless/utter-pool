import time

import webapp2

from google.appengine.api import channel

import config
from web.models.models import User
from web.models.models import Appliance
from web.models.models import Group
from web.basehandler import BaseHandler
from web.basehandler import user_required

class GroupHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up groups
		private_groups = Group.get_by_owner_private(user_info.key)
		public_groups = Group.get_public()

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'public_groups': public_groups,
			'private_groups': private_groups, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('groups/groups.html', **params)

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# build parameter list
		params = {}

		#load new group info
		if self.request.get('name'):
			
			group = Group(
				# need to safely escape as could affect admin/members - TODO
				name = self.request.get('name'),
				owner = user_info.key
			)
			group.put()
			time.sleep(1)
			
			# yup, all good
			params['response'] = "success"
			params['result'] = "group created"
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/response.json', **params)

		else:
			# that's a no go, jim
			params['response'] = "fail"
			params['result'] = "group not created created"
			self.response.set_status(403)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/response.json', **params)

class GroupDetailHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up groups
		private_groups = Group.get_by_owner_private(user_info.key)
		public_groups = Group.get_public()

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'public_groups': public_groups,
			'private_groups': private_groups, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('groups/group_detail.html', **params)

