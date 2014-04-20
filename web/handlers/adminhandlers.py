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
		description = self.form.description.data.strip()
		vpus = self.form.vpus.data
		memory = self.form.memory.data
		disk = self.form.disk.data
		network = self.form.network.data
		rate = self.form.rate.data

		# save the flavor in our database
		flavor = Flavor(
			name = name,
			description = description,
			vpus = vpus,
			memory = memory,
			disk = disk,
			network = network,
			rate = rate,
			launches = 0
		)
		flavor.put()

		# log to alert
		self.add_message(('Flavor <em>%s</em> successfully created!' % name), 'success')

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('admin-flavors')

	@webapp2.cached_property
	def form(self):
		return forms.FlavorForm(self)


class FlavorsActionsHandler(BaseHandler):
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
		size = self.form.size.data
		diskformat = self.form.diskformat.data.strip()
		containerformat = self.form.containerformat.data.strip()

		# save the flavor in our database
		image = Image(
			name = name,
			description = description,
			url = url,
			size = size,
			diskformat = diskformat,
			containerformat = containerformat
		)
		image.put()

		# log to alert
		self.add_message(('Image <em>%s</em> successfully created!' % name), 'success')

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('admin-images')

	@webapp2.cached_property
	def form(self):
		return forms.ImageForm(self)


class ImagesActionsHandler(BaseHandler):
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

