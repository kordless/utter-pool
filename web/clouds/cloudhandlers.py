import time

import webapp2

import config
from web.basehandler import BaseHandler
from web.basehandler import user_required
from web.models.models import User

class CloudHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		params = {}
		return self.render_template('cloud/clouds.html', **params)
