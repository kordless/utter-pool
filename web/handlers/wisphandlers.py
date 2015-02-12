import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, LogVisit
from web.models.models import Flavor, Image, Appliance, Group, Cloud, Wisp, Project, InstanceBid
from web.basehandler import BaseHandler
from web.basehandler import user_required

class WispListHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up wisps
		wisps = Wisp.get_by_user(user_info.key)

		# redirect if we don't have any wisps
		if not wisps:
			return self.redirect_to('account-wisps-new')

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'wisps': wisps, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		# check for default
		default = False
		for wisp in wisps:
			print wisp
			if wisp.default:
				default = True
		if not default:
			self.add_message("Please set a wisp to be default!", "error")

		return self.render_template('wisp/list.html', **params)

class WispNewHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# load projects pulldown
		self.form.project.choices = []

		# public + private
		projects = Project.get_available(user_info.key)
		for project in projects:
			self.form.project.choices.insert(0, (str(project.key.id()), project.name))

		# insert images into list for wisp
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# params build out
		params = {
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('wisp/new.html', **params)

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load projects pulldown
		self.form.project.choices = []

		# public + private
		projects = Project.get_available(user_info.key)
		for project in projects:
			self.form.project.choices.insert(0, (str(project.key.id()), project.name))

		# insert images into list for wisp
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The new wisp form did not validate.", "error")
			return self.get()

		# load form values
		name = self.form.name.data.strip()
		ssh_key = self.form.ssh_key.data.strip()
		dynamic_image_url = self.form.dynamic_image_url.data.strip()
		image_container_format = self.form.image_container_format.data.strip()
		image_disk_format = self.form.image_disk_format.data.strip()
		post_creation = self.form.post_creation.data.strip()
		callback_url = self.form.callback_url.data.strip()
		default = self.form.default.data # no strip cause bool

		# check if project is selected
		if self.form.wisp_type.data.strip() == 'project':
			project = Project.get_by_id(long(self.form.project.data.strip())).key
		else:
			project = None		

		# hack up form to deal with custom image
		if self.form.image.data.strip() == "custom":
			image = None
		else:
			image = Image.get_by_id(long(self.form.image.data.strip())).key

		# hack up form to deal with custom callback
		if self.form.wisp_type.data.strip() == "custom":
			image = None
			ssh_key = None
			dynamic_image_url = None
			post_creation = None
		elif self.form.wisp_type.data.strip() == "project":
			image = None
			dynamic_image_url = None
			post_creation = None
		else:
			callback_url = None

		# check if we have it already
		if Wisp.get_by_user_name(user_info.key, name):
			self.add_message("A wisp with that name already exists in this account!", "error")
			return self.redirect_to('account-wisps')		
		
		# check if we need to force default setting for first new wisp
		if not Wisp.get_by_user(user_info.key):
			default = True

		# save the new wisp in our database            
		wisp = Wisp(
			name = name,
			owner = user_info.key,
			image = image,
			ssh_key = ssh_key,
			dynamic_image_url = dynamic_image_url,
			image_container_format = image_container_format,
			image_disk_format = image_disk_format,
			post_creation = post_creation,
			callback_url = callback_url,
			project = project
		)
		wisp.put()

		# set default if true
		if default:
			Wisp.set_default(wisp)

		# log to alert
		self.add_message("Wisp %s successfully created!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('account-wisps-detail', wisp_id=wisp.key.id())

	@webapp2.cached_property
	def form(self):
		return forms.WispForm(self)

class WispEditHandler(BaseHandler):
	@user_required
	def get(self, wisp_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the wisp in question
		wisp = Wisp.get_by_id(long(wisp_id))

		# if doesn't exist, redirect
		if not wisp:
			return self.redirect_to('account-wisps')

		# load projects pulldown
		self.form.project.choices = []
		projects = Project.get_available(user_info.key)
		for project in projects:
			self.form.project.choices.insert(0, (str(project.key.id()), project.name))

		# insert images into list for wisp
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# load values out of db to show in form
		self.form.name.data = wisp.name
		self.form.ssh_key.data = wisp.ssh_key
		self.form.dynamic_image_url.data = wisp.dynamic_image_url
		self.form.image_disk_format.data = wisp.image_disk_format
		self.form.image_container_format.data = wisp.image_container_format
		self.form.post_creation.data = wisp.post_creation
		self.form.callback_url.data = wisp.callback_url
		self.form.default.data = wisp.default

		# adjust the form's pulldown settings
		self.form.wisp_type.data = "stock"
		if wisp.image:
			self.form.image.data = str(wisp.image.id())
		if wisp.callback_url:
			self.form.wisp_type.data = "custom"
		if wisp.project:
			self.form.wisp_type.data = "project"
			self.form.project.data = str(wisp.project.id())
		if wisp.dynamic_image_url:
			self.form.wisp_type.data = "stock"
			self.form.image.data = "custom"

		# check if the owner is this user
		if wisp and wisp.owner == user_info.key:
			# setup channel to do page refresh
			channel_token = user_info.key.urlsafe()
			refresh_channel = channel.create_channel(channel_token)

			# params build out
			params = {
				'wisp': wisp,
				'refresh_channel': refresh_channel,
				'channel_token': channel_token 
			}

			return self.render_template('wisp/edit.html', **params)
		
		else:
			return self.redirect_to('account-wisps')

	@user_required
	def post(self, wisp_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load the wisp in question
		wisp = Wisp.get_by_id(long(wisp_id))

		# if doesn't exist, redirect
		if not wisp:
			return self.redirect_to('account-wisps')

		# load projects pulldown
		self.form.project.choices = []
		projects = Project.get_available(user_info.key)
		for project in projects:
			self.form.project.choices.insert(0, (str(project.key.id()), project.name))

		# insert images into list for wisp
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The new wisp form did not validate.", "error")
			return self.get(wisp_id = wisp_id)

		# load form values
		name = self.form.name.data.strip()
		ssh_key = self.form.ssh_key.data.strip()
		dynamic_image_url = self.form.dynamic_image_url.data.strip()
		image_container_format = self.form.image_container_format.data.strip()
		image_disk_format = self.form.image_disk_format.data.strip()
		post_creation = self.form.post_creation.data.strip()
		callback_url = self.form.callback_url.data.strip()
		default = self.form.default.data

		# hack up form to deal with custom callback
		if self.form.wisp_type.data.strip() == "custom":
			# custom callback, so zero everything
			image = None
			ssh_key = None
			dynamic_image_url = None
			post_creation = None
			project = None
		elif self.form.wisp_type.data.strip() == "project":
			# project, so zero image, urls, post_creation
			image = None
			dynamic_image_url = None
			post_creation = None
			callback_url = None
			project = Project.get_by_id(long(self.form.project.data.strip())).key
		else:
			# stock
			callback_url = None
			project = None

		# hack up results to deal with custom images
		if self.form.image.data.strip() == "custom":
			image = None
		else:
			if project:
				image = None
			else:
				image = Image.get_by_id(int(self.form.image.data.strip())).key


		# check if the wisp owner is this user
		if wisp and wisp.owner == user_info.key:
			# save the new wisp in our database            
			wisp.name = name
			wisp.image = image
			wisp.ssh_key = ssh_key
			wisp.dynamic_image_url = dynamic_image_url
			wisp.image_container_format = image_container_format
			wisp.image_disk_format = image_disk_format
			wisp.post_creation = post_creation
			wisp.callback_url = callback_url
			wisp.project = project
			wisp.put()

			# set default if true, or turn it off if false
			if default:
				Wisp.set_default(wisp)
			else:
				wisp.default = False
				wisp.put()

			# log to alert
			self.add_message("Wisp %s updated!" % name, "success")

			# give it a few seconds to update db, then redirect
			time.sleep(1)
		else:
			# log to alert
			self.add_message("Wisp was not updated!", "error")
		
		return self.redirect_to('account-wisps')

	@user_required
	def delete(self, wisp_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# pull the entry from the db
		wisp = Wisp.get_by_id(long(wisp_id))

		# if we found it and own it, delete
		if wisp and wisp.owner == user_info.key:
			# delete any associated bids, if they exist
			InstanceBid.delete_by_wisp(wisp.key)

			# delete the wisp
			wisp.key.delete()

			self.add_message('Wisp successfully deleted!', 'success')
		else:
			self.add_message('Wisp was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)
		channel.send_message(channel_token, 'reload')

		return

	@webapp2.cached_property
	def form(self):
		return forms.WispForm(self)


# render project files locally from those stored on project's github repo
class WispProjectFilesHandler(BaseHandler):
	def get(self, wisp_id = None, file = None):
		# get wisp
		wisp = Wisp.get_by_id(long(wisp_id))
		try:
			# get the project
			project = wisp.project.get()

			# params build out
			params = {
				'project_name': project.name,
				'project_url': project.url,
				'donation_address': project.address,
				'port': project.port,
				'state': 1,
				'ipv4_address': '127.0.0.1',
				'ipv6_address': '::1'
			}

			# pull out the meta data from the instance and build into key/values
			# for key,value in instance.meta_data
			# params[key] = value
			
			# also add api_url
			#'api_url': '%s/api/v1/instance/' 

			if project:
				# return proxied github content
				if file == 'README.md':
					return self.render_url(project.readme_url, **params)

				elif file == 'install.sh':
					return self.render_url(project.install_url, **params)
		except:
			pass
		
		# default response is we don't have it
		self.response.set_status(404)
		return