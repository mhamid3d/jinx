import logging

from qtswitch import QtCore, QtGui

from datautil import DataValueType
import wizqt
from wizqt.modelview.model_item import ModelItem

import ivyqt
from .datasource import IvyDataSource

_LOGGER = logging.getLogger(__name__)


# TODO tags
# t = sh["Twig"].getUuid("838da4fd-15f1-4400-98b2-dc567251d5a4")
# t.getDataTagAttributeNames()
# t.hasTagAttr("lod")
# t.getDataTagAttribute("lod").value()
# sh["IvyTag"].distinct(sh["IvyTag"]["tag"], sh["IvyTag"]["twig_dnuuid"] != None)


##############################################################################################################
# 	ColumnDescriptor
##############################################################################################################
class ColumnDescriptor(object):
    def __init__(self):
        super(ColumnDescriptor, self).__init__()
        self.name = None
        self.code = None
        self.fields = {}
        self.wizqtDataType = wizqt.TYPE_STRING_SINGLELINE
        self.ivyDataType = DataValueType.UNDEFINED
        self.sortable = False

    def __repr__(self):
        return "{0} ({1}): {2}".format(self.name, self.ivyDataType, self.fields)


##############################################################################################################
# 	TwigDataSource
##############################################################################################################
class DynamicHeaderDataSource(IvyDataSource):
    # keeping this list to retain column order
    COLUMN_HEADER_ORDER = []
    ROLE_COLUMN_DESCRIPTOR = wizqt.registerDataRole()
    ROLE_HIDDEN_DATA = wizqt.registerDataRole()

    # Properties
    @property
    def columnHeaderMap(self):
        return self.__columnHeaderMap

    @property
    def fullColumnOrder(self):
        return self.__fullColumnOrder

    @property
    def fullColumnCodeOrder(self):
        return self.__fullColumnCodeOrder

    ##############################################################################################################
    # 	__init__
    ##############################################################################################################
    def __init__(
            self,
            handler,
            mainInterface,
            additionalInterfaces=None,
            nonQueryInterfaces=None,
            headerOrder=COLUMN_HEADER_ORDER,
            enableCaching=True,
            parent=None
    ):
        """

        :parameters:
            mainInterface : cobweb._base.DataInterface
                The main interface of the datasource
                e.g. sh['Twig']
        :keywords:
            additionalInterfaces : list
                list of cobweb._base.DataInterface
                Additional interfaces that also have search results represented by model items
                e.g. [ sh['Stalk'], sh['Leaf'] ]
            nonQueryInterfaces : list
                list of cobweb._base.DataInterface
                Interfaces that are not represented in search results, but their keys are still represented as columns
                e.g. [ sh['TwigType'], sh['YSubmission'] ]
        :return:

        :rtype:

        """
        # these datatypes are the ones we support sorting on
        self.__sortableTypes = [
            wizqt.TYPE_STRING_SINGLELINE,
            wizqt.TYPE_DATE,
            wizqt.TYPE_DATE_TIME,
            wizqt.TYPE_FLOAT,
            wizqt.TYPE_INTEGER,
            wizqt.TYPE_UNSIGNED_INTEGER,
        ]
        self._additionalQueryInterfaces = additionalInterfaces[:] if additionalInterfaces is not None else []
        self._nonQueryInterfaces = nonQueryInterfaces[:] if nonQueryInterfaces is not None else []

        # make list of interfaces
        self._allInterfaces = additionalInterfaces[:]
        if mainInterface not in additionalInterfaces:
            self._allInterfaces.insert(0, mainInterface)
        self._allInterfaces.extend(nonQueryInterfaces)

        # generate column info map
        self.__columnHeaderMap = self.__generateHeaderMap()

        # get list of columns: COLUMN_HEADER_ORDER + [ everything not in COLUMN_HEADER_ORDER sorted alphabetically ]
        self.__fullColumnCodeOrder = filter(self.__columnHeaderMap.get, self.COLUMN_HEADER_ORDER)
        for columnCode in sorted(self.__columnHeaderMap.keys()):
            if columnCode not in self.COLUMN_HEADER_ORDER:
                self.__fullColumnCodeOrder.append(columnCode)

        self.__fullColumnOrder = [self.__columnHeaderMap.get(columnCode).name for columnCode in
                                  self.__fullColumnCodeOrder]

        # init superclass
        super(DynamicHeaderDataSource, self).__init__(
            mainInterface,
            columnNames=self.__fullColumnCodeOrder,
            enableCaching=enableCaching,
            parent=parent
        )

    def __isSortable(self, dataType):
        return dataType in self.__sortableTypes

    def __generateHeaderMap(self):
        """
        """
        columnHeaderMap = {}
        for interface in self._allInterfaces:
            interfaceName = interface.name()
            for field in interface.getFields():
                if field.getProperty('visible', True) is False:
                    continue
                realName = field.name()
                columnCode = field.getProperty('code', realName)
                if not columnCode in columnHeaderMap:
                    cd = ColumnDescriptor()
                    cd.ivyDataType = field.dataType()
                    cd.wizqtDataType = self._getColumnType(columnCode, cd.ivyDataType)
                    cd.sortable = self.__isSortable(cd.wizqtDataType)
                    cd.name = field.getProperty('display_name', realName)
                    cd.code = columnCode
                    # cd.code = field.getProperty( 'code', realName )
                    columnHeaderMap[columnCode] = cd
                assert field.getProperty('code', realName) == columnHeaderMap[columnCode].code, \
                    "Code1 = %s %s Code2 = %s " % (field.interface(), \
                                                   field.getProperty('code', realName),
                                                   columnHeaderMap[columnCode].code)
                columnHeaderMap[columnCode].fields[interfaceName] = field
        return columnHeaderMap

    def _getColumnType(self, columnCode, ivyDataType):
        if columnCode == "thumbnail":
            # hack to make thumbnails image type even though they're stored as paths in the db
            return wizqt.TYPE_IMAGE
        if columnCode == "size":
            # hack to make file sizes string type even though they're stored as uint64 in the db
            return wizqt.TYPE_STRING_SINGLELINE
        return ivyqt.IVY_TO_WIZQT_TYPE_MAP[ivyDataType]

    def isWidgetField(self, descriptor, dataObject):
        field = descriptor.fields.get(dataObject.dataInterface().name())
        return (field and field.getProperty("display_type") == 'multi_line_text')

    def _getIndexDialog(self, item, data, columnDescriptor):
        d = QtGui.QDialog()
        field = columnDescriptor.fields.get(item.dataObject.dataInterface().name())
        dataType = field.getProperty("display_type")
        if field == 'multi_line_text':
            dataType = wizqt.TYPE_STRING_MULTILINE
        else:
            dataType = columnDescriptor.wizqtDataType
        typeHandler = wizqt.core.type_handler.getTypeHandler(dataType)
        displayWidget = typeHandler.getInputWidget(d)
        assert typeHandler.setInputValue(displayWidget, data), \
            "Failed to set data for object {0}".format(item.uniqueId)
        layout = QtGui.QVBoxLayout(d)
        scrollArea = QtGui.QScrollArea()
        layout.addWidget(scrollArea)
        scrollArea.setWidget(displayWidget)
        scrollArea.setWidgetResizable(True)
        d.setWindowTitle("{0} for {1} {2}".format(columnDescriptor.name, item.dataType, item.uniqueId))
        d.resize(d.height(), 640)
        return d

    def _createHeaderItem(self, columnCodes):
        """
        Create a modelitem to represent header data

        :parameters:
            columnCodes : list
                Create a modelitem with columns <columnNames>
        :return:
            the created model item
        :rtype:
            wizqt.modelview.model_item.ModelItem
        """
        # This is based on unpacking the 3 levels of inheritance to
        # avoid all the nonsense settings and calls that get
        # overridden anyway.

        # Note: this uses the bulk initialisation options in the
        # ModelItem in recent vesions of wizqt. The data array is
        # prepared here and assigned in the model item's
        # constructors. This saves many thousands of method chain calls.
        itemdata = []
        for columnCode in columnCodes:
            data = None

            descriptor = self.__columnHeaderMap.get(columnCode)
            if descriptor is None:
                _LOGGER.warning('Column "{0}" has no entry in column header map, skipping _populateHeaderColumn')
            else:
                columnName = descriptor.name
                topLevelField = self._getTopLevelField(descriptor)
                doc = topLevelField.doc()

                data = {self.ROLE_COLUMN_DESCRIPTOR: descriptor,
                        ivyqt.ROLE_CODE: columnCode,
                        wizqt.ROLE_TYPE: descriptor.wizqtDataType,
                        wizqt.ROLE_IS_SORTABLE: descriptor.sortable,
                        QtCore.Qt.DisplayRole: columnName,
                        wizqt.ROLE_NAME: descriptor.code,
                        wizqt.ROLE_FILTER: bool(topLevelField),
                        QtCore.Qt.ToolTipRole: doc,
                        QtCore.Qt.StatusTipRole: doc,
                        }
            itemdata.append(data)

        headerItem = ModelItem(len(columnCodes), uniqueId=None, dataObject=None, itemData=itemdata)
        return headerItem

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

    def _getSortField(self, descriptor):
        # could be reimplemented in subclasses to use custom logic
        return self._getTopLevelField(descriptor)

    def sortByColumns(self, columns, directions, refresh=True):
        """
        Sort the result set by columns in the specified directions.

        :parameters:
            columns : list
                list of column index ints
            directions : list
                list of QtCore.Qt.SortOrder
        """
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
