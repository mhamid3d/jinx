import logging
import mongorm
import jinxqt
from qtpy import QtCore, QtGui, QtWidgets
import mongorm

from jinxqt import common
from jinxqt.modelview.model_item import ModelItem


_LOGGER = logging.getLogger(__name__)


class ColumnDescriptor(object):
    def __init__(self):
        super(ColumnDescriptor, self).__init__()
        self.name = None
        self.code = None
        self.fields = {}
        self.icon = None
        self.jinxqtDataType = common.TYPE_STRING_SINGLELINE
        self.jinxDataType = None
        self.sortable = False

    def __repr__(self):
        return "{0} ({1}): {2}".format(self.name, self.jinxqtDataType, self.fields)


class JinxDataSource(QtCore.QObject):

    dataNeedsRefresh = QtCore.Signal()
    totalCountChanged = QtCore.Signal(int)

    COLUMN_HEADER_ORDER = []
    ROLE_COLUMN_DESCRIPTER = common.registerDataRole()
    ROLE_HIDDEN_DATA = common.registerDataRole()

    @property
    def model(self):
        return self._model

    @property
    def headerItem(self):
        return self._headerItem

    @property
    def needToRefresh(self):
        return self._needToRefresh

    def __init__(self, sourceInterface=None, additionalInterfaces=[], parent=None):
        super(JinxDataSource, self).__init__(parent)
        self._model = None
        self._needToRefresh = True
        self._sortableTypes = [
            common.TYPE_STRING_SINGLELINE,
            common.TYPE_DATE,
            common.TYPE_DATE_TIME,
            common.TYPE_FLOAT,
            common.TYPE_INTEGER,
            common.TYPE_UNSIGNED_INTEGER
        ]
        self._allInterfaces = []
        self._totalCount = -1
        self._filter = mongorm.getFilter()
        self._interface = sourceInterface
        self._additionalInterfaces = additionalInterfaces
        self._allInterfaces.extend(self._additionalInterfaces)
        self._allInterfaces.append(self._interface)

        self._columnHeaderMap = self._generateHeaderMap()
        self._columnList = filter(self._columnHeaderMap.get, self.COLUMN_HEADER_ORDER)
        for columnCode in sorted(self._columnHeaderMap.keys()):
            if columnCode not in self.COLUMN_HEADER_ORDER:
                self._columnList.append(columnCode)

        if not self._columnList:
            self._columnList = self._columnHeaderMap.keys()

        self._headerItem = self._createHeaderItem(self._columnList)

    def _generateHeaderMap(self):
        columnHeaderMap = {}
        for interface in self._allInterfaces:
            interfaceName = interface.name()
            for field in [x for x in interface.getFields() if x.visible()]:
                # if not field.visible():
                #     continue
                realName = field.db_name()
                columnCode = realName
                if not columnCode in columnHeaderMap:
                    cd = ColumnDescriptor()
                    cd.jinxDataType = field.dataType()
                    cd.jinxqtDataType = self._getColumnType(columnCode, cd.jinxDataType)
                    cd.sortable = self._isSortable(cd.jinxqtDataType)
                    cd.name = field.display_name()
                    cd.code = columnCode
                    cd.icon = field.icon()
                    columnHeaderMap[columnCode] = cd
                assert field.db_name() == columnHeaderMap[columnCode].code, \
                    "Code1 = %s %s Code2 = %s " % (field.interface(),
                                                   field.db_name(),
                                                   columnHeaderMap[columnCode].code)
                columnHeaderMap[columnCode].fields[interfaceName] = field

        return columnHeaderMap

    def _createHeaderItem(self, columnNames):
        itemdata = []
        for columnCode in columnNames:
            data = None

            descriptor = self._columnHeaderMap.get(columnCode)
            if descriptor is None:
                _LOGGER.warning('Column "{0}" has no entry in column header map, skipping _populateHeaderColumn')
            else:
                columnName = descriptor.name
                topLevelField = self._getTopLevelField(descriptor)
                doc = topLevelField.doc()
                icon = QtGui.QIcon(descriptor.icon) if descriptor.icon else None

                dataType = common.TYPE_IMAGE if columnCode == "thumbnail" else descriptor.jinxqtDataType

                data = {self.ROLE_COLUMN_DESCRIPTER: descriptor,
                        common.ROLE_CODE: columnCode,
                        common.ROLE_TYPE: dataType,
                        common.ROLE_IS_SORTABLE: descriptor.sortable,
                        QtCore.Qt.DisplayRole: columnName,
                        common.ROLE_NAME: descriptor.code,
                        common.ROLE_FILTER: bool(topLevelField),
                        QtCore.Qt.ToolTipRole: doc,
                        QtCore.Qt.StatusTipRole: doc,
                        QtCore.Qt.DecorationRole: icon
                        }

            itemdata.append(data)

        headerItem = ModelItem(len(columnNames), uuid=None, dataObject=None, itemData=itemdata)
        return headerItem

    def _getColumnType(self, columnCode, jinxDataType):
        return common.JINX_TO_JINXQT_TYPE_MAP[jinxDataType]

    def _setTotalCount(self, totalCount):
        if self._totalCount != totalCount:
            self._totalCount = totalCount
            self.totalCountChanged.emit(self._totalCount)

    def setModel(self, model):
        self._model = model

    def setNeedToRefresh(self, needToRefresh):
        if self._needToRefresh != needToRefresh:
            self._needToRefresh = needToRefresh
            if self._needToRefresh:
                self.dataNeedsRefresh.emit()

    def _isSortable(self, dataType):
        return dataType in self._sortableTypes

    def _getTopLevelInterface(self, descriptor):
        for interface in self._allInterfaces:
            if descriptor.fields.has_key(interface.name()):
                return interface
        return None

    def _getTopLevelField(self, descriptor):
        for interface in self._allInterfaces:
            field = descriptor.fields.get(interface.name())
            if field is not None:
                return field
        return None

    def makeItems(self, dataContainer):
        raise NotImplementedError

    def createNewItems(self):
        dataContainer = self._interface.all(self._filter)
        itemList = self.makeItems(dataContainer)

        return itemList, dataContainer

    def fetchBatch(self, parentIndex):
        itemList = []
        itemList, dataContainer = self.createNewItems()
        totalCount = len(dataContainer)

        self._setTotalCount(totalCount)

        return itemList

    def fetchItems(self, parentIndex):
        itemList = self.fetchBatch(parentIndex)
        # Do sorting here
        return itemList

    def sortByColumns(self, columns, directions, refresh=True):
        # update sort criteria on the filter
        filter = self._filter.clone()
        filter.resetSort()

        for (column, direction) in zip(columns, directions):
            descriptor = self._headerItem.data(column, role=self.ROLE_COLUMN_DESCRIPTOR)
            if descriptor:
                if not descriptor.sortable:
                    continue

                field = self._getSortField(descriptor)
                if field is None:
                    continue

                if direction == QtCore.Qt.AscendingOrder:
                    filter.sort(field.asc())
                elif direction == QtCore.Qt.DescendingOrder:
                    filter.sort(field.desc())

        if filter != self._filter:
            self._filter = filter
            if (refresh):
                self.setNeedToRefresh(True)
