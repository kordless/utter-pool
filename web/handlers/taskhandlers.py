import time
from datetime import datetime

import config
from web.models.models import Instance
from web.basehandler import BaseHandler

class InstancesHandler(BaseHandler):
	def get(self):
		print "running tasks"