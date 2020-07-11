from qtpy import QtCore
from jinxqt import common


class ModelItem(object):
    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
    DEFAULT_DATA = {
        common.ROLE_IS_SORTABLE: True,
    }

    @property
    def model(self):
        return self._model

    @property
    def uuid(self):
        return self._uuid

    @property
    def dataObject(self):
        return self._dataObject

    @property
    def dataType(self):
        return self._dataType

    def __init__(self, columnCount, uuid=None, dataObject=None, itemData=None, dataType=None):
        self._model = None
        self._itemData = itemData if itemData else [None] * columnCount
        self._itemDataLen = columnCount
        self._flags = [None] * columnCount
        self._isDeletable = False
        self._uuid = uuid
        self._dataType = dataType
        self._dataObject = dataObject
        self._parentItem = None
        self._childList = []
        self._childListSize = 0
        self._childLookup = {} # {item: index}
        self._totalChildCount = -1

    def setModel(self, model, columnCountDelta=None):
        if columnCountDelta is None:
            columnCountDelta = (model.columnCount() - self._itemDataLen) if model else 0

        self._model = model

        if columnCountDelta > 0:
            self.insertColumns(self._itemDataLen, columnCountDelta)
        elif columnCountDelta < 0:
            self.removeColumns(self._itemDataLen + columnCountDelta, columnCountDelta * -1)

        for child in self._childList:
            child.setModel(model, columnCountDelta)

    def setUuid(self, uuid):
        self._uuid = uuid

    def setDataObject(self, dataObject):
        self._dataObject = dataObject

    def setDataType(self, dataType):
        self._dataType = dataType

    def __len__(self):
        return self._itemDataLen

    def __str__(self):
        return str([str(self.data(i) for i in range(self._itemDataLen))])

    def __repr__(self):
        return str(self)

    def copyData(self, otherItem):
        for column in range(len(otherItem)):
            for role in [QtCore.Qt.DisplayRole, QtCore.Qt.DecorationRole, QtCore.Qt.BackgroundRole,
                         QtCore.Qt.ForegroundRole, common.ROLE_CATEGORY, common.ROLE_FILE_PATH]:
                otherItem.setDataObject(self._dataObject)
                otherItem.setUuid(self._uuid)

    def copyFlags(self, otherItem):
        for column in range(len(otherItem)):
            otherItem.setFlags(self.flags(column=column), column=column)

    def getStyleData(self, column=0):
        coldata = self._itemData[column]

        err = None
        try:
            err = coldata[common.ROLE_ERROR]
        except (IndexError, KeyError, TypeError):
            pass

        bg = None
        try:
            bg = coldata[QtCore.Qt.BackgroundRole]
        except (IndexError, KeyError, TypeError):
            pass

        fg = None
        try:
            fg = coldata[QtCore.Qt.ForegroundRole]
        except (IndexError, KeyError, TypeError):
            pass

        if err is None:
            try:
                err = self.DEFAULT_DATA[common.ROLE_ERROR]
            except KeyError:
                pass

        if bg is None:
            try:
                bg = self.DEFAULT_DATA[QtCore.Qt.BackgroundRole]
            except KeyError:
                pass

        if fg is None:
            try:
                fg = self.DEFAULT_DATA[QtCore.Qt.ForegroundRole]
            except KeyError:
                pass

        return err, bg, fg

    def data(self, column=0, role=QtCore.Qt.DisplayRole):
        try:
            return self._itemData[column][role]
        except(IndexError, KeyError, TypeError):
            pass
        try:
            return self.DEFAULT_DATA[role]
        except KeyError:
            pass

        if role == QtCore.Qt.EditRole:
            return self.data(column, QtCore.Qt.DisplayRole)

        return None

    def data_role_tree_node(self, column=0):
        return self.data(column, common.ROLE_TREE_NODE)

    def setData(self, value, column=0, role=QtCore.Qt.DisplayRole):
        if self._itemData[column] is None:
            self._itemData[column] = {}
        self._itemData[column][role] = value
        return True

    def setDataRoleTreeNode(self, value, column):
        return self.setData(value, column, common.ROLE_TREE_NODE)

    def flags(self, column=0):
        try:
            flags = self._flags[column]
            if flags is not None:
                return flags
        except IndexError:
            pass

        return self.DEFAULT_FLAGS

    def setFlags(self, flags, column=0):
        self._flags[column] = flags

    def insertColumns(self, position, count):
        self._itemData[position:position] = [None] * count
        self._itemDataLen += count
        self._flags[position:position] = [None] * count

        for child in self._childList:
            child.insertColumns(position, count)

    def removeColumns(self, position, count):
        del self._itemData[position:position + count]
        self._itemDataLen -= count
        del self._flags[position:position + count]

        for child in self._childList:
            child.removeColumns(position, count)

    def parent(self):
        return self._parentItem

    def setParent(self, parent):
        self._parentItem = parent

    def child(self, position):
        try:
            return self._childList[position]
        except IndexError:
            return None

    def children(self):
        return self._childList

    def childPosition(self, childItem):
        try:
            return self._childLookup[childItem]
        except KeyError:
            return -1

    def hasChildren(self):
        if self._childList:
            return True
        return False

    def hasNoChildren(self):
        return not self._childList

    def childCount(self):
        return self._childListSize

    def totalChildCount(self):
        return self._totalChildCount

    def setTotalChildCount(self, totalChildCount):
        self._totalChildCount = totalChildCount

    def insertChildren(self, position, childItems):
        if not 0 <= position <= self._childListSize:
            return False
        if not childItems:
            return True

        count = 0
        for childItem in childItems:
            assert childItem not in self._childLookup

            for descendant in childItem.iterTree(includeRoot=True):
                descendant.setModel(self._model)

            childItem.setParent(self)

            count += 1

        if childItems:
            self._childList[position:position] = childItems

            for i, childItem in enumerate(self._childList[position:]):
                self._childLookup[childItem] = position + i

            self._childListSize += len(childItems)

        if self._model:
            self._model.addToTotalItemCount(count)
        return True

    def appendChildren(self, childItems):
        return self.insertChildren(self._childListSize, childItems)

    def insertChild(self, position, childItem):
        return self.insertChildren(position, [childItem])

    def appendChild(self, childItem):
        return self.insertChildren(self._childListSize, [childItem])

    def removeChildren(self, position, count):
        if position == 0 and count == self._childListSize:
            return self.removeAllChildren()
        childItems = self._childList[position:position + count]
        if len(childItems) != count:
            return False

        for childItem in childItems:
            for descendant in childItem.iterTree(includeRoot=True):
                descendant.setModel(None)
            childItem.setParent(None)
            del self._childLookup[childItem]

        del self._childList[position:position + count]
        self._childListSize -= count

        for i, childItem in enumerate(self._childList[position:]):
            self._childLookup[childItem] = position + i

        return True

    def removeChild(self, position):
        return self.removeChildren(position, 1)

    def removeAllChildren(self):
        for descendant in self.iterTree():
            descendant.setModel(None)
        for child in self._childList:
            child.setParent(None)
        self._childList = []
        self._childLookup = {}
        self._childListSize = 0
        return True

    def iterChildren(self):
        for child in self._childList:
            yield child

    def iterTree(self, includeRoot=False):
        if includeRoot:
            itemQueue = [self]
            if self.hasNoChildren():
                return itemQueue
        else:
            if self.hasNoChildren():
                return []
            itemQueue = self._childList[:]

        current = 0
        while current < len(itemQueue):
            itemQueue.extend(itemQueue[current].children())
            current += 1

        return itemQueue

    def sortTree(self, cmp=None):
        self._childList.sort(cmp=cmp)
        for i, childItem in enumerate(self._childList):
            self._childLookup[childItem] = i
        for childItem in self._childList:
            childItem.sortTree(cmp=cmp)

    def _getFlag(self, column, flag):
        return bool(self.flags(column) & flag)

    def _setFlag(self, column, flag, enabled):
        currFlags = self.flags(column)
        if enabled:
            self._flags[column] = currFlags | flag
        else:
            self._flags[column] = currFlags & ~flag

    def isEnabled(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsEnabled)

    def setEnabled(self, enabled, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsEnabled, enabled)

    def isSelectable(self, colunm=0):
        return self._getFlag(colunm, QtCore.Qt.ItemIsSelectable)

    def setSelectable(self, selectable, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsSelectable, selectable)

    def isEditable(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsEditable)

    def setEditable(self, editable, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsEditable, editable)

    def isCheckable(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsUserCheckable)

    def setCheckable(self, checkable, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsUserCheckable, checkable)
        if checkable and self.checkState(column) is None:
            self.setCheckState(QtCore.Qt.Unchecked, column)

    def isTristate(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsTristate)

    def setTristate(self, tristate, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsTristate, tristate)

    def setCheckState(self, checkState, column=0):
        self.setData(checkState, column, QtCore.Qt.CheckStateRole)

    def checkState(self, column=0):
        return self.data(column, QtCore.Qt.CheckStateRole)

    def isDragEnabled(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsDragEnabled)

    def setDragEnabled(self, dragEnabled, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsDragEnabled, dragEnabled)

    def isDropEnabled(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsDropEnabled)

    def setDropEnabled(self, dropEnabled, column=0):
        self._setFlag(column, QtCore.Qt.ItemIsDropEnabled, dropEnabled)

    def isDeletable(self):
        return self._isDeletable

    def setDeletable(self, deletable):
        self._isDeletable = deletable