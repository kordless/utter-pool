import types

from python_jsonschema_objects.classbuilder import ProtocolBase


class ApiSchemaHelper(object):

  # take and object and fill it with values from schema content type
  @staticmethod
  def fill_object_from_schema(schema, dst, exceptions=[]):
    for (k, v) in schema.__class__.__dict__['__propinfo__'].iteritems():
      if k in exceptions:
        continue
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
