import logging
import operator
import itertools

from qtpy import QtCore
from jinxqt import common
from jinxqt.modelview.model_item import ModelItem
from jinxqt.modelview.model_item_sorter import ModelItemSorter
from jinxqt import common


_LOGGER = logging.getLogger(__name__)


def calcGroupingKey(pairing):
    (i, x) = pairing
    return i - x


class Model(QtCore.QAbstractItemModel):

    dataNeedsRefresh = QtCore.Signal()
    dataAboutToBeRefreshed = QtCore.Signal()
    dataRefreshed = QtCore.Signal()

    @property
    def rootItem(self):
        return self._rootItem

    @property
    def dataSource(self):
        return self._dataSource

    @property
    def sorter(self):
        return self._sorter

    def __init__(self):
        super(Model, self).__init__()
        self._columnCount = 0
        self._dataSource = None
        self._sorter = None
        self._uuidLookup = {}
        self._totalItemCount = 0

        self._sorter = ModelItemSorter(self)
        self._sorter.sortingChanged.connect(self.doSort)
        self._maintainSorted = False

        self._headerItem = self.newItem()
        self._rootItem = self.newItem()
        self._rootItem.setModel(self)
        self._rootItem.setTotalChildCount(-1)

        self.dataNeedsRefresh.connect(self.requestRefresh)

    def addToTotalItemCount(self, count):
        self._totalItemCount += count

    def num_items(self):
        return self._totalItemCount

    def setColumnCount(self, columnCount):
        countDelta = columnCount - self._columnCount
        if countDelta > 0:
            self.insertColumns(self._columnCount, countDelta)
        elif countDelta < 0:
            self.removeColumns(self._columnCount + countDelta, -countDelta)

    def rowCount(self, parentIndex=QtCore.QModelIndex()):
        return self.itemFromIndex(parentIndex).childCount()

    def columnCount(self, parentIndex=QtCore.QModelIndex()):
        return self._columnCount

    def index(self, row, column, parentIndex=QtCore.QModelIndex()):
        if self.hasIndex(row, column, parentIndex):
            childItem = self.itemFromIndex(parentIndex).child(row)
            if childItem:
                return self.createIndex(row, column, childItem)
        return QtCore.QModelIndex()

    def parent(self, index):
        if index.isValid():
            parentItem = self.itemFromIndex(index, False).parent()
            return self.indexFromItem(parentItem)
        return QtCore.QModelIndex()

    def flags(self, index):
        if not index.isValid():
            return self._rootItem.flags()
        return self.itemFromIndex(index, False).flags(index.column())

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            return self.itemFromIndex(index, False).data(index.column(), role)
        return None

    def dataType(self, index):
        dataType = self.data(index, common.ROLE_TYPE)
        if dataType in common.TYPES:
            return dataType

        dataType = self.headerData(index.column(), QtCore.Qt.Horizontal, common.ROLE_TYPE)
        if dataType in common.TYPES:
            return dataType

        return common.TYPE_DEFAULT

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal:
            return self._headerItem.data(section, role)
        return None

    def indexFromItem(self, item):
        if item and item.model is self and item.parent():
            row = item.parent().childPosition(item)
            if row >= 0:
                return self.createIndex(row, 0, item)
        return QtCore.QModelIndex()

    def itemFromIndex(self, index, validate=True):
        if validate:
            if not index.isValid():
                return self._rootItem
        return index.internalPointer()

    def uuidFromIndex(self, index):
        item = self.itemFromIndex(index)
        if item:
            return item.uuid
        return None

    def indexFromUuid(self, uuid):
        if uuid is not None:
            modelName = (self.dataSource or self).__class__.__name__
            try:
                item = self._uuidLookup[uuid]
            except KeyError:
                pass
            else:
                if item.model is self and item.uuid == uuid:
                    return self.indexFromItem(item)
                else:
                    _LOGGER.debug("%s: removing invalid uniqueId key %s -> %s" % (modelName, uuid, item))
                    del self._uniqueIdLookup[uuid]
            # lookup failed, search for the item the slow way
            _LOGGER.debug("%s: uniqueId lookup failed; performing exhaustive search for %s" % (modelName, uuid))
            for item in self.iterItems():
                if item.uuid == uuid:
                    _LOGGER.debug("%s: adding new uniqueId key %s -> %s" % (modelName, uuid, item))
                    self._uuidLookup[uuid] = item
                    return self.indexFromItem(item)
        return QtCore.QModelIndex()

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        return self.setItemData(index, {role: value})

    def setItemData(self, index, roles):
        item = self.itemFromIndex(index)
        column = index.column()
        for (role, value) in roles.items():
            item.setData(value, column, role)

        self.dataChanged.emit(index, index)
        return True

    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal:
            if self._headerItem.setData(value, section, role):
                success = True
                if role == QtCore.Qt.DisplayRole and not self.headerData(section, orientation, common.ROLE_NAME):
                    success = self._headerItem.setData(value, section, common.ROLE_NAME)

                if success:
                    self.headerDataChanged.emit(orientation, section, section)
                    return success
        return False

    def _emitDataChanged(self, itemList):
        for (parentItem, first, last) in self._splitContiguousSegments(itemList):
            _LOGGER.debug("emitting data changed: rows %d-%d of parent %s" % (first, last, parentItem))
            parentIndex = self.indexFromItem(parentItem)
            startIndex = self.index(first, 0, parentIndex)
            endIndex = self.index(last, self._columnCount - 1, parentIndex)
            self.dataChanged.emit(startIndex, endIndex)

    def newItem(self):
        item = ModelItem(self._columnCount)
        return item

    def clear(self):
        self.beginResetModel()
        self._rootItem.removeAllChildren()
        self._rootItem.setTotalChildCount(-1)
        self._totalItemCount = 0
        self._uuidLookup = {}
        self.endResetModel()

    def appendRow(self, parentIndex=QtCore.QModelIndex()):
        return self.appendRows(1, parentIndex)

    def appendRows(self, count, parentIndex=QtCore.QModelIndex()):
        return self.insertRows(self.rowCount(parentIndex), count, parentIndex)

    def insertRows(self, position, count, parentIndex=QtCore.QModelIndex()):
        return self.insertItems(position, [self.newItem() for i in range(count)], parentIndex)

    def insertItem(self, position, item, parentIndex=QtCore.QModelIndex()):
        return self.insertItems(position, [item], parentIndex)

    def insertItems(self, position, itemList, parentIndex=QtCore.QModelIndex()):
        parentItem = self.itemFromIndex(parentIndex)

        if not 0 <= position <= parentItem.childCount():
            return False
        if not itemList:
            return True

        self.beginInsertRows(parentIndex, position, position + len(itemList) - 1)

        for item in itemList:
            uuid = item.uuid
            if uuid is not None:
                self._uuidLookup[uuid] = item
            if item.hasChildren():
                for descendant in item.iterTree(includeRoot=False):
                    uuid = descendant.uuid
                    if uuid is not None:
                        self._uuidLookup[uuid] = descendant

        assert parentItem.insertChildren(position, itemList)

        self.endInsertRows()

        return True

    def appendItem(self, item, parentIndex=QtCore.QModelIndex()):
        return self.appendItems([item], parentIndex)

    def appendItems(self, itemList, parentIndex=QtCore.QModelIndex()):
        return self.insertItems(self.rowCount(parentIndex), itemList, parentIndex)

    def setItems(self, itemList):
        self.beginResetModel()
        self._rootItem.removeAllChildren()
        self._uuidLookup = {}
        self._rootItem.appendChildren(itemList)
        for item in self.iterItems():
            if item.uuid is not None:
                self._uuidLookup[item.uuid] = item
        self.endResetModel()
        self._rootItem.setTotalChildCount(len(itemList))

    def removeRows(self, position, count, parentIndex=QtCore.QModelIndex()):
        if count < 0 or position < 0:
            return False
        if count == 0:
            return True
        parentItem = self.itemFromIndex(parentIndex)
        if position + count > parentItem.childCount():
            return False
        return self.removeItems([parentItem.child(i) for i in range(position, position + count)])

    def removeItem(self, item):
        return self.removeItems([item])

    def removeItems(self, itemList):
        if not itemList:
            return True
        for item in itemList:
            if item.model is not self:
                return False
        itemsToRemove = set(itemList)
        for item in itemsToRemove:
            for descendant in item.iterTree(includeRoot=True):
                if descendant.uuid is not None:
                    try:
                        del self._uuidLookup[descendant.uuid]
                    except KeyError:
                        pass
        segments = list(self._splitContiguousSegments(itemsToRemove))
        for (parentItem, first, last) in reversed(segments):
            if parentItem.model is self:
                _LOGGER.debug("removing: rows %d-%d of parent %s" % (first, last, parentItem))
                parentIndex = self.indexFromItem(parentItem)
                self.beginRemoveRows(parentIndex, first, last)
                parentItem.removeChildren(first, last - first + 1)
                self._totalItemCount -= last - first + 1
                self.endRemoveRows()

        return True

    def disableItem(self, item):
        return self.disableItems([item])

    def disableItems(self, itemList):
        pass

    def reviveItem(self, item):
        return self.reviveItems([item])

    def reviveItems(self, itemList):
        pass

    def enableItem(self, item):
        return self.enableItems([item])

    def enableItems(self, itemList):
        pass

    def moveRow(self, fromPosition, toPosition, fromParent=QtCore.QModelIndex(), toParent=QtCore.QModelIndex()):
        return self.moveRows(fromPosition, 1, toPosition, fromParent, toParent)

    def moveRows(self, fromPosition, count, toPosition, fromParent=QtCore.QModelIndex(), toParent=QtCore.QModelIndex()):
        if fromPosition < 0 or count < 0:
            return False
        if count == 0:
            return True
        fromParentItem = self.itemFromIndex(fromParent)
        toParentItem = self.itemFromIndex(toParent)
        if fromPosition + count > fromParentItem.childCount() or toPosition > toParentItem.childCount():
            return False
        if fromParentItem is toParentItem and fromPosition <= toPosition < fromPosition + count:
            return True
        itemsToMove = fromParentItem.children()[fromPosition:fromPosition + count]

        assert len(itemsToMove) == count

        sourceLast = fromPosition + count - 1

        if fromPosition <= toPosition <= sourceLast and fromParent == toParent:
            return True

        if toPosition > sourceLast:
            toPosition += 1

        if not self.beginMoveRows(fromParent, fromPosition, sourceLast, toParent, toPosition):
            return False

        assert fromParentItem.removeChildren(fromPosition, count)
        if fromParentItem is toParentItem and fromPosition + count < toPosition:
            toPosition -= count

        assert toParentItem.insertChildren(toPosition, itemsToMove)
        self.endMoveRows()
        return True

    def moveItem(self, item, toPosition, toParent=QtCore.QModelIndex()):
        return self.moveItems([item], toPosition, toParent)

    def moveItems(self, itemList, toPosition, toParent=QtCore.QModelIndex()):
        if not itemList:
            return True
        for item in itemList:
            if item.model is not self:
                return False

        toParentItem = self.itemFromIndex(toParent)

        if toPosition < 0:
            toPosition = toParentItem.childCount() - 1
        elif toPosition > toParentItem.childCount() - 1:
            toPosition = 0

        itemSet = set(itemList)
        parentItem = toParentItem
        while parentItem:
            if parentItem in itemSet:
                return False
            parentItem = parentItem.parent()
        segments = list(self._splitContiguousSegments(itemList))

        for (fromParentItem, first, last) in reversed(segments):
            fromParentIndex = self.indexFromItem(fromParentItem)
            toParentIndex = self.indexFromItem(toParentItem)
            count = last - first + 1
            if not self.moveRows(first, count, toPosition, fromParentIndex, toParentIndex):
                return False
            if fromParentItem is toParentItem and toPosition > last:
                toPosition -= count
        self._emitDataChanged(itemList)
        return True

    def insertColumns(self, position, count, parentIndex=QtCore.QModelIndex()):
        if position < 0 or position > self._columnCount:
            return False
        if count > 0:
            self.beginInsertColumns(QtCore.QModelIndex(), position, position + count - 1)
            self._headerItem.insertColumns(position, count)
            self._rootItem.insertColumns(position, count)
            self._columnCount += count
            self.endInsertColumns()
        return True

    def removeColumns(self, position, count, parentIndex=QtCore.QModelIndex()):
        if position < 0 or position + count > self._columnCount:
            return False
        if count > 0:
            self.beginRemoveColumns(QtCore.QModelIndex(), position, position + count - 1)
            self._headerItem.removeColumns(position, count)
            self._rootItem.removeColumns(position, count)
            self._columnCount -= count
            self.endRemoveColumns()
        return True

    def hasChildren(self, parentIndex=QtCore.QModelIndex()):
        item = self.itemFromIndex(parentIndex)
        if item.childCount() > 0:
            return True

        return False

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
            for column in range(self._columnCount):
                fromList.append(self.createIndex(oldRow, column, newIdx.internalPointer()))
                toList.append(self.createIndex(newIdx.row(), column, newIdx.internalPointer()))
        self.changePersistentIndexList(fromList, toList)

        self.layoutChanged.emit()

    def beginResetModel(self):
        self.modelAboutToBeReset.emit()

    def endResetModel(self):
        persistentIndexList = self.persistentIndexList()
        for index in persistentIndexList:
            self.changePersistentIndex(index, QtCore.QModelIndex())
        self.modelReset.emit()

    def setDataSource(self, dataSource):
        if self._dataSource:
            self._dataSource.dataNeedsRefresh.disconnect(self.dataNeedsRefresh)
            self._dataSource.setModel(None)
            self._dataSource.setParent(None)
        self._dataSource = dataSource
        self.clear()
        if self._dataSource:
            self._dataSource.setModel(self)
            self._dataSource.setParent(self)
            self.setColumnCount(len(self._dataSource.headerItem))
            self._headerItem = self._dataSource.headerItem
            self._dataSource.dataNeedsRefresh.connect(self.dataNeedsRefresh)
            self.dataNeedsRefresh.emit()
        else:
            self.setColumnCount(0)

    def requestRefresh(self):
        if self._dataSource and (reload or self._dataSource.needToRefresh):
            self._dataSource.setNeedToRefresh(False)

        self.dataAboutToBeRefreshed.emit()

        itemList = self._dataSource.fetchItems(QtCore.QModelIndex())

        self.setItems(itemList)

        self.dataRefreshed.emit()

        return True

    def iterItems(self, includeRoot=True):
        return self._rootItem.iterTree(includeRoot=includeRoot)

    def _splitContiguousSegments(self, itemList):
        partitions = {}
        for item in itemList:
            index = self.indexFromItem(item)
            parentIndex = index.parent()

            if parentIndex not in partitions:
                partitions[parentIndex] = set()
            parentIndex[parentIndex].add(index.row())

        for parentIndex in sorted(partitions):
            parentItem = self.itemFromIndex(parentIndex)
            rowList = partitions[parentIndex]
            sequences = [map(operator.itemgetter(1), g) for k, g in
                         itertools.groupby(enumerate(sorted(rowList)), calcGroupingKey)]

            for seq in sequences:
                yield (parentItem, seq[0], seq[-1])