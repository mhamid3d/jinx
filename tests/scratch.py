from qtpy import QtGui, QtWidgets, QtCore
import qdarkstyle
from mongorm import DbHandler
from mongorm.interfaces import Twig, Stalk, Leaf
import sys
from collections import OrderedDict
from jinxicon import icon_paths
import operator
import itertools
import time
import functools
import datetime


class MyModel(QtCore.QAbstractItemModel):

    HEADER_TO_FIELD = OrderedDict({
        "Name": "label",
        "Job": "job",
        "Path": "path",
        "Modified": "modified",
        "Created": "created",
        "Owner": "created_by"
    })

    def __init__(self):
        super(MyModel, self).__init__()
        self.handler = DbHandler()
        self.job = "GARB"
        self._root = self.newItem()
        # self._root.setModel(self)
        # self._root.setTotalChildCount(-1)
        self.make_items()

    @property
    def twigs(self):
        return self.handler.twig(job=self.job).all()

    # @property
    # def header_items(self):
    #     twig_headers = Twig._fields.keys()
    #     stalk_headers = Stalk._fields.keys()
    #     leaf_headers = Leaf._fields.keys()
    #
    #     twig_set = set(twig_headers)
    #     twig_set = twig_set.intersection(stalk_headers)
    #     twig_set = twig_set.intersection(leaf_headers)
    #
    #     header_items = list(twig_set)
    #
    #     return header_items

    def newItem(self):
        item = QtGui.QStandardItem()
        return item

    def parent(self, index):
        if index.isValid():
            parent_item = self.itemFromIndex(index).parent()
            return self.indexFromItem(parent_item)
        return QtCore.QModelIndex()

    def indexFromItem(self, item):
        if item and item.model is self and item.parent():
            row = item.parent().childPosition(item)
            if row >= 0:
                return self.createIndex(row, 0, item)
        return QtCore.QModelIndex()

    def index(self, row, column, parentIndex=QtCore.QModelIndex()):
        if self.hasIndex(row, column, parentIndex):
            child_item = self.itemFromIndex(parentIndex).child(row)
            if child_item:
                return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def itemFromIndex(self, index):
        if not index.isValid():
            return self._root
        return index.internalPointer()

    def make_items(self):
        for twig in self.twigs:
            twigs_rows = []
            for field in self.HEADER_TO_FIELD.values():
                twigs_rows.append(QtGui.QStandardItem(str(twig[field])))
            self._root.appendRow(twigs_rows)
            for stalk in twig.stalks():
                stalk_rows = []
                for field in self.HEADER_TO_FIELD.values():
                    stalk_rows.append(QtGui.QStandardItem(str(stalk[field])))
                twigs_rows[0].appendRow(stalk_rows)
                for leaf in stalk.leafs():
                    leaf_rows = []
                    for field in self.HEADER_TO_FIELD.values():
                        leaf_rows.append(QtGui.QStandardItem(str(leaf[field])))
                    stalk_rows[0].appendRow(leaf_rows)

    def data(self, index, role=None):
        row = index.row()
        column = index.column()

        if index.isValid():
            if role == QtCore.Qt.SizeHintRole:
                return QtCore.QSize(32, 32)
            elif role == QtCore.Qt.DisplayRole:
                pass
            elif role == QtCore.Qt.DecorationRole:
                if column == 0:
                    item = self.itemFromIndex(index)
                    if not item.parent():
                        return QtGui.QIcon(icon_paths.ICON_PACKAGE_LRG)
                    elif item.parent() and not item.parent().parent():
                        return QtGui.QIcon(icon_paths.ICON_VERSION_LRG)
                    elif item.parent() and item.parent().parent():
                        return QtGui.QIcon(icon_paths.ICON_FILE_LRG)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.HEADER_TO_FIELD.keys())

    def rowCount(self, parent=None, *args, **kwargs):
        return 15

    def headerData(self, section, orientation, role=None):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return str(self.HEADER_TO_FIELD.keys()[section])


ROLE_LAST = QtCore.Qt.UserRole + 1
ROLES_EDITSTATE = set([QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.CheckStateRole])


def registerDataRole():
    global ROLE_LAST
    ROLE_LAST += 1
    return ROLE_LAST

def calcGroupingKey( pairing ):
	(i, x) = pairing
	return i - x

ROLE_NAME = registerDataRole()
ROLE_TYPE = registerDataRole()
ROLE_CATEGORY = registerDataRole()
ROLE_FILE_PATH = registerDataRole()
ROLE_SORT = registerDataRole()
ROLE_ERROR = registerDataRole()
ROLE_CANNOT_HIDE = registerDataRole()
ROLE_CHILDREN_POPULATED = registerDataRole()
ROLE_IS_SORTABLE = registerDataRole()
ROLE_POSSIBLE_VALUES = registerDataRole()
ROLE_SELECTION_STATE = registerDataRole()
ROLE_SELECTABLE = registerDataRole()
ROLE_FILTER = registerDataRole()
ROLE_IMAGE = registerDataRole()
ROLE_TREE_NODE = registerDataRole()

TYPE_STRING_SINGLELINE = "single-line string"
TYPE_STRING_MULTILINE = "multi-line string"
TYPE_INTEGER = "integer"
TYPE_UNSIGNED_INTEGER = "unsigned integer"
TYPE_FLOAT = "float"
TYPE_BOOLEAN = "boolean"
TYPE_DATE = "date"
TYPE_DATE_TIME = "datetime"
TYPE_FILE_PATH = "file path"
TYPE_DN_PATH = "dnpath"
TYPE_DN_RANGE = "dnrange"
TYPE_RESOLUTION = "resolution"
TYPE_IMAGE = "image"
TYPE_ENUM = "enumeration"
TYPE_LABEL = "label"
TYPES = set( [TYPE_STRING_SINGLELINE, TYPE_STRING_MULTILINE, TYPE_INTEGER, TYPE_UNSIGNED_INTEGER, TYPE_FLOAT, TYPE_BOOLEAN,
			TYPE_DATE, TYPE_DATE_TIME, TYPE_FILE_PATH, TYPE_DN_PATH, TYPE_DN_RANGE, TYPE_RESOLUTION, TYPE_IMAGE, TYPE_ENUM, TYPE_LABEL] )
TYPE_DEFAULT = TYPE_STRING_SINGLELINE

MIME_TYPE_PLAIN_TEXT = "text/plain"
MIME_TYPE_HTML = "text/html"
MIME_TYPE_CSV = "text/csv"
MIME_TYPE_MODEL_INDEXES = "application/x-model-indexes"
MIME_TYPE_IVY_ITEMS = "application/x-ivy-items"

EDITBITMASK_INSERT = 0x1 << 0
EDITBITMASK_DELETE = 0x1 << 1
EDITBITMASK_REVIVE = 0x1 << 2
EDITBITMASK_UPDATE = 0x1 << 3
EDITBITMASK_MOVE = 0x1 << 4
EDITBITMASK_ARCHIVE = 0x1 << 5
EDITBITMASK_DISABLE = 0x1 << 6
EDITBITMASK_ENABLE = 0x1 << 7

EDITNAME_INSERT = "INSERT"
EDITNAME_DELETE = "DELETE"
EDITNAME_REVIVE = "REVIVE"
EDITNAME_UPDATE = "UPDATE"
EDITNAME_MOVE = "MOVE"
EDITNAME_MOVEUPDATE = "MOVE+UPDATE"
EDITNAME_ARCHIVE = "ARCHIVE"
EDITNAME_DISABLE = "DISABLE"
EDITNAME_ENABLE = "ENABLE"


