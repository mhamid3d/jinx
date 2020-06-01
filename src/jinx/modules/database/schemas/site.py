import mongoengine
import uuid


class BaseJinxObject(object):
    """
    Site base class schema for MongoDB engine.
    """

    # Required fields
    _id = mongoengine.UUIDField(required=True, primary_key=True)
    path = mongoengine.StringField(required=True)
    uuid = mongoengine.StringField(required=True)
    label = mongoengine.StringField(required=True)
    created = mongoengine.DateTimeField(required=True)
    modified = mongoengine.DateTimeField(required=True)
    job = mongoengine.StringField(required=True)
    created_by = mongoengine.StringField(required=True)

    def generate_id(self):
        self._id = uuid.uuid4()
        self.uuid = self._id.__str__()
        return

    def get_type(self):
        return str(self.__class__.__name__)
