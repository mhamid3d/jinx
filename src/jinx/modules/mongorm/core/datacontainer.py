from mongorm.core.dataobject import BaseJinxObject


class DataContainer(object):
    def __init__(self, interface, querySet=None):
        self._objects = []
        self._interface = interface
        if querySet:
            for object in querySet:
                self.append_object(object)
            self.sort("label")

    def append_object(self, object):

        assert isinstance(object, BaseJinxObject), "Object must be DataObject instance"

        if not object.interfaceName() == self._interface.name():
            raise TypeError("Data Object of type ({}) does not match with DataContainer type ({})".format(
                object.interfaceName(), self._interface.name()))

        self._objects.append(object)

    def remove_object(self, object):
        try:
            self._objects.remove(object)
        except ValueError as e:
            raise e("Object does not exist in DataContainer")

    def size(self):
        return len(self._objects)

    def hasObjects(self):
        return False if self.size() == 0 else True

    def __len__(self):
        return self.size()

    def __iter__(self):
        return iter(self._objects)

    def __getitem__(self, item):
        return self._objects[item]

    def get(self, object):
        assert isinstance(object, BaseJinxObject), "Object must be DataObject instance"

        for obj in self._objects:
            if object.getUuid() == obj.getUuid():
                return object

        raise ValueError("DataObject does not exist in DataContainer")

    def dataInterface(self):
        return self._interface

    def interfaceName(self):
        return self.dataInterface().name()

    def sort(self, sort_field, reverse=False):
        if sort_field not in [field.db_name() for field in self._interface.getFields()]:
            raise RuntimeError(
                "Invalid sort field ({}) for DataInterface ({})".format(sort_field, self.interfaceName()))
        self._sortField = sort_field
        self._objects = sorted(self._objects, key=lambda i: i.get(sort_field), reverse=reverse)