"""
DataFilter base class
"""


class DataFilter(object):
    def __init__(self):
        self._filter = None
        self._interface = None
        self._querySet = None
        self._filterStrings = {}
        self._objects = []
        self._omitDeleted = True
        self._omitArchived = True

    def filter(self):
        return self._filter

    def querySet(self):
        self._querySet = self._interface.objectPrototype.objects(**self._filterStrings)
        return self._querySet

    def count(self):
        return len(self.objects())

    def filterStrings(self):
        return self._filterStrings

    def overrideFilterStrings(self, filterStrings):
        self._filterStrings = filterStrings

    def interface(self):
        return self._interface

    def setInterface(self, interface):
        self._interface = interface

    def search(self, *args, **kwargs):
        datainterface = args[0]

        if not self.interface() or not self.interface().name() == datainterface.name():
            self.setInterface(datainterface)
            self._filterStrings = {}

        for k, v in kwargs.items():
            self._filterStrings[k] = v

        return True

    def objects(self):
        self._objects = []

        for object in self.querySet():
            if object.get("deleted") and self.getOmitDeleted():
                continue
            elif object.get("archived") and self.getOmitArchived():
                continue

            self._objects.append(object)

        return self._objects

    def getOmitDeleted(self):
        return bool(self._omitDeleted)

    def getOmitArchived(self):
        return bool(self._omitArchived)

    def omitDeleted(self, value):
        self._omitDeleted = bool(value)

    def omitArchived(self, value):
        self._omitArchived = bool(value)

    def sort(self, sort):
        return None

    def getSort(self):
        return None
