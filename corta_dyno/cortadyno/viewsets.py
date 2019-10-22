"""
This is a very generic module for dynamic format accepted data
Persistance: dynamodb
DeleteControl: Yes
"""
import base64
import json
from uuid import uuid4

from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class ListCreateAPIView(APIView):
    model = None
    index_name = None
    serializer = {
        'list': None,
        'create': None
    }

    def get_serializer(self):
        if not hasattr(self, 'serializer'):
            raise AttributeError("serializer not defined")
        if not isinstance(self.serializer, serializers.SerializerMetaclass) and not isinstance(self.serializer, dict):
            raise TypeError("serializer should be <serializer> or <dict>")
        if isinstance(self.serializer, serializers.SerializerMetaclass):
            return self.serializer
        if isinstance(self.serializer, dict):
            if self.action not in self.serializer:
                raise KeyError("{} serializer not defined".format(self.action))
            if not isinstance(self.serializer.get(self.action), serializers.SerializerMetaclass):
                raise TypeError("{} serializer is not a valid serializer, it should be a base class serializers.SerializerMetaclass")
            return self.serializer.get(self.action)

    def get(self, request, **kwargs):
        self.action = 'list'
        # Read user query params
        params = request.query_params
        next_key, limit = params.get('next_key', None), int(params.get('limit', 25))
        # Decode next_key
        if next_key is not None:
            next_key = base64.b64decode(next_key).decode('utf-8')
            next_key = json.loads(next_key)
        
        # Query the model & build response
        if self.index_name is not None:
            if not hasattr(self, 'get_index_value'):
                raise KeyError('get_index_value is not Defined')
            index_value = self.get_index_value()
            response = self.model.query(
                index_value,
                index_name=self.index_name,
                last_evaluated_key=next_key,
                limit=limit,
                scan_index_forward=False
            )
        else:
            response = self.model.scan(
                last_evaluated_key=next_key,
                limit=limit
            )
        results = [item.attribute_values for item in response]
        
        # Generate pagination info
        next_key = response.last_evaluated_key
        # INFO: next_key: {'<hash_key>: {'<type>': '<value>'}, '<sort_key>': {'<type>': '<value>'}}
        # INFO: Converting dict to base64 hash (DSL)
        if next_key is not None:
            next_key = json.dumps(next_key, sort_keys=True).encode('ascii')
            next_key = base64.b64encode(next_key)
        
        # Serialize the reponse
        serializer_class = self.get_serializer()
        serializer = serializer_class(data=results, many=True, context={'request': request, 'action': self.action})
        serializer.is_valid()
        # Return the response
        return Response({
            'total_count': len(results),
            'items_per_page': limit,
            'results': serializer.data,
            'next_key': next_key
        }, status=status.HTTP_200_OK)  # exit
        
    def post(self, request):
        self.action = 'create'
        # Get data from request
        payload = request.data.copy()
        # Validate the required fields
        serializer_class = self.get_serializer()
        serializer = serializer_class(data=payload, context={'request': request, 'action': self.action})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # Hook for updating the payload
        if hasattr(self, 'presave'):
            payload = self.presave(payload=payload, validated_data=serializer.validated_data)
        # Save the entry
        try:
            new_entry = self.model(**payload)
            new_entry.save()
        except Exception as e:
            return Response(str(e), status=HTTP_400_BAD_REQUEST)
        # Hook for format the reponse and do some async things
        # For example invoke some celery task
        if hasattr(self, 'postsave'):
            # Response can be altered (call by reference)
            new_entry = self.postsave(instance=new_entry)
        # Return the response
        response = new_entry.attribute_values
        return Response(response, status=status.HTTP_201_CREATED)


class RetrieveUpdateDestroyAPIView(APIView):

    model = None
    index_name = None
    serializer = {
        'retrieve': None,
        'destroy': None
    }
    lookup = None

    def get_object(self, lookup_id):
        return self.model.query(lookup_id).next()

    def get_serializer(self):
        if not hasattr(self, 'serializer'):
            raise AttributeError("serializer not defined")
        if not isinstance(self.serializer, serializers.SerializerMetaclass) and not isinstance(self.serializer, dict):
            raise TypeError("serializer should be <serializer> or <dict>")
        if isinstance(self.serializer, serializers.SerializerMetaclass):
            return self.serializer
        if isinstance(self.serializer, dict):
            if self.action not in self.serializer:
                raise KeyError("{} serializer not defined".format(self.action))
            if not isinstance(self.serializer.get(self.action), serializers.SerializerMetaclass):
                raise TypeError("{} serializer is not a valid serializer, it should be a base class serializers.SerializerMetaclass")
            return self.serializer.get(self.action)

    def get(self, request, **kwargs):
        self.action = 'retrieve'
        # Validate lookup
        lookup_id = kwargs.get(self.lookup, None)
        if lookup_id is None:
            return Response({'message': '{} is required'.format(lookup)}, status=status.HTTP_400_BAD_REQUEST)
        # Check for item existance
        try:
            selected_item = self.get_object(lookup_id)
        except Exception as e:
            return Response({'message': 'Item Not Found'}, status=status.HTTP_404_NOT_FOUND)
        # Hook for another validation (if any)
        if hasattr(self, 'validate'):
            valid, message = self.validate(instance=selected_item)
            if not valid:
                return Response(str(message), status=status.HTTP_403_FORBIDDEN)
        # Serialize the response
        response = selected_item.attribute_values
        serializer_class = self.get_serializer()
        serializer = serializer_class(data=response, partial=True, context={'request': request, 'action': self.action})
        serializer.is_valid()
        # Return the response
        return Response(serializer.data, status=status.HTTP_200_OK)  # exit

    def put(self, request, **kwargs):
        self.action = 'update'
        # Validate lookup
        lookup_id = kwargs.get(self.lookup, None)
        if lookup_id is None:
            return Response({'message': '{} is required'.format(lookup)}, status=status.HTTP_400_BAD_REQUEST)
        # Check for item existance
        try:
            selected_item = self.get_object(lookup_id)
        except Exception as e:
            return Response({'message': 'Item Not Found'}, status=status.HTTP_404_NOT_FOUND)
        # Hook for another validation (if any)
        if hasattr(self, 'validate'):
            valid, message = self.validate(instance=selected_item)
            if not valid:
                return Response(str(message), status=status.HTTP_403_FORBIDDEN)
        payload = request.data.copy()
        # Validate the payload
        serializer_class = self.get_serializer()
        serializer = serializer_class(data=payload, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if not serializer.validated_data:
            return Response(status=status.HTTP_200_OK)
        try:
            selected_item.update(
                actions=[getattr(self.model, key).set(value) for key, value in serializer.validated_data.items()]
            )
            response = selected_item.attribute_values
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, **kwargs):
        self.action = 'destroy'
        if not getattr(self, 'hard_delete', False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # Validate lookup
        lookup_id = kwargs.get(self.lookup, None)
        if lookup_id is None:
            return Response({'message': '{} is required'.format(lookup)}, status=status.HTTP_400_BAD_REQUEST)
        # Check for item existance
        try:
            selected_item = self.get_object(lookup_id)
        except Exception as e:
            return Response({'message': 'Item Not Found'}, status=status.HTTP_404_NOT_FOUND)
        # Hook for another validation (if any)
        if hasattr(self, 'validate'):
            valid, message = self.validate(instance=selected_item)
            if not valid:
                return Response(str(message), status=status.HTTP_403_FORBIDDEN)
        # Try to delete the item
        try:
            selected_item.delete()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
