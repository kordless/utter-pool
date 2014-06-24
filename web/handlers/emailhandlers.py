import logging

from google.appengine.api import mail, app_identity
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.runtime import apiproxy_errors

import config
from web.models.models import User, LogEmail, Group
from web.basehandler import BaseHandler

class SendEmailInviteHandler(BaseHandler):
	def post(self):
		to = self.request.get("to")
		group_id = self.request.get("group_id")
		invitor_id = self.request.get("invitor_id")

		# admin of the pool
		sender = config.contact_sender

		# test to see if the sender_id and group number is real
		invitor = User.get_by_id(invitor_id)
		group = Group.get_by_id(group_id)

		# if we found the sending user and group
		if invitor and group:
			# rest of the email stuff
			subject = "You've been invited to the %s group on %s." % (group.name, config.app_name)
			body = """
Howdy!

You've been invited to the %s group on the %s Compute Pool.  

This invite will allow you to start instances which are managed by appliances in 
the %s group.  Instance starts are initiated by Bitcoin payments.

Your memebership in the group will also allow you to add your own OpenStack cluster 
to the group.  Any instances your cluster serves will be paid for using Bitcoin.

If this email comes as a complete suprise to you, simply delete it.  We may yet
meet again.

Cheers,

Kord Campbell
Founder
Utter.io

t: @kordless, @stackape, @stackgeek
c: 510.230.3482
		""" % (group.name, config.app_name, group.name)

			logEmail = LogEmail(
				sender = sender,
				to = to,
				subject = subject,
				body = body,
				when = utils.get_date_time("datetimeProperty")
			)
			logEmail.put()

			mail.send_mail(sender, to, subject, body)

		else:
			# doing nothing, you fuckers
			logging.error("Failed attempt to send invite email.")