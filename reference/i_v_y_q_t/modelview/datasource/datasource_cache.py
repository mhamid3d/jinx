"""Cache system used by all ivy data sources.

This stores the results of previous datasource searches, so that searching for
the same set of results more than once doesn't require a repeat query.

Has capacity to do threaded total counts to avoid slow paged queries of large data sets.
"""
import logging

import dnlogging
from spider.orm import DataFilter, DataOpType

_LOGGER = logging.getLogger(__name__)


################################################################################
# CACHED RESULTS
################################################################################

class CachedResults(object):
    """
        A set of results for a given filter search criteria (but not dependent on the sort criteria or range)
        Broken up into a set of cache chunks, each corresponding to a batch of fetched results and indexed by the offset
    """

    class SortedCacheSet(object):
        def __init__(self):
            self.loadedCount = 0
            self.sortCriteria = None
            self.itemChunks = {}
            self.dataContainers = {}

    # properties
    totalCount = property(lambda self: self.__totalCount)

    def __init__(self, batchSize):
        """
        :parameters:
            batchSize : int
        """
        self.__batchSize = batchSize
        self.__totalCount = -1
        self.__completeSet = None
        self.__partialSets = {}

    def setBatchSize(self, batchSize):
        """
        Set the batch size of this set of results.

        :parameters:
            batchSize : int
        """
        if self.__batchSize != batchSize:
            # batch size has changed, must purge the cache
            self.clear()
            self.__batchSize = batchSize

    def clear(self):
        """
        Clear this result set.
        """
        self.__completeSet = None
        self.__partialSets.clear()

    def __getSortCriteriaKey(self, interface, filter):
        """
        Return the sort criteria key of filter.

        :parameters:
            interface : spider.orm.DataInterface
                ivy interface
            filter : spider.orm.DataFilter
                ivy data filter
        :return:
            sort criteria filter string
        :rtype:
            str
        """
        # clear everything except the sort criteria
        filterCopy = DataFilter.create()
        filterCopy.sort(*filter.getSort())
        return filterCopy.getFilterString(interface)

    @classmethod
    def __getInterfaceData(cls, item, sortInterface, field):
        """
        Get first child, if its still not right,
        try again e.g. get first leaf
        """
        if sortInterface != item.dataObject.dataInterface().name():
            for child in item.children():
                if child.dataObject.dataInterface().name() == sortInterface:
                    return child.dataObject.get(field)
                return cls.__getInterfaceData(item, sortInterface, field)
            return None
        return item.dataObject.get(field)

    @classmethod
    def compare(cls, item1, item2, sortCriteria):
        """
        Compare item1 with item2 on sortCriteria.

        :parameters:
            item1 : wizqt.modelview.ModelItem
            item2 : wizqt.modelview.ModelItem
            sortCriteria : list
        :return:
            comparison result
        :rtype:
            int
        """
        comparison = 0
        for sortOp in sortCriteria:
            field = sortOp.dataField()
            sortInterface = field.interface()
            data1 = cls.__getInterfaceData(item1, sortInterface, field)
            data2 = cls.__getInterfaceData(item2, sortInterface, field)
            try:
                comparison = cmp(data1, data2)
            except TypeError:
                comparison = 0
            if comparison != 0:
                return comparison if sortOp.opType() == DataOpType.ASC else -comparison
        return comparison

    def getItems(self, interface, filter):
        """
        Return the items in this result set corresponding to filter.

        :parameters:
            interface : spider.orm.DataInterface
            filter : spider.orm.DataFilter
        :return:
            list of model items
        :rtype:
            list
        """
        # wipe the offset/limit from the filter to construct the key
        offset = filter.getOffset()
        newSortCriteria = filter.getSort()
        if self.__completeSet:
            # results are fully loaded
            # check the sort criteria
            if self.__completeSet.sortCriteria == newSortCriteria:
                # the sort criteria is a match, return the requested chunk
                return self.__completeSet.itemChunks[offset]
            else:
                # the results need to be resorted
                # merge all chunks into a single list
                itemList = []
                for off in sorted(self.__completeSet.itemChunks.keys()):
                    itemList.extend(self.__completeSet.itemChunks.pop(off))

                # sort the items using the new sort criteria
                itemList.sort(cmp=lambda x, y: self.compare(x, y, newSortCriteria))

                # split the list back up into chunks
                for off in xrange(0, len(itemList), self.__batchSize):
                    self.__completeSet.itemChunks[off] = itemList[off:off + self.__batchSize]

                # update sort criteria
                self.__completeSet.sortCriteria = newSortCriteria
                return self.__completeSet.itemChunks[offset]
        else:
            # we only have partial results
            # try to return a match, or throw KeyError if missing
            sortCriteriaKey = self.__getSortCriteriaKey(interface, filter)
            return self.__partialSets[sortCriteriaKey].itemChunks[offset]

    def addItems(self, interface, filter, dataContainer, itemList):
        """
        Add itemList and dataContainer to the result set.

        :parameters:
            interface : spider.orm.DataInterface
            filter : spider.orm.DataFilter
            dataContainer : spider.orm.DataContainer
            itemList : list of wizqt.modelview.ModelItems
        """
        sortCriteriaKey = self.__getSortCriteriaKey(interface, filter)
        offset = filter.getOffset()

        # update total count
        if self.__totalCount < 0:
            self.__totalCount = dataContainer.getTotalFound() if filter.isFindingTotal() else dataContainer.size()

        # get the cache set for this sort criteria
        try:
            cacheSet = self.__partialSets[sortCriteriaKey]
        except KeyError:
            cacheSet = self.SortedCacheSet()
            cacheSet.sortCriteria = filter.getSort()
            self.__partialSets[sortCriteriaKey] = cacheSet

        # add this chunk to the cache set
        assert offset not in cacheSet.itemChunks
        assert offset not in cacheSet.dataContainers
        cacheSet.itemChunks[offset] = itemList
        cacheSet.dataContainers[offset] = dataContainer
        cacheSet.loadedCount += dataContainer.size()
        if cacheSet.loadedCount >= self.__totalCount:
            # cache set is now fully loaded, promote it to a complete set and remove all partial sets
            self.__completeSet = cacheSet
            self.__partialSets.clear()


