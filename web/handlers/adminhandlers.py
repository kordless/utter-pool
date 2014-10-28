import time

import webapp2
from google.appengine.api import channel

import config
import web.forms as forms
from web.basehandler import BaseHandler
from web.basehandler import user_required, admin_required
from web.models.models import User, Flavor, Image

class AdminHandler(BaseHandler):
	@user_required
	@admin_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		params = {}
		return self.render_template('admin/status.html', **params)


class UsersHandler(BaseHandler):
	@user_required
	@admin_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up usrs
		users = User.get_all()

		params = {
			'users': users
		}

		return self.render_template('admin/users.html', **params)


class UsersExportHandler(BaseHandler):
	@user_required
	@admin_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up usrs
		users = User.get_all()

		params = {
			'users': users
		}

		# mime it up
		self.response.headers['Content-Type'] = "text/csv"
		self.response.headers['Content-Disposition'] = "attachment; filename=users.csv"
		return self.render_template('admin/user.csv', **params)


class FlavorsListHandler(BaseHandler):
	@user_required
	@admin_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up user's articles
		flavors = Flavor.get_all()

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)
		params = {
			'flavors': flavors, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('admin/flavors.html', **params)

	@user_required
	@admin_required
	def post(self):
		if not self.form.validate():          
			self.add_message("The form did not validate.", 'error')
			return self.get()

		# load values out of the form
		name = self.form.name.data.strip()
		vpus = self.form.vpus.data
		memory = self.form.memory.data
		disk = self.form.disk.data
		network_down = self.form.network_down.data
		network_up = self.form.network_up.data
		rate = self.form.rate.data

		# save the flavor in our database
		flavor = Flavor(
			name = name,
			vpus = vpus,
			memory = memory,
			disk = disk,
			network_down = network_down,
			network_up = network_up,
			rate = rate, # current market rate
			launches = 0, # number of total launches
			hot = 2 # suggest minimum two instance addresses hot
		)
		flavor.put()

		# log to alert
		self.add_message(('Flavor %s successfully created!' % name), 'success')

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('admin-flavors')

	@webapp2.cached_property
	def form(self):
		return forms.FlavorForm(self)


class FlavorsActionsHandler(BaseHandler):
	@user_required
	@admin_required
	def put(self, flavor_id = None):
		flavor = Flavor.get_by_id(long(flavor_id))

		# get the enable/active state
		enable = self.request.get("enable")
		
		if flavor:
			if enable == '1':
				flavor.active = True
				flavor.put()
			else:
				flavor.active = False
				flavor.put()
		
		# hangout for a second
		time.sleep(1)
		
		return

	@user_required
	@admin_required
	def delete(self, flavor_id = None):
		# delete the entry from the db
		flavor = Flavor.get_by_id(long(flavor_id))

		if flavor:
			flavor.key.delete()
			self.add_message('Flavor successfully deleted!', 'success')
		else:
			self.add_message('Flavor was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return


class ImagesListHandler(BaseHandler):
	@user_required
	@admin_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up user's articles
		images = Image.get_all()

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)
		params = {
			'images': images, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('admin/images.html', **params)

	@user_required
	@admin_required
	def post(self):
		if not self.form.validate():          
			self.add_message("The form did not validate.", 'error')
			return self.get()

		# load values out of the form
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()
		url = self.form.url.data.strip()
		disk_format = self.form.disk_format.data.strip()
		container_format = self.form.container_format.data.strip()

		# save the flavor in our database
		image = Image(
			name = name,
			description = description,
			url = url,
			disk_format = disk_format,
			container_format = container_format
		)
		image.put()

		# log to alert
		self.add_message(('Image %s successfully created!' % name), 'success')

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('admin-images')

	@webapp2.cached_property
	def form(self):
		return forms.ImageForm(self)


class ImagesActionsHandler(BaseHandler):
	@user_required
	@admin_required
	def put(self, image_id = None):
		image = Image.get_by_id(long(image_id))

		# get the enable/active state
		enable = self.request.get("enable")

		if image:
			if enable == '1':
				image.active = True
				image.put()
			else:
				image.active = False
				image.put()
		
		# hangout for a second
		time.sleep(1)
		
		return

	@user_required
	@admin_required
	def delete(self, image_id = None):
		# delete the entry from the db
		image = Image.get_by_id(long(image_id))

		if image:
			image.key.delete()
			self.add_message('Image successfully deleted!', 'success')
		else:
			self.add_message('Image was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)
		
		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return


class GroupsHandler(BaseHandler):
	@user_required
	@admin_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		params = {}
		return self.render_template('admin/groups.html', **params)

