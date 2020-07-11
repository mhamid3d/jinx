import logging
import time
from qtpy import QtCore

from jinxqt import common
# from common.core.type_handler import getTypeHandler

_LOGGER = logging.getLogger(__name__)


class ModelItemSorter(QtCore.QObject):
    # constants
    DEFAULT_SORT_DIRECTION = QtCore.Qt.AscendingOrder
    _OPPOSITE_SORT_DIRECTION = int(not DEFAULT_SORT_DIRECTION)
    _SORT_DIRECTION_MAP = {
        common.TYPE_STRING_SINGLELINE: DEFAULT_SORT_DIRECTION,
        common.TYPE_STRING_MULTILINE: DEFAULT_SORT_DIRECTION,
        common.TYPE_INTEGER: _OPPOSITE_SORT_DIRECTION,
        common.TYPE_UNSIGNED_INTEGER: _OPPOSITE_SORT_DIRECTION,
        common.TYPE_FLOAT: _OPPOSITE_SORT_DIRECTION,
        common.TYPE_BOOLEAN: DEFAULT_SORT_DIRECTION,
        common.TYPE_DATE: _OPPOSITE_SORT_DIRECTION,
        common.TYPE_DATE_TIME: _OPPOSITE_SORT_DIRECTION,
        common.TYPE_FILE_PATH: DEFAULT_SORT_DIRECTION,
        common.TYPE_JX_PATH: DEFAULT_SORT_DIRECTION,
        common.TYPE_JX_RANGE: DEFAULT_SORT_DIRECTION,
        common.TYPE_RESOLUTION: _OPPOSITE_SORT_DIRECTION,
        common.TYPE_IMAGE: DEFAULT_SORT_DIRECTION,
        common.TYPE_ENUM: DEFAULT_SORT_DIRECTION
    }
    MAX_SORT_COLUMNS = 3

    # signals
    sortingChanged = QtCore.Signal()

    # properties
    sortColumns = property(lambda self: self._sortColumns[:])
    sortDirections = property(lambda self: self._sortDirections[:])

    def __init__(self, model):
        super(ModelItemSorter, self).__init__(model)
        self._model = model
        self._sortColumns = []
        self._sortDirections = []

    def setSortColumns(self, columns, directions):
        """
        Update the list of columns/directions for multi-sorting
        """
        # copy the current column/directions for comparison
        oldColumns = self._sortColumns[:]
        oldDirections = self._sortDirections[:]

        self._sortColumns = []
        self._sortDirections = []
        for (column, direction) in zip(columns, directions):
            self.__addSortColumn(column, direction)

        if self._sortColumns != oldColumns or self._sortDirections != oldDirections:
            self.sortingChanged.emit()

    def addSortColumn(self, column, direction=None):
        """
        Add one more column/direction to the multi-sort list
        """
        # copy the current column/directions for comparison
        oldColumns = self._sortColumns[:]
        oldDirections = self._sortDirections[:]

        self.__addSortColumn(column, direction)

        if self._sortColumns != oldColumns or self._sortDirections != oldDirections:
            self.sortingChanged.emit()

    def __addSortColumn(self, column, direction):
        # skip invalid and unsortable columns
        if column < 0 or not self._model.headerData(column, QtCore.Qt.Horizontal, common.ROLE_IS_SORTABLE):
            return

        # check if this column is already in the list
        try:
            idx = self._sortColumns.index(column)
        except ValueError:
            pass
        else:
            # remove the column/direction from the list
            del self._sortColumns[idx]
            del self._sortDirections[idx]

        # add the column/direction to the list
        self._sortColumns.append(column)
        self._sortDirections.append(direction)

        # limit the number of columns that can be sorted on
        if len(self._sortColumns) > self.MAX_SORT_COLUMNS:
            del self._sortColumns[:-self.MAX_SORT_COLUMNS]
            del self._sortDirections[:-self.MAX_SORT_COLUMNS]

    def defaultSortDirection(self, column):
        dataType = self._model.headerData(column, QtCore.Qt.Horizontal, common.ROLE_TYPE)
        if dataType not in common.TYPES:
            dataType = common.TYPE_DEFAULT
        return self._SORT_DIRECTION_MAP.get(dataType, self.DEFAULT_SORT_DIRECTION)

    def sortItems(self, itemList):
        """
        Sort a list of ModelItems in-place. All child items are recursively sorted as well.
        The itemList argument is re-ordered based on the current multisort column/direction settings in the sorter.
        When sorting, ModelItems are compared based on their dataType.
        """
        if not (self._sortColumns and self._sortDirections):
            return

        name = (self._model.dataSource or self._model).__class__.__name__
        _LOGGER.debug("Sorting %s items on columns %s..." % (name, zip(self._sortColumns, self._sortDirections)))
        start = time.time()

        # sort the list
        itemList.sort(cmp=self.__compareItems)

        # recursively sort each child
        for item in itemList:
            item.sortTree(cmp=self.__compareItems)

        end = time.time()
        _LOGGER.debug("%f seconds" % (end - start))

    def __compareItems(self, item1, item2):
        """
        Compare the value of 2 ModelItems based on their dataType.
        """
        comparison = 0
        for (column, direction) in zip(self._sortColumns, self._sortDirections):

            # first compare values by sort role
            sortVal1 = item1.data(column, common.ROLE_SORT)
            sortVal2 = item2.data(column, common.ROLE_SORT)
            if sortVal1 or sortVal2:
                # do case insensitive comparison of strings
                if isinstance(sortVal1, basestring):
                    sortVal1 = sortVal1.lower()
                if isinstance(sortVal2, basestring):
                    sortVal2 = sortVal2.lower()
                comparison = cmp(sortVal1, sortVal2)
                if comparison != 0:
                    return comparison if direction == QtCore.Qt.AscendingOrder else -comparison

            # next check the display role
            displayVal1 = item1.data(column)
            displayVal2 = item2.data(column)

            # compare items using the typehandler for the data type set on this column
            dataType = self._model.headerData(column, QtCore.Qt.Horizontal, common.ROLE_TYPE)
            if dataType not in common.TYPES:
                dataType = common.TYPE_DEFAULT

            # comparison = getTypeHandler(dataType).compare(displayVal1, displayVal2)
            if comparison != 0:
                return comparison if direction == QtCore.Qt.AscendingOrder else -comparison

        return False
