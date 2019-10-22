# cortadyno
Expose your dynamo tables as REST endpoints. Customer Isolation supported

```
from cortadyno.serializers import Serializer
from cortadyno.viewsets import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from cortadyno.schema import Schema

from your_app import model1
from your_app import serializer1, serializer2

class TodoListCreateAPIView(ListCreateAPIView):
    model = model1
    serializer = {
        'list': serializer1,
        'create': serializer2
    }
    index_name = '<your_index>' ## Optional: if you want isolation

    def get_index_value(self):
        ### This will be used to isolate the data or partition or index query value
        return "<>"

    def presave(self, payload=None, validated_data=None):
        # Update the necessary fields
        return payload

    def postsave(self, instance):
        # Do some actions if any
        return instance


class TodoRetreiveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):

    model = model1
    serializer = {
        'retrieve': serializer1,
        'update': serializer2
    }
    index_name = '<index_name>'
    lookup = '<your url lookup id>'  # Ex: /todo/<todo_id>/, todo_id is the lookup
    hard_delete = True  # delete will be allowed if True

    def validate(self, instance):
        # Validate before saving
        return <True|False>, <message|None>
```