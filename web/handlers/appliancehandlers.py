import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, LogVisit, Appliance, Group
from web.basehandler import BaseHandler
from web.basehandler import user_required

class ApplianceHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up appliances
		appliances = Appliance.get_by_user(user_info.key)

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'appliances': appliances, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('appliance/appliances.html', **params)

# appliance detail
class ApplianceConfigureHandler(BaseHandler):
	@user_required
	def delete(self, appliance_id = None):
		# delete the entry from the db
		appliance = Appliance.get_by_id(long(appliance_id))

		if appliance:
			appliance.key.delete()
			self.add_message('Appliance successfully deleted!', 'success')
		else:
			self.add_message('Appliance was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

# new appliances
class ApplianceNewHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load token and produce form page or show instructions
		if self.request.get('token'):
			self.form.token.data = self.request.get('token')

			# initialize form choices for group
			self.form.group.choices = []

			# add public list of groups
			public_groups = Group.get_public()
			for group in public_groups:
				self.form.group.choices.insert(0, (group.key.id(), group.name))

			# add to group list from owner's groups
			private_groups = Group.get_by_owner_private(user_info.key)
			for group in private_groups:
				self.form.group.choices.insert(0, (group.key.id(), group.name))

			# should run only one time when there are no groups in db
			# add public group if we have an empty set
			if len(self.form.group.choices) == 0:
				group = Group(
					name = "Public",
					owner = User.get_by_email(config.contact_sender).key,
					public = True
				)
				group.put()
				time.sleep(1)
				
				# rerun the insert into list
				public_groups = Group.get_public()
				for group in public_groups:
					self.form.group.choices.insert(0, (group.key.id(), group.name))

				self.add_message("A new public group named Public was created and placed in the database.");

			# render new appliance page
			return self.render_template('appliance/new.html')
		
		else:
			# render instructions
			return self.render_template('appliance/instructions.html')

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# initialize form choices for group
		self.form.group.choices = []

		# populate with all possible groups for this user
		# add public list of groups
		public_groups = Group.get_public()
		for group in public_groups:
			self.form.group.choices.insert(0, (str(group.key.id()), group.name))

		# add to group list from owner's groups
		private_groups = Group.get_by_owner_private(user_info.key)
		for group in private_groups:
			self.form.group.choices.insert(0, (str(group.key.id()), group.name))

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The new appliance form did not validate.", "error")
			return self.get()

		# load form values
		name = self.form.name.data.strip()
		token = self.form.token.data.strip()
		group = Group.get_by_id(int(self.form.group.data.strip()))

		# check if we have it already
		if Appliance.get_by_token(token):
			self.add_message("An appliance with that token already exists!", "error")
			return self.redirect_to('account-appliances')
		
		# save the new appliance in our database            
		appliance = Appliance(
			name = name,
			token = token,
			group = group.key,
			owner = user_info.key
		)
		appliance.put()

		# log to alert
		self.add_message("Appliance %s successfully created!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(2)
		return self.redirect_to('account-appliances')

	@webapp2.cached_property
	def form(self):
		return forms.ApplianceForm(self)


class ApplianceGroupHandler(BaseHandler):
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

		return self.render_template('appliance/groups.html', **params)
