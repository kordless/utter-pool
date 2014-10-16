from utter_libs.schemas.flavor import flavor_schema

ip_address_schema = {
	'type': 'object',
	'title': 'IPAddress',
	'properties': {
		'version': {'type': 'number'},
		'scope': { 'enum': [ 'public', 'private', ], },
		'address': {'type': 'string'},
	},
	'required': ['version', 'scope', 'address', ],
}

instance_schema = {
	'$schema': 'http://json-schema.org/draft-04/schema#',
	'type': 'object',
	'title': 'Instance',
	'properties': {
		'name': {'type': 'string'},
		'state': {'type': 'number'},
		'address': {'type': 'string'},
		'console_output': {
			'type': 'array',
			'items': {'type': 'string'},
		},
		'expires': {'type': 'number'},
		'ip_addresses': {
			'type': 'array',
			'items': ip_address_schema,
		},
		'flavor': flavor_schema,
	},
	'required': [
		'name', 'state', 'address',
		'expires', 'flavor',
	],
}

instance_list_schema = {
	'type': 'object',
	'title': 'InstanceList',
	'properties': {
		'items': {
			'type': 'array',
			'items': instance_schema,
		},
	},
}
