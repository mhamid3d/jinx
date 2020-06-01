from .site import BaseJinxObject
import mongoengine


class Leaf(BaseJinxObject, mongoengine.Document):
    """
    Leaf base class schema for MongoDB engine
    """

    meta = {
        'collection': 'leaf'
    }

    # Required fields
    stalk_uuid = mongoengine.UUIDField(required=True)
    format = mongoengine.StringField(required=True)

    # Optional fields
    resolution = mongoengine.ListField()
    framerange = mongoengine.ListField()
    thumbnail = mongoengine.StringField()