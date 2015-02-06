import time
from datetime import datetime
import logging

from google.appengine.api import channel

import config
from web.models.models import Instance, InstanceBid, Wisp, Appliance
from web.basehandler import BaseHandler

def channel_message(token, message):
	channel_token = token
	refresh_channel = channel.create_channel(channel_token)
	channel.send_message(refresh_channel, message)

# search and delete stale appliance's instances
class AppliancesHandler(BaseHandler):
	def get(self):
		pass

# search and delete instances who 
class InstancesHandler(BaseHandler):
	def get(self):
		# look up instances that were updated more than 15 minutes ago
		instances = Instance.get_older_than(900)

		# loop through results and mark returned instances as 'inactive'
		if instances:
			for instance in instances:
				if instance.state == 1 and instance.reserved == False:
					logging.info("Marking instance=(%s) stale." % instance.name)
					instance.state = 0
					instance.put()

					# notification channel
					if instance.token:
						channel_message(instance.token, "stale")

		# look up instances that were updated more than 24 hours ago
		instances = Instance.get_older_than(86400)

		# loop through results and delete them
		if instances:
			for instance in instances:
				# whack instances that are decomissioned or never been started 
				if instance.state == 7 or instance.state < 3:
					logging.info("Deleting stale instance=(%s)." % instance.name)
					instance.key.delete()

					# notification channel
					if instance.token:
						channel_message(instance.token, "delete")
		return


# expire instance reservations
class InstanceBidsHandler(BaseHandler):
	def get(self):
		# look up bid instance reservations older than 5 minutes
		instancebids = InstanceBid.get_expired()

		if instancebids:
			# remove reservations and update instances
			for instancebid in instancebids:
				# update instance
				if instancebid.instance:
					instance = instancebid.instance.get()

					if instance.state <=1:
						instance.reserved = False
						instance.token = None
						instance.put()

				# delete reservation
				instancebid.key.delete()

				# notification channel
				if instancebid.token:
					channel_message(instancebid.token, "delete")

		return

# expire anonymous wisps
class AnonymousWispHandler(BaseHandler):
	def get(self):
		# get older anonymous wisps to delete
		wisps = Wisp.get_expired_anonymous()

		if wisps:
			# remove wisps
			for wisp in wisps:
				# delete wisp
				wisp.key.delete()

		return