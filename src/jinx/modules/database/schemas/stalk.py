from .site import BaseJinxObject
from .leaf import Leaf
import mongoengine


class Stalk(BaseJinxObject, mongoengine.Document):
    """
    Stalk base class schema for MongoDB engine
    """

    meta = {
        'collection': 'stalk'
    }

    # Required fields
    comment = mongoengine.StringField(required=True)
    status = mongoengine.StringField(required=True)
    version = mongoengine.IntField(required=True)
    twig_uuid = mongoengine.UUIDField(required=True)
    state = mongoengine.StringField(required=True)  # 'complete', 'working', 'failed', eg: ip rendering means 'working'

    # Optional fields
    framerange = mongoengine.ListField()
    thumbnail = mongoengine.StringField()

    def leafs(self):
        """
        Returns all leaf objects associated with this (self) stalk.
        """
        return Leaf.objects(stalk_uuid=self.uuid)