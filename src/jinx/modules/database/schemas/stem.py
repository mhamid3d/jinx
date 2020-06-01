from .site import BaseJinxObject
import mongoengine


class Stem(BaseJinxObject, mongoengine.Document):
    """
    Stem base class schema for MongoDB engine
    """

    meta = {
        'collection': 'stem'
    }

    # Required fields
    directory = mongoengine.StringField(required=True)    # eg: 'GARB/asset/character', 'GARB/aa_seq/aa1920'
    type = mongoengine.StringField(required=True)       # eg: 'sequence', 'shot', 'asset'
    production = mongoengine.BooleanField(required=True) # Set false for testing / rnd stems

    # Optional fields
    parent_uuid = mongoengine.StringField()
    framerange = mongoengine.ListField()
    thumbnail = mongoengine.StringField()