class Delegate(QtWidgets.QStyledItemDelegate):
    """Abstract delegate class.

    The wizqt delegate class loads images in a separate thread.
    Any data stored under the :data:`wizqt.common.TYPE_IMAGE` role will be loaded in this way.
    """
    # constants
    CYCLE_FRAME_INTERVAL = 300  # milliseconds
    ONE_MINUTE = datetime.timedelta(minutes=1)
    ONE_HOUR = datetime.timedelta(hours=1)
    ONE_DAY = datetime.timedelta(days=1)
    ROLE_SCALED_IMAGE = registerDataRole()
    ROLE_FAILED_IMAGE = registerDataRole()
    MARGIN = None

    # properties
    @property
    def imageLoader(self):
        return self.__imageLoader

    def _getCheckboxRect(self, boundingRect):
        """
        Get the bounding box of a checkbox that has been centered in a cell

        :rtype:
            QtCore.QRect
        """
        checkboxRect = QtWidgets.QApplication.style().subElementRect(QtGui.QStyle.SE_CheckBoxIndicator,
                                                                 QtGui.QStyleOptionButton(), None)
        checkboxRect.moveCenter(boundingRect.center())
        return checkboxRect

    def _paintBoolean(self, painter, option, index):
        """
        Draw a check box

        :parameters:
            painter : QtGui.QPainter
                painter to draw the image with
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to draw
        """
        buttonStyleOption = QtGui.QStyleOptionButton()
        # set the check state based on the boolean value for this model index
        buttonStyleOption.state = QtGui.QStyle.State_On if index.data() else QtGui.QStyle.State_Off
        # center the checkbox in the cell
        buttonStyleOption.rect = self._getCheckboxRect(option.rect)
        # paint the checkbox
        painter.save()
        QtWidgets.QApplication.style().drawControl(QtGui.QStyle.CE_CheckBox, buttonStyleOption, painter)
        painter.restore()

    def __init__(self, view):
        """
        Initialiser

        :parameters:
            view : QtGui.QAbstractItemView
                The view that this delegate acts upon
        """
        super(Delegate, self).__init__(view)
        self._view = view
        self.__viewStyle = None
        self.__shadedSortColumn = False
        self.__imageCellAspectRatio = 16.0 / 9
        # image cycling
        self.__cycleIndex = QtCore.QPersistentModelIndex(QtCore.QModelIndex())
        self.__imageCyclingEnabled = True

    def __getStyle(self):
        """
        Get the QStyle of self._view. This is stored so we don't have to keep calling
        self._view.style() or QtWidgets.QApplication.style()

        :return:
            The current style
        :rtype:
            QtCore.QStyle
        """
        if self.__viewStyle is not None:
            return self.__viewStyle
        self.__viewStyle = self._view.style() if self._view else QtWidgets.QApplication.style()
        return self.__viewStyle

    def _getForegroundColor(self, option, index):
        """
        To be re-implemented in subclasses

        :parameters:
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to query
        """
        return None

    def _getBackgroundColor(self, option, index):
        """
        To be re-implemented in subclasses

        :parameters:
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to query
        """
        return None

    def _getBorderColor(self, option, index):
        """
        To be re-implemented in subclasses

        :parameters:
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to query
        """
        return None

    def _getFont(self, option, index):
        """
        To be re-implemented in subclasses

        :parameters:
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to query
        """
        return None

    def _paintImage(self, painter, option, index):
        """
        Draw an image in the cell

        :parameters:
            painter : QtGui.QPainter
                painter to draw the image with
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to draw
        """
        # using old method for now
        imageFile = index.data()
        if not imageFile:
            return
        model = index.model()
        # only load an image where one hasn't already been loaded
        origImage = image = index.data(role=ROLE_IMAGE)
        origScaledImage = scaledImage = index.data(role=self.ROLE_SCALED_IMAGE)
        origFailedImage = failedImage = index.data(role=self.ROLE_FAILED_IMAGE)
        # On OSX 10.9 PyQt 4.10 replaces null QImages with QPyNullVariants when retreiving them from a model
        if image is not None and not isinstance(image, QtGui.QImage):
            image = QtGui.QImage()
        if scaledImage is not None and not isinstance(scaledImage, QtGui.QImage):
            scaledImage = QtGui.QImage()
        if not failedImage:
            if image is None:
                # if it's a null image or a loading image, load it.
                scaledImage = image = self.__imageLoader.loadImage(
                    imageFile,
                    None,
                    QtCore.QPersistentModelIndex(index)
                )
            # if it's not a null image or a loading image...
            if not image.isNull():
                if scaledImage is None:
                    scaledImage = image
                scaledImageSize = scaledImage.size()
                targetSize = option.rect.size().boundedTo(image.size())
                targetSize.setHeight(int(targetSize.width() / self.__imageCellAspectRatio))
                if scaledImageSize.width() != targetSize.width() and scaledImageSize.height() != targetSize.height():
                    scaledImage = image.scaled(targetSize,
                                               QtCore.Qt.KeepAspectRatio,
                                               QtCore.Qt.SmoothTransformation)
            else:
                failedImage = True
            # if <image> is null, set scaled image to null as well
            # this would make null images show up as failed, we could maybe have a more neutral icon?
            # scaledImage = self.__imageLoader._imageMissingLrg
            # update model data
            dataUpdateMap = {}
            if origImage is not image:
                dataUpdateMap[ROLE_IMAGE] = image
            if origScaledImage is not scaledImage:
                dataUpdateMap[self.ROLE_SCALED_IMAGE] = scaledImage
            if origFailedImage != failedImage:
                dataUpdateMap[self.ROLE_FAILED_IMAGE] = failedImage
            if dataUpdateMap:
                model.setItemData(index, dataUpdateMap)
        # center the image in the cell
        targetRect = scaledImage.rect()
        targetRect.moveCenter(option.rect.center())
        # draw the image
        painter.save()
        painter.drawImage(targetRect, scaledImage)
        # Image cycling icon ( test )
        # if common.imageFormatIsAnimatable( imageFile ) and os.path.isfile( imageFile ):
        # 	animIcon = QtGui.QImage( common.ICON_CLAPBOARD_SML )
        # 	animIconSize = animIcon.size()
        # 	brPoint = targetRect.bottomRight() - QtCore.QPoint( animIconSize.width(), animIconSize.height() )
        # 	painter.drawImage( brPoint, animIcon ) # TODO proper icon
        painter.restore()

    def _displayText(self, index, dataType):
        """
        Get the text for a cell

        :parameters:
            index : QtCore.QModelIndex
                index of the cell to get text for
        """
        # TODO: speed this up further, if possible
        value = index.data(QtCore.Qt.DisplayRole)
        return str(value)

    def _thumbnailRect(self, index):
        """
        Get the bounding rect of a model index.

        :parameters:
            index : QtCore.QModelIndex
                index to get the bounding rect of
        :return:
            index bounding rect
        :rtype:
            QtCore.QRect
        """
        return self._view.visualRect(index)

    def clearImageLoaderTaskQueue(self):
        self.__imageLoader.clearUnfinishedTasks()

    def setShadedSortColumn(self, enabled):
        """
        Set whether sorted columns are shaded

        :parameters:
            enabled : bool
                True == shaded
        """
        self.__shadedSortColumn = enabled

    def initStyleOption(self, option, index, model=None, dataType=None):
        """
        Initialize <option> with the values using the index <index>.

        :parameters:
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to draw
        """
        # TODO: speed this up further, by caching more?
        QtWidgets.QStyledItemDelegate.initStyleOption(self, option, index)

        editBitMask = 0

        if model is None:
            model = index.model()

        column = index.column()
        item = None
        if model:
            item = model.itemFromIndex(index)
            if dataType is None:
                dataType = model.dataType(index)
            if model.isEditMode:
                # get the edit type for this column
                if item:
                    editBitMask = item.editBitMask(index.column())
        # border color
        option.borderColor = self._getBorderColor(option, index)

        # catch qvariants
        isError, bgrole, fgrole = item.getStyleData(column)

        # background color
        bgColor = None
        # text color
        fgColor = None
        if isError:  # errored item
            pass
        else:
            if bgrole:
                bgColor = QtGui.QColor(bgrole)
            else:
                bgColor = self._getBackgroundColor(option, index)

            if fgrole:
                fgColor = QtGui.QColor(fgrole)
            else:
                fgColor = self._getForegroundColor(option, index)

        # overlay the custom background color
        if isinstance(bgColor, QtGui.QColor) and bgColor.isValid():
            option.backgroundBrush = QtGui.QBrush(bgColor)
        if isinstance(fgColor, QtGui.QColor) and fgColor.isValid():
            option.palette.setColor(QtGui.QPalette.Text, fgColor)

        # text font
        font = None
        if editBitMask:
            if editBitMask & EDITBITMASK_DELETE:
                # use strikethrough with deletion edits
                font = option.font
                font.setStrikeOut(True)
        else:
            font = self._getFont(option, index)
        # why is instance? why not is not None?
        if isinstance(font, QtGui.QFont):
            option.font = font

        # alignment
        option.displayAlignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        if index.column() == 0:
            option.displayAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        # set display text
        if model:
            displayText = self._displayText(index, dataType)
            if displayText is not None:
                if hasattr(option, "features"):
                    option.features |= QtWidgets.QStyleOptionViewItem.HasDisplay
                option.text = displayText

    def old_paint(self, painter, option, index):
        """
        Paint the cell

        :parameters:
            painter : QtGui.QPainter
                painter to draw the cell with
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to draw
        """
        option4 = QtWidgets.QStyleOptionViewItem(option)
        i_model = index.model()
        # TODO: cache the data type of the model, if seen before
        dataType = i_model.dataType(index)

        self.initStyleOption(option4, index, model=i_model, dataType=dataType)
        style = self._view.style()

        if dataType == TYPE_IMAGE:
            # draw background
            style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option4, painter, self._view)
            # paint image
            self._paintImage(painter, option, index)
        elif dataType == TYPE_BOOLEAN:
            # draw background
            style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option4, painter, self._view)
            # paint checkbox
            self._paintBoolean(painter, option4, index)
        else:
            # paint everything normally
            style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, option4, painter, self._view)
        # paint border
        if option4.borderColor:
            oldPen = painter.pen()
            painter.setPen(option4.borderColor)
            if option4.viewItemPosition == option4.OnlyOne:
                painter.drawRect(option4.rect.adjusted(0, 0, -1, -1))
            else:
                topRight = option4.rect.topRight()
                topLeft = option4.rect.topLeft()
                bottomRight = option4.rect.bottomRight()
                bottomLeft = option4.rect.bottomLeft()
                drawLine = painter.drawLine
                # draw rect edges
                drawLine(topLeft, topRight)
                drawLine(bottomLeft, bottomRight)
                if option4.viewItemPosition == option4.Beginning:
                    drawLine(topLeft, bottomLeft)
                elif option4.viewItemPosition == option4.End:
                    drawLine(topRight, bottomRight)
            painter.setPen(oldPen)

    def paint(self, painter, option, index):
        """
        """
        origRect = QtCore.QRect(option.rect)
        if self._view.showGrid():
            # remove 1 pixel from right and bottom edge of rect, to
            # make room for drawing grid
            option.rect.setRight(option.rect.right() - 1)
            option.rect.setBottom(option.rect.bottom() - 1)

        # paint the item
        self.old_paint(painter, option, index)

        # draw the vertical grid lines (horizontal lines are painted
        # in TreeView.drawRow())
        if self._view.showGrid():
            painter.save()
            gridHint = QtWidgets.QApplication.style().styleHint(QtWidgets.QStyle.SH_Table_GridLineColor, option, self._view,
                                                            None)
            # must ensure that the value is positive before
            # constructing a QColor from it
            # http://www.riverbankcomputing.com/pipermail/pyqt/2010-February/025893.html
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            # paint the vertical line
            painter.drawLine(origRect.right(), origRect.top(), origRect.right(), origRect.bottom())
            painter.restore()

    def old_size_hint(self, option, index):
        i_dataType = None
        i_model = index.model()
        if i_model:
            i_dataType = i_model.dataType(index)

        size = index.data(QtCore.Qt.SizeHintRole)
        if not size:
            option4 = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(option4, index, model=i_model, dataType=i_dataType)
            style = self._view.style()
            size = style.sizeFromContents(QtWidgets.QStyle.CT_ItemViewItem, option4, QtCore.QSize(), self._view)

        # if it is an image column and has data...
        if i_model and i_dataType == TYPE_IMAGE and index.data(QtCore.Qt.DisplayRole):
            imageHeight = int(self._view.topHeader().sectionSize(
                index.column()) / self.__imageCellAspectRatio)  # give the cell a 16/9 aspect ratio
            if imageHeight > size.height():
                size.setHeight(imageHeight)

        size = QtCore.QSize(32, 32)

        return size if isinstance(size, QtCore.QSize) else size.toSize()

    def sizeHint(self, option, index):
        """
        :parameters:
            option :QStyleOptionViewItem
                drawing parameters
            index : QModelIndex
                index of item
        """
        # TODO: speed this up, by caching more?
        widget = self._view.indexWidget(index)
        if widget:
            hint = widget.sizeHint()
            gridSize = 1 if self._view.showGrid() else 0
            return QtCore.QSize(hint.width(), hint.height() + gridSize)

        hint = self.old_size_hint(option, index)

        if self._view.showGrid():
            if self.MARGIN is None:
                self.MARGIN = QtWidgets.QApplication.style().pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, None)
            margin = self.MARGIN
            minimumHeight = max(QtWidgets.QApplication.globalStrut().height(), option.fontMetrics.height() + margin)
            return QtCore.QSize(hint.width(), max(hint.height(), minimumHeight))

        return hint

    def createEditor(self, parent, option, index):
        """
        Create an editor widget based on the column type

        :parameters:
            parent : QtCore.QObject
                the parent for the type handler gui
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index to get the data type info from
        :return:
             a type handler gui
        :rtype:
            wizqt.core.type_handler.AbstractTypeHandler
        """
        dataType = index.model().dataType(index)
        # images are not editable and booleans checkboxes behave as an active widget at all times
        # so no need to create an editor in the usual way
        # if dataType not in [TYPE_IMAGE, TYPE_BOOLEAN]:
        #     dataTypeHandler = getTypeHandler(dataType)
        #     editor = dataTypeHandler.getInputWidget(parent)
        #     # set the possible options for enum combo boxes
        #     # FIXME: should be done with extra args to getInputWidget?
        #     if dataType == TYPE_ENUM:
        #         # first try getting possible values from index itself
        #         possibleVals = index.data(ROLE_POSSIBLE_VALUES)
        #         if possibleVals is None:
        #             # next try getting possible values from header
        #             possibleVals = index.model().headerData(index.column(), QtCore.Qt.Horizontal,
        #                                                     ROLE_POSSIBLE_VALUES)
        #         if isinstance(possibleVals, list):
        #             editor.addItems(map(unicode, possibleVals))
        #     return editor
        # return None

    def editorEvent(self, event, model, option, index):
        """
        When editing of an item starts, this function is called with the event that triggered the editing

        :parameters:
            event : QtCore.QEvent
                the event object
            model : QtCore.QAbstractItemModel
                model of the view that this is the delegate of
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                the index of the item being edited
        :return:
            the item has been edited
        :rtype:
            bool
        """
        # deal with checking of boolean checkbox
        dataType = model.dataType(index)
        if dataType == TYPE_BOOLEAN:
            # both the item and the delegate must be editable
            # if not (self._isEditable and item and item.isEditable(column)):
            # 	return False
            currVal = index.data()
            newVal = not currVal
            # handle left mouse button click
            if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
                # determine if mouse clicked inside the checkbox
                checkboxRect = self._getCheckboxRect(option.rect)
                if checkboxRect.contains(event.pos()):
                    # change the boolean value of the model index
                    model.setData(index, newVal)
                    return True
            # handle spacebar/select key press
            elif event.type() == QtCore.QEvent.KeyPress and event.key() in [QtCore.Qt.Key_Space, QtCore.Qt.Key_Select]:
                # change the boolean value of the model index
                model.setData(index, newVal)
                return True
            return False
        else:
            return super(Delegate, self).editorEvent(event, model, option, index)


