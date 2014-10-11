import python_jsonschema_objects as pjs

from instance import instance_schema
from instance import instance_list_schema
from appliance import appliance_schema
from flavor import flavor_schema
from flavor import flavor_list_schema
from instance_startup_parameters import \
	instance_startup_parameters_request_schema
from instance_startup_parameters import \
	instance_startup_parameters_response_schema


schemas = {
    'InstanceSchema': (instance_schema, 'Instance'),
    'InstanceListSchema': (instance_list_schema, 'Instancelist'),
    'ApplianceSchema': (appliance_schema, 'Appliance'),
    'FlavorSchema': (flavor_schema, 'Flavor'),
    'FlavorListSchema': (flavor_list_schema, 'Flavorlist'),
    'InstanceStartupParametersRequestSchema': (
      instance_startup_parameters_request_schema,
      'Instancestartupparametersrequest'),
    'InstanceStartupParametersResponseSchema': (
      instance_startup_parameters_response_schema,
      'Instancestartupparametersresponse'),
}

# iterate over schemas and create their according content-types
for (k, v) in schemas.iteritems():
    schemas[k] = getattr(pjs.ObjectBuilder(v[0]).build_classes(), v[1])
