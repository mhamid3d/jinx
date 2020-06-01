from .site import BaseJinxObject
import mongoengine


class Seed(BaseJinxObject, mongoengine.Document):
    """
    Seed base class schema for MongoDB engine
    """

    meta = {
        'collection': 'seed'
    }

    # Required fields
    pod_stalk_uuid = mongoengine.UUIDField()
    seed_stalk_uuid = mongoengine.UUIDField()
