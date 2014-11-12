# standard library imports
import logging, os
import urllib, urllib2, httplib2
import hashlib, json

# related webapp2 imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

# google imports
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.api import channel

# local application/library specific imports
import config
import web.forms as forms
import web.models.models as models
from web.models.models import InstanceBid, Instance

from lib import utils, httpagentparser
from web.basehandler import BaseHandler
from web.basehandler import user_required

class SendEmailHandler(BaseHandler):
	# task queue stuff for sending emails
	def post(self):
		from google.appengine.api import mail, app_identity
		from google.appengine.api.datastore_errors import BadValueError
		from google.appengine.runtime import apiproxy_errors
		import config
		from web.models import models

		to = self.request.get("to")
		subject = self.request.get("subject")
		body = self.request.get("body")
		sender = self.request.get("sender")

		if sender != '' or not utils.is_email_valid(sender):
			if utils.is_email_valid(config.contact_sender):
				sender = config.contact_sender
			else:
				app_id = app_identity.get_application_id()
				sender = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)

		try:
			logEmail = models.LogEmail(
				sender = sender,
				to = to,
				subject = subject,
				body = body,
				when = utils.get_date_time("datetimeProperty")
			)
			logEmail.put()
			
		except (apiproxy_errors.OverQuotaError, BadValueError):
			logging.error("Error saving Email Log in datastore")

		mail.send_mail(sender, to, subject, body)


class AboutHandler(BaseHandler):
	def get(self):
		if self.user:
			user_info = models.User.get_by_id(long(self.user_id))
			if user_info.name:
				self.form.name.data = user_info.name
			if user_info.email:
				self.form.email.data = user_info.email
		
		# wtf is this?
		params = {"exception" : self.request.get('exception')}

		return self.render_template('site/about.html', **params)

	def post(self):
		# validate form
		if not self.form.validate():
			return self.get()
			
		remoteip  = self.request.remote_addr
		user_agent  = self.request.user_agent
		exception = self.request.POST.get('exception')
		name = self.form.name.data.strip()
		email = self.form.email.data.lower()
		message = self.form.message.data.strip()

		try:
			subject = "Contact this person, please."
			
			# exceptions for error pages that redirect to contact
			template_val = {
				"name": name,
				"email": email,
				"browser": str(httpagentparser.detect(user_agent)['browser']['name']),
				"browser_version": str(httpagentparser.detect(user_agent)['browser']['version']),
				"operating_system": str(httpagentparser.detect(user_agent)['flavor']['name']) + " " +
									str(httpagentparser.detect(user_agent)['flavor']['version']),
				"ip": remoteip,
				"message": message
			}
			body_path = "emails/contact.txt"
			body = self.jinja2.render_template(body_path, **template_val)

			email_url = self.uri_for('taskqueue-send-email')
			taskqueue.add(url = email_url, params={
				'to': config.contact_recipient,
				'subject' : subject,
				'body' : body,
				'sender' : config.contact_sender,
				})

			message = "Your message was sent successfully."
			self.add_message(message, 'success')
			return self.redirect_to('about')

		except (AttributeError, KeyError), e:
			logging.error('Error sending contact form: %s' % e)
			message = "Error sending the message. Please try again later."
			self.add_message(message, 'error')
			return self.redirect_to('about')

	@webapp2.cached_property
	def form(self):
		return forms.AboutForm(self)


class DemoHandler(BaseHandler):
	def get(self, demo_name = None):
		params = {}
		return self.render_template('site/demo.html', **params)


class DemosHandler(BaseHandler):
	def get(self, demo_name = None):
		params = {}
		return self.render_template('site/demos/%s.html' % demo_name, **params)

	@webapp2.cached_property
	def form(self):
		return forms.DemoForm(self)


class DemosBidHandler(BaseHandler):
	def get(self, demo_name = None, token = None):
		# lookup up bid
		bid = InstanceBid.get_by_token(token)
		if not bid:
			self.add_message("Instance reservation token %s has expired." % token, 'error')
			return self.redirect_to('demos', demo_name=demo_name)

		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("All available instance reservations are in use. Please try again in a few minutes.", 'error')
			return self.redirect_to('demos', demo_name=demo_name)

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		params = {
			'instance': instance,
			'bid': bid,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('site/demos/%s_bid.html' % demo_name, **params)


class DemosInstanceHandler(BaseHandler):
	def get(self, demo_name = None, token = None):
		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("That instance cannot be found.", 'error')
			return self.redirect_to('demos', demo_name=demo_name)

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		# hack in time max for timer
		instance.data_max = int(instance.expires - int(instance.started.strftime('%s')))

		# dict the meta
		if instance.meta:
			instance.meta_dict = json.loads(instance.meta)
		else:
			instance.meta_dict = {}

		params = {
			'instance': instance,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('site/demos/%s_instance.html' % demo_name, **params)


class DocsHandler(BaseHandler):
	def get(self):
		params = {}
		return self.render_template('site/docs.html', **params)


class HomeRequestHandler(BaseHandler):
	def get(self):
		params = {}
		return self.render_template('site/index.html', **params)


class PricingHandler(BaseHandler):
	def get(self):
		params = {}
		return self.render_template('site/pricing.html', **params)


class FeaturesHandler(BaseHandler):
	def get(self):
		params = {}
		return self.render_template('site/features.html', **params)

