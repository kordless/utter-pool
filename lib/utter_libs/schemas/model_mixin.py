import abc

from utter_libs.schemas.helpers import ApiSchemaHelper


class ModelSchemaMixin(object):

	@abc.abstractproperty
	def schema():
		pass

	# create api schema and fill it with data from self
	def as_schema(self):
		schema = self.object_schema()
		ApiSchemaHelper.fill_schema_from_object(schema, self)
		return schema
