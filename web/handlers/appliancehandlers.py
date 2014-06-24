import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, LogVisit, Appliance, Group, GroupMembers
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


# new appliances
class ApplianceNewHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load token and produce form page or show instructions
		if self.request.get('token'):
			self.form.token.data = self.request.get('token')

			# group choices pulldown
			self.form.group.choices=[]
			
			# add list of user's groups, if any
			groups = Group.get_by_owner(user_info.key)
			for group in groups:
				self.form.group.choices.insert(0, (group.key.id(), group.name))

			# public group
			self.form.group.choices.insert(0, ('public', "Public"))

			# render new appliance page
			parms = {'gform': self.gform, 'appliance_token': self.request.get('token')}
			return self.render_template('appliance/new.html', **parms)

		else:
			# render instructions
			return self.render_template('appliance/instructions.html')

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# initialize form choices for group
		self.form.group.choices = []

		# add list of user's groups, if any
		groups = Group.get_by_owner(user_info.key)
		for group in groups:
			self.form.group.choices.insert(0, (str(group.key.id()), group.name))

		# public group
		self.form.group.choices.insert(0, ('public', "Public"))

		# check if we are getting a custom group entry
		if self.form.group.data == "custom":
			# make the new group
			group = Group(
				name = self.form.custom.data.strip(),
				owner = user_info.key
			)
			group.put()
			group_key = group.key

			# create the group member entry
			groupmember = GroupMembers(
				group = group_key,
				member = user_info.key,
				invitor = user_info.key, # same same
				active = True
			)
			groupmember.put()

			# hack the form with new group
			self.form.group.choices.insert(0, ('custom', "Custom"))
		else:
			# grab an existing group
			if self.form.group.data.strip() == 'public':
				# no group for public appliances
				group_key = None
			else:
				group = Group.get_by_id(int(self.form.group.data.strip()))
				group_key = group.key

		# check what was returned from the rest of the form validates
		if not self.form.validate():          
			self.add_message("The new appliance form did not validate.", "error")
			return self.get()

		# load form values
		name = self.form.name.data.strip()
		token = self.form.token.data.strip()

		# check if we have it already - all that work bitches?
		if Appliance.get_by_token(token):
			self.add_message("An appliance with that token already exists!", "error")
			return self.redirect_to('account-appliances')
		
		# save the new appliance in our database            
		appliance = Appliance(
			name = name,
			token = token,
			group = group_key,
			owner = user_info.key
		)
		appliance.put()

		# log to alert
		self.add_message("Appliance %s successfully created!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('account-appliances')

	@webapp2.cached_property
	def gform(self):
		return forms.GroupForm(self)

	@webapp2.cached_property
	def form(self):
		return forms.ApplianceForm(self)

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

