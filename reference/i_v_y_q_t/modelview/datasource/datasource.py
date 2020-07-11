"""Inherits wizqt's :class:`wizqt.modelview.abstract_datasource.AbstractDataSource`,
and creates model items based on results of ivy queries.

This class should be inherited by all ivy datasources.
"""
import hashlib
import logging
import time

from qtswitch import QtCore

import dnlogging
from dnpath import DnPath
from pipetheme import utils as theme
import spider
from spider.base import DataAccessLevel
from spider.orm import DataFilter
import wizqt
from wizqt.modelview.abstract_datasource import AbstractDataSource

import ivyqt
from .datasource_cache import IvyDataSourceCache
from ... import exc

ARCHIVEDFGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_ARCHIVED)
ARCHIVEDBGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_ARCHIVED, foreground=False)
DELETEDFGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_DELETED)
DELETEDBGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_DELETED, foreground=False)

_LOGGER = logging.getLogger(__name__)


###############################################################################
# IvyDataSource
###############################################################################

class IvyDataSource(AbstractDataSource):
    # constants
    DEFAULT_QUERY_TYPE = "all"
    IVY_TO_WIZQT_TYPE_MAP = ivyqt.IVY_TO_WIZQT_TYPE_MAP

    # properties
    @property
    def handler(self):
        return self._handler

    @property
    def filterSources(self):
        return [fs[0] for fs in self._filterSources]

    def __init__(self, interface, columnNames=[], enableCaching=True, parent=None):
        """
        :parameters:
            interface : spider.orm.DataInterface
            columnNames : list of str column headings
            parent : QtGui.QWidget
        """
        self._interface = interface
        self._handler = spider.getHandler(datainst=interface)
        super(IvyDataSource, self).__init__(columnNames, parent)
        self.__cache = None
        self.__enableCaching = enableCaching
        self._queryType = self.DEFAULT_QUERY_TYPE
        self._filter = DataFilter.create()
        # ordered list of filters, each corresponding with a filter source
        self._filterSources = []
        # keyed by filter source name
        self._filterSourceMap = {}
        # custom style function
        self._customStyleFunction = None

    @property
    def _cache(self):
        assert self.__enableCaching, \
            (
                "enableCaching must be set to True to access the datasource cache."
                " ( pass enableCaching = True to __init__ or call setEnableCaching( True )"
            )
        if self.__cache is None:
            self.__cache = self._createCache()
        return self.__cache

    def _createCache(self):
        return IvyDataSourceCache(self)

    def setEnableCaching(self, state):
        self.__enableCaching = bool(state)

    def cachingEnabled(self):
        return self.__enableCaching

    ###############################################################################
    # DATASOURCE METHODS
    # methods inherited from AbstractDataSource
    ###############################################################################
    @property
    def stateId(self):
        """
        A string uniquely identifying the current state of the data source contents.
        Use the queryType + search criteria of the filter.

        :return:
            hash of master filter state
        :rtype:
            str
        """
        if not self._isValid:
            return None
        # extract search criteria + range from active filter
        filterCopy = DataFilter.create()
        filterCopy.offset(self._filter.getOffset())
        filterCopy.limit(self._filter.getLimit())
        # don't include 'deleted' or 'ondisk_*' search criteria -- shouldn't factor into the state id
        for dataOp in self._filter.getSearch():
            if hasattr(dataOp, "dataField") and dataOp.dataField().name() in ["deleted", "ondisk_sg", "ondisk_lon"]:
                continue
            filterCopy.search(dataOp)
        idString = "%s(%s)" % (self._queryType, filterCopy.getFilterString(self._interface))
        # condense string into an MD5 hash
        return hashlib.md5(idString).hexdigest()

    def setBatchSize(self, batchSize):
        """
        Set the batch size of the result set.

        :parameters:
            batchSize : int
        """
        if self._batchSize != batchSize:
            # must purge the cache when batch size is changed
            if self.cachingEnabled():
                self._cache.clear()
        super(IvyDataSource, self).setBatchSize(batchSize)

    def sortByColumns(self, columns, directions, refresh=True):
        """
        Sort the result set by columns in the specified directions.

        :parameters:
            columns : list of column index ints
            directions : list of QtCore.Qt.SortOrder
        """
        # update sort criteria on the filter
        filter = self._filter.clone()
        filter.resetSort()
        for (column, direction) in zip(columns, directions):
            fieldName = self._headerItem.data(column, wizqt.ROLE_NAME)
            if fieldName:
                try:
                    field = self._interface.getField(fieldName)
                except ValueError:
                    continue
                if direction == QtCore.Qt.AscendingOrder:
                    filter.sort(field.asc())
                elif direction == QtCore.Qt.DescendingOrder:
                    filter.sort(field.desc())
        if filter != self._filter:
            self._filter = filter
            self.setNeedToRefresh(True)

    def _createHeaderItem(self, columnNames):
        """
        Create the header model item with headings columnNames.

        :parameters:
            columnNames : list of column heading str
        :return:
            header model item
        :rtype:
            wizqt.modelview.ModelItem
        """
        if not columnNames:
            columnNames = [f.name() for f in self._interface.getFields() if f.getAttr("visible")]

        return super(IvyDataSource, self)._createHeaderItem(columnNames)

    def _populateHeaderColumn(self, headerItem, col, columnName):
        """
        Populate header columns.

        :parameters:
            headerItem : wizqt.modelview.ModelItem
            col : int
            columnName : str
        """
        super(IvyDataSource, self)._populateHeaderColumn(headerItem, col, columnName)
        try:
            field = self._interface.getField(columnName)
        except ValueError:
            return
        else:
            headerItem.setData(field.getAttr("display_name"), col, QtCore.Qt.DisplayRole)
            headerItem.setData(field.name(), col, wizqt.ROLE_NAME)  # internal name
            headerItem.setData(field.doc(), col, QtCore.Qt.ToolTipRole)
            headerItem.setData(field in self._interface.getFields(), col, wizqt.ROLE_FILTER)
            # headerItem.setData(field.doc(), col, QtCore.Qt.StatusTipRole)
            # data type
            if columnName == "thumbnail":
                headerItem.setData(wizqt.TYPE_IMAGE, col, wizqt.ROLE_TYPE)
                headerItem.setData(False, col, wizqt.ROLE_IS_SORTABLE)
            else:
                headerItem.setData(self.IVY_TO_WIZQT_TYPE_MAP[field.dataType()], col,
                                   wizqt.ROLE_TYPE)  # field data type

    def _ivyFetchBatch(self, parentIndex, offset, limit, reload):
        """
        Return a list of ModelItem entities to the model.

        :parameters:
            parentIndex : QtGui.QModelIndex
                checks the index of the parent item is valid (?)
            offset : int
                page offset
            limit : int
                limit of results per page
            reload : bool
                reload existing results
        :return:
            list of model items to be displayed
        :rtype:
            list
        """

        assert not parentIndex.isValid()
        self._filter.offset(offset)
        self._filter.limit(limit)
        self._filter.reload(reload)
        findTotal = self._loadMethod != self.LOAD_METHOD_ALL
        self._filter.findTotal(findTotal)
        result = True
        itemList = []
        totalCount = 0
        try:
            accesskey = self.handler.createAccessKey(DataAccessLevel.PIPELINE)
            with self.handler.requestAccess(accesskey):
                result, log = self._interface.isValidDataFilter(self._filter)
        except:
            pass
        if result:
            if self.cachingEnabled():
                (itemList, totalCount) = self._cache.getItems(self._interface, self._queryType, self._filter)
            else:
                (itemList, dataContainer) = self._createNewItems()
                totalCount = dataContainer.getTotalFound() if findTotal else dataContainer.size()
        # apply custom style
        if self._customStyleFunction:
            itemList = self._customStyleFunction(itemList, self.headerItem, self._handler)
        # update total count
        self._setTotalCount(totalCount)
        return itemList

    def _fetchBatch(self, parentIndex, offset, limit, reload):
        """
        Return a list of ModelItem entities to the model.

        :parameters:
            parentIndex : QtGui.QModelIndex
                checks the index of the parent item is valid (?)
            offset : int
                page offset
            limit : int
                limit of results per page
            reload : bool
                reload existing results
        :return:
            list of model items to be displayed
        :rtype:
            list
        """
        with self._handler.connect():
            return self._ivyFetchBatch(parentIndex, offset, limit, reload)

    def _createNewItems(self):
        with self._handler.connect():

            queryMethod = self._interface
            for attr in self._queryType.split("."):
                queryMethod = getattr(queryMethod, attr)

            # do ivy query
            _LOGGER.log(
                dnlogging.VERBOSE,
                "Querying Ivy: {0}".format(self._filter.getFilterString(self._interface))
            )

            start = time.time()
            try:
                dataContainer = queryMethod(self._filter)
            # Debugging helper
            # print( "Q:", self._interface.name(), self._queryType, self._filter.getFilterString( self._interface ) )
            except spider.base.CacheLimitExceeded as e:
                _LOGGER.warning("{0}; purging cache and retrying...".format(e))
                # we've reached the ivy cache limit, purge the cache
                # and retry query
                self._interface.clearDataCache()
                dataContainer = queryMethod(self._filter)
            end = time.time()

            _LOGGER.info("Query time: {0:0.3f} seconds".format(end - start))
            # Debugging/tracing helper
            #
            # print( "Querying Ivy: {0} {1} {2}".format(self._interface.name(), [f.name() for f in self._interface.getFields()], self._filter.getFilterString( self._interface ) ) )
            # print( "Query time: {0:0.3f} seconds: {1} - {2} via {3}".format(( end - start ), queryMethod, self._filter, queryMethod ) )

            # create items from the results
            start = time.time()
            itemList = self.makeItems(dataContainer)
            end = time.time()

            _LOGGER.debug("Model item creation time: {0:0.3f} seconds".format(end - start))
            # Debugging/tracing helper
            #
            # print( "Model item creation time: {0:0.3f} seconds".format(( end - start )) )
            return itemList, dataContainer

    def __updateTotalCountFound(self, count):
        """
        Update the total count to count.

        :parameters:
            count : int
        """
        _LOGGER.debug("Received count %s" % count)
        self._setTotalCount(count)

    def setCustomStyleFunction(self, function):
        """
        Set a custom function on the data source to be used for styling model items.
        The function must have the following signature: fn([wizqt.modelview.ModelItems], headerItem, spider.portal.SpiderHandler)

        :parameters:
            function : callable
        """
        # allow None so we can remove the function
        if not callable(function) and function is not None:
            raise exc.IvyQtError("Custom style function must be callable")
        self._customStyleFunction = function

    def customStyleFunction(self):
        """
        Return the custom style function set on the data source.

        :return:
            custom style function
        :rtype:
            callable
        """
        return self._customStyleFunction

    ###############################################################################
    # IVY DATASOURCE METHODS
    # methods specific to IvyDataSource
    ###############################################################################
    def _populateItem(self, item, dataRecord):
        """
        Populate item from its corresponding dataRecord.

        :parameters:
            item : wizqt.modelview.ModelItem
            dataRecord : spider.orm.DataObject
        """
        try:
            isDeleted = bool(dataRecord.get("deleted"))
        except ValueError:
            isDeleted = False
        try:
            isArchived = bool(dataRecord.get("archived"))
        except ValueError:
            isArchived = False

        for column in xrange(len(self._headerItem)):
            columnName = self._headerItem.data(column, wizqt.ROLE_NAME)
            columnType = self._headerItem.data(column, wizqt.ROLE_TYPE)
            if columnName:
                # set data value
                try:
                    value = dataRecord.get(columnName)
                except ValueError:
                    pass
                else:
                    if columnType == wizqt.TYPE_IMAGE:
                        # image columns expect a DnPath
                        try:
                            value = DnPath(value)
                        except:
                            pass
                    item.setData(value, column)
            # colorize deleted/archived items
            if columnType != wizqt.TYPE_IMAGE:  # don't set any style on image columns
                if isArchived:
                    item.setData(ARCHIVEDFGCOLOUR, column, QtCore.Qt.ForegroundRole)
                    item.setData(ARCHIVEDBGCOLOUR, column, QtCore.Qt.BackgroundRole)
                if isDeleted:
                    item.setData(DELETEDFGCOLOUR, column, QtCore.Qt.ForegroundRole)
                    item.setData(DELETEDBGCOLOUR, column, QtCore.Qt.BackgroundRole)
        # store the uuid as the item's unique id
        uuid = dataRecord.getUuid()
        assert uuid
        item.setUniqueId(uuid)
        # TODO: This method is deprecated, apparently?. Change this to
        # use the modelitem init version.
        item.setDataType(dataRecord.dataInterface().name())
        # store the data record object in the item as well
        item.setDataObject(dataRecord)

    def makeItems(self, resultContainer):
        """
        Construct model items from resultContainer - the results from a query - to pass back to the model.
        This method is called by IvyDataSourceCache and should make use of _populateItem() to populate each ModelItem.

        :parameters:
            resultContainer : spider.orm.DataContainer
        """
        raise NotImplementedError

    ###############################################################################
    # FILTERSOURCE METHODS
    # these methods introduce the concept of an Ivy FilterSource, which can be inserted as an input to the Ivy DataSource
    ###############################################################################
    def insertFilterSource(self, index, filterSource, required=False):
        """
        Insert filterSource onto the data source at index

        :parameters:
            index : int
                the position in the data source's filter source list to add it to
            filterSource : ivyqt.filtersource.AbstractFilterSource
                the filter source object
            required : bool
                if the filter source is required and is not valid, the data source is not valid
        """
        if not hasattr(filterSource, "filterChanged"):
            raise exc.IvyQtError(
                "Invalid argument to %s.insertFilterSource(); '%s' is not a subclass of FilterSource" % \
                (self.__class__.__name__, filterSource.__class__.__name__)
            )
        if filterSource.name in self._filterSourceMap:
            raise exc.IvyQtError(
                "%s already has a FilterSource named '%s'" % (self.__class__.__name__, filterSource.name))
        self._filterSources.insert(index, (filterSource, required))
        self._filterSourceMap[filterSource.name] = (filterSource, required)
        filterSource.filterChanged.connect(self._updateFilter)
        # re-query the database
        self._updateFilter()

    def appendFilterSource(self, filterSource, required=False):
        """
        Add filterSource onto the end of the data source

        :parameters:
            filterSource : ivyqt.filtersource.AbstractFilterSource
                the filter source object
            required : bool
                if the filter source is required and is not valid, the data source is not valid
        """
        self.insertFilterSource(len(self._filterSources), filterSource, required)

    def removeFilterSource(self, filterSource):
        """
        Remove filterSource from the data source

        :parameters:
            filterSource : ivyqt.filtersource.AbstractFilterSource
                the filter source object
        """
        # remove from self._filterSources
        for pair in self._filterSources:
            if pair[0] == filterSource:
                # disconnect signal
                filterSource.filterChanged.disconnect(self._updateFilter)
                self._filterSources.remove(pair)
                break
        # remove from self._filterSourceMap
        for name, pair in self._filterSourceMap.iteritems():
            if pair[0].name == filterSource.name:
                del (self._filterSourceMap[filterSource.name])
                return

    def filterSource(self, name):
        """
        Return the filter source corresponding to name, or None if none exists.

        :return:
            filter source
        :rtype:
            ivyqt.filtersource.AbstractFilterSource
        """
        if name in self._filterSourceMap:
            return self._filterSourceMap[name][0]
        return None

    def applyFilterStateMap(self, filterStateMap):
        """
        Apply filterStateMap to the filter sources on the data source.

        :parameters:
            filterStateMap : dict
        """
        for (filterSourceName, filterState) in filterStateMap.items():
            filterSource = self.filterSource(filterSourceName)
            if not filterSource:
                _LOGGER.error("Unknown filter '%s' in filter state applied to %s; skipping" % (
                filterSourceName, self.__class__.__name__))
                continue
            try:
                # apply the filter state
                filterSource._blockFilterChangeSignal(True)
                filterSource.applyFilterState(filterState)
                filterSource._blockFilterChangeSignal(False)
            except Exception as e:
                _LOGGER.exception("Failed to apply filter '%s' to %s" % (filterSourceName, self.__class__.__name__))
        # update filter just once after all filter states have been applied
        self._updateFilter()

    def applyMergedFilterStateMaps(self, filterStateMapList):
        """
        """
        combinedMap = {}
        for filterStateMap in filterStateMapList:
            for filterSourceName, filterState in filterStateMap.iteritems():
                # skip if there is not filter source with this name
                filterSource = self.filterSource(filterSourceName)
                if not filterSource:
                    _LOGGER.error("Unknown filter '%s' in filter state applied to %s; skipping" % (
                    filterSourceName, self.__class__.__name__))
                    continue
                # if we already have a filter state with this name in the combined map, merge the new map into it
                if combinedMap.has_key(filterSourceName):
                    filterState = filterSource.mergeFilterStates([combinedMap[filterSourceName], filterState])
                combinedMap[filterSourceName] = filterState
        self.applyFilterStateMap(combinedMap)

    def _updateFilter(self):
        """
        Rebuild the master filter by merging all filter components together.
        """
        filter = self._filter.clone()
        isValid = True
        filter.resetSearch()
        queryTypeOverrides = {}
        for (filterSource, required) in self._filterSources:
            if filterSource.isValid:
                # merge search/sort/select/omit criteria
                filter.update(filterSource.filter, True, True, True, True)
                # set any query type overrides
                if filterSource.queryType:
                    queryTypeOverrides[filterSource.name] = filterSource.queryType
            elif required:
                # filter is invalid
                isValid = False
        # validate query type overrides
        queryType = self.DEFAULT_QUERY_TYPE
        if isValid and queryTypeOverrides:
            uniqueQueryTypes = set(queryTypeOverrides.values())
            if len(uniqueQueryTypes) > 1:
                _LOGGER.error(
                    "Conflicting query types given to %s by filter sources:\n%s" %
                    (self.__class__.__name__, "\n".join(["\t%s: '%s'" % (k, v) for k, v in queryTypeOverrides.items()]))
                )
                isValid = False
            else:
                queryType = uniqueQueryTypes.pop()
        # re-query the database
        if isValid != self.isValid or filter != self._filter or queryType != self._queryType:
            self._filter = filter
            self._isValid = isValid
            self._queryType = queryType
            self.setPage(0)  # reset to first page
            self.setNeedToRefresh(True)

    ###############################################################################
    # PERSISTENT SETTINGS
    ##############################################################################
    def saveSettings(self, settings):
        """
        Save data source settings.

        :parameters:
            settings : wizqt.core.Settings
        """
        # save the settings of all filter sources
        if self._filterSources:
            settings.beginGroup("filterSources")
            for (filterSource, _) in self._filterSources:
                settings.beginGroup(filterSource.name)
                filterSource.saveSettings(settings)
                settings.endGroup()
            settings.endGroup()

    def loadSettings(self, settings):
        """
        Load data source settings.

        :parameters:
            settings : wizqt.core.Settings
        """
        # load the settings of all filter sources
        settings.beginGroup("filterSources")
        for (filterSource, _) in self._filterSources:
            if filterSource.name in settings:
                settings.beginGroup(filterSource.name)
                filterSource.loadSettings(settings)
                settings.endGroup()
        settings.endGroup()
