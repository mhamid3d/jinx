import logging
from qtpy import QtGui, QtCore, QtWidgets
from jinxicon import icon_paths
from jinxqt import common
from jinxqt.modelview.model_item import ModelItem
from mongorm.core.datafilter import DataFilter
from jinxqt.modelview.datasource.jinxdatasource import JinxDataSource
import datetime

_LOGGER = logging.getLogger(__name__)


class TwigDataSource(JinxDataSource):

    COLUMN_HEADER_ORDER = [
        "label",
        "thumbnail",
        "version",
        "modified",
        "created",
        "created_by",
        "path",
        "framerange",
        "uuid"
    ]

    ICON_WIDTH = 16

    def _generateCompPixmap(self, iconPath):
        pixmap = QtGui.QPixmap(iconPath)
        pixmap = pixmap.scaledToHeight(self.ICON_WIDTH, QtCore.Qt.SmoothTransformation)
        compPixmap = QtGui.QPixmap(pixmap.width() + 32, pixmap.height())
        compPixmap.fill(QtGui.QColor(0, 0, 0, 0))

        painter = QtGui.QPainter(compPixmap)
        painter.drawPixmap(QtCore.QPoint(0, 0), pixmap)
        painter.end()
        return compPixmap

    def __init__(self, handler, parent=None):
        self._twigCompPixmap = self._generateCompPixmap(icon_paths.ICON_PACKAGE_SML)
        self._stalkCompPixmap = self._generateCompPixmap(icon_paths.ICON_VERSION_SML)
        self._leafCompPixmap = self._generateCompPixmap(icon_paths.ICON_FILE_SML)
        self._childCountPenColor = QtGui.QPalette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        self._handler = handler
        self._twigInterface = handler['twig']
        self._stalkInterface = handler['stalk']
        self._defaultTypesMap = {
            "label": self.configure_label,
            "thumbnail": self.configure_thumbnail,
            "uuid": self.configure_uuid,
            "path": self.configure_path,
            "created": self.configure_created,
            "modified": self.configure_modified,
            "version": self.configure_version,
            "comment": self.configure_comment,
            "framerange": self.configure_framerange,
            "status": self.configure_status,
            "tags": self.configure_tags
        }
        additionalInterfaces = [handler['stalk'], handler['leaf']]
        super(TwigDataSource, self).__init__(
            sourceInterface=handler['twig'],
            additionalInterfaces=additionalInterfaces,
            parent=parent
        )

    def configure_label(self, dataObject):
        label = dataObject.get("label")

        number = None

        if dataObject.interfaceName() == "Twig":
            basePixmap = self._twigCompPixmap
            number = dataObject.childCount()
        elif dataObject.interfaceName() == "Stalk":
            basePixmap = self._stalkCompPixmap
            number = dataObject.childCount()
        else:
            basePixmap = self._leafCompPixmap

        pixmap = QtGui.QPixmap(basePixmap)
        painter = QtGui.QPainter(pixmap)
        painter.setPen(self._childCountPenColor)
        if number is not None:
            painter.drawText(self.ICON_WIDTH, self.ICON_WIDTH, str(number))
        painter.end()

        return {QtCore.Qt.DisplayRole: label, QtCore.Qt.ToolTipRole: label, QtCore.Qt.DecorationRole: pixmap}

    def configure_thumbnail(self, dataObject):
        value = dataObject.get("thumbnail")
        if dataObject.interfaceName() == "Twig":
            children = dataObject.children()
            if children:
                children.sort("version", reverse=True)
                value = children[0].get("thumbnail")

        return {QtCore.Qt.DisplayRole: value}

    def configure_uuid(self, dataObject):
        value = dataObject.get("uuid")

        return {QtCore.Qt.DisplayRole: value}

    def configure_path(self, dataObject):
        value = dataObject.get("path")

        return {QtCore.Qt.DisplayRole: value}

    def configure_created(self, dataObject):
        value = dataObject.get("created")
        if dataObject.interfaceName() == "Twig":
            children = dataObject.children()
            if children:
                children.sort("version", reverse=True)
                value = children[0].get("created")

        return {QtCore.Qt.DisplayRole: value.strftime("%m-%d-%Y %H:%M:%S")}

    def configure_modified(self, dataObject):
        value = dataObject.get("modified")
        if dataObject.interfaceName() == "Twig":
            children = dataObject.children()
            if children:
                children.sort("version", reverse=True)
                value = children[0].get("modified")

        return {QtCore.Qt.DisplayRole: value.strftime("%m-%d-%Y %H:%M:%S")}

    def configure_version(self, dataObject):
        value = dataObject.get("version")
        if dataObject.interfaceName() == "Twig":
            children = dataObject.children()
            if children:
                children.sort("version", reverse=True)
                value = children[0].get("version")

        return {QtCore.Qt.DisplayRole: value}

    def configure_comment(self, dataObject):
        value = dataObject.get("comment")

        return {QtCore.Qt.DisplayRole: value}

    def configure_framerange(self, dataObject):
        value = dataObject.get("framerange")
        if dataObject.interfaceName() == "Twig":
            children = dataObject.children()
            if children:
                children.sort("version", reverse=True)
                value = children[0].get("framerange")

        if isinstance(value, list):
            value = "{}-{}".format(value[0], value[1])

        return {QtCore.Qt.DisplayRole: value}

    def configure_status(self, dataObject):
        value = dataObject.get("status")
        children = dataObject.children()
        interface = dataObject.interfaceName()
        if children:
            if interface == "Twig":
                children.sort("version", reverse=True)
            elif interface == "Stalk":
                children.sort("label")
            value = children[0].get("status")

        status_icon_map = {"In Progress": icon_paths.ICON_INPROGRESS_SML,
                           "Available": icon_paths.ICON_AVAILABLE_SML,
                           "Approved": icon_paths.ICON_CHECKGREEN_SML,
                           "Declined": icon_paths.ICON_XRED_SML}

        if value in status_icon_map.keys():
            return {QtCore.Qt.DisplayRole: value, QtCore.Qt.DecorationRole: QtGui.QIcon(status_icon_map.get(value))}

        return {QtCore.Qt.DisplayRole: value}

    def configure_tags(self, dataObject):
        value = dataObject.get("tags")
        if dataObject.interfaceName() == "Twig":
            children = dataObject.children()
            if children:
                children.sort("version", reverse=True)
                value = children[0].get("tags")

        if value and len(value) > 0:
            value = ", ".join(value)

        return {QtCore.Qt.DisplayRole: value}

    def makeItems(self, dataContainer):
        interfaceName = dataContainer.interfaceName()

        items = []

        top_interface = "Twig"
        bottom_interface = "Leaf"

        for dataObject in dataContainer:
            itemdata = []
            for idx, field in enumerate(self._columnList):
                data = {}
                if field in self._defaultTypesMap.keys():
                    data = self._defaultTypesMap[field](dataObject)
                else:
                    value = dataObject.get(field)
                    if not value is None:
                        value = str(value)
                    data = {QtCore.Qt.DisplayRole: value}

                tempDisplayValue = data[QtCore.Qt.DisplayRole]
                if tempDisplayValue:
                    data[QtCore.Qt.DisplayRole] = str(tempDisplayValue)

                itemdata.append(data)

            item = ModelItem(len(self.headerItem), uuid=dataObject.getUuid(), dataObject=dataObject,
                             itemData=itemdata, dataType=interfaceName)

            items.append(item)

        for result in items:
            children = result.dataObject.children()
            if children:
                if interfaceName == "Twig":
                    children.sort("version", reverse=True)
                elif interfaceName == "Stalk":
                    children.sort("label")

                result.appendChildren(self.makeItems(children))

        return items