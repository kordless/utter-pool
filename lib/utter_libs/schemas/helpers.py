import types

from python_jsonschema_objects.classbuilder import ProtocolBase


class ApiSchemaHelper(object):

  # take and object and fill it with values from schema content type
  @staticmethod
  def fill_object_from_schema(schema, dst):
    for (k, v) in schema.__class__.__dict__['__propinfo__'].iteritems():
      if getattr(schema, k) != None:
        attr = getattr(schema, k)
        if type(attr) == types.ListType:
          setattr(dst, k, attr)
        else:
          setattr(dst, k, attr.as_dict())

  # take a schema content type and fill it with values from object
  @classmethod
  def fill_schema_from_object(cls, schema, src):
    schema.update(cls.iterate_properties(src, schema.__class__.__dict__['__propinfo__']))

  # iterate over properties of schema and copy valuees from src object into schema
  @classmethod
  def iterate_properties(cls, src, properties):
    data = {}
    for (k, v) in properties.iteritems():
      if type(v['type']) == types.StringType:
        if hasattr(src, k) and getattr(src, k) != None:
          data[k] = getattr(src, k)
      elif issubclass(v['type'], ProtocolBase):
        prop = getattr(src, k)
        if prop != None:
          try:
            # if that's a Google Appengine key referencing another model
            # it needs to be fetched first
            if prop.__class__.__name__ == "Key":
              prop = prop.get()
          except Exception:
            pass
          data[k] = cls.iterate_properties(prop, v['properties'])
    return data

  # render list of objects
  @classmethod
  def build_schema_list(cls, object_list, list_schema, object_schema):
    schema = list_schema()

    # populate list schema with list of object schemas as dictionaries
    schema.update({'items': [
      cls.build_schema_object(x, object_schema).as_dict()
      for x in object_list]})

    # return schema
    return schema

  # build schema from object
  @classmethod
  def build_schema_object(cls, object, schema):
    schema = schema()
    cls.fill_schema_from_object(schema, object)
    return schema
