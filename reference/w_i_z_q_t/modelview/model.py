"""This module contains the primary Model class, to be used in all model-based Qt applications.

An instance of the Model class is required for use with the
:class:`~wizqt.modelview.tree_view.TreeView`/:class:`~wizqt.modelview.table_view.TableView` widgets.

Data is added to the model as :class:`~wizqt.modelview.model_item.ModelItem` instances.
This model can be used with any wizqt view which inherits :class:`~wizqt.modelview.abstract_view.AbstractView`.

It implements the :class:`~QtCore.QAbstractItemModel` class, extending it with several additional features such as:

- Internal items sorted as ModelItem objects
- Support for DataSource objects
- Multi-column sorting
- Monitoring/saving/restoring edits made by the user, via the "editState"

"""

# Standard imports
import functools
import itertools
import logging
import operator

# Local imports
import wizqt
from wizqt import exc
from model_item import ModelItem
from model_item_sorter import ModelItemSorter

# PyQt imports
from qtswitch import QtCore

_LOGGER = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------------------------------------------------------------------------
# CLASSES
# ----------------------------------------------------------------------------------------------------------------------------------------------------

class ModelMimeData(QtCore.QMimeData):
    # properties
    @property
    def sourceModel(self):
        return self._sourceModel

    @property
    def sourceIndexes(self):
        return self.__getIndexes()

    def __init__(self, sourceModel, sourceIndexes):
        super(ModelMimeData, self).__init__()
        self._sourceModel = sourceModel
        self.__sourceIndexes = map(QtCore.QPersistentModelIndex, sourceIndexes)
        # plain text data is just the DisplayRole of each cell
        pathStrings = []
        for index in self.__sourceIndexes:
            if index.column() != 0:
                continue
            plainText = "{0} {1} {2}".format(
                unicode(index.data() or ""),
                unicode(self.sourceModel.uniqueIdFromIndex(QtCore.QModelIndex(index))),
                unicode(self.sourceModel.itemFromIndex(QtCore.QModelIndex(index)).dataType)
            )
            pathStrings.append(plainText)
        self.__plainText = "\n".join(pathStrings)

    def formats(self):
        """
        """
        return QtCore.QMimeData.formats(self) + [wizqt.MIME_TYPE_PLAIN_TEXT, wizqt.MIME_TYPE_MODEL_INDEXES]

    def retrieveData(self, format, preferredType):
        """
        """
        if format == wizqt.MIME_TYPE_PLAIN_TEXT:
            return self.__plainText
        return QtCore.QMimeData.retrieveData(self, format, preferredType)

    def _setPersistentIndexes(self, indexes):
        """
        """
        self.__sourceIndexes = indexes

    def __getIndexes(self):
        """
        Generator function for a sorted list of the source indexes
        """
        for pIdx in sorted(self.__sourceIndexes):
            yield QtCore.QModelIndex(pIdx)


def calcGroupingKey(pairing):
    (i, x) = pairing
    return i - x


