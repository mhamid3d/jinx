# Local imports
import dndeprecate
import wizqt
from wizqt import common

# PyQt imports
from qtswitch import QtCore

from wizmo.wizutil import toUtf8

from .. import _APITRACKER


# ----------------------------------------------------------------------------------------------------------------------------------------------------
# CLASSES
# ----------------------------------------------------------------------------------------------------------------------------------------------------

class ModelItem(object):
    """Represents a row in a wizqt :class:`~wizqt.modelview.model.Model`.

    The Model has a root item (:py:attr:`~wizqt.modelview.model.Model.rootItem`),
    which all other model items are parented under.
    Populating the model with ModelItems is done in the data source.
    """
    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
    DEFAULT_DATA = {
        common.ROLE_IS_SORTABLE: True,
    }

    # properties
    @property
    def model(self):
        return self._model

    @property
    def uniqueId(self):
        return self._uniqueId

    @property
    def dataObject(self):
        return self._dataObject

    @property
    def dataType(self):
        return self._dataType

    def __init__(self, columnCount, uniqueId=None, dataObject=None, itemData=None, dataType=None):
        # pointer to model, remains None until added to a model
        self._model = None

        # internal storage of data
        # list in column order containing dictionaries for the data
        # corresponding to each role { [ {<role>: <data>}, ...]
        if itemData is not None:
            self._itemData = itemData
        else:
            self._itemData = [None] * columnCount
        self._itemDataLen = columnCount

        # flags, list in column order
        self._flags = [None] * columnCount

        # additional flags for entire item
        self._isDeletable = False

        # unique persistent identifier (for example: UUID, file path, etc)
        self._uniqueId = uniqueId

        # arbitrary string describing the data
        self._dataType = dataType

        # store a data object of any arbitrary type (for example, an
        # Ivy data record) best to store this on the item itself
        # rather than in data(), since PySide throws segfaults
        # converting Ivy objects from QVariants
        self._dataObject = dataObject

        # edit data
        self._editBitMask = 0
        self._origData = [None] * columnCount
        self._origDataSet = False
        self._origParentId = None
        self._origParentSet = False

        # store pointers to parent and children
        self.__parentItem = None
        self.__childList = []
        self.__childListSize = 0
        self.__childLookup = {}  # dictionary of { item: index number } for fast lookup

        # for lazy loading in batches (new batches are fetched when user scrolls down in the view)
        self.__totalChildCount = -1  # -1 indicates that the item has not been populated with children yet

    def setModel(self, model, columnCountDelta=None):
        if columnCountDelta is None:
            columnCountDelta = (model.columnCount() - self._itemDataLen) if model else 0

        self._model = model

        # update column count
        if columnCountDelta > 0:
            self.insertColumns(self._itemDataLen, columnCountDelta)
        elif columnCountDelta < 0:
            self.removeColumns(self._itemDataLen + columnCountDelta, columnCountDelta * -1)

        # set model on children too
        for child in self.__childList:
            child.setModel(model, columnCountDelta)

    def setUniqueId(self, uniqueId):
        self._uniqueId = uniqueId

    def setDataObject(self, dataObject):
        self._dataObject = dataObject

    @_APITRACKER.track_calls(-1)
    def setDataType(self, dataType):
        dndeprecate.warn("This method is deprecated. Please use setData(dataType, role=wizqt.ROLE_TYPE) instead.")
        self._dataType = dataType

    def __len__(self):
        # Use the stored length rather than recalculating it
        return self._itemDataLen

    def __str__(self):
        # Uncomment the next line for extra debugging, tracing or
        # profiling info. I didn't replace the current return in the
        # production code because I'm unused where this might be used
        # and what might expect the existing string format.
        # return str( self.data( role = wizqt.ROLE_TYPE ) ) + ":[%s]" % ", ".join( [str( toUtf8( self.data( i ) ) ) for i in xrange( self._itemDataLen )] )
        # return str(self._uniqueId) + " " + str(self.data(0))
        return "[%s]" % ", ".join([str(toUtf8(self.data(i))) for i in xrange(self._itemDataLen)])

    def __repr__(self):
        return str(self)

    def copyData(self, otherItem):
        # FIXME: is this everything we need?
        for column in xrange(len(otherItem)):
            for role in [QtCore.Qt.DisplayRole, QtCore.Qt.DecorationRole, QtCore.Qt.BackgroundRole,
                         QtCore.Qt.ForegroundRole, wizqt.ROLE_CATEGORY, wizqt.ROLE_FILE_PATH]:
                otherItem.setData(self.data(column=column, role=role), column=column, role=role)

        # copy data item and object
        otherItem.setDataObject(self._dataObject)
        otherItem.setUniqueId(self._uniqueId)

    def copyFlags(self, otherItem):
        otherItem.setDeletable(self.isDeletable())
        for column in xrange(len(otherItem)):
            otherItem.setFlags(self.flags(column=column), column=column)

    def getStyleData(self, column=0):
        # Note: this is a badly named helper function to allow
        # delegate::initStyleOption calls to reduce the number of
        # model_item.data() calls they make by 3. This is part of
        # speeding up ivybrowser. Do not try to make subfunctions and
        # have this call them because that will slow things down.
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
        except (IndexError, KeyError, TypeError):
            pass
        try:
            return self.DEFAULT_DATA[role]
        except KeyError:
            pass

        # use display role for edit role if empty
        if role == QtCore.Qt.EditRole:
            return self.data(column, QtCore.Qt.DisplayRole)

        return None

    def data_role_tree_node(self, column=0):
        # A helper short-cut to get the ROLE_TREE_NODE data out
        # without needing to directly import
        # wizqt.common.ROLE_TREE_NODE, most useful for inherited
        # objects.
        return self.data(column, common.ROLE_TREE_NODE)

    def setData(self, value, column=0, role=QtCore.Qt.DisplayRole):
        if self._itemData[column] is None:
            self._itemData[column] = {}
        # NOTE: the roles are ints, would and array of arrays be better. The trouble is its sparse and all sorts of rules might exist
        self._itemData[column][role] = value
        return True

    def setDataRoleTreeNode(self, value, column):
        """A short-cut wrapper for setData(index, value,
        wizqt.common.ROLE_TREE_NODE) for use by inheriting objects to
        avoid the need to import the ROLE_TREE_NODE constant.
        """
        return self.setData(value, column, common.ROLE_TREE_NODE)

    def flags(self, column=0):
        try:
            flags = self._flags[column]
            if flags is not None:
                return flags
        except IndexError:
            pass
        # use base defaults
        return self.DEFAULT_FLAGS

    def setFlags(self, flags, column=0):
        self._flags[column] = flags

    def insertColumns(self, position, count):
        self._itemData[position:position] = [None] * count
        self._itemDataLen += count
        self._origData[position:position] = [None] * count
        self._flags[position:position] = [None] * count

        # insert columns on children too
        for child in self.__childList:
            child.insertColumns(position, count)

    def removeColumns(self, position, count):
        del self._itemData[position:position + count]
        self._itemDataLen -= count
        del self._origData[position:position + count]
        del self._flags[position:position + count]

        # remove columns from children too
        for child in self.__childList:
            child.removeColumns(position, count)

    def parent(self):
        return self.__parentItem

    def setParent(self, parent):
        self.__parentItem = parent

    def child(self, position):
        try:
            return self.__childList[position]
        except IndexError:
            return None

    def children(self):
        return self.__childList

    def childPosition(self, childItem):
        try:
            return self.__childLookup[childItem]
        except KeyError:
            return -1

    def hasChildren(self):
        if self.__childList:
            return True
        return False

    def hasNoChildren(self):
        return not self.__childList

    def childCount(self):
        return self.__childListSize

    def totalChildCount(self):
        return self.__totalChildCount

    def setTotalChildCount(self, totalChildCount):
        self.__totalChildCount = totalChildCount

    def insertChildren(self, position, childItems):
        if not 0 <= position <= self.__childListSize:
            return False
        if not childItems:
            return True

        count = 0
        for childItem in childItems:
            # TODO: why?
            assert childItem not in self.__childLookup

            for descendant in childItem.iterTree(includeRoot=True):
                descendant.setModel(self._model)

            # set parent on the child
            childItem.setParent(self)

            count += 1

        # insert the children, if any
        if childItems:
            self.__childList[position:position] = childItems

            # update any affected child indexes and length
            for i, childItem in enumerate(self.__childList[position:]):
                self.__childLookup[childItem] = position + i

            self.__childListSize += len(childItems)

        # Part of the fix for cases when there isn't a model yet
        if (self._model):
            self._model.addToTotalItemCount(count)
        return True

    def appendChildren(self, childItems):
        return self.insertChildren(self.__childListSize, childItems)

    def insertChild(self, position, childItem):
        return self.insertChildren(position, [childItem])

    def appendChild(self, childItem):
        return self.insertChildren(self.__childListSize, [childItem])

    def removeChildren(self, position, count):
        if position == 0 and count == self.__childListSize:
            return self.removeAllChildren()
        childItems = self.__childList[position:position + count]
        if len(childItems) != count:
            return False

        for childItem in childItems:

            # clear the model on child and all descendants
            for descendant in childItem.iterTree(includeRoot=True):
                descendant.setModel(None)

            # clear parent on the child
            childItem.setParent(None)
            del self.__childLookup[childItem]

        # remove the children
        del self.__childList[position:position + count]
        self.__childListSize -= count

        # update any affected child indexes
        for i, childItem in enumerate(self.__childList[position:]):
            self.__childLookup[childItem] = position + i

        return True

    def removeChild(self, position):
        return self.removeChildren(position, 1)

    def removeAllChildren(self):
        # clear the model on all descendents
        for descendant in self.iterTree():
            descendant.setModel(None)
        # clear parent on children
        for child in self.__childList:
            child.setParent(None)
        self.__childList = []
        self.__childLookup = {}
        self.__childListSize = 0
        return True

    def iterChildren(self):
        for child in self.__childList:
            yield child

    def iterTree(self, includeRoot=False):
        """
        Iterate over all descendants in breadth-first order.

        This returns a list. It does not yield.
        """
        # Reworked to remove pop() because it is linear in list each time
        if includeRoot:
            itemQueue = [self]
            if self.hasNoChildren():
                return itemQueue
        else:
            if self.hasNoChildren():
                return []
            itemQueue = self.__childList[:]

        current = 0
        while current < len(itemQueue):
            itemQueue.extend(itemQueue[current].children())
            current += 1

        return itemQueue

    # ------------------------------------------------------------------------------------------------------------------------------
    # EDIT METHODS
    # ------------------------------------------------------------------------------------------------------------------------------
    def editBitMask(self, column=None):
        """
        Return the editBitMask for the given column, if specified, otherwise for the entire item.
        The editBitMask is an OR'd bitmask of all possible edits on the item: INSERT, DELETE, UPDATE, and MOVE.
        Only UPDATE edits are column-specific. INSERT, DELETE, MOVE edits apply to the whole item.
        """
        if not self._editBitMask & (
                common.EDITBITMASK_INSERT | common.EDITBITMASK_DELETE | common.EDITBITMASK_ARCHIVE | common.EDITBITMASK_DISABLE | common.EDITBITMASK_REVIVE | common.EDITBITMASK_ENABLE | common.EDITBITMASK_UPDATE | common.EDITBITMASK_MOVE):
            # no valid edits
            return 0

        editBitMask = 0

        # insert edits can't co-exist with any other type
        if self._editBitMask & common.EDITBITMASK_INSERT:
            return common.EDITBITMASK_INSERT

        # delete and revive edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DELETE:
            editBitMask |= common.EDITBITMASK_DELETE
        elif self._editBitMask & common.EDITBITMASK_REVIVE:
            editBitMask |= common.EDITBITMASK_REVIVE

        # delete and enable edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DELETE:
            editBitMask |= common.EDITBITMASK_DELETE
        elif self._editBitMask & common.EDITBITMASK_ENABLE:
            editBitMask |= common.EDITBITMASK_ENABLE

        # disable and enable edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DISABLE:
            editBitMask |= common.EDITBITMASK_DISABLE
        elif self._editBitMask & common.EDITBITMASK_ENABLE:
            editBitMask |= common.EDITBITMASK_ENABLE

        # archive and enable edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_ARCHIVE:
            editBitMask |= common.EDITBITMASK_ARCHIVE
        elif self._editBitMask & common.EDITBITMASK_ENABLE:
            editBitMask |= common.EDITBITMASK_ENABLE

        # archive and revive edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_ARCHIVE:
            editBitMask |= common.EDITBITMASK_ARCHIVE
        elif self._editBitMask & common.EDITBITMASK_REVIVE:
            editBitMask |= common.EDITBITMASK_REVIVE

        # disable and revive edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DISABLE:
            editBitMask |= common.EDITBITMASK_DISABLE
        elif self._editBitMask & common.EDITBITMASK_REVIVE:
            editBitMask |= common.EDITBITMASK_REVIVE

        if self._editBitMask & common.EDITBITMASK_MOVE:
            origParentId = self._origParentId
            currParentId = self.parent().uniqueId if self.parent() else None
            if origParentId != currParentId:
                editBitMask |= common.EDITBITMASK_MOVE

        if self._editBitMask & common.EDITBITMASK_UPDATE:
            # update edits are the only type that can be column specific
            if column is None:
                editBitMask |= common.EDITBITMASK_UPDATE
            else:
                # check if there is an update edit on this particular column
                for role in self._origData[column]:
                    origData = self._origData[column][role]
                    currData = self.data(column, role)
                    if origData != currData:
                        editBitMask |= common.EDITBITMASK_UPDATE
                        break
        return editBitMask

    def addEdit(self, editBitMask):
        """
        Adds an edit of the specified type to the ModelItem.
        Don't ever call this method directly, it should only be called by Model when the model is in edit mode.
        """
        # OR the new bitmask with the existing edits
        editBitMaskInt = int(editBitMask)
        self._editBitMask |= editBitMaskInt

        # delete and revive edits are mutually exclusive
        if editBitMaskInt & common.EDITBITMASK_DELETE:
            self._editBitMask &= ~common.EDITBITMASK_REVIVE  # unset revive bit
        elif editBitMaskInt & common.EDITBITMASK_REVIVE:
            self._editBitMask &= ~common.EDITBITMASK_DELETE  # unset delete bit

        # delete and enable edits are mutually exclusive
        if editBitMaskInt & common.EDITBITMASK_DELETE:
            self._editBitMask &= ~common.EDITBITMASK_ENABLE  # unset enable bit
        elif editBitMaskInt & common.EDITBITMASK_ENABLE:
            self._editBitMask &= ~common.EDITBITMASK_DELETE  # unset delete bit

        # archive and revive edits are mutually exclusive
        if editBitMaskInt & common.EDITBITMASK_ARCHIVE:
            self._editBitMask &= ~common.EDITBITMASK_REVIVE  # unset revive bit
        elif editBitMaskInt & common.EDITBITMASK_REVIVE:
            self._editBitMask &= ~common.EDITBITMASK_ARCHIVE  # unset archive bit

        # archive and enable edits are mutually exclusive
        if editBitMaskInt & common.EDITBITMASK_ARCHIVE:
            self._editBitMask &= ~common.EDITBITMASK_ENABLE  # unset enable bit
        elif editBitMaskInt & common.EDITBITMASK_ENABLE:
            self._editBitMask &= ~common.EDITBITMASK_ARCHIVE  # unset archive bit

        # disable and revive edits are mutually exclusive
        if editBitMaskInt & common.EDITBITMASK_DISABLE:
            self._editBitMask &= ~common.EDITBITMASK_REVIVE  # unset revive bit
        elif editBitMaskInt & common.EDITBITMASK_REVIVE:
            self._editBitMask &= ~common.EDITBITMASK_DISABLE  # unset disable bit

        # disable and enable edits are mutually exclusive
        if editBitMaskInt & common.EDITBITMASK_DISABLE:
            self._editBitMask &= ~common.EDITBITMASK_ENABLE  # unset enable bit
        elif editBitMaskInt & common.EDITBITMASK_ENABLE:
            self._editBitMask &= ~common.EDITBITMASK_DISABLE  # unset disable bit

        # for move edits, store the current parent id as the original parent
        if editBitMaskInt & common.EDITBITMASK_MOVE and not self._origParentSet:
            if self.parent():
                self._origParentId = self.parent().uniqueId
            self._origParentSet = True

        # for update edits, store the current data as the original data
        if editBitMaskInt & common.EDITBITMASK_UPDATE and not self._origDataSet:
            for column in xrange(len(self)):
                self._origData[column] = {}
                for role in common.ROLES_EDITSTATE:
                    self._origData[column][role] = self.data(column, role)
            self._origDataSet = True

    def clearEdit(self):
        # erase all edit information
        self._editBitMask = 0
        #		self._origData = [None] * len( self )
        self._origData = [None] * self._itemDataLen
        self._origDataSet = False
        self._origParentId = None
        self._origParentSet = False

    def getEdit(self):
        if not self._editBitMask & (
                common.EDITBITMASK_INSERT | common.EDITBITMASK_DELETE | common.EDITBITMASK_ARCHIVE | common.EDITBITMASK_DISABLE | common.EDITBITMASK_ENABLE | common.EDITBITMASK_REVIVE | common.EDITBITMASK_UPDATE | common.EDITBITMASK_MOVE):
            # no valid edits
            return None

        assert self._uniqueId
        edit = {"itemId": self._uniqueId, "type": 0}
        if self._editBitMask & common.EDITBITMASK_INSERT:
            edit["type"] = common.EDITBITMASK_INSERT

            # parent id
            parent = self.parent()
            if parent and parent.parent():  # if not child of root
                assert parent.uniqueId
                edit["parentId"] = parent.uniqueId

            # column data
            edit["columnData"] = {}
            for column in xrange(len(self)):
                fieldName = self._model.headerData(column, QtCore.Qt.Horizontal,
                                                   common.ROLE_NAME)  # internal column name
                assert fieldName is not None
                if self._itemData[column]:
                    edit["columnData"][fieldName] = {}
                    for role in self._itemData[column]:
                        value = self.data(column, role)
                        edit["columnData"][fieldName][role] = value

            # no other edits can co-exist with INSERT edits
            return edit

        # delete and revive edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DELETE:
            edit["type"] |= common.EDITBITMASK_DELETE
        elif self._editBitMask & common.EDITBITMASK_REVIVE:
            edit["type"] |= common.EDITBITMASK_REVIVE

        # archive and revive edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_ARCHIVE:
            edit["type"] = common.EDITBITMASK_ARCHIVE
        elif self._editBitMask & common.EDITBITMASK_REVIVE:
            edit["type"] |= common.EDITBITMASK_REVIVE

        # disable and revive edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DISABLE:
            edit["type"] = common.EDITBITMASK_DISABLE
        elif self._editBitMask & common.EDITBITMASK_REVIVE:
            edit["type"] |= common.EDITBITMASK_REVIVE

        # delete and enable edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DELETE:
            edit["type"] |= common.EDITBITMASK_DELETE
        elif self._editBitMask & common.EDITBITMASK_ENABLE:
            edit["type"] |= common.EDITBITMASK_ENABLE

        # archive and enable edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_ARCHIVE:
            edit["type"] = common.EDITBITMASK_ARCHIVE
        elif self._editBitMask & common.EDITBITMASK_ENABLE:
            edit["type"] |= common.EDITBITMASK_ENABLE

        # disable and enable edits are mutually exclusive
        if self._editBitMask & common.EDITBITMASK_DISABLE:
            edit["type"] = common.EDITBITMASK_DISABLE
        elif self._editBitMask & common.EDITBITMASK_ENABLE:
            edit["type"] |= common.EDITBITMASK_ENABLE

        if self._editBitMask & common.EDITBITMASK_MOVE:
            # parent id
            origParentId = self._origParentId
            currParentId = None
            parent = self.parent()
            if parent and parent.parent():  # if not child of root
                assert parent.uniqueId
                currParentId = parent.uniqueId
                edit["type"] |= common.EDITBITMASK_MOVE
                edit["oldParentId"] = origParentId
                edit["newParentId"] = currParentId

        if self._editBitMask & common.EDITBITMASK_UPDATE:
            # column data
            for column in xrange(len(self)):
                fieldName = self._model.headerData(column, QtCore.Qt.Horizontal,
                                                   common.ROLE_NAME)  # internal column name
                assert fieldName is not None
                for role in self._origData[column]:
                    origData = self._origData[column][role]
                    currData = self.data(column, role)
                    if origData != currData:
                        # data has changed, store the difference
                        edit["type"] |= common.EDITBITMASK_UPDATE
                        if "oldColumnData" not in edit:
                            edit["oldColumnData"] = {}
                            edit["newColumnData"] = {}
                        if fieldName not in edit["oldColumnData"]:
                            edit["oldColumnData"][fieldName] = {}
                            edit["newColumnData"][fieldName] = {}
                        edit["oldColumnData"][fieldName][role] = origData
                        edit["newColumnData"][fieldName][role] = currData

        if edit["type"]:
            return edit
        return None

    # ------------------------------------------------------------------------------------------------------------------------------
    # SORTING METHODS
    # ------------------------------------------------------------------------------------------------------------------------------
    def sortTree(self, cmp=None):
        """
        Sort all descendants of this item
        """
        # sort children
        self.__childList.sort(cmp=cmp)
        # update the child index lookup
        for i, childItem in enumerate(self.__childList):
            self.__childLookup[childItem] = i
        # recursively sort each child
        for childItem in self.__childList:
            childItem.sortTree(cmp=cmp)

    # ------------------------------------------------------------------------------------------------------------------------------
    # PROPERTIES
    # ------------------------------------------------------------------------------------------------------------------------------
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

    def isSelectable(self, column=0):
        return self._getFlag(column, QtCore.Qt.ItemIsSelectable)

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
        # initialize check state to unchecked
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
