from mongorm import interfaces
from mongorm.core.datacontainer import DataContainer
from mongoengine.errors import MultipleObjectsReturned
import re


DATA_OBJECT_MAP = {
    'job': interfaces.Job,
    'stem': interfaces.Stem,
    'twig': interfaces.Twig,
    'stalk': interfaces.Stalk,
    'leaf': interfaces.Leaf,
    'seed': interfaces.Seed
}


class DataInterface(object):
    """
    This is orm representation of a Collection in MongoDB
    """
    def __init__(self, db_name):
        self._db_name = db_name
        self._object_prototype = DATA_OBJECT_MAP[db_name]
        self._name = db_name.replace(db_name[0], db_name[0].upper())
        self._cacheSizeLimit = 100000

    def __repr__(self):
        reprstring = object.__repr__(self)
        reprstring = re.sub("object at", "object ({}) at".format(self.name()), reprstring)
        reprstring = reprstring.replace("mongorm.core.datainterface..", "")

        return reprstring

    def __getitem__(self, item):
        return self.getField(item)

    def all(self, dataFilter):
        """Return all objects from filter"""
        datacontainer = DataContainer(self, querySet=dataFilter.querySet())
        return datacontainer

    def one(self, dataFilter):
        """Implied that there is only one result. Will return that object."""

        objects = self.all(dataFilter)

        try:
            assert len(objects) == 1
        except AssertionError:
            raise MultipleObjectsReturned

        return objects[0]

    @property
    def objectPrototype(self):
        return self._object_prototype

    def cacheSizeLimit(self):
        """Return cache size limit"""
        return self._cacheSizeLimit

    def clearDataCache(self):
        """Clear data cache"""
        return

    def count(self, dataFilter):
        """Get count of all objects of this DataInterface type"""
        return len(self.all())

    def get(self, uuid):
        """Get Data object that matches uuid value of this DataInterface type"""
        return

    def name(self):
        return self._name

    def getFields(self):
        return self.objectPrototype().getFields()

    def getField(self, field):
        return self.objectPrototype().getField(field)