from jinxicon import icon_paths
import mongoengine
import uuid
import re


class BaseJinxObject(object):
    """
    Site base class schema for MongoDB engine.
    """

    INTERFACE_STRING = ""

    _id = mongoengine.UUIDField(required=True, primary_key=True, visible=False, dispName="_ID")
    uuid = mongoengine.StringField(required=True, dispName="UUID", visible=True, icon=icon_paths.ICON_FINGERPRINT_SML)
    path = mongoengine.StringField(required=True, dispName="Path", icon=icon_paths.ICON_LOCATION_SML)
    label = mongoengine.StringField(required=True, dispName="Name")
    created = mongoengine.DateTimeField(required=True, dispName="Created", icon=icon_paths.ICON_CLOCK_SML)
    job = mongoengine.StringField(required=True, dispName="Job", visible=False)
    created_by = mongoengine.StringField(required=True, dispName="Owner", icon=icon_paths.ICON_USER_SML)
    modified = mongoengine.DateTimeField(required=True, dispName="Modified", icon=icon_paths.ICON_CLOCK_SML)
    deleted = mongoengine.BooleanField(required=True, dispName="Deleted", default=False, visible=False)
    archived = mongoengine.BooleanField(required=True, dispName="Archived", default=False, visible=False)

    def __init__(self, *args, **kwargs):
        super(BaseJinxObject, self).__init__(*args, **kwargs)

    def __repr__(self):
        reprstring = object.__repr__(self)
        reprstring = re.sub("object", "object [{}]".format(self.label), reprstring)
        reprstring = reprstring.replace("mongorm.interfaces.", "")

        return reprstring

    def interfaceName(self):
        return self.dataInterface().name()

    def __str__(self):
        return "{} object [{}]".format(self.interfaceName(), self.label)

    def get(self, item):
        return self.getDataDict().get(item)

    def _generate_id(self):
        """
        Generate unique uuid for uuid and _id fields
        :return:
        """
        self._id = uuid.uuid4()
        self.uuid = self._id.__str__()
        return self.uuid

    @classmethod
    def dataInterface(cls):
        from mongorm.core.datainterface import DataInterface
        return DataInterface(cls.INTERFACE_STRING)

    def getFields(self):
        return self._fields.values()

    def getField(self, field):
        for field_item in self.getFields():
            if field_item.db_name() == field:
                return field_item

        raise ValueError("Invalid field [{}] for data type: {}".format(field, self.dataInterface().name()))

    def getDataDict(self):
        return {k: v for k, v in [(field.db_name(), self[field.db_name()]) for field in self.getFields()]}

    def getUuid(self):
        return self.uuid

    def getDataType(self, field):
        return self.getField(field).dataType()

    def children(self, *args, **kwargs):
        # Reimplement - the other interface children in sub-class
        interface = self.interfaceName()
        if interface == "Leaf":
            return None

    def child(self, index):
        children = self.children()
        if not children:
            return None
        return children[index]

    def childCount(self):
        children = self.children()
        if not children:
            return 0
        return len(children)

    def parent(self, *args, **kwargs):
        # Reimplement - the other interface children in sub-class
        interface = self.interfaceName()
        if interface == "Job":
            return None

    def siblings(self):
        raise NotImplementedError

    def pprint(self):
        import pprint
        pprint.pprint(self.getDataDict())