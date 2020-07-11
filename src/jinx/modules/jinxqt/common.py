import sys
import types
from qtpy import QtCore


ROLE_LAST = QtCore.Qt.UserRole + 1
ROLES_EDITSTATE = set([QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.CheckStateRole])


def registerDataRole(trackEdits=False):
    global ROLE_LAST
    global ROLES_EDITSTATE
    ROLE_LAST += 1
    if trackEdits:
        ROLES_EDITSTATE.add(ROLE_LAST)
    return ROLE_LAST


ROLE_NAME = registerDataRole(trackEdits=True)
ROLE_TYPE = registerDataRole(trackEdits=True)
ROLE_CATEGORY = registerDataRole(trackEdits=True)
ROLE_FILE_PATH = registerDataRole(trackEdits=True)
ROLE_SORT = registerDataRole()
ROLE_ERROR = registerDataRole()
ROLE_CANNOT_HIDE = registerDataRole()
ROLE_CHILDREN_POPULATED = registerDataRole()
ROLE_IS_SORTABLE = registerDataRole()
ROLE_POSSIBLE_VALUES = registerDataRole()
ROLE_SELECTION_STATE = registerDataRole()
ROLE_SELECTABLE = registerDataRole()
ROLE_FILTER = registerDataRole()
ROLE_IMAGE = registerDataRole()
ROLE_TREE_NODE = registerDataRole()
ROLE_CODE = registerDataRole()

# Column types
TYPE_STRING_SINGLELINE = "single-line string"
TYPE_STRING_MULTILINE = "multi-line string"
TYPE_INTEGER = "integer"
TYPE_UNSIGNED_INTEGER = "unsigned integer"
TYPE_FLOAT = "float"
TYPE_BOOLEAN = "boolean"
TYPE_DATE = "date"
TYPE_DATE_TIME = "datetime"
TYPE_FILE_PATH = "file path"
TYPE_JX_PATH = "dnpath"
TYPE_JX_RANGE = "dnrange"
TYPE_RESOLUTION = "resolution"
TYPE_IMAGE = "image"
TYPE_ENUM = "enumeration"
TYPE_LABEL = "label"
TYPE_ARRAY = "array"
TYPES = set(
    [TYPE_STRING_SINGLELINE, TYPE_STRING_MULTILINE, TYPE_INTEGER, TYPE_UNSIGNED_INTEGER, TYPE_FLOAT, TYPE_BOOLEAN,
     TYPE_DATE, TYPE_DATE_TIME, TYPE_FILE_PATH, TYPE_JX_PATH, TYPE_JX_RANGE, TYPE_RESOLUTION, TYPE_IMAGE, TYPE_ENUM,
     TYPE_LABEL])
TYPE_DEFAULT = TYPE_STRING_SINGLELINE


JINX_TO_JINXQT_TYPE_MAP = {
    'StringField': TYPE_STRING_SINGLELINE,
    'LineStringField': TYPE_STRING_SINGLELINE,
    'MultiLineStringField': TYPE_STRING_MULTILINE,
    'IntField': TYPE_INTEGER,
    'FloatField': TYPE_FLOAT,
    'BooleanField': TYPE_BOOLEAN,
    'DateField': TYPE_DATE,
    'DateTimeField': TYPE_DATE_TIME,
    'ImageField': TYPE_IMAGE,
    'UUIDField': TYPE_DEFAULT,
    'ObjectIdField': TYPE_DEFAULT,
    'ListField': TYPE_ARRAY
}
