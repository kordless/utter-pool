import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, Cloud, Wisp
from web.basehandler import BaseHandler
from web.basehandler import user_required


class StatusHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up wisps
		wisps = Wisp.get_by_user(user_info.key)
		if len(wisps) > 0:
			wisps_exist = True
		else:
			wisps_exist = False
			
		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'wisps_exist': wisps_exist,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('status/status.html', **params)
