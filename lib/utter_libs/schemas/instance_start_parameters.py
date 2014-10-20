
instance_start_parameters_schema = {
	'$schema': 'http://json-schema.org/draft-04/schema#',
	'type': 'object',
	'title': 'InstanceStartParameters',
	'properties': {
		'image': {
			'type': 'object',
			'properties': {
				'url': {'type': 'string'},
				'name': {'type': 'string'},
				'container_format': {'type': 'string'},
				'disk_format': {'type': 'string'}},
			'required': ['url', 'name', 'container_format', 'disk_format']},
		'callback_url': {'type': 'string'},
		'ssh_keys': {'type': 'array',
								 'items': {'type': 'string'}},
		'post_create': {'type': 'array',
										'items': {'type': 'string'}},
	},
	'required': [
		'image', 'callback_url', 'ssh_keys', 'post_create',
	],
}