################################################################################
# IVY DATASOURCE CACHE
################################################################################

class IvyDataSourceCache(object):

    def __init__(self, dataSource):
        """
        :parameters:
            dataSource : wizqt.modelview.AbstractDataSource
        """
        self.__dataSource = dataSource
        self.__cache = {}

    ################################################################################
    # CREATE SEARCH CRITERIA KEY
    ################################################################################

    def __getSearchCriteriaKey(self, interface, filter):
        """
        Return search criteria key of filter.

        :parameters:
            interface : spider.orm.DataInterface
            filter : spider.orm.DataFilter
        :return:
            search criteria filter string
        :rtype:
            str
        """
        filterCopy = DataFilter.create()
        filterCopy.search(*filter.getSearch())
        filterCopy.omitDeleted(filter.getOmitDeleted())
        filterCopy.omitArchived(filter.getOmitArchived())
        return filterCopy.getFilterString(interface)

    ################################################################################
    # CLEAR CACHE
    ################################################################################

    def clear(self):
        """
        Clear the cache.
        """
        self.__cache = {}

    ################################################################################
    # GET IVY ITEMS
    ################################################################################

    def getItems(self, interface, queryType, filter, parentQueryString=None):
        """
        Return a list of ModelItems corresponding to filter, checking cached results prior to querying the database.

        :parameters:
            interface : spider.orm.DataInterface
            queryType : str
            filter : spider.orm.DataFilter
            parentQueryString : str
        :return:
            tuple of ModelItem list and int total count
        :rtype:
            tuple
        """
        searchCriteriaKey = self.__getSearchCriteriaKey(interface, filter)
        interfaceQueryType = "%s.%s_parentQueryString=%s" % (
            interface.name(),
            queryType,
            parentQueryString
        )
        cachedResults = None
        # get query method
        queryMethod = interface
        for attr in queryType.split("."):
            queryMethod = getattr(queryMethod, attr)

        if filter.isReloading():
            # a forced reload has been requested, purge the entire cache
            _LOGGER.log(dnlogging.VERBOSE, "Forced reload requested; purging cache")
            self.clear()
        else:
            # check if we already have cached results for this search criteria
            try:
                cachedResults = self.__cache[interfaceQueryType][searchCriteriaKey]
            except KeyError:
                pass
            else:
                # try to get the item list from these cached results
                try:
                    itemList = cachedResults.getItems(interface, filter)
                except KeyError:
                    pass
                else:
                    return (itemList, cachedResults.totalCount)
        # items are not cached, fetch them from ivy
        itemList, dataContainer = self.__dataSource._createNewItems()
        # add items to the cache
        if not cachedResults:
            cachedResults = CachedResults(self.__dataSource.batchSize)
            if interfaceQueryType not in self.__cache:
                self.__cache[interfaceQueryType] = {}
            self.__cache[interfaceQueryType][searchCriteriaKey] = cachedResults
        cachedResults.addItems(interface, filter, dataContainer, itemList)
        return (itemList, cachedResults.totalCount)
