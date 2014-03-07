# -*- coding: utf-8 -*-
import os
import logging
import hashlib
import json

import urllib
import urllib2
import httplib2
import webapp2

from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

from google.appengine.api import taskqueue
from google.appengine.api import users

import config
import web.forms as forms
import web.models.models as models
from lib import utils, httpagentparser
from web.basehandler import BaseHandler
from web.basehandler import user_required

class ProviderLogoutHandler(BaseHandler):
	def get(self):
		self.redirect_to('home')
		

class ProviderLoginHandler(BaseHandler):
	"""
	Handler for Social authentication
	"""

	def get(self):
		self.redirect_to('home')


class ProviderProfileHandler(BaseHandler):
	"""
	Handler for Social authentication
	"""

	def get(self):
		self.redirect_to('home')


class ProviderSignupHandler(BaseHandler):
	"""
	Handler for Social authentication
	"""

	def get(self):
		self.redirect_to('home')


class SocialLoginHandler(BaseHandler):
	"""
	Handler for Social authentication
	"""

	def get(self):
		if not config.enable_federated_login:
			message = _('Federated login is disabled.')
			self.add_message(message, 'warning')
			return self.redirect_to('login')

		callback_url = "%s/login/complete" % (self.request.host_url)
		continue_url = self.request.get('continue_url')
		
		if continue_url:
			dest_url=self.uri_for('social-login-complete', continue_url=continue_url)
		else:
			dest_url=self.uri_for('social-login-complete')
		try:
			login_url = users.create_login_url(federated_identity='gmail.com', dest_url=dest_url)
			self.redirect(login_url)
		except users.NotAllowedError:
			self.add_message('You must enable Federated Login Before for this application.<br> '
							'<a href="http://appengine.google.com" target="_blank">Google App Engine Control Panel</a> -> '
							'Administration -> Application Settings -> Authentication Options', 'error')
			self.redirect_to('login')


class CallbackSocialLoginHandler(BaseHandler):
	"""
	Callback (Save Information) for Social Authentication
	"""

	def get(self):
		if not config.enable_federated_login:
			message = _('Federated login is disabled.')
			self.add_message(message, 'warning')
			return self.redirect_to('login')

		# google OpenID Provider
		provider_display_name = "Google"

		# get info passed from Google
		current_user = users.get_current_user()
		if current_user:
			if current_user.federated_identity():
				uid = current_user.federated_identity()
			else:
				uid = current_user.user_id()
			email = current_user.email()
		else:
			message = _('No user authentication information received from %s. '
						'Please ensure you are logged in to your Google account.'
						% provider_display_name)
			self.add_message(message, 'error')
			return self.redirect_to('login')
		
		if self.user:
			# add social account to user
			user_info = models.User.get_by_id(long(self.user_id))
			if models.SocialUser.check_unique(user_info.key, provider_name, uid):
				social_user = models.SocialUser(
					user = user_info.key,
					provider = provider_name,
					uid = uid
				)
				social_user.put()

				message = _('%s association successfully added.' % provider_display_name)
				self.add_message(message, 'success')
			else:
				message = _('This %s account is already in use.' % provider_display_name)
				self.add_message(message, 'error')
			self.redirect_to('edit-profile')
		else:
			# login with OpenId Provider
			social_user = models.SocialUser.get_by_provider_and_uid(provider_name, uid)
			if social_user:
				# Social user found. Authenticate the user
				user = social_user.user.get()
				self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
				logVisit = models.LogVisit(
					user = user.key,
					uastring = self.request.user_agent,
					ip = self.request.remote_addr,
					timestamp = utils.get_date_time()
				)
				logVisit.put()
				self.redirect_to('home')
			else:
				message = _('This OpenID based account is not associated with a TinyProbe account. '
							'Please sign in or create a TinyProbe account before continuing.')
				self.add_message(message, 'warning')
				self.redirect_to('login')


