import time
from datetime import datetime
import logging

from google.appengine.api import channel

import config
from web.basehandler import BaseHandler

def channel_message(token, message):
	channel_token = token
	refresh_channel = channel.create_channel(channel_token)
	channel.send_message(refresh_channel, message)

# left for reference
'''
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
'''
