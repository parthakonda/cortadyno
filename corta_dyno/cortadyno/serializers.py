import pytz
from datetime import datetime
from rest_framework import serializers


class ExtendedBooleanField(serializers.BooleanField):
    def to_internal_value(self, value):
        if value in ('true', 't', 'True', '1', 'yes', 'YES', 'Yes', 'TRUE', 1):
            return True
        if value in ('false', 'f', 'False', '0', 'no', 'NO', 'No', 'FALSE', 0):
            return False
        raise serializers.ValidationError("Boolean type requires either true or false")


class ExtendedUUIDField(serializers.UUIDField):
    def to_internal_value(self, value):
        super(ExtendedUUIDField, self).to_internal_value(value)
        return str(value)


class ExtendedDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        compiled_value = super(ExtendedDateTimeField, self).to_internal_value(value)
        value = compiled_value.replace(tzinfo=pytz.UTC)
        return value
        

class Serializer(serializers.Serializer):
    """
    Dynamically return the serializer with validation
    """

    mapping = {
        'integer': serializers.IntegerField,
        'float': serializers.FloatField,
        'string': serializers.CharField,
        'boolean': ExtendedBooleanField,
        'email': serializers.EmailField,
        'url': serializers.URLField,
        'uuid': ExtendedUUIDField,
        'datetime': ExtendedDateTimeField,
        'json': serializers.JSONField
    }

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super(Serializer, self).__init__(*args, **kwargs)
        for field in fields:
            compiled_field = self.resolve_field(**field)
            if compiled_field is None:
                raise ValueError('unable to compile the format; invalid type {} for field {}'.format(field['type'], field['field']))
            self.fields.update({
                field['field']: compiled_field
            })

    def resolve_field(self, **kwargs):
        """
        resolve the field (returns the instance)
        """
        params = {
            'required': kwargs['is_required']
        }
        field_type = kwargs['type'].lower()
        if field_type == 'date':
            params.update({
                'format': kwargs.get('format', '%Y-%m-%d')  # ex: 01-23-2019
            })
        if field_type == 'time':
            params.update({
                'format': kwargs.get('format', '%H:%M:%S')  # ex: 12:10:30 (24hr clock)
            })
        if field_type == 'datetime':
            params.update({
                'format': kwargs.get('format', '%Y-%m-%d %H:%M:%S')  # ex: 01-23-2019 12:10:30 (24hr clock)
            })
        if field_type == 'decimal':
            params.update({
                'max_digits': kwargs.get('max_digits', 10),
                'decimal_places': kwargs.get('decimal_places', 8)})
        # if field_type == 'string':
        #     params.update({
        #         'max_length': kwargs.get('max_length', 30)  # ex: 30
        #     })
        if field_type in ['url', 'string', 'email'] and kwargs['is_required'] is False:
            params.update({
                'allow_blank': not kwargs['is_required']  # ex: null or ""
            })
        if field_type in self.mapping:
            return self.mapping[field_type](**params)
