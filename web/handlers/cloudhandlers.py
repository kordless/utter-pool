import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, Cloud, Wisp, Instance
from web.basehandler import BaseHandler
from web.basehandler import user_required


class CloudListHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up appliances
		clouds = Cloud.get_by_user(user_info.key)

		# instance counts
		for cloud in clouds:
			count = Instance.get_count_by_cloud(cloud.key)
			cloud.instance_count = count

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'clouds': clouds,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('cloud/list.html', **params)

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load form values
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()

		# check if we have it already
		if Cloud.get_by_user_name(user_info.key, name):
			self.add_message("A cloud with that name already exists!", "error")
			return self.redirect_to('account-clouds')

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The new cloud form did not validate.", "error")
			return self.get()

		cloud = Cloud(
			name = name,
			description = description,
			owner = user_info.key
		)
		cloud.put()

		# log to alert
		self.add_message("Cloud %s successfully created!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('account-clouds-configure', cloud_id = cloud.key.id())

	@webapp2.cached_property
	def form(self):
		return forms.CloudForm(self)


# provide editing for cloud instance		
class CloudInstanceHandler(BaseHandler):
	@user_required
	def delete(self, cloud_id = None, instance_id = None):
		# hangout for a second
		time.sleep(1)

		# look up the instance
		instance = Instance.get_by_id(long(instance_id))

		if instance:
			cloud = instance.cloud
			if long(cloud.id()) == long(cloud_id):
				instance.cloud = None
				instance.put()
			else:
				self.add_message("Clouds don't match.", "error")
		else:
			self.add_message("Instance not found!", "error")

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')

		return


# provide editing for cloud object		
class CloudEditHandler(BaseHandler):
	@user_required
	def get(self, cloud_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the cloud in question
		cloud = Cloud.get_by_id(long(cloud_id))

		# bail if cloud doesn't exist or not owned by this user
		if not cloud or cloud.owner != user_info.key:
			return self.redirect_to('account-clouds')

		# look up cloud's instances
		instances = Instance.get_by_cloud(cloud.key)

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'cloud': cloud,
			'instances': instances, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('cloud/edit.html', **params)
	
	@user_required
	def post(self, cloud_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# load the cloud in question
		cloud = Cloud.get_by_id(long(cloud_id))
		
		# bail if cloud doesn't exist or not owned by this user
		if not cloud or cloud.owner != user_info.key:
			return self.redirect_to('account-clouds')
		
		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The %s cloud was not updated." % cloud.name, "info")
			return self.redirect_to('account-clouds')

		# load form values
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()

		# save the new cloud in our database            
		cloud.name = name
		cloud.description = description
		cloud.put()

		# log to alert
		self.add_message("Cloud %s updated!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		
		return self.redirect_to('account-clouds')

	def delete(self, cloud_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# pull the entry from the db
		cloud = Cloud.get_by_id(long(cloud_id))

		# check the number of instances
		count = Instance.get_count_by_cloud(cloud.key)

		# deny if it has instances
		if count > 0:
			self.add_message('You may not delete a cloud with instances!', 'info')

		# if we found it and own it, delete
		elif cloud and cloud.owner == user_info.key:
			cloud.key.delete()
			self.add_message('Cloud successfully deleted!', 'success')
		else:
			self.add_message('Cloud was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

	@webapp2.cached_property
	def form(self):
		return forms.CloudForm(self)