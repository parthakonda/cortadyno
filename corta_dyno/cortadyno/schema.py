__author__ = 'partha saradhi konda <pkonda@incorta.in>'

# Data islocation from customer to customer is the key factor in deciding the design.
# Right now, for every customer a dynamodb table will get created for storing data for all extensions
# Pertaining to a customer
# How will these extension data get distinguished from each other?
# Using a GSI(Global Secondary Index) - maintain an attribute called `extension` and partiotion will be done
# based on this attribute

from pynamodb.attributes import (
    JSONAttribute, NumberAttribute, UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute
)


class Schema:
    """
    To create&update the schema of a dynamodb table on-fly
    @name - name of the table
    @fields - fields that you want to create
    """

    model = None

    mapping = {
        'integer': NumberAttribute,
        'float': NumberAttribute,
        'string': UnicodeAttribute,
        'boolean': BooleanAttribute,
        'email': UnicodeAttribute,
        'url': UnicodeAttribute,
        'uuid': UnicodeAttribute,
        'datetime': UTCDateTimeAttribute,
        'json': JSONAttribute
    }

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        fields = kwargs.pop('fields', None)
        table_name = self.model.Meta.table_name
        assert fields is not None, "fields should not be empty"
        super(Schema, self).__init__(*args, **kwargs)
        for field in fields:
            # Note: In order to set the attributes dynamically for participation of saving,
            # you need to set the attribute `_attributes` which is a dict
            # and should get updated with proper data type
            self.model._attributes[field['field']] = self.resolve_field(**field)
            # Note: If you set the project to `all` then in order to make your
            # dynamic fields visible then you should add those attributes
            # as part of the class attributes
            setattr(self.model, field['field'], self.resolve_field(**field))

    def resolve_field(self, **kwargs):
        """
        resolve the field (returns the instance)
        @kwargs: dict
        example:
        # [{
        # field: null,
        # type: "string",
        # is_required: false,
        # alias: null,
        # null_value: null
        # }]
        """
        params = {
            'null': not kwargs['is_required'],
            'attr_name': kwargs['field']  # this is required(will be considered in _serializing the attributes)
        }
        field_type = kwargs['type'].lower()
        if field_type in self.mapping:
            return self.mapping[field_type](**params)
