
instance_startup_parameters_request_schema = {
	'$schema': 'http://json-schema.org/draft-04/schema#',
	'type': 'object',
	'title': 'InstanceStartupParametersRequest',
	'properties': {
		'name': {'type': 'string'},
	},
	'required': [
		'name',
	],
}

instance_startup_parameters_response_schema = {
	'$schema': 'http://json-schema.org/draft-04/schema#',
	'type': 'object',
	'title': 'InstanceStartupParametersResponse',
	'properties': {
		'image_url': {'type': 'string'},
		'image_name': {'type': 'string'},
		'callback_url': {'type': 'string'},
		'ssh_keys': {'type': 'array',
								 'items': {'type': 'string'}},
		'post_create': {'type': 'array',
										'items': {'type': 'string'}},
	},
	'required': [
		'image_url', 'callback_url', 'ssh_keys', 'post_create',
	],
}
