# standard library imports
import time
import webapp2

# google
from google.appengine.api import channel

# local application/library specific imports
import config
from lib.utils import generate_token
import web.forms as forms
from web.models.models import User, Flavor, Instance, InstanceBid, Wisp, Cloud
from web.basehandler import BaseHandler

class LauncherHandler(BaseHandler):
	def get(self):
		# basics
		ip = self.request.remote_addr

		# setup channel to do page refresh
		channel_token = generate_token()
		refresh_channel = channel.create_channel(channel_token)

		# various pulldown initialization
		self.form.flavor.choices=[]
		self.form.wisp.choices=[]
		self.form.cloud.choices=[]

		# add list of user's flavors, if any
		flavors = Flavor.flavors_with_instances_on_sale()
		for flavor in flavors:
			self.form.flavor.choices.insert(0, (flavor.name, flavor.description))

		# used for determining element layout
		wisp = None
		cloud = None

		# if the user is logged in, we build out the list of their wisps
		if self.user_id:
			# lookup user's auth info and wisps
			user_info = User.get_by_id(long(self.user_id))
			wisps = Wisp.get_by_user(user_info.key)
			for wisp in wisps:
				self.form.wisp.choices.insert(0, (wisp.key.id(), wisp.name))
		
			# load clouds
			clouds = Cloud.get_by_user(user_info.key)

			# create default cloud if none
			if not clouds:
				cloud = Cloud.create_default(user_info.key)
				clouds.append(cloud)
				self.add_message("Default cloud created.", 'success')

			for cloud in clouds:
				self.form.cloud.choices.insert(0, (cloud.key.id(), cloud.name))

		# params build out (injects the last wisp, if there was one)
		params = {
			'remote_ip': ip,
			'wisp': wisp,
			'cloud': cloud,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('lab/launcher.html', **params)

	@webapp2.cached_property
	def form(self):
		return forms.InstanceLauncherForm(self)


class InstanceDetailHandler(BaseHandler):
	def get(self, token = None):
		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("Could not find an instance with token %s." % token, 'error')
			return self.redirect_to('lab-launcher')

		# hack in time max for timer
		instance.data_max = int(instance.expires - int(instance.started.strftime('%s')))

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'instance': instance,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('lab/instance.html', **params)


class BidsHandler(BaseHandler):
	def get(self):
		return


class BidDetailHandler(BaseHandler):
	def get(self, token = None):
		# lookup up bid
		bid = InstanceBid.get_by_token(token)
		if not bid:
			self.add_message("Instance reservation token %s has expired." % token, 'error')
			return self.redirect_to('lab-launcher')

		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("Could not find an instance with token %s." % token, 'error')
			return self.redirect_to('lab-launcher')

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'bid': bid,
			'instance': instance,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('lab/bid.html', **params)
