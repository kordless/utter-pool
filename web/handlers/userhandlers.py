import os
import logging
import time
import random

import urllib
import urllib2
import httplib2
import hashlib
import json

from datetime import datetime
from datetime import timedelta
from StringIO import StringIO

import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, Wisp
from web.models.models import LogVisit
from web.basehandler import BaseHandler
from web.basehandler import user_required
from lib import utils, httpagentparser
from lib import pyotp

# user logout
class LogoutHandler(BaseHandler):
	def get(self):
		if self.user:
			user_info = User.get_by_id(long(self.user_id))

			# if 2fa enabled, set the last login to an hour ago
			if user_info.tfenabled:
				user_info.last_login = datetime.now() + timedelta(0, -config.session_age)
				user_info.put()

			message = "You have been logged out."
			self.add_message(message, 'info')

		self.auth.unset_session()
		self.redirect_to('home')


# user login w/google
class LoginHandler(BaseHandler):
	def get(self):
		callback_url = "%s/login/complete" % (self.request.host_url)

		# check if we have somewhere to go
		next = self.request.get('next')
		print next
		if next:
			dest_url=self.uri_for('login-complete', next=next)
		else:
			dest_url=self.uri_for('login-complete')
		
		try:
			login_url = users.create_login_url(dest_url=dest_url)
			self.redirect(login_url)
		except users.NotAllowedError:
			self.add_message("The pool operator must enable Federated Login before you can login.", "error")
			self.redirect_to('home')


# google auth callback
class CallbackLoginHandler(BaseHandler):
	def get(self):
		# get info from Google login
		current_user = users.get_current_user()

		# handle old and new users
		try:
			uid = current_user.user_id()

			# see if user is in database
			user_info = User.get_by_uid(uid)

			# get the destination URL from the next parameter
			next = self.request.get('next')

			# create association if user doesn't exist
			if user_info is None:
				username = current_user.email().split("@")[0]
				email = current_user.email()

				# create entry in db
				user_info = User(
					last_login = datetime.now(),
					uid = str(uid),
					username = username,
					email = email,
					activated = True
				)

				# try to create unique username
				while True:
					user_info.unique_properties = ['username']
					uniques = ['User.username:%s' % user_info.username]
					success, existing = Unique.create_multi(uniques)

					# if we already have that username, create a new one and try again
					if existing:
						user_info.username = "%s%s" % (username, random.randrange(100)) 
					else:
						break
				
				# write out the user
				user_info.put()

				# wait a few seconds for database server to update
				time.sleep(1)
				log_message = "new user registered"

				# slack the new user signup
				if config.debug:
					in_dev = " (in development)"
				else:
					in_dev = ""

				slack_data = {
					'text': "Woot! New user %s just signed up%s!" % (user_info.username, in_dev),
					'username': "VP of Cloud",
					'icon_emoji': ":cloud:" 
				}
				h = httplib2.Http()
				resp, content = h.request(config.slack_webhook, 
			        'POST', 
			        json.dumps(slack_data),
			        headers={'Content-Type': 'application/json'})

			else:
				# existing user logging in - force a2fa check before continuing
				now_minus_an_hour = datetime.now() + timedelta(0, -config.session_age)

				if user_info.tfenabled and (user_info.last_login < now_minus_an_hour): 
						return self.redirect_to('login-tfa', next=next)
				else:
					# two factor is disabled, or already complete
					user_info.last_login = datetime.now()
					user_info.put()
					log_message = "user login"

			# set the user's session
			self.auth.set_session(self.auth.store.user_to_dict(user_info), remember=True)
			
			# log visit
			log = LogVisit(
				user = user_info.key,
				message = log_message,
				uastring = self.request.user_agent,
				ip = self.request.remote_addr
			)
			log.put()
			message = "You have successfully logged in!"            
			self.add_message(message, 'success')

			# take user to whatever page was originally requested, or status if none
			if next:
				return self.redirect(str(next))
			else:
				return self.redirect_to('account-status')
				
		except Exception as ex:
			message = "No user authentication information received from Google: %s" % ex            
			self.add_message(message, 'error')
			return self.redirect_to('home')


class TwoFactorLoginHandler(BaseHandler):
	def get(self):
		params = {}
		return self.render_template('user/twofactorlogin.html', **params)

	def post(self):
		# user information from google login
		current_user = users.get_current_user()
		uid = current_user.user_id()
		user_info = User.get_by_uid(uid)
		
		# pull in tfa info
		authcode = self.request.get('authcode')
		secret = user_info.tfsecret
		totp = pyotp.TOTP(secret)

		# get the destination URL from the next parameter
		next = self.request.get('next')

		# check if token verifies
		if totp.verify(authcode):
			# user has completed tfa - update login time
			user_info.last_login = datetime.now()
			user_info.put()
			time.sleep(2)
			return self.redirect_to('login-complete', next=next)

		# did not 2fa - force them back through login
		self.redirect_to('login', next=next)


