# Local imports
from wizqt import common
from model_item import ModelItem
# PyQt imports
from qtswitch import QtCore


########################################################################################################################
# 	AbstractDataSource
########################################################################################################################
class AbstractDataSource(QtCore.QObject):
    """
    This is an abstract base class representing the datasource for a model.
    The datasource is what supplies a model with its items.
    The model requests items via the :meth:`fetchItems` and :meth:`fetchMore` methods.
    The datasource could receive its data from an SQL database, a file, etc.
    Subclass AbstractDataSource to provide your own datasource and connect it to a model
    using :meth:`~wizqt.modelview.model.Model.setDataSource`
    """
    # load methods
    LOAD_METHOD_ALL = "all"
    LOAD_METHOD_PAGINATED = "paginated"
    LOAD_METHOD_INCREMENTAL = "incremental"
    DEFAULT_LOAD_METHOD = LOAD_METHOD_ALL
    DEFAULT_BATCH_SIZE = 500
    # signals
    dataNeedsRefresh = QtCore.Signal()
    totalCountChanged = QtCore.Signal(int)
    pageChanged = QtCore.Signal(int)

    # properties
    @property
    def model(self):
        return self._model

    @property
    def headerItem(self):
        return self._headerItem

    @property
    def loadMethod(self):
        return self._loadMethod

    @property
    def lazyLoadChildren(self):
        return self._lazyLoadChildren

    @property
    def batchSize(self):
        return self._batchSize

    @property
    def needToRefresh(self):
        return self._needToRefresh

    @property
    def isValid(self):
        return self._isValid

    def __init__(self, columnNames=[], parent=None):
        """
        Initialiser

        :keywords:
            columnNames : list
                list of column header names
            parent : QtCore.QObject
                parent qt object
        """
        super(AbstractDataSource, self).__init__(parent)
        self._model = None  # link to the model this datasource is populating
        self._loadMethod = self.DEFAULT_LOAD_METHOD
        self._needToRefresh = True  # indicate that data needs to be refreshed to trigger initial population
        self._isValid = True
        self._itemsCheckable = False
        # lazy-load children for tree models
        # children are not populated until parent is expanded in tree
        self._lazyLoadChildren = False
        # lazy-load in batches
        self._pageNum = 0
        self._batchSize = self.DEFAULT_BATCH_SIZE
        self._totalCount = -1
        # initialize the header item
        self._headerItem = self._createHeaderItem(columnNames)

    def _setTotalCount(self, totalCount):
        """
        Store the number of results

        :parameters:
            totalCount : int
                number of results
        """
        if self._totalCount != totalCount:
            self._totalCount = totalCount
            self.totalCountChanged.emit(self._totalCount)

    def _createHeaderItem(self, columnNames):
        """
        Create a modelitem to represent header data

        :parameters:
            columnNames : list
                Create a modelitem with columns <columnNames>
        :return:
            the created model item
        :rtype:
            wizqt.modelview.model_item.ModelItem
        """
        headerItem = ModelItem(len(columnNames))
        for i, columnName in enumerate(columnNames):
            self._populateHeaderColumn(headerItem, i, columnName)
        return headerItem

    def _populateHeaderColumn(self, headerItem, col, columnName):
        """
        Add the text <columnName> to the modelitem <headerItem> at column index <col>

        :parameters:
            headerItem : wizqt.modelview.model_item.ModelItem
                the header's model item
            col : int
                index of a column
            columnName : str
                column name
        """
        headerItem.setData(columnName, col, QtCore.Qt.DisplayRole)
        headerItem.setData(columnName, col, common.ROLE_NAME)

    def setModel(self, model):
        """
        Set the model that this datasource is populating

        :parameters:
            model : wizqt.modelview.model_item.Model
                the model
        """
        self._model = model

    def setLoadMethod(self, loadMethod):
        """
        Set the way that data is loaded

        :parameters:
            loadMethod : str
                the load method

                self.LOAD_METHOD_ALL
                    load all data in one go
                self.LOAD_METHOD_PAGINATED
                    load data in groups i.e. pages. The number of items per page is self.DEFAULT_BATCH_SIZE
                    :see:
                        self.setBatchSize
                self.LOAD_METHOD_INCREMENTAL
                    load data incrementally, as long as self.canFetchMore() returns True
        """
        self._loadMethod = loadMethod

    def setLazyLoadChildren(self, enabled):
        """
        lazy load children (children are not populated until parent is expanded in tree)

        :parameters:
            enabled : bool
                enabled state
        """
        self._lazyLoadChildren = bool(enabled)

    def setNeedToRefresh(self, needToRefresh):
        """
        Either emit a signal that indicates that the data is no longer up to date,
        or stop the signal from being emitted, i.e. the data is now up to date

        :parameters:
            needToRefresh : bool
                the data needs to be updated
        """
        if self._needToRefresh != needToRefresh:
            self._needToRefresh = needToRefresh
            if self._needToRefresh:
                self.dataNeedsRefresh.emit()

    def setBatchSize(self, batchSize):
        """
        Set the maximum number of items that can be loaded in one go.

        :parameters:
            batchSize : int
                the result count limit
        """
        if self._batchSize != batchSize:
            self._batchSize = batchSize
            self.setNeedToRefresh(True)

    def setPage(self, pageNum):
        """
        If we're loading data in pages, set the current page that we're on

        :parameters:
            pageNum : int
                page number
        """
        if self._loadMethod == self.LOAD_METHOD_PAGINATED and self._pageNum != pageNum:
            self._pageNum = pageNum
            self.pageChanged.emit(pageNum)
            self.setNeedToRefresh(True)

    def canFetchMore(self, parentIndex):
        """
        Check whether the parentIndex needs to be populated. This applies only to
        incremental loading or lazy population of children

        :parameters:
            parentIndex : QtCore.QModelIndex
                model index to be queried
        :return:
            True if item needs to be populated
        :rtype:
            bool
        """
        if self._isValid and (self._loadMethod == self.LOAD_METHOD_INCREMENTAL or self._lazyLoadChildren):
            """
            if not parentIndex.isValid():
                # top-level item
                if self._totalCount < 0: # total count is uninitialized, so item is unpopulated
                    return True
                elif self._loadMethod == self.LOAD_METHOD_INCREMENTAL and self._model.rowCount( parentIndex ) < self._totalCount:
                    return True
            else:
            """
            if True:
                # must be a tree model
                item = self._model.itemFromIndex(parentIndex)
                if self._lazyLoadChildren and item.totalChildCount() < 0:  # totalChildCount is uninitialized, so item is unpopulated
                    return True
                elif self._loadMethod == self.LOAD_METHOD_INCREMENTAL and item.childCount() < item.totalChildCount():
                    return True
        return False

    def fetchMore(self, parentIndex):
        """
        This method only gets called when canFetchMore() returns True
        should only be for incremental loading or lazy population of children

        :parameters:
            parentIndex : QtCore.QModelIndex
                model index to be queried
        """
        assert self._isValid and (self._loadMethod == self.LOAD_METHOD_INCREMENTAL or self._lazyLoadChildren)
        offset = self._model.rowCount(parentIndex)
        limit = self._batchSize if self._loadMethod == self.LOAD_METHOD_INCREMENTAL else 0
        itemList = self._fetchBatch(parentIndex, offset, limit, False)  # FIXME: reload?
        # sort the items using the model's sorter
        self._model.sorter.sortItems(itemList)
        # mark parent as populated
        if self._lazyLoadChildren:  # and parentIndex.isValid():
            parentItem = self._model.itemFromIndex(parentIndex)
            parentItem.setTotalChildCount(len(itemList))
        # insert the new items in the model
        self._model.appendItems(itemList, parentIndex)

    def fetchItems(self, parentIndex, reload):
        """
        Get modelitems for this index. This method should only be called by requestRefresh()
        in Model, and only for top-level items.

        :parameters:
            parentIndex : QtCore.QModelIndex
                model index to be populated
            reload : bool
                the index's data should be replaced
        :return:
            The result of self._fetchBatch
        :rtype:
            ?, self._fetchBatch is abstract in this class
        """
        assert not parentIndex.isValid()
        if not self._isValid:
            self._setTotalCount(-1)
            return []
        limit = 0
        offset = 0
        if self._loadMethod == self.LOAD_METHOD_PAGINATED and not parentIndex.isValid():
            limit = self._batchSize
            offset = self._pageNum * self._batchSize
        elif self._loadMethod == self.LOAD_METHOD_INCREMENTAL:
            limit = self._batchSize
            item = self._model.itemFromIndex(parentIndex)
            if item.totalChildCount() < 0:
                offset = 0
            else:
                offset = self._model.rowCount(parentIndex)
        itemList = self._fetchBatch(parentIndex, offset, limit, reload)
        # sort the items using the model's sorter
        self._model.sorter.sortItems(itemList)
        return itemList

    def setItemsCheckable(self, checkable):
        """
        Set model items to be checkable.
        This setting should be taken into account when model items are constructed in _fetchBatch.

        :parameters:
            checkable : bool
        """
        if self._itemsCheckable != checkable:
            self._itemsCheckable = checkable
            self.setNeedToRefresh(True)

    ##############################################################################################
    # ABSTRACT METHODS
    # these are the only methods you should need to implement in datasource sub-classes
    ##############################################################################################
    def _fetchBatch(self, parentIndex, offset, limit, reload):
        """
        ABSTRACT: Return a list of ModelItem entities to the model

        :parameters:
            parentIndex : QtCore.QModelIndex
                model index to be populated
            offset : int
                page offset
            limit : int
                limit of results per page
            reload : bool
                reload existing results
        """
        raise NotImplementedError

    def sortByColumns(self, columns, directions, refresh=True):
        """
        ABSTRACT: multi sort columns

        :parameters:
            columns : list
                list of int
            directions : list
                list of QtCore.Qt.SortOrder
        """
        raise NotImplementedError

    @property
    def stateId(self):
        """
        ABSTRACT:
        A string uniquely identifying the current state of the data source contents
        For example, a string representation of the active filter
        """
        return None
