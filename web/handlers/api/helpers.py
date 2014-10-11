from web.models.models import Appliance

# handler decorater to authenticate appliance based on header
def authenticate_appliance(fun):
	def with_appliance_check(self, *args, **kwargs):
		if "Appliance-Token" in self.request.headers.keys():
			appliance = Appliance.get_by_token(self.request.headers['Appliance-Token'])

			# if appliance can't be fetched by token we consider it invalid
			if appliance and appliance.activated:
				# auth succesfull, call function and pass the appliance
				kwargs['appliance'] = appliance
				return fun(self, *args, **kwargs)

		logging.error(
			"{0} failed to authenticate with apitoken.".format(
				self.request.remote_addr))
		self.response.set_status(403)
		self.response.write("Authentication failed.")

	return with_appliance_check
