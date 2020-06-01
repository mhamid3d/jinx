from .site import BaseJinxObject
from .stalk import Stalk
import mongoengine


class Twig(BaseJinxObject, mongoengine.Document):
    """
    Twig base class schema for MongoDB engine
    """

    meta = {
        'collection': 'twig'
    }

    # Required fields
    stem_uuid = mongoengine.UUIDField(required=True)

    # Optional fields
    task = mongoengine.StringField()
    transfix_map = mongoengine.StringField()
    comment = mongoengine.StringField()
    thumbnail = mongoengine.StringField()
    tags = mongoengine.DictField()

    def stalks(self):
        """
        Returns all stalk versions associated with this (self) twig.
        """
        return Stalk.objects(twig_uuid=self.uuid)

    def latest(self):
        """
        Returns the latest version stalk associated with this (self) twig.
        """
        stalks = self.stalks()
        version_dict = []
        for idx, stalk in enumerate(stalks):
            version_dict.append({'idx': idx, 'version': stalk.version})
        version_dict.sort(key=lambda i: i['version'])
        return stalks[version_dict[-1]['idx']]