class TwoFactorSettingsHandler(BaseHandler):
	@user_required
	def get(self):
		# get the authcode and desired action
		authcode = self.request.get('authcode')
		action = self.request.get('action')

		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		secret = user_info.tfsecret
		totp = pyotp.TOTP(secret)
		
		# build paramater list
		params = {}
		
		# verify
		if action == "enable" and totp.verify(authcode):
			# authorized to enable
			user_info.tfenabled = True
			user_info.put()
		elif action == "disable" and totp.verify(authcode):
			# authorized to disable
			user_info.tfenabled = False
			user_info.put()
		else:
			# not authorized - javascript will handle adding a user message to the UI
			params['response'] = "error"
			params['result'] = "two factor auth failed"
			self.response.set_status(401)
			self.response.headers['Content-Type'] = 'application/json'
			return self.render_template('api/response.json', **params)

		# respond
		params['response'] = "success"
		params['result'] = "two factor auth successful"
		self.response.headers['Content-Type'] = "application/json"
		return self.render_template('api/response.json', **params)


class SettingsHandler(BaseHandler):
	@user_required
	def get(self):
		# load user information
		user_info = User.get_by_id(long(self.user_id))

		# form fields
		self.form.username.data = user_info.username
		self.form.name.data = user_info.name
		self.form.email.data = user_info.email
		self.form.company.data = user_info.company
		self.form.country.data = user_info.country
		self.form.timezone.data = user_info.timezone
	
		# extras
		params = {}
		params['tfenabled'] = user_info.tfenabled

		# create holder token to setup 2FA - this will continue until user enables 2fa
		if user_info.tfenabled == False:
			secret = pyotp.random_base32()
			totp = pyotp.TOTP(secret)
			qrcode = totp.provisioning_uri("%s-%s" % (config.app_name, user_info.email))
			params['qrcode'] = qrcode
			params['secret'] = secret
			
			# update the user's key
			user_info.tfsecret = secret
			user_info.put()

			# tell the user they need to setup 2fa
			self.add_message("Please take a moment and set up two factor authentication.", "error")

		return self.render_template('user/settings.html', **params)

	def post(self):
		if not self.form.validate():
			self.add_message("There were errors in subbitting the form.", "error")
			return self.get()

		username = self.form.username.data.lower()
		name = self.form.name.data.strip()
		email = self.form.email.data.strip()
		company = self.form.company.data.strip()
		country = self.form.country.data.strip()
		timezone = self.form.timezone.data.strip()

		user_info = User.get_by_id(long(self.user_id))

		try:
			# update username if it has changed and it isn't already taken
			if username != user_info.username:
				user_info.unique_properties = ['username']
				uniques = ['User.username:%s' % username]
				
				# create the unique username and auth_id
				success, existing = Unique.create_multi(uniques)

				if success:
					# free old uniques and update user
					Unique.delete_multi(['User.username:%s' % user_info.username])
					user_info.username = username
					self.add_message('Your new username is %s.' % format(username), 'success')

				else:
					# username not unique
					self.add_message('The username %s is already in use.' % format(username), 'error')
					return self.get()

			# update email if it has changed and it isn't already taken
			if email != user_info.email:
				user_info.unique_properties = ['email']
				uniques = ['User.email:%s' % email]
				
				# create the unique username and auth_id
				success, existing = Unique.create_multi(uniques)

				if success:
					# free old uniques and update user
					Unique.delete_multi(['User.email:%s' % user_info.email])
					user_info.email = email
					self.add_message('Your new email is %s.' % format(email), 'success')

				else:
					# user's email not unique
					self.add_message('That email address is already in use.', 'error')
					return self.get()

			# update database                
			user_info.name = name
			user_info.company = company
			user_info.country = country
			user_info.timezone = timezone
			user_info.put()

			self.add_message("Your settings have been saved.", 'success')
			return self.get()

		except (AttributeError, KeyError, ValueError), e:
			logging.error('Error updating profile: ' + e)
			self.add_message('Unable to update profile. Please try again later.', 'error')
			return self.get()


	@webapp2.cached_property
	def form(self):
		return forms.EditProfileForm(self)



class StatusHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up wisps
		wisps = Wisp.get_by_user(user_info.key)
		if len(wisps) > 0:
			wisps_exist = True
		else:
			wisps_exist = False
			
		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'wisps_exist': wisps_exist,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('user/status.html', **params)


class AccountHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		params = {}
		return self.render_template('user/account.html', **params)


class AccountDeleteHandler(BaseHandler):
	@user_required
	def get(self):
		# delete a user from the system
		pass
		