class DeleteSocialProviderHandler(BaseHandler):
	"""
	Delete Social association with an account
	"""

	@user_required
	def get(self, provider_name):
		if self.user:
			user_info = models.User.get_by_id(long(self.user_id))
			social_user = models.SocialUser.get_by_user_and_provider(user_info.key, provider_name)
			if social_user:
				social_user.key.delete()
				message = _('%s successfully disassociated.' % provider_name.title())
				self.add_message(message, 'success')
			else:
				message = _('Social account on %s not found for this user.' % provider_name.title())
				self.add_message(message, 'error')
		self.redirect_to('edit-profile')


class LogoutHandler(BaseHandler):
	"""
	Destroy user session and redirect to login
	"""

	def get(self):
		if self.user:
			message = _("You've been logged out.  Remember to log out of other providers as well for saftey's sake!")
			self.add_message(message, 'info')

		self.auth.unset_session()
		# User is logged out, let's try redirecting to login page
		try:
			self.redirect(self.auth_config['login_url'])
		except (AttributeError, KeyError), e:
			logging.error("Error logging out: %s" % e)
			message = _("User is logged out, but there was an error on the redirection.")
			self.add_message(message, 'error')
			return self.redirect_to('home')


class EditProfileHandler(BaseHandler):
	"""
	Handler for Edit User Profile
	"""

	@user_required
	def get(self):
		""" Returns a simple HTML form for edit profile """

		params = {}

		if self.user:
			logging.info("logged in")
		if self.user:
			user_info = models.User.get_by_id(long(self.user_id))
			self.form.username.data = user_info.username
			self.form.name.data = user_info.name
			self.form.last_name.data = user_info.last_name
			self.form.country.data = user_info.country
			providers_info = user_info.get_social_providers_info()
			params['used_providers'] = providers_info['used']
			params['unused_providers'] = providers_info['unused']
			params['country'] = user_info.country
			params['company'] = user_info.company

		return self.render_template('user/edit_profile.html', **params)

	def post(self):
		""" Get fields from POST dict """

		if not self.form.validate():
			return self.get()
		username = self.form.username.data.lower()
		name = self.form.name.data.strip()
		last_name = self.form.last_name.data.strip()
		country = self.form.country.data

		try:
			user_info = models.User.get_by_id(long(self.user_id))

			try:
				message=''
				# update username if it has changed and it isn't already taken
				if username != user_info.username:
					user_info.unique_properties = ['username','email']
					uniques = [
							   'User.username:%s' % username,
							   'User.auth_id:own:%s' % username,
							   ]
					# Create the unique username and auth_id.
					success, existing = Unique.create_multi(uniques)
					if success:
						# free old uniques
						Unique.delete_multi(['User.username:%s' % user_info.username, 'User.auth_id:own:%s' % user_info.username])
						# The unique values were created, so we can save the user.
						user_info.username=username
						user_info.auth_ids[0]='own:%s' % username
						message+= _('Your new username is %s' % '<strong>{0:>s}</strong>'.format(username) )

					else:
						message+= _('The username %s is already taken. Please choose another.'
								% '<strong>{0:>s}</strong>'.format(username) )
						# At least one of the values is not unique.
						self.add_message(message, 'error')
						return self.get()
				user_info.name=name
				user_info.last_name=last_name
				user_info.country=country
				user_info.put()
				message+= " " + _('Thanks, your settings have been saved.  You may now dance.')
				self.add_message(message, 'success')
				return self.get()

			except (AttributeError, KeyError, ValueError), e:
				logging.error('Error updating profile: ' + e)
				message = _('Unable to update profile. Please try again later.')
				self.add_message(message, 'error')
				return self.get()

		except (AttributeError, TypeError), e:
			login_error_message = _('Sorry you are not logged in.')
			self.add_message(login_error_message, 'error')
			self.redirect_to('login')

	@webapp2.cached_property
	def form(self):
		return forms.EditProfileForm(self)