class ModelMimeData(QtCore.QMimeData):
    # properties
    sourceModel = property(fget=lambda self: self._sourceModel)
    sourceIndexes = property(fget=lambda self: self.__getIndexes())

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
        return QtCore.QMimeData.formats(self) + [MIME_TYPE_PLAIN_TEXT, MIME_TYPE_MODEL_INDEXES]

    def retrieveData(self, format, preferredType):
        """
        """
        if format == MIME_TYPE_PLAIN_TEXT:
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


class ModelItem(object):
    DEFAULT_FLAGS = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
    DEFAULT_DATA = {ROLE_IS_SORTABLE: True, }

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

    def setDataType(self, dataType):
        self._dataType = dataType

    def __len__(self):
        # Use the stored length rather than recalculating it
        return self._itemDataLen

    def __str__(self):
        return "[%s]" % ", ".join([str(self.data(i)) for i in xrange(self._itemDataLen)])

    def __repr__(self):
        return str(self)

    def copyData(self, otherItem):
        # FIXME: is this everything we need?
        for column in xrange(len(otherItem)):
            for role in [QtCore.Qt.DisplayRole, QtCore.Qt.DecorationRole, QtCore.Qt.BackgroundRole,
                         QtCore.Qt.ForegroundRole, ROLE_CATEGORY, ROLE_FILE_PATH]:
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
            err = coldata[ROLE_ERROR]
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
                err = self.DEFAULT_DATA[ROLE_ERROR]
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
        # ROLE_TREE_NODE, most useful for inherited
        # objects.
        return self.data(column, ROLE_TREE_NODE)

    def setData(self, value, column=0, role=QtCore.Qt.DisplayRole):
        if self._itemData[column] is None:
            self._itemData[column] = {}
        # NOTE: the roles are ints, would and array of arrays be better. The trouble is its sparse and all sorts of rules might exist
        self._itemData[column][role] = value
        return True

    def setDataRoleTreeNode(self, value, column):
        """A short-cut wrapper for setData(index, value,
        ROLE_TREE_NODE) for use by inheriting objects to
        avoid the need to import the ROLE_TREE_NODE constant.
        """
        return self.setData(value, column, ROLE_TREE_NODE)

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
                EDITBITMASK_INSERT | EDITBITMASK_DELETE | EDITBITMASK_ARCHIVE | EDITBITMASK_DISABLE | EDITBITMASK_REVIVE | EDITBITMASK_ENABLE | EDITBITMASK_UPDATE | EDITBITMASK_MOVE):
            # no valid edits
            return 0

        editBitMask = 0

        # insert edits can't co-exist with any other type
        if self._editBitMask & EDITBITMASK_INSERT:
            return EDITBITMASK_INSERT

        # delete and revive edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DELETE:
            editBitMask |= EDITBITMASK_DELETE
        elif self._editBitMask & EDITBITMASK_REVIVE:
            editBitMask |= EDITBITMASK_REVIVE

        # delete and enable edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DELETE:
            editBitMask |= EDITBITMASK_DELETE
        elif self._editBitMask & EDITBITMASK_ENABLE:
            editBitMask |= EDITBITMASK_ENABLE

        # disable and enable edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DISABLE:
            editBitMask |= EDITBITMASK_DISABLE
        elif self._editBitMask & EDITBITMASK_ENABLE:
            editBitMask |= EDITBITMASK_ENABLE

        # archive and enable edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_ARCHIVE:
            editBitMask |= EDITBITMASK_ARCHIVE
        elif self._editBitMask & EDITBITMASK_ENABLE:
            editBitMask |= EDITBITMASK_ENABLE

        # archive and revive edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_ARCHIVE:
            editBitMask |= EDITBITMASK_ARCHIVE
        elif self._editBitMask & EDITBITMASK_REVIVE:
            editBitMask |= EDITBITMASK_REVIVE

        # disable and revive edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DISABLE:
            editBitMask |= EDITBITMASK_DISABLE
        elif self._editBitMask & EDITBITMASK_REVIVE:
            editBitMask |= EDITBITMASK_REVIVE

        if self._editBitMask & EDITBITMASK_MOVE:
            origParentId = self._origParentId
            currParentId = self.parent().uniqueId if self.parent() else None
            if origParentId != currParentId:
                editBitMask |= EDITBITMASK_MOVE

        if self._editBitMask & EDITBITMASK_UPDATE:
            # update edits are the only type that can be column specific
            if column is None:
                editBitMask |= EDITBITMASK_UPDATE
            else:
                # check if there is an update edit on this particular column
                for role in self._origData[column]:
                    origData = self._origData[column][role]
                    currData = self.data(column, role)
                    if origData != currData:
                        editBitMask |= EDITBITMASK_UPDATE
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
        if editBitMaskInt & EDITBITMASK_DELETE:
            self._editBitMask &= ~EDITBITMASK_REVIVE  # unset revive bit
        elif editBitMaskInt & EDITBITMASK_REVIVE:
            self._editBitMask &= ~EDITBITMASK_DELETE  # unset delete bit

        # delete and enable edits are mutually exclusive
        if editBitMaskInt & EDITBITMASK_DELETE:
            self._editBitMask &= ~EDITBITMASK_ENABLE  # unset enable bit
        elif editBitMaskInt & EDITBITMASK_ENABLE:
            self._editBitMask &= ~EDITBITMASK_DELETE  # unset delete bit

        # archive and revive edits are mutually exclusive
        if editBitMaskInt & EDITBITMASK_ARCHIVE:
            self._editBitMask &= ~EDITBITMASK_REVIVE  # unset revive bit
        elif editBitMaskInt & EDITBITMASK_REVIVE:
            self._editBitMask &= ~EDITBITMASK_ARCHIVE  # unset archive bit

        # archive and enable edits are mutually exclusive
        if editBitMaskInt & EDITBITMASK_ARCHIVE:
            self._editBitMask &= ~EDITBITMASK_ENABLE  # unset enable bit
        elif editBitMaskInt & EDITBITMASK_ENABLE:
            self._editBitMask &= ~EDITBITMASK_ARCHIVE  # unset archive bit

        # disable and revive edits are mutually exclusive
        if editBitMaskInt & EDITBITMASK_DISABLE:
            self._editBitMask &= ~EDITBITMASK_REVIVE  # unset revive bit
        elif editBitMaskInt & EDITBITMASK_REVIVE:
            self._editBitMask &= ~EDITBITMASK_DISABLE  # unset disable bit

        # disable and enable edits are mutually exclusive
        if editBitMaskInt & EDITBITMASK_DISABLE:
            self._editBitMask &= ~EDITBITMASK_ENABLE  # unset enable bit
        elif editBitMaskInt & EDITBITMASK_ENABLE:
            self._editBitMask &= ~EDITBITMASK_DISABLE  # unset disable bit

        # for move edits, store the current parent id as the original parent
        if editBitMaskInt & EDITBITMASK_MOVE and not self._origParentSet:
            if self.parent():
                self._origParentId = self.parent().uniqueId
            self._origParentSet = True

        # for update edits, store the current data as the original data
        if editBitMaskInt & EDITBITMASK_UPDATE and not self._origDataSet:
            for column in xrange(len(self)):
                self._origData[column] = {}
                for role in ROLES_EDITSTATE:
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
                EDITBITMASK_INSERT | EDITBITMASK_DELETE | EDITBITMASK_ARCHIVE | EDITBITMASK_DISABLE | EDITBITMASK_ENABLE | EDITBITMASK_REVIVE | EDITBITMASK_UPDATE | EDITBITMASK_MOVE):
            # no valid edits
            return None

        assert self._uniqueId
        edit = {"itemId": self._uniqueId, "type": 0}
        if self._editBitMask & EDITBITMASK_INSERT:
            edit["type"] = EDITBITMASK_INSERT

            # parent id
            parent = self.parent()
            if parent and parent.parent():  # if not child of root
                assert parent.uniqueId
                edit["parentId"] = parent.uniqueId

            # column data
            edit["columnData"] = {}
            for column in xrange(len(self)):
                fieldName = self._model.headerData(column, QtCore.Qt.Horizontal,
                                                   ROLE_NAME)  # internal column name
                assert fieldName is not None
                if self._itemData[column]:
                    edit["columnData"][fieldName] = {}
                    for role in self._itemData[column]:
                        value = self.data(column, role)
                        edit["columnData"][fieldName][role] = value

            # no other edits can co-exist with INSERT edits
            return edit

        # delete and revive edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DELETE:
            edit["type"] |= EDITBITMASK_DELETE
        elif self._editBitMask & EDITBITMASK_REVIVE:
            edit["type"] |= EDITBITMASK_REVIVE

        # archive and revive edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_ARCHIVE:
            edit["type"] = EDITBITMASK_ARCHIVE
        elif self._editBitMask & EDITBITMASK_REVIVE:
            edit["type"] |= EDITBITMASK_REVIVE

        # disable and revive edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DISABLE:
            edit["type"] = EDITBITMASK_DISABLE
        elif self._editBitMask & EDITBITMASK_REVIVE:
            edit["type"] |= EDITBITMASK_REVIVE

        # delete and enable edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DELETE:
            edit["type"] |= EDITBITMASK_DELETE
        elif self._editBitMask & EDITBITMASK_ENABLE:
            edit["type"] |= EDITBITMASK_ENABLE

        # archive and enable edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_ARCHIVE:
            edit["type"] = EDITBITMASK_ARCHIVE
        elif self._editBitMask & EDITBITMASK_ENABLE:
            edit["type"] |= EDITBITMASK_ENABLE

        # disable and enable edits are mutually exclusive
        if self._editBitMask & EDITBITMASK_DISABLE:
            edit["type"] = EDITBITMASK_DISABLE
        elif self._editBitMask & EDITBITMASK_ENABLE:
            edit["type"] |= EDITBITMASK_ENABLE

        if self._editBitMask & EDITBITMASK_MOVE:
            # parent id
            origParentId = self._origParentId
            currParentId = None
            parent = self.parent()
            if parent and parent.parent():  # if not child of root
                assert parent.uniqueId
                currParentId = parent.uniqueId
                edit["type"] |= EDITBITMASK_MOVE
                edit["oldParentId"] = origParentId
                edit["newParentId"] = currParentId

        if self._editBitMask & EDITBITMASK_UPDATE:
            # column data
            for column in xrange(len(self)):
                fieldName = self._model.headerData(column, QtCore.Qt.Horizontal,
                                                   ROLE_NAME)  # internal column name
                assert fieldName is not None
                for role in self._origData[column]:
                    origData = self._origData[column][role]
                    currData = self.data(column, role)
                    if origData != currData:
                        # data has changed, store the difference
                        edit["type"] |= EDITBITMASK_UPDATE
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


