import time

import webapp2

import config
from web.models.models import User
from web.models.models import Appliance
from web.models.models import Group
from web.basehandler import BaseHandler
from web.basehandler import user_required

class GroupHandler(BaseHandler):
	@user_required
	def get(self):
		pass

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		#load new group info
		if self.request.get('name'):
			
			group = Group(
				# need to safely escape as could affect admin/members - TODO
				name = self.request.get('name'),
				owner = user_info.key
			)
			group.put()
			time.sleep(2)
			
			# yup, all good
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('response.json', result="success")

		else:
			# that's a no go, jim
			self.response.set_status(403)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('response.json', result="fail")

