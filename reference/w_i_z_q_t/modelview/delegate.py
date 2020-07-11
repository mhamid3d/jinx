# Standard imports
import datetime, os
# Local imports
from wizqt import common
from wizqt.core.type_handler import getTypeHandler
from wizqt.core.thread.image_loader import ImageLoader
from pipetheme import utils as theme
# PyQt imports
from qtswitch import QtCore, QtGui

# Constants
#
ERRORBGCOLOUR = theme.getLogLevelColour(common.COLORKEY_CRITICAL, foreground=False)
ERRORFGCOLOUR = theme.getLogLevelColour(common.COLORKEY_CRITICAL)

INT_TYPES = [common.TYPE_INTEGER, common.TYPE_UNSIGNED_INTEGER]


#################################################################################################################################
# 	Delegate
#################################################################################################################################
class Delegate(QtGui.QStyledItemDelegate):
    """Abstract delegate class.

    The wizqt delegate class loads images in a separate thread.
    Any data stored under the :data:`wizqt.common.TYPE_IMAGE` role will be loaded in this way.
    """
    # constants
    CYCLE_FRAME_INTERVAL = 300  # milliseconds
    ONE_MINUTE = datetime.timedelta(minutes=1)
    ONE_HOUR = datetime.timedelta(hours=1)
    ONE_DAY = datetime.timedelta(days=1)
    ROLE_SCALED_IMAGE = common.registerDataRole()
    ROLE_FAILED_IMAGE = common.registerDataRole()

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
        checkboxRect = QtGui.QApplication.style().subElementRect(QtGui.QStyle.SE_CheckBoxIndicator,
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
        QtGui.QApplication.style().drawControl(QtGui.QStyle.CE_CheckBox, buttonStyleOption, painter)
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
        self.__imageLoader = ImageLoader()
        self.__imageLoader.imageLoaded.connect(self.__imageLoaded)
        # image cycling
        self.__cycleIndex = QtCore.QPersistentModelIndex(QtCore.QModelIndex())
        self.__imageCyclingEnabled = True

    def __imageLoaded(self, filePath, targetSize, image, extraArgs):
        """
        Repaint the rect containing the image

        :parameters:
            filePath : str
                path to image file
            targetSize : QtCore.QSize
                intended size of the image
            image : QtGui.QImage
                the image that has been loaded
            extraArgs : list
                Index of model item containing the image
                [ QtCore.QPersistandModelIndex ]
        """
        index = QtCore.QModelIndex(extraArgs[0])
        model = index.model()
        if model is None:
            return
        # On OSX 10.9 PyQt 4.10 replaces null QImages with QPyNullVariants when retreiving them from a model
        if not isinstance(image, QtGui.QImage):
            image = QtGui.QImage()
        model.setItemData(index, {common.ROLE_IMAGE: image, self.ROLE_SCALED_IMAGE: image})
        if image.isNull():
            return
        if index.isValid():
            rect = self._view.visualRect(index)
            if rect.isValid():
                self._view.viewport().repaint(rect)

    def __getStyle(self):
        """
        Get the QStyle of self._view. This is stored so we don't have to keep calling
        self._view.style() or QtGui.QApplication.style()

        :return:
            The current style
        :rtype:
            QtCore.QStyle
        """
        if self.__viewStyle is not None:
            return self.__viewStyle
        self.__viewStyle = self._view.style() if self._view else QtGui.QApplication.style()
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
        origImage = image = index.data(role=common.ROLE_IMAGE)
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
                dataUpdateMap[common.ROLE_IMAGE] = image
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
        return getTypeHandler(dataType).toString(value)

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
        QtGui.QStyledItemDelegate.initStyleOption(self, option, index)

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
        if common.IS_PYQT_SIP1:
            isError = not isError.isNull()

        # background color
        bgColor = None
        # text color
        fgColor = None
        if isError:  # errored items
            bgColor = ERRORBGCOLOUR
            fgColor = ERRORFGCOLOUR
        elif editBitMask:
            # model is in edit mode and cell has edits, paint
            # background based on edit type
            editName = common.getEditName(editBitMask)
            bgColor = theme.getIvyEditColour(editName, foreground=False)
            fgColor = theme.getIvyEditColour(editName)
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
            if editBitMask & common.EDITBITMASK_DELETE:
                # use strikethrough with deletion edits
                font = option.font
                font.setStrikeOut(True)
        else:
            font = self._getFont(option, index)
        # why is instance? why not is not None?
        if isinstance(font, QtGui.QFont):
            option.font = font

        # alignment
        if dataType in INT_TYPES:
            option.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

        # set display text
        if model:
            displayText = self._displayText(index, dataType)
            if displayText is not None:
                if hasattr(option, "features"):
                    option.features |= QtGui.QStyleOptionViewItemV2.HasDisplay
                option.text = displayText

    def paint(self, painter, option, index):
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
        option4 = QtGui.QStyleOptionViewItemV4(option)
        i_model = index.model()
        # TODO: cache the data type of the model, if seen before
        dataType = i_model.dataType(index)

        self.initStyleOption(option4, index, model=i_model, dataType=dataType)
        style = self._view.style()

        if dataType == common.TYPE_IMAGE:
            # draw background
            style.drawPrimitive(QtGui.QStyle.PE_PanelItemViewItem, option4, painter, self._view)
            # paint image
            self._paintImage(painter, option, index)
        elif dataType == common.TYPE_BOOLEAN:
            # draw background
            style.drawPrimitive(QtGui.QStyle.PE_PanelItemViewItem, option4, painter, self._view)
            # paint checkbox
            self._paintBoolean(painter, option4, index)
        else:
            # paint everything normally
            style.drawControl(QtGui.QStyle.CE_ItemViewItem, option4, painter, self._view)
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

    def sizeHint(self, option, index):
        """
        Get the sizehint for a cell

        :parameters:
            option : QtGui.QStyleOption
                style information
            index : QtCore.QModelIndex
                index if the cell to draw
        :return:
            The preferred size
        :rtype:
            QtCore.QSize
        """
        # TODO: speed this up further by caching more?
        i_dataType = None
        i_model = index.model()
        if i_model:
            i_dataType = i_model.dataType(index)

        size = index.data(QtCore.Qt.SizeHintRole)
        if not size:
            option4 = QtGui.QStyleOptionViewItemV4(option)
            self.initStyleOption(option4, index, model=i_model, dataType=i_dataType)
            style = self._view.style()
            size = style.sizeFromContents(QtGui.QStyle.CT_ItemViewItem, option4, QtCore.QSize(), self._view)

        # if it is an image column and has data...
        if i_model and i_dataType == common.TYPE_IMAGE and index.data(QtCore.Qt.DisplayRole):
            imageHeight = int(self._view.topHeader().sectionSize(
                index.column()) / self.__imageCellAspectRatio)  # give the cell a 16/9 aspect ratio
            if imageHeight > size.height():
                size.setHeight(imageHeight)

        return size if isinstance(size, QtCore.QSize) else size.toSize()

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
        if dataType not in [common.TYPE_IMAGE, common.TYPE_BOOLEAN]:
            dataTypeHandler = getTypeHandler(dataType)
            editor = dataTypeHandler.getInputWidget(parent)
            # set the possible options for enum combo boxes
            # FIXME: should be done with extra args to getInputWidget?
            if dataType == common.TYPE_ENUM:
                # first try getting possible values from index itself
                possibleVals = index.data(common.ROLE_POSSIBLE_VALUES)
                if possibleVals is None:
                    # next try getting possible values from header
                    possibleVals = index.model().headerData(index.column(), QtCore.Qt.Horizontal,
                                                            common.ROLE_POSSIBLE_VALUES)
                if isinstance(possibleVals, list):
                    editor.addItems(map(unicode, possibleVals))
            return editor
        return None

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
        if dataType == common.TYPE_BOOLEAN:
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

    def setEditorData(self, editor, index):
        """
        Initialize the editor with the data currently in the cell

        :parameters:
            editor : wizqt.core.type_handler.AbstractTypeHandler
                the editor to set data of
            index : QtCore.QModelIndex
                the index to get the new data from
        """
        dataType = index.model().dataType(index)
        dataTypeHandler = getTypeHandler(dataType)
        # 		TODO
        # 		if isinstance(dataTypeHandler, type_handler.StringMultilineHandler):
        # 			# get the original text with newlines still present
        # 			value = item.data(index.column(), asSingleLine=False)
        # 		else:
        # 			value = item.data(index.column())
        value = index.model().data(index)
        # set the editor data based on the column type
        if not dataTypeHandler.setInputValue(editor, value):
            dataTypeHandler.resetInputValue(editor)

    def setModelData(self, editor, model, index):
        """
        Submit the user-entered data value back to the model

        :parameters:
            editor : wizqt.core.type_handler.AbstractTypeHandler
                the editor to get data from
            model : QtCore.QAbstractItemModel
                the model to set the data to
            index : QtCore.QModelIndex
                the model index to set the new data to
        """
        dataTypeHandler = getTypeHandler(model.dataType(index))
        value = dataTypeHandler.getInputValue(editor)
        model.setData(index, value)

    def startImageCycling(self, index):
        """
        Start frame cycling on a cell at <index>

        :parameters:
            index : QtCore.QModelIndex
                the model index to start frame cycling on
        """
        if self.__imageCyclingEnabled and index.isValid() and index != self.__cycleIndex:
            # stop cycling on old index
            self.stopImageCycling()
            newRect = self._thumbnailRect(index)
            if newRect.isValid():
                filename = str(index.data())
                if not common.imageFormatIsAnimatable(filename) or not os.path.isfile(filename):
                    return
                scaledImage = index.data(role=self.ROLE_SCALED_IMAGE)
                # On OSX 10.9 PyQt 4.10 replaces null QImages with QPyNullVariants when retreiving them from a model
                if scaledImage is None or not isinstance(scaledImage, QtGui.QImage) or scaledImage.isNull():
                    return
                # make the index widget ( QLabel displaying a QMovie )
                movieLabel = QtGui.QLabel()
                movie = QtGui.QMovie(filename, parent=movieLabel)
                movie.setCacheMode(QtGui.QMovie.CacheAll)
                # QMovie bug?, jumpToNextFrame() will only return False for static images after it has been called more than once
                movie.jumpToNextFrame()
                # if there is no frame 1, then it is a static image, so abort.
                # this must be done after it has been set and started playing
                # or the QMovie has no frame attributes
                if movie.jumpToNextFrame() is False:
                    self.stopImageCycling()
                    return
                # movieLabel.setFrameStyle( QtGui.QFrame.Box )
                movieLabel.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
                newSize = scaledImage.size()
                movie.setScaledSize(newSize)
                movieLabel.setFixedSize(newSize)
                movieLabel.setMovie(movie)
                # start playing
                movie.start()
                self.__cycleIndex = QtCore.QPersistentModelIndex(index)
                # set the new index widget
                self._view.setIndexWidget(index, movieLabel)
                # move to center of cell
                movieLabel.move(
                    movieLabel.pos().x() + ((newRect.width() / 2) - (newSize.width() / 2)),
                    movieLabel.pos().y()
                )

    def stopImageCycling(self):
        """
        Stop frame cycling on a cell at <index>

        :parameters:
            index : QtCore.QModelIndex
                the model index to stop frame cycling on
        """
        cycleIndex = QtCore.QModelIndex(self.__cycleIndex)
        indexWidget = self._view.indexWidget(cycleIndex)
        if indexWidget is not None:
            # index widget could be set to something different in subclasses, so we can't be sure
            movie = indexWidget.movie() if hasattr(indexWidget, 'movie') else None
            if movie is not None:
                movie.stop()
            indexWidget.close()
            self._view.setIndexWidget(cycleIndex, None)
            self.__cycleIndex = QtCore.QPersistentModelIndex(QtCore.QModelIndex())

    def enableImageCycling(self, state):
        self.__imageCyclingEnabled = bool(state)
        if not state:
            self.stopImageCycling()

    def imageCyclingEnabled(self):
        return self.__imageCyclingEnabled