class Model(QtCore.QAbstractItemModel):
    # signals
    checkStateChanged = QtCore.Signal(object, object)

    # properties
    @property
    def rootItem(self):
        return self._rootItem

    def __init__(self, parent=None):
        super(Model, self).__init__(parent)
        self._columnCount = 0
        self._headerItem = ModelItem(self._columnCount)
        self._initItemFn = None

        # dynamic data source
        # for use with connecting to ivy, shotgun, etc
        self._dataSource = None
        self._stateId = None

        self.__delayedInitFns = []

        # create a sorter to manage the sorting of model items
        self._sorter = ModelItemSorter(self)
        self._sorter.sortingChanged.connect(self.doSort)
        self._maintainSorted = False

        # hash for quickly looking up items by their unique id
        self._uniqueIdLookup = {}

        # maintain a dictionary of checkable columns {columnNum: propagateCheckState}
        self._checkableColumns = {}

        # drag-and-drop data
        self._dropAcceptFn = None

        # edit mode
        self._isEditMode = False
        self._savedEditStates = {}

        # create root item
        self._rootItem = self.newItem()
        self._rootItem.setModel(self)
        self._rootItem.setTotalChildCount(-1)  # indicate model hasn't been populated yet

        self.totalitemcount = 0

    def addToTotalItemCount(self, count):
        self.totalitemcount += count

    def num_items(self):
        return self.totalitemcount

    def setColumnCount(self, columnCount):
        """
        """
        countDelta = columnCount - self._columnCount
        if countDelta > 0:  # adding more columns
            self.insertColumns(self._columnCount, countDelta)
        elif countDelta < 0:  # removing columns (remove from the end by convention)
            self.removeColumns(self._columnCount + countDelta, -countDelta)

    def setColumnCheckable(self, column, checkable, propagateCheckState=False):
        """
        """
        if checkable:
            self._checkableColumns[column] = propagateCheckState
        elif column in self._checkableColumns:
            del self._checkableColumns[column]

        # update any existing items
        # TODO - is this enough?
        if self._dataSource:
            self._dataSource.setItemsCheckable(checkable)

    def rowCount(self, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.itemFromIndex(parentIndex).childCount()

    def columnCount(self, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self._columnCount

    def index(self, row, column, parentIndex=QtCore.QModelIndex()):
        """
        """
        if self.hasIndex(row, column, parentIndex):
            childItem = self.itemFromIndex(parentIndex).child(row)
            if childItem:
                return self.createIndex(row, column,
                                        childItem)  # store the ModelItem in the QModelIndex.internalPointer()
        return QtCore.QModelIndex()

    def parent(self, index):
        # print "%s.parent(%s)" % ((self._dataSource or self).__class__.__name__, index)
        if index.isValid():
            parentItem = self.itemFromIndex(index, False).parent()
            return self.indexFromItem(parentItem)
        return QtCore.QModelIndex()

    def flags(self, index):
        """
        """
        if not index.isValid():
            return self._rootItem.flags()
        return self.itemFromIndex(index, False).flags(index.column())

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        """
        if index.isValid():
            return self.itemFromIndex(index, False).data(index.column(), role)
        return None

    def data_role_tree_node(self, index):
        # A helper short-cut to get the ROLE_TREE_NODE data out
        # without needing to directly import
        # wizqt.common.ROLE_TREE_NODE, most useful for inherited
        # objects.
        return self.data(index, wizqt.common.ROLE_TREE_NODE)

    def dataType(self, index):
        """
        """
        # check if any type value set on the index itself
        dataType = self.data(index, wizqt.ROLE_TYPE)
        if dataType in wizqt.TYPES:
            return dataType

        # next, check if any type value set on the header for this column
        dataType = self.headerData(index.column(), QtCore.Qt.Horizontal, wizqt.ROLE_TYPE)
        if dataType in wizqt.TYPES:
            return dataType

        # if nothing explicitly set, return a default value
        return wizqt.TYPE_DEFAULT

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """
        """
        # only top header supported
        if orientation == QtCore.Qt.Horizontal:
            return self._headerItem.data(section, role)
        return None

    def indexFromItem(self, item):
        """
        """
        if item and item.model is self and item.parent():
            row = item.parent().childPosition(item)
            if row >= 0:
                return self.createIndex(row, 0, item)  # store the ModelItem in the QModelIndex.internalPointer()
        return QtCore.QModelIndex()

    def itemFromIndex(self, index, validate=True):
        """
        """
        if validate:
            if not index.isValid():
                return self._rootItem
        return index.internalPointer()

    def uniqueIdFromIndex(self, index):
        """
        """
        item = self.itemFromIndex(index)
        if item:
            return item.uniqueId
        return None

    def indexFromUniqueId(self, uniqueId):
        """
        """
        if uniqueId is not None:
            modelName = (self.dataSource or self).__class__.__name__
            # lookup the item
            try:
                item = self._uniqueIdLookup[uniqueId]
            except KeyError:
                pass
            else:
                if item.model is self and item.uniqueId == uniqueId:
                    return self.indexFromItem(item)
                else:
                    _LOGGER.debug("%s: removing invalid uniqueId key %s -> %s" % (modelName, uniqueId, item))
                    del self._uniqueIdLookup[uniqueId]
            # lookup failed, search for the item the slow way
            _LOGGER.debug("%s: uniqueId lookup failed; performing exhaustive search for %s" % (modelName, uniqueId))
            for item in self.iterItems():
                if item.uniqueId == uniqueId:
                    _LOGGER.debug("%s: adding new uniqueId key %s -> %s" % (modelName, uniqueId, item))
                    self._uniqueIdLookup[uniqueId] = item
                    return self.indexFromItem(item)
        return QtCore.QModelIndex()

    ########################################################################################################################
    # WRITE METHODS
    # allow for editing of existing data in the model
    ########################################################################################################################
    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        """
        """
        return self.setItemData(index, {role: value})

    def setDataRoleTreeNode(self, index, value):
        """A short-cut wrapper for setData(index, value,
        wizqt.common.ROLE_TREE_NODE) for use by inheriting objects to
        avoid the need to import the ROLE_TREE_NODE constant.
        """
        return self.setItemData(index, {wizqt.common.ROLE_TREE_NODE: value})

    def setItemData(self, index, roles):
        """
        @param roles: dict of {<role>: <value> }

        Sets the role data for the item at index to the associated value in roles, for every Qt.ItemDataRole.
        Returns true if successful; otherwise returns false.
        Roles that are not in roles will not be modified.
        """
        item = self.itemFromIndex(index)
        column = index.column()
        # set the data on the item
        for (role, value) in roles.items():
            # if model is in edit mode, add an UPDATE edit before setting the new data
            # but only for certain roles
            if self._isEditMode and role in wizqt.ROLES_EDITSTATE:
                item.addEdit(wizqt.EDITBITMASK_UPDATE)
            # set the new data
            item.setData(value, column, role)
            if role == QtCore.Qt.CheckStateRole:
                # deal with check state propagation
                propagateCheckState = self._checkableColumns.get(column, True)  # or True # FIXME
                if propagateCheckState:
                    self._propagateCheckState(item, column, value)
                self.checkStateChanged.emit(index, index)
        # explicitly emit the dataChanged() signal to inform views/delegates of the change
        self.dataChanged.emit(index, index)
        return True

    def _propagateCheckState(self, item, column, state):
        """
        """
        self.__propagateCheckStateDown(item, column, state)
        self.__propagateCheckStateUp(item, column)

    def __propagateCheckStateDown(self, item, column, state):
        """
        """
        topLeftIndex = None
        bottomRightIndex = None
        for childItem in item.children():
            childState = childItem.checkState(column)
            if childState is None:  # child is not checkable
                continue
            if childState != state:
                childItem.setCheckState(state, column)
                index = self.indexFromItem(childItem)
                if index.isValid():
                    index = index.sibling(index.row(), column)
                    if topLeftIndex is None:
                        topLeftIndex = index
                    bottomRightIndex = index
        # notify views of change in data
        if topLeftIndex and bottomRightIndex:
            self.dataChanged.emit(topLeftIndex, bottomRightIndex)
        # recurse through children
        for childItem in item.children():
            self.__propagateCheckStateDown(childItem, column, state)

    def __propagateCheckStateUp(self, item, column):
        """
        """
        parent = item.parent()
        state = None
        while parent is not self._rootItem:
            parentState = parent.checkState(column)
            for childItem in parent.children():
                childState = childItem.checkState(column)
                if childState is None:  # child is not checkable
                    continue
                if state is None:
                    state = childState
                elif state != childState:
                    state = QtCore.Qt.PartiallyChecked
                    break
            if parentState is not None and parentState != state:
                parent.setCheckState(state)
                index = self.indexFromItem(parent)
                self.dataChanged.emit(index, index)
            parent = parent.parent()

    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.DisplayRole):
        """
        """
        # only top header supported
        if orientation == QtCore.Qt.Horizontal:
            if self._headerItem.setData(value, section, role):
                success = True
                # if the internal name is not set, use the display name to ensure it always has a value
                if role == QtCore.Qt.DisplayRole and not self.headerData(section, orientation, wizqt.ROLE_NAME):
                    success = self._headerItem.setData(value, section, wizqt.ROLE_NAME)
                # explicitly emit the headerDataChanged() signal to inform views/delegates of the change
                if success:
                    self.headerDataChanged.emit(orientation, section, section)
                    return success
        return False

    def _emitDataChanged(self, itemList):
        """
        """
        # emit data changed for a set of items
        for (parentItem, first, last) in self._splitContiguousSegments(itemList):
            _LOGGER.debug("emitting data changed: rows %d-%d of parent %s" % (first, last, parentItem))
            parentIndex = self.indexFromItem(parentItem)
            startIndex = self.index(first, 0, parentIndex)
            endIndex = self.index(last, self._columnCount - 1, parentIndex)
            self.dataChanged.emit(startIndex, endIndex)

    ########################################################################################################################
    # RESIZE METHODS
    # allow for adding/deleting data in the model, changing its overall size
    ########################################################################################################################
    def newItem(self):
        """
        """
        item = ModelItem(self._columnCount)
        if self._initItemFn:
            self._initItemFn(item)
        return item

    def setInitItemFn(self, initItemFn):
        """
        """
        if initItemFn is not None and not callable(initItemFn):
            raise exc.WizQtError("Invalid object '%s' passed to %s.setMakeItemFn(); object is not a callable function" % \
                                 initItemFn, self.__class__.__name__)
        self._initItemFn = initItemFn

    def clear(self):
        """
        """
        self.beginResetModel()
        self._rootItem.removeAllChildren()
        self._rootItem.setTotalChildCount(-1)  # indicate model hasn't been populated yet
        self.totalitemcount = 0
        self._uniqueIdLookup = {}
        self.endResetModel()

    def appendRow(self, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.appendRows(1, parentIndex)

    def appendRows(self, count, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.insertRows(self.rowCount(parentIndex), count, parentIndex)

    def insertRows(self, position, count, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.insertItems(position, [self.newItem() for _ in xrange(count)], parentIndex)

    def insertItem(self, position, item, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.insertItems(position, [item], parentIndex)

    def insertItems(self, position, itemList, parentIndex=QtCore.QModelIndex()):
        """
        """
        parentItem = self.itemFromIndex(parentIndex)

        if not 0 <= position <= parentItem.childCount():
            return False
        if not itemList:
            return True

        # perform the insertion
        self.beginInsertRows(parentIndex, position, position + len(itemList) - 1)

        for item in itemList:
            # Do the checks for the item first. This is faster when
            # you have a lot of shallow items, e.g. ivybrowser startup.
            uniq_id = item.uniqueId
            if uniq_id is not None:
                self._uniqueIdLookup[uniq_id] = item
            if self._isEditMode:
                # model is in edit mode, add an insert edit to item
                item.addEdit(wizqt.EDITBITMASK_INSERT)

            # Then only if it has any children, gather them and do the
            # checks on them. This is faster when you have a lot of
            # shallow items, e.g. ivybrowser startup.
            if (item.hasChildren()):
                for descendant in item.iterTree(includeRoot=False):
                    uniq_id = descendant.uniqueId
                    if uniq_id is not None:
                        self._uniqueIdLookup[uniq_id] = descendant
                    if self._isEditMode:
                        # model is in edit mode, add an insert edit to item
                        descendant.addEdit(wizqt.EDITBITMASK_INSERT)

        # NOTE: this calls iterItems() as well, making it repeat the
        # traverses just done here.
        assert parentItem.insertChildren(position, itemList)

        self.endInsertRows()

        return True

    def appendItem(self, item, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.appendItems([item], parentIndex)

    def appendItems(self, itemList, parentIndex=QtCore.QModelIndex()):
        """
        """
        return self.insertItems(self.rowCount(parentIndex), itemList, parentIndex)

    def setItems(self, itemList):
        """
        """
        self.beginResetModel()
        self._rootItem.removeAllChildren()
        self._uniqueIdLookup = {}
        self._rootItem.appendChildren(itemList)
        for item in self.iterItems():
            if item.uniqueId is not None:
                self._uniqueIdLookup[item.uniqueId] = item
        self.endResetModel()
        self._rootItem.setTotalChildCount(len(itemList))

    def removeRows(self, position, count, parentIndex=QtCore.QModelIndex()):
        """
        """
        if count < 0 or position < 0:
            # invalid values
            return False
        if count == 0:
            # no removal necessary
            return True
        parentItem = self.itemFromIndex(parentIndex)
        if position + count > parentItem.childCount():
            # invalid value
            return False
        return self.removeItems([parentItem.child(i) for i in xrange(position, position + count)])

    def removeItem(self, item):
        """
        """
        return self.removeItems([item])

    def removeItems(self, itemList):
        """
        """
        if not itemList:
            return True
        # validate items
        for item in itemList:
            if item.model is not self:
                # items don't belong to this model
                return False
        itemsToRemove = set(itemList)
        itemsToMarkDeleted = set()
        if self._isEditMode:
            # model is in edit mode, only remove rows with INSERT edits, mark the rest as deleted
            for item in itemList:
                if not item.editBitMask() & wizqt.EDITBITMASK_INSERT:
                    # don't remove, mark as deleted
                    itemsToRemove.discard(item)
                    itemsToMarkDeleted.add(item)
        # update unique id lookup for items being removed
        for item in itemsToRemove:
            for descendant in item.iterTree(includeRoot=True):
                if descendant.uniqueId is not None:
                    try:
                        del self._uniqueIdLookup[descendant.uniqueId]
                    except KeyError:
                        pass
        # perform the removal
        segments = list(self._splitContiguousSegments(itemsToRemove))
        for (parentItem, first, last) in reversed(segments):
            if parentItem.model is self:
                _LOGGER.debug("removing: rows %d-%d of parent %s" % (first, last, parentItem))
                parentIndex = self.indexFromItem(parentItem)
                self.beginRemoveRows(parentIndex, first, last)
                parentItem.removeChildren(first, last - first + 1)
                self.totalitemcount -= last - first + 1
                self.endRemoveRows()
        # mark items deleted
        if itemsToMarkDeleted:
            for item in list(itemsToMarkDeleted):
                if item.model is self:
                    item.addEdit(wizqt.EDITBITMASK_DELETE)
                else:
                    itemsToMarkDeleted.discard(item)
            self._emitDataChanged(itemsToMarkDeleted)
        return True

    def archiveItem(self, item):
        """
        """
        return self.archiveItems([item])

    def archiveItems(self, itemList):
        """
        """
        if not itemList:
            return True
        # valid items
        for item in itemList:
            if item.model is not self:
                # items don't belong to this model
                return False
        if self._isEditMode:
            # model is in edit mode, apply an ARCHIVE edit to each item
            for item in itemList:
                item.addEdit(wizqt.EDITBITMASK_ARCHIVE)
            self._emitDataChanged(itemList)
        return True

    def disableItem(self, item):
        """
        """
        return self.disableItems([item])

    def disableItems(self, itemList):
        """
        """
        if not itemList:
            return True
        # valid items
        for item in itemList:
            if item.model is not self:
                # items don't belong to this model
                return False
        if self._isEditMode:
            # model is in edit mode, apply a DISABLE edit to each item
            for item in itemList:
                item.addEdit(wizqt.EDITBITMASK_DISABLE)
            self._emitDataChanged(itemList)
        return True

    def reviveItem(self, item):
        """
        """
        return self.reviveItems([item])

    def reviveItems(self, itemList):
        """
        """
        if not itemList:
            return True
        # valid items
        for item in itemList:
            if item.model is not self:
                # items don't belong to this model
                return False
        if self._isEditMode:
            # model is in edit mode, apply a REVIVE edit to each item
            for item in itemList:
                item.addEdit(wizqt.EDITBITMASK_REVIVE)
            self._emitDataChanged(itemList)
        return True

    def enableItem(self, item):
        """
        """
        return self.enableItems([item])

    def enableItems(self, itemList):
        """
        """
        if not itemList:
            return True
        # valid items
        for item in itemList:
            if item.model is not self:
                # items don't belong to this model
                return False
        if self._isEditMode:
            # model is in edit mode, apply an ENABLE edit to each item
            for item in itemList:
                item.addEdit(wizqt.EDITBITMASK_ENABLE)
            self._emitDataChanged(itemList)
        return True

    def moveRow(self, fromPosition, toPosition, fromParent=QtCore.QModelIndex(), toParent=QtCore.QModelIndex()):
        """
        """
        return self.moveRows(fromPosition, 1, toPosition, fromParent, toParent)

    def moveRows(self, fromPosition, count, toPosition, fromParent=QtCore.QModelIndex(), toParent=QtCore.QModelIndex()):
        """
        """
        if fromPosition < 0 or count < 0:
            # invalid values
            return False
        if count == 0:
            # no move necessary
            return True
        fromParentItem = self.itemFromIndex(fromParent)
        toParentItem = self.itemFromIndex(toParent)
        if fromPosition + count > fromParentItem.childCount() or toPosition > toParentItem.childCount():
            # invalid values
            return False
        if fromParentItem is toParentItem and fromPosition <= toPosition < fromPosition + count:
            # target position lies inside the segment being moved, so no move necessary
            return True
        itemsToMove = fromParentItem.children()[fromPosition:fromPosition + count]

        assert len(itemsToMove) == count
        # begin the move operation
        sourceLast = fromPosition + count - 1  # sourceLast = fromPosition for single element

        if fromPosition <= toPosition <= sourceLast and fromParent == toParent:
            return True  # if we're not moving it and the dest pos is the same, dont do anything

        if toPosition > sourceLast:
            toPosition += 1  # for moving down, the destination index should be 1 + target index row

        if not self.beginMoveRows(fromParent, fromPosition, sourceLast, toParent, toPosition):
            return False
        # print "Moving %s:%d-%d -> %s:%d" % (fromParentItem, fromPosition, fromPosition+count-1, toParentItem, toPosition)
        # mark items with a move edit before removing them from their parent
        # so that the original parent gets stored on the item
        if self._isEditMode and fromParentItem is not toParentItem:
            for item in itemsToMove:
                item.addEdit(wizqt.EDITBITMASK_MOVE)
        # remove the items from the source parent
        assert fromParentItem.removeChildren(fromPosition, count)
        if fromParentItem is toParentItem and fromPosition + count < toPosition:
            # moving items in front of the target, adjust target to account for this
            toPosition -= count
        # insert the items in the destination parent
        assert toParentItem.insertChildren(toPosition, itemsToMove)
        self.endMoveRows()
        return True

    def moveItem(self, item, toPosition, toParent=QtCore.QModelIndex()):
        """
        """
        return self.moveItems([item], toPosition, toParent)

    def moveItems(self, itemList, toPosition, toParent=QtCore.QModelIndex()):
        """
        """
        if not itemList:
            return True
        # validate items
        for item in itemList:
            if item.model is not self:
                # items don't belong to this model
                return False

        toParentItem = self.itemFromIndex(toParent)

        # wrap items for long lists
        if toPosition < 0:
            toPosition = toParentItem.childCount() - 1
        elif toPosition > toParentItem.childCount() - 1:
            toPosition = 0

        # 19012018-cancelled for wrap, enable with toParentItem.childCount() - 1 if required
        # if toPosition < 0 or toPosition > toParentItem.childCount():
        # 	# invalid value
        # 	return False

        # ensure toParent is not among the items being moved, or its descendants
        itemSet = set(itemList)
        parentItem = toParentItem
        while parentItem:
            if parentItem in itemSet:
                return False
            parentItem = parentItem.parent()
        # split item list into contiguous segments
        segments = list(self._splitContiguousSegments(itemList))

        for (fromParentItem, first, last) in reversed(segments):
            # Single element move down satisfies first <= toPosition <= last + 1, should not be skipped
            # if fromParentItem is toParentItem and first <= toPosition <= last + 1:
            # Target position lies inside the segment, no move necessary, just adjust target accordingly
            # print "Skipping move %s:%d-%d -> %s:%d; adjusting target to %d" % (fromParentItem,first,last,toParentItem,toPosition,first)
            # toPosition = first
            # continue
            fromParentIndex = self.indexFromItem(fromParentItem)
            toParentIndex = self.indexFromItem(toParentItem)
            count = last - first + 1
            # move this segment
            if not self.moveRows(first, count, toPosition, fromParentIndex, toParentIndex):
                return False
            if fromParentItem is toParentItem and toPosition > last:
                # moving items in front of the target, adjust target to account for this
                toPosition -= count
        for item in itemList:
            item.addEdit(wizqt.EDITBITMASK_MOVE)
        self._emitDataChanged(itemList)
        return True

    def insertColumns(self, position, count, parentIndex=QtCore.QModelIndex()):
        """
        """
        if position < 0 or position > self._columnCount:
            return False
        if count > 0:
            # ignore the parentIndex argument and alter EVERY item to ensure they all have an equal columnCount
            self.beginInsertColumns(QtCore.QModelIndex(), position, position + count - 1)
            # insert the columns into the header item
            self._headerItem.insertColumns(position, count)
            # insert the columns into existing items (recursively beginning at the root)
            self._rootItem.insertColumns(position, count)
            # add to the total column count for the tree
            self._columnCount += count
            self.endInsertColumns()
        return True

    def removeColumns(self, position, count, parentIndex=QtCore.QModelIndex()):
        """
        """
        if position < 0 or position + count > self._columnCount:
            return False
        if count > 0:
            # ignore the parentIndex argument and alter EVERY item to ensure they all have an equal columnCount
            self.beginRemoveColumns(QtCore.QModelIndex(), position, position + count - 1)
            # remove the columns from the header item
            self._headerItem.removeColumns(position, count)
            # remove the columns from existing items (recursively beginning at the root)
            self._rootItem.removeColumns(position, count)
            # remove from the total column count for the tree
            self._columnCount -= count
            self.endRemoveColumns()
        return True

    ########################################################################################################################
    # LAZY LOAD
    # allow for incremental loading in batches, and lazy population of children
    ########################################################################################################################
    def hasChildren(self, parentIndex=QtCore.QModelIndex()):
        """
        """
        item = self.itemFromIndex(parentIndex)
        if item.childCount() > 0:
            return True
        elif self._dataSource and self._dataSource.lazyLoadChildren:
            return item.totalChildCount() != 0  # -1 = children have not been populated
        return False

    def canFetchMore(self, parentIndex):
        """
        """
        # due to messy garbage collection of Qt objects, this method can sometimes
        # get called when the _dataSource attribute has been cleaned up. So first check
        # that the attribute is still bound.
        if hasattr(self, "_dataSource") and self._dataSource:
            return self._dataSource.canFetchMore(parentIndex)
        return False

    def fetchMore(self, parentIndex):
        """
        """
        if self._dataSource:
            self._dataSource.fetchMore(parentIndex)

    ########################################################################################################################
    # SORT METHODS
    # allow for sorting the data of a model by column
    ########################################################################################################################
    # properties
    @property
    def sorter(self):
        return self._sorter

    @property
    def maintainSorted(self):
        return self._maintainSorted

    def setMaintainSorted(self, maintainSorted):
        """
        """
        self._maintainSorted = bool(maintainSorted)

    def doSort(self, refresh=True):
        """
        """
        # do the actual sort
        if self._dataSource:
            try:
                self._dataSource.sortByColumns(self._sorter.sortColumns, self._sorter.sortDirections, refresh=refresh)
                return
            except NotImplementedError:
                pass

        # save persistent indexes
        oldPersistentMap = dict([(self.itemFromIndex(idx), idx.row()) for idx in self.persistentIndexList()])

        self.layoutAboutToBeChanged.emit()

        # sort all items
        self._sorter.sortItems([self._rootItem])

        # update persistent indexes
        fromList = []
        toList = []
        for (item, oldRow) in oldPersistentMap.items():
            newIdx = self.indexFromItem(item)
            for column in xrange(self._columnCount):
                fromList.append(self.createIndex(oldRow, column, newIdx.internalPointer()))
                toList.append(self.createIndex(newIdx.row(), column, newIdx.internalPointer()))
        self.changePersistentIndexList(fromList, toList)

        self.layoutChanged.emit()

    ########################################################################################################################
    # DRAG-AND-DROP METHODS
    # allow for dragging/dropping items
    ########################################################################################################################
    def setDropAcceptFn(self, dropAcceptFn):
        """
        Pass a function that will be called any time a drop is attempted.
        The function must have the following signature: fn(dropIndex, mimeData)
        """
        if dropAcceptFn is not None and not callable(dropAcceptFn):
            raise exc.WizQtError(
                "Invalid object '%s' passed to %s.setDropAcceptFn(); object is not a callable function" % \
                dropAcceptFn, self.__class__.__name__)
        self._dropAcceptFn = dropAcceptFn

    def supportedDropActions(self):
        """
        """
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def mimeTypes(self):
        """
        """
        return [wizqt.MIME_TYPE_MODEL_INDEXES]

    def indexCanAcceptDrop(self, index, mimeData):
        """
        Re-implement this method in sub-classes to return True/False based on the content of the mime data.
        """
        if self.flags(index) & QtCore.Qt.ItemIsDropEnabled:
            if self._dropAcceptFn:
                return bool(self._dropAcceptFn(self, index, mimeData))
            return True
        return False

    def mimeData(self, indexes):
        """
        """
        return ModelMimeData(self, indexes)

    def dropMimeData(self, mimeData, dropAction, dropRow, dropColumn, dropParent):
        """
        """
        # IGNORE ACTION - return immediately
        if dropAction == QtCore.Qt.IgnoreAction:
            return True

        # only accept ModelMimeData objects
        if not hasattr(mimeData, "sourceIndexes"):
            return False
        if not mimeData.hasFormat(wizqt.MIME_TYPE_MODEL_INDEXES):
            return False
        if not self.indexCanAcceptDrop(dropParent, mimeData):
            return False

        srcModel = mimeData.sourceModel
        srcColCount = srcModel.columnCount()
        colCountDelta = self._columnCount - srcColCount
        toPosition = self.rowCount(dropParent) if dropRow < 0 else dropRow

        # items to move/copy - inspect children and remove duplicates
        itemList = [srcModel.itemFromIndex(QtCore.QModelIndex(pIdx)) for pIdx in sorted(mimeData.sourceIndexes)]
        childList = []
        for item in itemList:
            for childItem in item.iterTree():
                childList.append(childItem.uniqueId)
        itemList = [i for i in itemList if i.uniqueId not in childList]

        # add/remove columns - remove from end by convention
        for item in itemList:
            if colCountDelta > 0:
                item.insertColumns(srcColCount, colCountDelta)
            elif colCountDelta < 0:
                item.removeColumns(srcColCount + colCountDelta, -colCountDelta)

        # MOVE ACTION
        if dropAction == QtCore.Qt.MoveAction:
            if srcModel is self:
                # internal move within the same model
                return self.moveItems(itemList, toPosition, dropParent)
            else:
                # remove items from source model when moving items from another model into this one
                if not srcModel.removeItems(itemList):
                    return False
            itemCopies = itemList

        # COPY ACTION
        elif dropAction == QtCore.Qt.CopyAction:
            # clone the items
            for i in xrange(len(itemList)):
                item = itemList[i]
                itemCopy = self.newItem()
                itemList[i] = (item, itemCopy)
            itemQueue = itemList[:]
            while itemQueue:
                (item, itemCopy) = itemQueue.pop(0)
                item.copyData(itemCopy)
                item.copyFlags(itemCopy)
                for childItem in item.children():
                    childCopy = self.newItem()
                    itemCopy.appendChild(childCopy)
                    itemQueue.append((childItem, childCopy))
            itemCopies = [i[1] for i in itemList if i[0].uniqueId not in childList]

        if dropRow == -1:
            # append item to end of parent's children
            return self.appendItems(itemCopies, dropParent)
        else:
            # insert items at a specific position under parent
            return self.insertItems(dropRow, itemCopies, dropParent)

        return True

    ########################################################################################################################
    # BACKWARDS COMPATIBILITY
    # we have to re-implement these methods for compatibility with versions of Qt < 4.6. Remove these once all builds of Qt are 4.6+
    ########################################################################################################################
    def beginResetModel(self):
        """
        """
        self.modelAboutToBeReset.emit()

    def endResetModel(self):
        """
        """
        # invalidate persistent indexes
        persistentIndexList = self.persistentIndexList()
        for index in persistentIndexList:
            self.changePersistentIndex(index, QtCore.QModelIndex())
        self.modelReset.emit()

    ########################################################################################################################
    # DATASOURCE METHODS
    # dynamic population of data from an external data source (i.e. ivy)
    ########################################################################################################################
    # signals
    dataNeedsRefresh = QtCore.Signal()
    dataAboutToBeRefreshed = QtCore.Signal()
    dataRefreshed = QtCore.Signal()

    # properties
    @property
    def dataSource(self):
        return self._dataSource

    @property
    def stateId(self):
        return self._stateId or "DEFAULT"

    def setDataSource(self, dataSource):
        """
        """
        # disconnect any existing data source
        if self._dataSource:
            self._dataSource.dataNeedsRefresh.disconnect(self.dataNeedsRefresh)
            self._dataSource.setModel(None)
            self._dataSource.setParent(None)
        self._dataSource = dataSource
        # reset the state of the model
        self.clear()
        # set up the new data source
        if self._dataSource:
            self._dataSource.setModel(self)
            self._dataSource.setParent(self)
            self.setColumnCount(len(self._dataSource.headerItem))
            self._headerItem = self._dataSource.headerItem
            self._dataSource.dataNeedsRefresh.connect(self.dataNeedsRefresh)
            self.dataNeedsRefresh.emit()
        else:
            self.setColumnCount(0)

    def setStateId(self, stateId):
        """
        """
        self._stateId = stateId

    def requestRefresh(self, reload=False):
        """
        Requests a datasource refresh/reload, if appropriate.

        Returns True if the data reloaded or changed, otherwise False.
        """
        if self._dataSource and (reload or self._dataSource.needToRefresh):
            # Uncomment the next line for extra debugging, tracing or
            # profiling info.
            # print( "requestRefresh: {0} from {1} = {2} or {3}".format(super( Model, self ).parent(), self._dataSource, reload, self._dataSource.needToRefresh ))
            self._dataSource.setNeedToRefresh(False)

            # capture current edit state
            self.captureEditState()
            self.captureCheckState()
            self.dataAboutToBeRefreshed.emit()

            # update state identifier in between
            # modelAboutToBeRefreshed and modelRefreshed signals
            self._stateId = self._dataSource.stateId

            if self._dataSource.loadMethod == self._dataSource.LOAD_METHOD_INCREMENTAL:
                # just clear the model, it'll get populated by fetchMore()
                self.clear()  # emits modelRefreshed
            else:
                # loadMethod == LOAD_METHOD_PAGINATED or LOAD_METHOD_ALL
                # fetch items.
                # the items will be returned in sorted order
                try:
                    itemList = self._dataSource.fetchItems(QtCore.QModelIndex(), reload)
                except RuntimeError as e:
                    _LOGGER.critical(str(e))
                    itemList = []
                # update the items
                self.setItems(itemList)  # emits modelRefresh

            # restore the edit state
            if self._isEditMode:
                self.restoreEditState()

            self.dataRefreshed.emit()  # emits modelRefreshed
            self.restoreCheckState()
            # execute and purge the delayed init functions
            QtCore.QTimer.singleShot(0, self.__executeDelayedInitFns)
            # Data was reloaded, changed or updated or will be soon
            #
            return True
        else:
            # Data wasn't reloaded
            #
            return False

    ########################################################################################################################
    # CHECK STATE METHODS
    # capturing and restoring check states to a model
    ########################################################################################################################
    _savedCheckStates = {}

    def captureCheckState(self):
        """
        """
        # check if model is populated and items are checkable
        if not (self._dataSource._itemsCheckable and self.rowCount()):
            return
        stateId = self.stateId
        # first remove any existing edit state with this same id
        if stateId in self._savedCheckStates:
            del self._savedCheckStates[stateId]
        # get the check state of each checkable column
        checkState = {}
        for index in self._checkableColumns:
            checkState[index] = self.getCheckedItems(column=index)
        # store the check state
        if checkState:
            _LOGGER.debug(
                "Capturing %s model check state: %s" % ((self.dataSource or self).__class__.__name__, stateId))
            self._savedCheckStates[stateId] = checkState

    def getCheckedItems(self, column=0):
        """
        Get any checked items.

        :parameters:
            column : int column index of check box
        :return:
            list of checked items, if items are checkable, or None.
        :rtype:
            list of wizqt.modelview.ModelItems or None
        """
        checked = None
        if self._dataSource._itemsCheckable:
            checked = []
            for item in self.iterItems():
                if item.checkState(column=column) == QtCore.Qt.Checked:
                    checked.append(item)
        return checked

    def setAllCheckStateItems(self, checkState):
        for k, v in checkState.iteritems():
            self.setCheckedItems(v, column=k)

    def restoreCheckState(self):
        """
        """
        # check if items are checkable
        if not self._dataSource._itemsCheckable:
            return
        stateId = self.stateId
        if stateId in self._savedCheckStates:
            _LOGGER.debug(
                "Restoring %s model check state: %s" % ((self.dataSource or self).__class__.__name__, stateId))
            checkState = self._savedCheckStates[stateId]
            # put in a single shot timer to ensure things like expanding indexes take hold
            QtCore.QTimer.singleShot(0, functools.partial(self.setAllCheckStateItems, checkState))

    def setCheckedItems(self, checkedItemsList, column=0):
        """
        Set items checked.

        :parameters:
            checkedItemsList : list of wizqt.modelview.ModelItems
            column : int column index of check box
        """
        if self._dataSource._itemsCheckable:
            itemUuids = [item.uniqueId for item in checkedItemsList]
            for item in self.iterItems():
                if item.uniqueId in itemUuids:
                    item.setCheckState(QtCore.Qt.Checked, column=column)

    ########################################################################################################################
    # EDITING METHODS
    # tracking, capturing, restoring edits to a model
    ########################################################################################################################
    # properties
    @property
    def isEditMode(self):
        return self._isEditMode

    def setEditMode(self, enabled):
        """
        """
        self._isEditMode = enabled

    def captureEditState(self):
        """
        """
        # check if model is populated and in edit mode
        if not (self._isEditMode and self.rowCount()):
            return
        stateId = self.stateId
        # first remove any existing edit state with this same id
        if stateId in self._savedEditStates:
            del self._savedEditStates[stateId]
        editState = self.getEditState()
        if editState:
            _LOGGER.debug("Capturing %s model edits: %s" % ((self.dataSource or self).__class__.__name__, stateId))
            self._savedEditStates[stateId] = editState

    def getEditState(self):
        """
        """
        editState = []
        for item in self.iterItems():
            edit = item.getEdit()
            if edit:
                editState.append(edit)
        return editState

    def restoreEditState(self):
        """
        """
        # check if model is in edit mode
        if not self._isEditMode:
            return
        stateId = self.stateId
        if stateId in self._savedEditStates:
            _LOGGER.debug("Restoring %s model edits: %s" % ((self.dataSource or self).__class__.__name__, stateId))
            self.applyEditState(self._savedEditStates[stateId])

    def clearEditState(self):
        """
        """
        # check if model is in edit mode
        if not self._isEditMode:
            return
        # delete the current edit state
        stateId = self.stateId
        if stateId in self._savedEditStates:
            del self._savedEditStates[stateId]
        # hack: to delete the edit state we temporarily disable editMode, request a refresh, and re-enable editMode
        # this causes the captureEditState() and restoreEditState() to be skipped during the refresh
        self.setEditMode(False)
        self.requestRefresh(reload=True)
        self.setEditMode(True)

    def revertEdit(self, index):
        """
        """
        # get edit on this item
        if index.isValid() and index.model() is self:
            item = self.itemFromIndex(index, False)
            edit = item.getEdit()
            if edit:
                if edit["type"] & wizqt.EDITBITMASK_INSERT:
                    # revert an INSERT edit by deleting the item
                    # FIXME: but what about edits underneath?
                    if not self.removeItem(item):
                        return False
                else:
                    if edit["type"] & wizqt.EDITBITMASK_UPDATE:
                        # revert column data
                        if "oldColumnData" in edit:
                            for column in xrange(self.columnCount()):
                                columnName = self.headerData(column, QtCore.Qt.Horizontal, wizqt.ROLE_NAME)
                                if columnName in edit["oldColumnData"]:
                                    if not self.setItemData(index.sibling(index.row(), column),
                                                            edit["oldColumnData"][columnName]):
                                        return False
                    if edit["type"] & wizqt.EDITBITMASK_MOVE:
                        # move back to original parent
                        parentId = edit.get("oldParentId")
                        if parentId is not None:
                            parentIndex = self.indexFromUniqueId(parentId)
                            if parentIndex.isValid():
                                if not self.moveItem(item, self.rowCount(parentIndex), parentIndex):
                                    return False
                # clear the edit from the item
                item.clearEdit()
                self._emitDataChanged([item])
        return True

    def applyEditState(self, editState):
        """
        """
        # check if model is in edit mode
        if not self._isEditMode:
            return
        for edit in editState:
            editBitMask = int(edit.get("type") or 0)
            if not editBitMask & (
                    wizqt.EDITBITMASK_INSERT | wizqt.EDITBITMASK_DELETE | wizqt.EDITBITMASK_ARCHIVE | wizqt.EDITBITMASK_REVIVE | wizqt.EDITBITMASK_UPDATE | wizqt.EDITBITMASK_MOVE):
                # no valid edits
                continue
            itemId = edit.get("itemId")
            if itemId is None:
                # no valid item id
                continue
            index = self.indexFromUniqueId(itemId)
            if editBitMask & wizqt.EDITBITMASK_INSERT:
                if index.isValid():
                    # item with this unique id already exists, orphaned edit
                    continue
                # get the parent
                parentId = edit.get("parentId")
                if parentId is None:
                    parentIndex = QtCore.QModelIndex()
                else:
                    parentIndex = self.indexFromUniqueId(parentId)
                    if not parentIndex.isValid():
                        # orphaned edit
                        continue
                # populate new item
                item = self.newItem()  # FIXME: use some sort of model-specific initializer
                item.setUniqueId(itemId)
                if "columnData" in edit and isinstance(edit["columnData"], dict):
                    for column in xrange(self.columnCount()):
                        columnName = self.headerData(column, QtCore.Qt.Horizontal, wizqt.ROLE_NAME)
                        if columnName in edit["columnData"] and isinstance(edit["columnData"][columnName], dict):
                            for role in edit["columnData"][columnName]:
                                item.setData(edit["columnData"][columnName][role], column, role)
                # add to model
                self.appendItem(item, parentIndex)
            elif index.isValid():
                item = self.itemFromIndex(index, False)
                if editBitMask & wizqt.EDITBITMASK_DELETE:
                    # add a delete edit by removing the item
                    self.removeItem(item)
                    if item.model is not self:
                        # item was actually removed from the model, can't apply any further edits
                        continue
                elif editBitMask & wizqt.EDITBITMASK_REVIVE:
                    # add a revive edit
                    self.reviveItem(item)
                elif editBitMask & wizqt.EDITBITMASK_ARCHIVE:
                    # add an archive edit
                    self.archiveItem(item)
                if editBitMask & wizqt.EDITBITMASK_UPDATE:
                    # apply new column data
                    if "newColumnData" in edit and isinstance(edit["newColumnData"], dict):
                        for column in xrange(self.columnCount()):
                            columnName = self.headerData(column, QtCore.Qt.Horizontal, wizqt.ROLE_NAME)
                            if columnName in edit["newColumnData"] and isinstance(edit["newColumnData"][columnName],
                                                                                  dict):
                                self.setItemData(index.sibling(index.row(), column), edit["newColumnData"][columnName])
                if editBitMask & wizqt.EDITBITMASK_MOVE:
                    # move item to new parent
                    parentId = edit.get("newParentId")
                    if parentId is not None:
                        parentIndex = self.indexFromUniqueId(parentId)
                        if parentIndex.isValid():
                            assert self.moveItem(item, self.rowCount(parentIndex), parentIndex)

    ########################################################################################################################
    # PERSISTENT SETTINGS
    # for saving/restoring model state
    ########################################################################################################################
    def saveSettings(self, settings):
        pass

    def loadSettings(self, settings):
        pass

    ########################################################################################################################
    # CUSTOM METHODS
    # these methods are not a part of Qt's built-in model class definition
    ########################################################################################################################
    def iterItems(self, includeRoot=True):
        """
        """
        return self._rootItem.iterTree(includeRoot=includeRoot)

    def _splitContiguousSegments(self, itemList):
        """
        """
        # partition the list by parent
        partitions = {}
        for item in itemList:
            index = self.indexFromItem(item)
            parentIndex = index.parent()

            if parentIndex not in partitions:
                partitions[parentIndex] = set()
            partitions[parentIndex].add(index.row())

        for parentIndex in sorted(partitions):
            parentItem = self.itemFromIndex(parentIndex)
            # assert parentItem.model is self
            rowList = partitions[parentIndex]
            # split row list into sequential segments
            sequences = [map(operator.itemgetter(1), g) for k, g in
                         itertools.groupby(enumerate(sorted(rowList)), calcGroupingKey)]

            for seq in sequences:
                yield (parentItem, seq[0], seq[-1])

    def _setState(self, state):
        """
        """
        self.stateChanged.emit(state)

    def delayedInitFn(self, function):
        """
        """
        if not callable(function):
            raise exc.WizQtError("Invalid function given to %s.delayedInitFn(); %s is not a callable" % \
                                 (self.__class__.__name__, function))
        if self._dataSource and self._dataSource.needToRefresh:
            # delay for later
            self.__delayedInitFns.append(function)
        else:
            # execute immediately
            QtCore.QTimer.singleShot(0, function)

    def __executeDelayedInitFns(self):
        """
        """
        for function in self.__delayedInitFns:
            function()
        self.__delayedInitFns = []
