import time

import webapp2

import config
import web.forms as forms
from web.models.models import User
from web.models.models import LogVisit
from web.models.models import Appliance
from web.basehandler import BaseHandler
from web.basehandler import user_required

class ApplianceHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up appliances
		appliances = Appliance.get_by_user(user_info.key)

		params = {
			'appliances': appliances
		}

		return self.render_template('appliance/appliances.html', **params)


class NewApplianceHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))


		# load token and produce form page or show instructions
		if self.request.get('token'):
			self.form.token.data = self.request.get('token')

			# render new appliance page
			return self.render_template('appliance/new.html')
		
		else:
			# render instructions
			return self.render_template('appliance/instructions.html')

	@user_required
	def post(self):
		if not self.form.validate():          
			self.add_message("The new appliance form did not validate.", 'error')
			return self.get()

		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load form values
		name = self.form.name.data.strip()
		token = self.form.name.data.strip()
		group = self.form.group.data.strip()

		# save the appliance in our database            
		appliance = Appliance(
			name = name,
			token = token,
			group = group,
		)
		appliance.put()

		# log to alert
		self.add_message('Appliance <em>%s</em> successfully created!' % name, 'success')

		# give it a few seconds to update db, then redirect
		time.sleep(2)
		return self.redirect_to('appliances')

	@webapp2.cached_property
	def form(self):
		return forms.ApplianceForm(self)