
instance_start_parameters_schema = {
	'$schema': 'http://json-schema.org/draft-04/schema#',
	'type': 'object',
	'title': 'InstanceStartParameters',
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
