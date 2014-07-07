import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, LogVisit
from web.models.models import Flavor, Image, Appliance, Group, Cloud, Wisp 
from web.basehandler import BaseHandler
from web.basehandler import user_required

class WispHandler(BaseHandler):
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
			if wisp.default:
				default = True
		if not default:
			print "wtf"
			self.add_message("Please set a wisp to be default!", "error")

		return self.render_template('wisp/wisps.html', **params)

class WispNewHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

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
		post_creation = self.form.post_creation.data.strip()
		callback_url = self.form.callback_url.data.strip()
		default = self.form.default.data # no strip cause bool

		# hack up form to deal with custom image
		if self.form.image.data.strip() == "custom":
			image = None
		else:
			image = Image.get_by_id(int(self.form.image.data.strip())).key
		
		# hack up form to deal with custom callback
		if self.form.callback.data.strip() == "custom":
			image = None
			ssh_key = None
			dynamic_image_url = None
			post_creation = None
		else:
			callback_url = None
			
		# check if we have it already
		if Wisp.get_by_user_name(user_info.key, name):
			self.add_message("A wisp with that name already exists in this account!", "error")
			return self.redirect_to('account-wisps')		

		# save the new wisp in our database            
		wisp = Wisp(
			name = name,
			owner = user_info.key,
			image = image,
			ssh_key = ssh_key,
			dynamic_image_url = dynamic_image_url,
			post_creation = post_creation,
			callback_url = callback_url,
		)
		wisp.put()

		# set default if true
		if default:
			Wisp.set_default(wisp)

		# log to alert
		self.add_message("Wisp %s successfully created!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('account-wisps')

	@webapp2.cached_property
	def form(self):
		return forms.WispForm(self)

class WispDetailHandler(BaseHandler):
	@user_required
	def get(self, wisp_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the wisp in question
		wisp = Wisp.get_by_id(long(wisp_id))

		# if doesn't exist, redirect
		if not wisp:
			return self.redirect_to('account-wisps')

		# insert images into list for wisp
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# load form values
		self.form.name.data = wisp.name
		self.form.ssh_key.data = wisp.ssh_key
		self.form.dynamic_image_url.data = wisp.dynamic_image_url
		self.form.post_creation.data = wisp.post_creation
		self.form.callback_url.data = wisp.callback_url
		self.form.default.data = wisp.default

		# hack up the form a bit
		if wisp.callback_url:
			self.form.callback.data = "custom"
		if wisp.dynamic_image_url:
			self.form.image.data = "custom"
		else:
			self.form.image.data = wisp.image

		# check if the owner is this user
		if wisp and wisp.owner == user_info.key:
			# setup channel to do page refresh
			channel_token = user_info.key.urlsafe()
			refresh_channel = channel.create_channel(channel_token)

			# params build out
			params = {
				'wisp': wisp,
				'image': image,
				'refresh_channel': refresh_channel,
				'channel_token': channel_token 
			}

			return self.render_template('wisp/wisp_detail.html', **params)
		
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
		post_creation = self.form.post_creation.data.strip()
		callback_url = self.form.callback_url.data.strip()
		default = self.form.default.data

		# hack up form to deal with custom image
		if self.form.image.data.strip() == "custom":
			image = None
		else:
			image = Image.get_by_id(int(self.form.image.data.strip())).key

		# hack up form to deal with custom callback
		if self.form.callback.data.strip() == "custom":
			image = None
			ssh_key = None
			dynamic_image_url = None
			post_creation = None
		else:
			callback_url = None

		# check if the wisp owner is this user
		if wisp and wisp.owner == user_info.key:
			# save the new wisp in our database            
			wisp.name = name
			wisp.image = image
			wisp.ssh_key = ssh_key
			wisp.dynamic_image_url = dynamic_image_url
			wisp.post_creation = post_creation
			wisp.callback_url = callback_url
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

		# check if wisp is in use by a cloud

		# if we found it and own it, delete
		if wisp and wisp.owner == user_info.key:
			wisp.key.delete()
			self.add_message('Wisp successfully deleted!', 'success')
		else:
			self.add_message('Wisp was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

	@webapp2.cached_property
	def form(self):
		return forms.WispForm(self)