class ModelItemSorter(QtCore.QObject):
    # constants
    DEFAULT_SORT_DIRECTION = QtCore.Qt.AscendingOrder
    _OPPOSITE_SORT_DIRECTION = int(not DEFAULT_SORT_DIRECTION)
    _SORT_DIRECTION_MAP = {
        TYPE_STRING_SINGLELINE: DEFAULT_SORT_DIRECTION,
        TYPE_STRING_MULTILINE: DEFAULT_SORT_DIRECTION,
        TYPE_INTEGER: _OPPOSITE_SORT_DIRECTION,
        TYPE_UNSIGNED_INTEGER: _OPPOSITE_SORT_DIRECTION,
        TYPE_FLOAT: _OPPOSITE_SORT_DIRECTION,
        TYPE_BOOLEAN: DEFAULT_SORT_DIRECTION,
        TYPE_DATE: _OPPOSITE_SORT_DIRECTION,
        TYPE_DATE_TIME: _OPPOSITE_SORT_DIRECTION,
        TYPE_FILE_PATH: DEFAULT_SORT_DIRECTION,
        TYPE_DN_PATH: DEFAULT_SORT_DIRECTION,
        TYPE_DN_RANGE: DEFAULT_SORT_DIRECTION,
        TYPE_RESOLUTION: _OPPOSITE_SORT_DIRECTION,
        TYPE_IMAGE: DEFAULT_SORT_DIRECTION,
        TYPE_ENUM: DEFAULT_SORT_DIRECTION
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
        if column < 0 or not self._model.headerData(column, QtCore.Qt.Horizontal, ROLE_IS_SORTABLE):
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
        dataType = self._model.headerData(column, QtCore.Qt.Horizontal, ROLE_TYPE)
        if dataType not in TYPES:
            dataType = TYPE_DEFAULT
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
        start = time.time()

        # sort the list
        itemList.sort(cmp=self.__compareItems)

        # recursively sort each child
        for item in itemList:
            item.sortTree(cmp=self.__compareItems)

        end = time.time()

    def __compareItems(self, item1, item2):
        """
        Compare the value of 2 ModelItems based on their dataType.
        """
        comparison = 0
        for (column, direction) in zip(self._sortColumns, self._sortDirections):

            # first compare values by sort role
            sortVal1 = item1.data(column, ROLE_SORT)
            sortVal2 = item2.data(column, ROLE_SORT)
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
            dataType = self._model.headerData(column, QtCore.Qt.Horizontal, ROLE_TYPE)
            if dataType not in TYPES:
                dataType = TYPE_DEFAULT

            # comparison = getTypeHandler(dataType).compare(displayVal1, displayVal2)
            # if comparison != 0:
            #     return comparison if direction == QtCore.Qt.AscendingOrder else -comparison
            #TODO: commented lines above due to incompatiblility
            comparison = None

        return comparison


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

        self.handler = DbHandler()
        self.HEADER_TO_FIELD = OrderedDict({
            "Thumbnail": "thumbnail",
            "Name": "label",
            "Job": "job",
            "Path": "path",
            "Modified": "modified",
            "Created": "created",
            "Owner": "created_by"
        })
        self.setColumnCount(len(self.HEADER_TO_FIELD.keys()))
        self._headerItem = ModelItem(self._columnCount)
        for i, columnName in enumerate(self.HEADER_TO_FIELD.keys()):
            self._headerItem.setData(columnName, i, QtCore.Qt.DisplayRole)
            self._headerItem.setData(columnName, i, ROLE_NAME)

        items = []
        for twig in self.handler.twig(job="GARB").all():
            itemdata = [None for n in self.HEADER_TO_FIELD.keys()]
            for idx, col in enumerate(self.HEADER_TO_FIELD.items()):
                try:
                    data = str(twig[col[1]])
                except KeyError:
                    data = None

                itemdata[idx] = {
                    QtCore.Qt.DisplayRole: data,
                    QtCore.Qt.ToolTipRole: data,
                }

                self.set_pixmap(icon_paths.ICON_PACKAGE_LRG, itemdata, idx, len(twig.stalks()))

            twig_item = ModelItem(len(self._headerItem), uniqueId=twig.uuid, dataObject=twig, itemData=itemdata,
                             dataType="Twig")
            items.append(twig_item)
            for stalk in twig.stalks():
                itemdata = [None for n in self.HEADER_TO_FIELD.keys()]
                for idx, col in enumerate(self.HEADER_TO_FIELD.items()):
                    itemdata[idx] = {QtCore.Qt.DisplayRole: stalk[col[1]],
                                     QtCore.Qt.ToolTipRole: stalk[col[1]]}
                    self.set_pixmap(icon_paths.ICON_VERSION_LRG, itemdata, idx, len(stalk.leafs()))
                stalk_item = ModelItem(len(self._headerItem), uniqueId=stalk.uuid, dataObject=stalk, itemData=itemdata)
                twig_item.appendChild(stalk_item)
                for leaf in stalk.leafs():
                    itemdata = [None for n in self.HEADER_TO_FIELD.keys()]
                    for idx, col in enumerate(self.HEADER_TO_FIELD.items()):
                        itemdata[idx] = {QtCore.Qt.DisplayRole: leaf[col[1]],
                                         QtCore.Qt.ToolTipRole: leaf[col[1]],
                                         QtCore.Qt.SizeHintRole: QtCore.QSize(32, 32)}
                        self.set_pixmap(icon_paths.ICON_FILE_LRG, itemdata, idx)
                    leaf_item = ModelItem(len(self._headerItem), uniqueId=stalk.uuid, dataObject=leaf,
                                           itemData=itemdata)
                    stalk_item.appendChild(leaf_item)
        self._rootItem.appendChildren(items)

    def _generateCompPixmap(self, iconPath):
        # makes a wider pixmap so that there is room to draw the child count
        pixmap = QtGui.QPixmap(iconPath)
        pixmap = pixmap.scaledToHeight(16, QtCore.Qt.SmoothTransformation)
        compPixmap = QtGui.QPixmap(pixmap.width() + 32, pixmap.height())  # add pixel width to draw stalk count
        compPixmap.fill(QtGui.QColor(0, 0, 0, 0))
        # twig pixmap
        painter = QtGui.QPainter(compPixmap)
        painter.drawPixmap(QtCore.QPoint(0, 0), pixmap)
        painter.end()
        return compPixmap

    def set_pixmap(self, icon_path, itemdata, col, child_len=None):
        pixmap = QtGui.QPixmap(self._generateCompPixmap(icon_path))
        if icon_path == icon_paths.ICON_FILE_LRG:
            pixmap = QtGui.QPixmap(icon_path).scaledToHeight(16, QtCore.Qt.SmoothTransformation)
        painter = QtGui.QPainter(pixmap)
        painter.setPen(QtGui.QColor("green"))
        if child_len:
            painter.drawText(16 + 4, 16, str(child_len))
        painter.end()

        if col == 0:
            itemdata[col][QtCore.Qt.DecorationRole] = pixmap

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
        # common.ROLE_TREE_NODE, most useful for inherited
        # objects.
        return self.data(index, ROLE_TREE_NODE)

    def dataType(self, index):
        """
        """
        # check if any type value set on the index itself
        dataType = self.data(index, ROLE_TYPE)
        if dataType in TYPES:
            return dataType

        # next, check if any type value set on the header for this column
        dataType = self.headerData(index.column(), QtCore.Qt.Horizontal, ROLE_TYPE)
        if dataType in TYPES:
            return dataType

        # if nothing explicitly set, return a default value
        return TYPE_DEFAULT

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
                    del self._uniqueIdLookup[uniqueId]
            # lookup failed, search for the item the slow way
            for item in self.iterItems():
                if item.uniqueId == uniqueId:
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
        common.ROLE_TREE_NODE) for use by inheriting objects to
        avoid the need to import the ROLE_TREE_NODE constant.
        """
        return self.setItemData(index, {ROLE_TREE_NODE: value})

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
            if self._isEditMode and role in ROLES_EDITSTATE:
                item.addEdit(EDITBITMASK_UPDATE)
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
                if role == QtCore.Qt.DisplayRole and not self.headerData(section, orientation, ROLE_NAME):
                    success = self._headerItem.setData(value, section, ROLE_NAME)
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
            raise RuntimeError
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
                item.addEdit(EDITBITMASK_INSERT)

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
                        descendant.addEdit(EDITBITMASK_INSERT)

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
                if not item.editBitMask() & EDITBITMASK_INSERT:
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
                parentIndex = self.indexFromItem(parentItem)
                self.beginRemoveRows(parentIndex, first, last)
                parentItem.removeChildren(first, last - first + 1)
                self.totalitemcount -= last - first + 1
                self.endRemoveRows()
        # mark items deleted
        if itemsToMarkDeleted:
            for item in list(itemsToMarkDeleted):
                if item.model is self:
                    item.addEdit(EDITBITMASK_DELETE)
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
                item.addEdit(EDITBITMASK_ARCHIVE)
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
                item.addEdit(EDITBITMASK_DISABLE)
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
                item.addEdit(EDITBITMASK_REVIVE)
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
                item.addEdit(EDITBITMASK_ENABLE)
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
                item.addEdit(EDITBITMASK_MOVE)
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
            item.addEdit(EDITBITMASK_MOVE)
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
            raise RuntimeError
        self._dropAcceptFn = dropAcceptFn

    def supportedDropActions(self):
        """
        """
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def mimeTypes(self):
        """
        """
        return [MIME_TYPE_MODEL_INDEXES]

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
        if not mimeData.hasFormat(MIME_TYPE_MODEL_INDEXES):
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
                    print "CRITICAL!"
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
            self._savedCheckStates[stateId] = checkState

    def getCheckedItems(self, column=0):
        """
        Get any checked items.

        :parameters:
            column : int column index of check box
        :return:
            list of checked items, if items are checkable, or None.
        :rtype:
            list of modelview.ModelItems or None
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
            checkState = self._savedCheckStates[stateId]
            # put in a single shot timer to ensure things like expanding indexes take hold
            QtCore.QTimer.singleShot(0, functools.partial(self.setAllCheckStateItems, checkState))

    def setCheckedItems(self, checkedItemsList, column=0):
        """
        Set items checked.

        :parameters:
            checkedItemsList : list of modelview.ModelItems
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
                if edit["type"] & EDITBITMASK_INSERT:
                    # revert an INSERT edit by deleting the item
                    # FIXME: but what about edits underneath?
                    if not self.removeItem(item):
                        return False
                else:
                    if edit["type"] & EDITBITMASK_UPDATE:
                        # revert column data
                        if "oldColumnData" in edit:
                            for column in xrange(self.columnCount()):
                                columnName = self.headerData(column, QtCore.Qt.Horizontal, ROLE_NAME)
                                if columnName in edit["oldColumnData"]:
                                    if not self.setItemData(index.sibling(index.row(), column),
                                                            edit["oldColumnData"][columnName]):
                                        return False
                    if edit["type"] & EDITBITMASK_MOVE:
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
                    EDITBITMASK_INSERT | EDITBITMASK_DELETE | EDITBITMASK_ARCHIVE | EDITBITMASK_REVIVE | EDITBITMASK_UPDATE | EDITBITMASK_MOVE):
                # no valid edits
                continue
            itemId = edit.get("itemId")
            if itemId is None:
                # no valid item id
                continue
            index = self.indexFromUniqueId(itemId)
            if editBitMask & EDITBITMASK_INSERT:
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
                        columnName = self.headerData(column, QtCore.Qt.Horizontal, ROLE_NAME)
                        if columnName in edit["columnData"] and isinstance(edit["columnData"][columnName], dict):
                            for role in edit["columnData"][columnName]:
                                item.setData(edit["columnData"][columnName][role], column, role)
                # add to model
                self.appendItem(item, parentIndex)
            elif index.isValid():
                item = self.itemFromIndex(index, False)
                if editBitMask & EDITBITMASK_DELETE:
                    # add a delete edit by removing the item
                    self.removeItem(item)
                    if item.model is not self:
                        # item was actually removed from the model, can't apply any further edits
                        continue
                elif editBitMask & EDITBITMASK_REVIVE:
                    # add a revive edit
                    self.reviveItem(item)
                elif editBitMask & EDITBITMASK_ARCHIVE:
                    # add an archive edit
                    self.archiveItem(item)
                if editBitMask & EDITBITMASK_UPDATE:
                    # apply new column data
                    if "newColumnData" in edit and isinstance(edit["newColumnData"], dict):
                        for column in xrange(self.columnCount()):
                            columnName = self.headerData(column, QtCore.Qt.Horizontal, ROLE_NAME)
                            if columnName in edit["newColumnData"] and isinstance(edit["newColumnData"][columnName],
                                                                                  dict):
                                self.setItemData(index.sibling(index.row(), column), edit["newColumnData"][columnName])
                if editBitMask & EDITBITMASK_MOVE:
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
            raise RuntimeError
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


class TopHeaderView(QtWidgets.QHeaderView):
    """
    """

    def __init__(self, parent=None):
        self.__dragLogicalIdx = None
        super(TopHeaderView, self).__init__(QtCore.Qt.Horizontal, parent)
        self.setParent(parent)
        self.__dragTimer = QtCore.QTimer()
        self.__dragTimer.setSingleShot(True)
        # use a slightly smaller font than the default and decrease margins
        self.setStyleSheet("QHeaderView::section { margin: 4px 1px 4px 1px; } QHeaderView { font: 9pt; } ")
        # self.sectionClicked.connect( self._columnClicked )
        self.setSectionsMovable(True)
        self.setSectionsClickable(True)
        self.setMinimumSectionSize(64)

    def __columnIsUnlocked(self, logicalIndex):
        """
        Check if a column is unlocked
        """
        parentView = self.parent()
        return parentView.model().headerData(logicalIndex, QtCore.Qt.Horizontal) not in parentView.LOCKED_COLUMNS

    def _columnClicked(self, column):
        """

        :parameters:

        :return:

        :rtype:

        """
        parentView = self.parent()
        if parentView.isSortingEnabled():
            # check if this column is already being sorted on
            sorter = self.model().sorter
            try:
                idx = sorter.sortColumns.index(column)
            except ValueError:
                # use the default sort direction
                direction = sorter.defaultSortDirection(column)
            else:
                # flip the sort direction
                direction = int(not sorter.sortDirections[idx])

            # do a multisort if the user is holding down the Ctrl key when they click on the column header
            if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier:
                sorter.addSortColumn(column, direction)
            else:
                # not multisorting
                sorter.setSortColumns([column], [direction])

    ##################################################################################################
    # 	events
    ##################################################################################################

    def leaveEvent(self, event):
        QtWidgets.QHeaderView.leaveEvent(self, event)
        self.__dragLogicalIdx = None

    def mouseReleaseEvent(self, event):
        QtWidgets.QHeaderView.mouseReleaseEvent(self, event)
        # if it was a click not a drag, call _columnClicked
        if self.__dragTimer.isActive() and event.button() & QtCore.Qt.LeftButton:
            self._columnClicked(self.logicalIndexAt(event.pos().x()))
        self.__dragLogicalIdx = None
        if event.button() & QtCore.Qt.RightButton:
            self.customContextMenuRequested.emit(event.pos())

    def mousePressEvent(self, event):
        """
        Don't allow user to pick up locked columns
        """
        initialPos = event.pos().x()
        logicalIdx = self.logicalIndexAt(initialPos)
        # if the column is locked, see if there is a
        # different column 3 pixels either side which is unlocked,
        # to account for cursor width
        dragCursorMargin = 3
        self.__dragTimer.start(300)
        if any(
                map(
                    self.__columnIsUnlocked,
                    [logicalIdx, self.logicalIndexAt(initialPos + dragCursorMargin),
                     self.logicalIndexAt(initialPos - dragCursorMargin)]
                )
        ):
            sectionSize = self.sectionSize(logicalIdx)
            # how far the cursor is from the center of the column:
            offset = (self.sectionPosition(logicalIdx) + (sectionSize / 2)) - initialPos
            QtWidgets.QHeaderView.mousePressEvent(self, event)

            self.__dragLogicalIdx = (logicalIdx, offset)

    def mouseMoveEvent(self, event):
        """
        Don't allow user to move locked columns
        """
        if (
                self.cursor().shape() == QtCore.Qt.ArrowCursor and  # not a resize
                event.buttons() == QtCore.Qt.LeftButton and  # not a context menu
                self.__dragLogicalIdx is not None  # is a drag-move
        ):
            scrollOffset = self.offset()
            pos = event.pos().x()  # current mouse x position
            logicalIdx, cursorOffset = self.__dragLogicalIdx  # the logical column index of the column currently being dragged
            draggedSize = self.sectionSize(logicalIdx)  # the size of the column that's being dragged
            rightLogicalIndex = self.logicalIndexAt((pos + (
                        draggedSize / 2) + cursorOffset) - scrollOffset)  # the column under the right hand edge of the dragged column
            leftLogicalIndex = self.logicalIndexAt((pos - (
                        draggedSize / 2) + cursorOffset) - scrollOffset)  # the column under the left hand edge of the dragged column
            centralLogicalIndex = self.logicalIndexAt(pos)  # the column under the cursor
            currentVisualIndex = self.visualIndexAt(pos)
            startVisualIndex = self.visualIndex(logicalIdx)
            columnOnLeftIsLocked = not self.__columnIsUnlocked(
                leftLogicalIndex)  # the column under the left hand edge is locked
            columnOnRightIsLocked = not self.__columnIsUnlocked(
                rightLogicalIndex)  # the column under the right hand edge is locked
            columnUnderMouseIsLocked = not self.__columnIsUnlocked(centralLogicalIndex)

            def snapToLeft():
                # get furthest left column
                furthestLeft = sorted(filter(self.__columnIsUnlocked, range(self.count())), key=self.sectionPosition)[0]
                offset = (self.sectionPosition(furthestLeft) - scrollOffset) + (draggedSize / 2)
                return offset

            def snapToRight():
                # get furthest right column
                furthestRight = sorted(filter(self.__columnIsUnlocked, range(self.count())), key=self.sectionPosition)[
                    -1]
                offset = self.sectionPosition(furthestRight) - (draggedSize / 2) - scrollOffset
                return offset

            offset = None
            # if its gone to the far left and the first column on the far left is locked...
            if currentVisualIndex == 0 and (columnOnLeftIsLocked or columnUnderMouseIsLocked):
                offset = snapToLeft()
            # if its dragged as far right as it can go and the last column is locked...
            elif currentVisualIndex == self.count() - 1 and (columnOnRightIsLocked or columnUnderMouseIsLocked):
                offset = snapToRight()
            # if we've dragged it into left-hand edge of a locked column
            elif startVisualIndex > self.visualIndex(leftLogicalIndex) and (
                    columnOnLeftIsLocked or columnUnderMouseIsLocked):
                offset = snapToLeft()
            # if we've dragged it into right-hand edge of a locked column
            elif startVisualIndex < self.visualIndex(rightLogicalIndex) and (
                    columnOnRightIsLocked or columnUnderMouseIsLocked):
                offset = snapToRight()
            # if we need to override the position because we've hit a locked column...
            if offset is not None:
                QtWidgets.QHeaderView.mouseMoveEvent(
                    self,
                    QtGui.QMouseEvent(
                        event.type(),
                        QtCore.QPoint(offset - cursorOffset, 0),
                        event.button(),
                        event.buttons(),
                        event.modifiers(),
                    )
                )
                return
        QtWidgets.QHeaderView.mouseMoveEvent(self, event)

    def paintSection(self, painter, rect, logicalIndex):
        """
        Re-implementation of QHeaderView.paintSection() to deal with multi-sorting.
        """
        if not rect.isValid():
            return
        painter.save()
        # get the state of the section
        opt = QtWidgets.QStyleOptionHeader()
        self.initStyleOption(opt)
        state = QtWidgets.QStyle.State_None
        if self.isEnabled():
            state |= QtWidgets.QStyle.State_Enabled
        if self.window().isActiveWindow():
            state |= QtWidgets.QStyle.State_Active
        # store some frequently used objects
        setOptBrush = opt.palette.setBrush
        getHeaderData = self.model().headerData
        palette = self.palette()
        orientation = self.orientation()
        # set up sorted column headers
        sortColumns = self.model().sorter.sortColumns
        sortDirections = self.model().sorter.sortDirections
        sortIndex = -1
        if self.isSortIndicatorShown():
            try:
                sortIndex = sortColumns.index(logicalIndex)
            except ValueError:
                pass  # this column is not a part of the multi-sort
            if sortIndex >= 0:
                opt.sortIndicator = QtWidgets.QStyleOptionHeader.SortDown if sortDirections[
                                                                             sortIndex] == QtCore.Qt.AscendingOrder else QtWidgets.QStyleOptionHeader.SortUp
                # paint sorted column slightly darker than normal
                setOptBrush(QtGui.QPalette.Button, QtGui.QBrush(palette.button().color().darker(110)))
                setOptBrush(QtGui.QPalette.Window, QtGui.QBrush(palette.window().color().darker(110)))
                setOptBrush(QtGui.QPalette.Dark, QtGui.QBrush(palette.dark().color().darker(110)))
        # setup the style options structure
        opt.rect = rect
        opt.section = logicalIndex
        opt.state |= state
        opt.text = getHeaderData(logicalIndex, orientation, QtCore.Qt.DisplayRole)
        textAlignment = getHeaderData(logicalIndex, orientation, QtCore.Qt.TextAlignmentRole)
        opt.textAlignment = QtCore.Qt.Alignment(textAlignment if textAlignment is not None else self.defaultAlignment())
        opt.iconAlignment = QtCore.Qt.AlignVCenter
        if self.textElideMode() != QtCore.Qt.ElideNone:
            opt.text = opt.fontMetrics.elidedText(opt.text, self.textElideMode(), rect.width() - 4)
        icon = getHeaderData(logicalIndex, orientation, QtCore.Qt.DecorationRole)
        if icon:
            opt.icon = icon
        foregroundBrush = getHeaderData(logicalIndex, orientation, QtCore.Qt.ForegroundRole)
        if foregroundBrush:
            setOptBrush(QtGui.QPalette.ButtonText, foregroundBrush)
        backgroundBrush = getHeaderData(logicalIndex, orientation, QtCore.Qt.BackgroundRole)
        if backgroundBrush:
            setOptBrush(QtGui.QPalette.Button, backgroundBrush)
            setOptBrush(QtGui.QPalette.Window, backgroundBrush)
            painter.setBrushOrigin(opt.rect.topLeft())
        # determine column position
        visual = self.visualIndex(logicalIndex)
        assert visual != -1
        if self.count() == 1:
            opt.position = QtWidgets.QStyleOptionHeader.OnlyOneSection
        elif visual == 0:
            opt.position = QtWidgets.QStyleOptionHeader.Beginning
        elif visual == self.count() - 1:
            opt.position = QtWidgets.QStyleOptionHeader.End
        else:
            opt.position = QtWidgets.QStyleOptionHeader.Middle
        opt.orientation = orientation
        # draw the section
        self.style().drawControl(QtWidgets.QStyle.CE_Header, opt, painter, self)
        painter.restore()
        # darken if it is a locked column in the view
        if not self.__columnIsUnlocked(logicalIndex):
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, 40))
        # paint a number overlay when multi-sorting
        if sortIndex >= 0 and len(sortColumns) > 1:
            # paint a number indicator when multi-sorting
            text = str(sortIndex + 1)
            headerFont = QtGui.QFont(painter.font())
            headerFont.setPointSize(headerFont.pointSize() - 2)
            textWidth = QtGui.QFontMetrics(headerFont).boundingRect(text).width()
            # calculate the indicator location
            point = QtCore.QPointF(rect.bottomRight())
            point.setX(point.x() - textWidth - 1)
            point.setY(point.y() - 1)
            # paint the number overlay
            painter.save()
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            painter.setFont(headerFont)
            painter.drawText(point, text)
            painter.restore()

    # can't sort with wacom tablet
    # https://bugreports.qt-project.org/browse/QTBUG-4981?page=com.atlassian.jira.plugin.system.issuetabpanels:all-tabpanel

    def sectionSizeFromContents(self, logicalIndex):
        """

        :parameters:

        :return:

        :rtype:

        """
        size = QtWidgets.QHeaderView.sectionSizeFromContents(self, logicalIndex)
        if self.model():
            if self.isSortIndicatorShown() and not self.model().headerData(logicalIndex, self.orientation(),
                                                                           ROLE_IS_SORTABLE):
                # remove the sort indicator margin for columns that aren't sortable
                opt = QtGui.QStyleOptionHeader()
                self.initStyleOption(opt)
                margin = self.style().pixelMetric(QtGui.QStyle.PM_HeaderMargin, opt, self)
                if self.orientation() == QtCore.Qt.Horizontal:
                    size.setWidth(size.width() - size.height() - margin)
                else:
                    size.setHeight(size.height() - size.width() - margin)
            # compensate for icon
            if self.model().headerData(logicalIndex, QtCore.Qt.Horizontal, role=QtCore.Qt.DecorationRole):
                size.setWidth(size.width() + 12)
        return size


class TreeView(QtWidgets.QTreeView):
    LOCKED_COLUMNS = []
    def __init__(self):
        self.__showGrid = True
        super(TreeView, self).__init__()
        self.topHeader = TopHeaderView(self)
        self.setHeader(self.topHeader)
        self.setUniformRowHeights(True)
        self.setModel(Model())
        self.setItemDelegate(Delegate(self))
        self.expandAll()
        self.topHeader.setFirstSectionMovable(True)
        self.topHeader.moveSection(len(self.model()._headerItem) - 1, 0)

    def showGrid(self):
        return True

    def visualRect(self, index):
        """
        """
        rect = QtWidgets.QTreeView.visualRect(self, index)
        if self.__showGrid and rect.isValid():
            # remove 1 pixel from right and bottom edge of rect, to account for grid lines
            rect.setRight(rect.right() - 1)
            rect.setBottom(rect.bottom() - 1)
        return rect

    def drawRow(self, painter, option, index):
        """
        """
        # draw the partially selected rows a lighter colour
        selectionState = index.model().itemFromIndex(index).data(role=ROLE_SELECTION_STATE)
        if selectionState == 1:
            palette = self.palette()
            selectionColor = palette.color(palette.Highlight)
            selectionColor.setAlpha(127)
            painter.save()
            painter.fillRect(option.rect, selectionColor)
            painter.restore()

        QtWidgets.QTreeView.drawRow(self, painter, option, index)

        # draw the grid line
        if self.__showGrid:
            painter.save()
            gridHint = self.style().styleHint(QtWidgets.QStyle.SH_Table_GridLineColor, self.viewOptions(), self, None)
            # must ensure that the value is positive before constructing a QColor from it
            # http://www.riverbankcomputing.com/pipermail/pyqt/2010-February/025893.html
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            # paint the horizontal line
            painter.drawLine(option.rect.left(), option.rect.bottom(), option.rect.right(), option.rect.bottom())
            painter.restore()

    def drawBranches(self, painter, rect, index):
        """
        """

        QtWidgets.QTreeView.drawBranches(self, painter, rect, index)
        # draw the grid line
        if self.__showGrid:
            painter.save()
            gridHint = QtWidgets.QApplication.style().styleHint(QtWidgets.QStyle.SH_Table_GridLineColor, self.viewOptions(),
                                                            self, None)
            # must ensure that the value is positive before
            # constructing a QColor from it
            # http://www.riverbankcomputing.com/pipermail/pyqt/2010-February/025893.html
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            # paint the horizontal line
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
            painter.restore()

    def paintEvent(self, event):
        """
        """
        QtWidgets.QTreeView.paintEvent(self, event)

    def viewportEvent(self, event):
        """
        """
        return QtWidgets.QTreeView.viewportEvent(self, event)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.tree_view = TreeView()
        self.setCentralWidget(self.tree_view)
        self.resize(800, 700)
        TREE_WIDGET = """
                    QTreeView{
                        outline: 0;
                        background: #1e1e1e;
                        color: #D9D9D9;
                        border: 0px;
                        border-radius: 1px;
                        selection-background-color: transparent;
                    }
                    QTreeView:item{
                        background-color: #3e3e3e;
                        margin: 0px 0px 0px 0px;
                        padding: 1px;
                        border: 1px solid #4e4e4e;
                        border-right: 0px;
                    }
                    QTreeView::item:hover{
                        background-color: #807153;
                        color: #D9D9D9
                    }
                    QTreeView::item:selected:hover{
                        color: #D9D9D9;
                    }
                    QTreeView::item:selected{
                        color: #D9D9D9;
                        background-color: #148CD2;
                    }
                    QTreeView::branch:hover{
                        background: #2e2e2e;
                    }
                    QHeaderView::section{
                        background-color: #3e3e3e;
                        color: white;
                    }
                    QScrollBar:vertical{
                        background: #1e1e1e;
                        width: 15px;
                        padding: 1px;
                        margin: 0;
                    }
                    QScrollBar:horizontal{
                        background: #1e1e1e;
                        height: 15px;
                        padding: 1px;
                        margin: 0;
                    }
                    QScrollBar::handle:vertical,
                    QScrollBar::handle:horizontal{
                        background: #3e3e3e;
                    }
                    QScrollBar::handle:vertical:hover,
                    QScrollBar::handle:horizontal:hover{
                        background: #5e5e5e;
                    }
                    QScrollBar::add-line:vertical,
                    QScrollBar::sub-line:vertical,
                    QScrollBar::add-page:vertical,
                    QScrollBar::sub-page:vertical{
                        height: 0px;
                    }
                    QScrollBar::add-line:horizontal,
                    QScrollBar::sub-line:horizontal,
                    QScrollBar::add-page:horizontal,
                    QScrollBar::sub-page:horizontal{
                        width: 0px;
                    }
                """
        # self.tree_view.setStyleSheet(TREE_WIDGET)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())