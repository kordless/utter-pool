import time
import json
from urlparse import urlparse

import webapp2

from google.appengine.api import channel
from google.appengine.api import urlfetch

import config
import web.forms as forms
from web.models.models import User, App
from web.basehandler import BaseHandler
from web.basehandler import user_required


class AppHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up applications
		apps = App.get_by_user(user_info.key)

		# redirect if we don't have any apps
		if not apps:
			return self.redirect_to('account-apps-new')

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'apps': apps,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('app/apps.html', **params)


class AppNewHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('app/new.html', **params)

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The new application form did not validate.", "error")
			return self.get()

		# load form values
		url = self.form.url.data.strip()
		
		# check if we have it already
		if App.get_by_user_url(user_info.key, url):
			self.add_message("An application with that URL already exists.", "error")
			return self.redirect_to('account-apps')		

		try:
			# parse the url and build a normalized github URL
			parts = urlparse(url)
			url = "https://%s/%s" % (config.github_url.strip('/'), parts[2].strip('/'))
			
			# use the path to make an API GET for the repo JSON
			repo = json.loads(
				urlfetch.fetch("https://%s/%s/%s" % (
					config.github_api_url.strip('/'),
					'repos',
					parts[2].strip('/')
				), deadline=5).content
			)

			if 'name' not in repo:
				raise Exception("A valid repository was not found.")

		except Exception as ex:
			self.add_message('Application was not added. %s' % ex, 'error')
			return self.redirect_to('account-apps')


		# save the new app in our database
		app = App()           
		app.url = url
		app.name = repo['name']
		app.description = repo['description']
		app.owner = user_info.key 
		app.put()

		# log to alert
		self.add_message("Application %s successfully created!" % app.name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('account-apps-detail', app_id = app.key.id())

	@webapp2.cached_property
	def form(self):
		return forms.AppForm(self)


# provide editing for app object		
class AppDetailHandler(BaseHandler):
	@user_required
	def get(self, app_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the app in question
		app = App.get_by_id(long(app_id))

		# bail if app doesn't exist or not owned by this user
		if not app or app.owner != user_info.key:
			return self.redirect_to('account-apps')

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'app': app,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('app/app_manage.html', **params)
	
	@user_required
	def post(self, app_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# load the app in question
		app = App.get_by_id(long(app_id))
		
		# bail if app doesn't exist or not owned by this user
		if not app or app.owner != user_info.key:
			return self.redirect_to('account-apps')
		
		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The %s application was not updated." % app.name, "info")
			return self.redirect_to('account-apps')

		# load form values
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()

		# save the new app in our database            
		app.name = name
		app.description = description
		app.put()

		# log to alert
		self.add_message("Application %s updated!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		
		return self.redirect_to('account-apps')

	def delete(self, app_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# pull the entry from the db
		app = App.get_by_id(long(app_id))

		# if we found it and own it, delete
		if app and app.owner == user_info.key:
			app.key.delete()
			self.add_message('Application successfully deleted!', 'success')
		else:
			self.add_message('Application was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

	@webapp2.cached_property
	def form(self):
		return forms.AppForm(self)