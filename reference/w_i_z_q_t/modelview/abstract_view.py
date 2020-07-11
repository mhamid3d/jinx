"""
	Abstract base class of all views
"""
# Standard imports
import functools
import logging

# Local imports
import wizqt
from wizqt import common, exc
from wizqt.core.lazy_init_event_handler import LazyInitEventHandler
from wizqt.core.action import Action
from wizqt.core.menu_handler import ContextMenu, MenuHandler
from model import Model
from top_header_view import TopHeaderView
from delegate import Delegate
# PyQt imports
from qtswitch import QtGui, QtCore, QT_API
# pipeicon imports
from pipeicon import common as icons

_LOGGER = logging.getLogger(__name__)


# Sorting methods
#
def sortByText(a, b):
    return cmp(a.text(), b.text())


def rowKey(i):
    return i.row()


################################################################################
# DRAG AND DROP EVENTS
################################################################################
class PreDropEvent(QtCore.QEvent):
    """
    Event called before a drop
    """

    def __init__(self, data, action, row, col, parent):
        super(PreDropEvent, self).__init__(common.EVENT_PRE_DROP)
        self.mimeData = data
        self.dropAction = action
        self.row = row
        self.col = col
        self.parent = parent


class PostDropEvent(QtCore.QEvent):
    """
    Event called after a drop
    """

    def __init__(self, data, action, row, col, parent):
        super(PostDropEvent, self).__init__(common.EVENT_POST_DROP)
        self.mimeData = data
        self.dropAction = action
        self.row = row
        self.col = col
        self.parent = parent


class PostDragMoveEvent(QtCore.QEvent):
    """
    Event called after a drag move
    """

    def __init__(self):
        super(PostDragMoveEvent, self).__init__(common.EVENT_POST_DRAG_MOVE)


################################################################################
# StandardMenuHandler
################################################################################
class StandardMenuHandler(MenuHandler):
    """
    """

    def __init__(self, view, parent=None):
        super(StandardMenuHandler, self).__init__(view, parent=parent)
        self._staticActions = [
            Action(
                selectionBased=True,
                text="Copy",
                icon=QtGui.QIcon(icons.ICON_COPY_SML),
                # shortcut = QtGui.QKeySequence.Copy, # we cant use the keyboard if we're using the cursor position.
                isValidFn=self.view._canCopy,
                runFn=self.view._copySelected,
            ),
            Action(
                text="Select All",
                icon=QtGui.QIcon(icons.ICON_SELECT_ALL_SML),
                shortcut=QtGui.QKeySequence.SelectAll,
                isValidFn=self.view._canSelectAll,
                runFn=self.view.selectAll,
            ),
            Action(
                text="Refresh",
                icon=QtGui.QIcon(icons.ICON_REFRESH_SML),
                shortcut=QtGui.QKeySequence.Refresh,
                runFn=self.refreshModel,
            )
        ]

    def refreshModel(self):
        return self.view.doModelRefresh(reload=True)

    def _iterSelected(self):
        """
        Get the current selection in the view.
        Order the indexes by row so that the items are returned in the order they appear.
        """
        # There's no point in iterating if you just get the whole list
        # and sort it and then hand the items back one at a time. So
        # changed this do stop with the yielding all the time.
        # NOTE: I didn't rename the function because of inheritence
        # nightmare that this library gets used inside.

        # If you don't have per column selection enabled
        # (QtGui.QItemSelectionModel.Columns) then calling
        # selectedRows() it much faster and returns 1 entry per row
        # instead of 1 per column per row (many times more).
        #
        selection_model = self.view.selectionModel()
        if (hasattr(selection_model,
                    'getSelectionFlags') and selection_model.getSelectionFlags() & QtGui.QItemSelectionModel.Columns):
            selected_indexes = selection_model.selectedIndexes()
        else:
            selected_indexes = selection_model.selectedRows()

        selected = sorted(selected_indexes, key=rowKey)

        # validate = False because we just got a list of valid indexes
        # so there's no need to validate them again inside
        # itemFromIndex().
        #
        view_model = self.view.model()
        return [view_model.itemFromIndex(index, validate=False) for index in selected]

    def _getSelected(self):
        """
        """
        # TODO: this can be simplified
        itemList = []
        for item in self._iterSelected():
            if item not in itemList:
                itemList.append(item)

        return {
            "modelItems": itemList,
        }

    def _getSelectedItems(self):
        """
        Get the model items for the current selection.
        """
        if not self._selected:
            self._selected = self._getSelected()
        return self._selected["modelItems"]

    def _actionOrder(self):
        """
        Create a list of action names to determine the order that
        the actions are added in.
        """
        return [
            self.SEPARATOR,
            "Copy",
            self.SEPARATOR,
            "Select All",
            "Refresh",
        ]


################################################################################
# ABSTRACT VIEW
################################################################################
class AbstractView(object):
    """This is an abstract base class for common functionality between
    :class:`~wizqt.modelview.tree_view.TreeView` and :class:`~wizqt.modelview.table_view.TableView`.

    This should be inherited by any view which uses the wizqt :class:`~wizqt.modelview.model.Model`.
    It is not generally needed to be inherited directly,
    :class:`~wizqt.modelview.tree_view.TreeView` and :class:`~wizqt.modelview.table_view.TableView` provide higher level base classes.

    This class is intended to be subclassed in conjunction with either :class:`~QtGui.QTreeView` or :class:`~QtGui.QTableView`.
    Because of the multiple inheritance, it is IMPORTANT that this class not derive from :class:`~QtCore.QObject`
    (because the Qt docs say that multiply inheriting from QObject is not supported and results in undefined behavior).
    So instead, we subclass from object but still make function calls here that belong to :class:`~QtGui.QAbstractItemView`.
    This works thanks to Python's dynamically-typed nature.
    """
    # constants
    TOP_HEADER_CLASS = TopHeaderView
    HIDDEN_COLUMNS = []
    LOCKED_COLUMNS = []
    AUTO_SCROLL_MARGIN = 50  # pixels
    AUTO_SCROLL_TIME_INTERVAL = 100  # milliseconds
    AUTO_SCROLL_VERTICAL_INCREMENT = 20  # pixels
    AUTO_SCROLL_HORIZONTAL_INCREMENT = 50  # pixels
    MAX_SAVED_STATES = 3
    IS_CURRENT_QT = common.isCurrentQt()

    dragButton = QtCore.Qt.LeftButton

    MENU_HANDLER_CLASS = StandardMenuHandler

    # properties
    @property
    def contextMenu(self):
        return self.__contextMenu

    @property
    def currentHiddenColumns(self):
        return self.__currentHiddenColumns

    @property
    def currentLockedColumns(self):
        return self.__currentLockedColumns

    @property
    def autoApplyState(self):
        return self.__autoApplyState

    def __init__(self):
        self.installEventFilter(LazyInitEventHandler(self))
        # receive MouseMove events for tracking image cycling
        self.setMouseTracking(True)
        self._sourceModel = None
        self.__isReloading = False

        self.__autoApplyState = True
        self.__maxSavedStates = self.MAX_SAVED_STATES

        # create a set copy so we can edit it at the instance level
        self.__currentHiddenColumns = set(self.HIDDEN_COLUMNS)
        self.__currentLockedColumns = set(self.LOCKED_COLUMNS)
        # saved model states  as a list of (stateId, state) tuples
        self.__savedStates = []
        # use a custom delegate
        self.setItemDelegate(Delegate(self))
        # create actions
        self.__contextMenu = ContextMenu(parent=self)
        self.__contextMenu.setSeparatorsCollapsible(True)
        self._menuHandlers = []
        mainMenuHandler = self.MENU_HANDLER_CLASS(self, parent=self)
        self.addMenuHandler(mainMenuHandler)
        self._createActions()
        # edit button
        self.__editButtonEnabled = False
        self.__editButtonAlignment = QtCore.Qt.AlignRight
        self.__editButtonIndex = QtCore.QModelIndex()
        self.__editButton = QtGui.QToolButton(self)
        self.__editButton.setIcon(QtGui.QIcon(icons.ICON_EDIT_SML))
        self.__editButton.setToolTip("Click to edit...")
        # self.__editButton.setAutoRaise( True )
        self.__editButton.clicked.connect(self.__editButtonClicked)
        self.__editButton.hide()
        # set default values for properties
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        # drag/drop support
        self.setAutoScrollMargin(self.AUTO_SCROLL_MARGIN)
        self._autoScrollTimer = QtCore.QTimer(self)
        self._autoScrollTimer.timeout.connect(self.__doAutoScroll)
        self.__dropIndicatorRect = QtCore.QRect()
        self.__dropIndicatorPosition = None
        # set drop indicator color based on current stylesheet
        self.__dropIndicatorColor = QtCore.Qt.black  # if self.palette().color(QtGui.QPalette.Window).value() >= 128 else QtCore.Qt.white
        # default to copy behaviour between widgets and move behaviour within widgets
        self.setDefaultDropAction(QtCore.Qt.CopyAction)
        # set up the top header
        self.setTopHeader(self.TOP_HEADER_CLASS(self))
        # enable sorting
        self.setSortingEnabled(True)

    def setAutoApplyState(self, autoApply):
        self.__autoApplyState = autoApply

        if autoApply:
            self.__maxSavedStates = self.MAX_SAVED_STATES
        else:
            self.__maxSavedStates = 1

    def setContextMenu(self, newMenu):
        assert isinstance(newMenu, ContextMenu), \
            "<newMenu> must be a wizqt.core.menu_handler.ContextMenu, got {0} instead".format(type(newMenu))
        self.__contextMenu = newMenu
        self.setMenuHandlers(self._menuHandlers)

    ################################################################################################################################
    # Menu handlers
    ################################################################################################################################
    def actions(self):
        actions = []
        map(actions.extend, [menuHandler.allActions for menuHandler in self._menuHandlers])
        return actions + super(AbstractView, self).actions()

    def addMenuHandler(self, newHandler):
        self.__contextMenu.addMenuHandler(newHandler)
        self._menuHandlers.append(newHandler)

    def insertMenuHandler(self, index, newHandler):
        self.__contextMenu.insertMenuHandler(index, newHandler)
        self._menuHandlers.insert(index, newHandler)

    def setMenuHandlers(self, newHandlers):
        self.__contextMenu.setMenuHandlers(newHandlers)
        self._menuHandlers = newHandlers[:]

    def __doAutoScroll(self):
        """
        Scroll when dragging something outside of the edges of the view
        """
        # this private method re-implementation is taken from the source code for QAbstractItemView
        cursorPos = self.viewport().mapFromGlobal(QtGui.QCursor.pos())
        viewportRect = self.viewport().rect()
        autoScrollMargin = self.autoScrollMargin()
        # vertical scroll
        verticalScroll = 0
        if cursorPos.y() - viewportRect.top() < autoScrollMargin:
            acceleration = float(autoScrollMargin - (cursorPos.y() - viewportRect.top())) / autoScrollMargin
            verticalScroll = -self.AUTO_SCROLL_VERTICAL_INCREMENT * acceleration
        elif viewportRect.bottom() - cursorPos.y() < autoScrollMargin:
            acceleration = float(autoScrollMargin - (viewportRect.bottom() - cursorPos.y())) / autoScrollMargin
            verticalScroll = self.AUTO_SCROLL_VERTICAL_INCREMENT * acceleration
        # horizontal scroll
        horizontalScroll = 0
        if cursorPos.x() - viewportRect.left() < autoScrollMargin:
            acceleration = float(autoScrollMargin - (cursorPos.x() - viewportRect.left())) / autoScrollMargin
            horizontalScroll = -self.AUTO_SCROLL_HORIZONTAL_INCREMENT * acceleration
        elif viewportRect.right() - cursorPos.x() < autoScrollMargin:
            acceleration = float(autoScrollMargin - (viewportRect.right() - cursorPos.x())) / autoScrollMargin
            horizontalScroll = self.AUTO_SCROLL_HORIZONTAL_INCREMENT * acceleration
        prevVerticalOffset = self.verticalOffset()
        # move the scrollbars
        prevVerticalValue = self.verticalScrollBar().value()
        prevHorizontalValue = self.horizontalScrollBar().value()
        self.verticalScrollBar().setValue(prevVerticalValue + verticalScroll)
        self.horizontalScrollBar().setValue(prevHorizontalValue + horizontalScroll)
        if prevVerticalValue != self.verticalScrollBar().value():
            # we scrolled vertically, repaint the portion of the viewport where the drop indicator used to be (to erase it)
            if self.__dropIndicatorRect.isValid():
                verticalDelta = self.verticalOffset() - prevVerticalOffset
                if verticalDelta:
                    self.viewport().repaint(self.__dropIndicatorRect.translated(0, -verticalDelta))
        elif prevHorizontalValue == self.horizontalScrollBar().value:
            # nothing changed, stop autoscrolling
            self._autoScrollTimer.stop()

    def _toSourceIndex(self, modelIndex):
        """
        TODO is this ever used?

        :parameters:

        :return:

        :rtype:

        """
        # map a model index into the source index
        index = modelIndex
        model = index.model()
        while isinstance(model, QtGui.QAbstractProxyModel):
            index = model.mapToSource(index)
            if not index.isValid():
                return QtCore.QModelIndex()
            model = model.sourceModel()
        return index

    ################################################################################################################################
    # DRAG/DROP EVENTS
    ################################################################################################################################
    def paintEvent(self, event):
        """
        Change item colour if something is dragged over it.
        """
        if self.__dropIndicatorRect.isValid():
            if self.__dropIndicatorPosition == QtGui.QAbstractItemView.OnItem:
                painter = QtGui.QPainter(self.viewport())
                painter.setPen(
                    QtGui.QPen(QtGui.QBrush(self.__dropIndicatorColor), 3, QtCore.Qt.SolidLine, QtCore.Qt.SquareCap,
                               QtCore.Qt.MiterJoin))
                painter.drawRect(self.__dropIndicatorRect.adjusted(1, 1, -2, -2))
                painter.end()
            elif self.__dropIndicatorPosition in [QtGui.QAbstractItemView.AboveItem, QtGui.QAbstractItemView.BelowItem]:
                painter = QtGui.QPainter(self.viewport())
                painter.fillRect(self.__dropIndicatorRect, self.__dropIndicatorColor)
                painter.end()

    def __isValidDragDropEvent(self, event):
        isInternalMove = self.dragDropMode() == QtGui.QAbstractItemView.InternalMove
        isFromAnotherModel = event.source() is not self
        isMoveAction = event.possibleActions() & QtCore.Qt.MoveAction
        if isInternalMove and (isFromAnotherModel or not isMoveAction):
            return False
        return True

    def __dragDropSameModel(self, event):
        """
        Returns whether or not the given drag/drop event came from the same model as this view
        """
        return hasattr(event.source(), "model") and event.source().model() is self.model()

    def dragEnterEvent(self, event):
        """
        Validate a drag
        """
        if not self.__isValidDragDropEvent(event):
            return

        # if the source and destination models are the same, this is a move action, otherwise it is a copy action
        dropAction = QtCore.Qt.MoveAction if self.__dragDropSameModel(event) else QtCore.Qt.CopyAction
        event.setDropAction(QtCore.Qt.DropAction(dropAction))

        if self._canDecode(event):
            event.accept()
            self.setState(QtGui.QAbstractItemView.DraggingState)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """
        do not also call the superclass's dragMoveEvent, it repaints the entire viewport and is slow
        instead we override it with a speedier implementation
        """
        if not self.__isValidDragDropEvent(event):
            return

        # if the source and destination models are the same, this is a move action, otherwise it is a copy action
        dropAction = QtCore.Qt.MoveAction if self.__dragDropSameModel(event) else QtCore.Qt.CopyAction
        event.setDropAction(dropAction)

        # ignore by default
        event.ignore()

        cursorPos = event.pos()
        viewportRect = self.viewport().rect()
        dropIndex = self.indexAt(cursorPos)
        oldDropIndicatorRect = self.__dropIndicatorRect
        self.__dropIndicatorRect = QtCore.QRect()

        if self._canDecode(event):
            indexRect = self.visualRect(dropIndex)
            self.__dropIndicatorPosition = self._getDropLocation(cursorPos, dropIndex, indexRect, event.mimeData())
            # create a QRect to define the location of the line/box which will act as the drop indicator
            if self.__dropIndicatorPosition == QtGui.QAbstractItemView.AboveItem:
                self.__dropIndicatorRect = QtCore.QRect(indexRect.left(),
                                                        indexRect.top() - 1,
                                                        # TODO: adjustment when TreeView.showGrid() is -2
                                                        indexRect.width(), 3)
                event.accept()
            elif self.__dropIndicatorPosition == QtGui.QAbstractItemView.BelowItem:
                self.__dropIndicatorRect = QtCore.QRect(indexRect.left(),
                                                        indexRect.bottom(),
                                                        indexRect.width(), 3)
                event.accept()
            elif self.__dropIndicatorPosition == QtGui.QAbstractItemView.OnItem:
                self.__dropIndicatorRect = indexRect.adjusted(-1, -1, 1, 2)
                event.accept()
            elif self.__dropIndicatorPosition == QtGui.QAbstractItemView.OnViewport:
                # add as last top-level item
                # TODO: get the visual rect for the last visible item under the root (but how to do that for trees?)
                event.accept()
        # create a custom post-dragmove event
        # to allow for custom event filters to do any postprocessing of the dragemove
        postDragMoveEvent = PostDragMoveEvent()  # TODO: pass any args that may be needed
        postDragMoveEvent.setAccepted(event.isAccepted())
        QtGui.QApplication.sendEvent(self, postDragMoveEvent)
        if self.showDropIndicator() and oldDropIndicatorRect != self.__dropIndicatorRect:
            if oldDropIndicatorRect.isValid():
                # repaint the region where the drop indicator used to be
                self.viewport().repaint(oldDropIndicatorRect)
            # repaint only the portion of the viewport containing the drop indicator
            # this speeds up interaction drastically
            if self.__dropIndicatorRect.isValid():
                self.viewport().repaint(self.__dropIndicatorRect)
        # re-implement autoScroll behavior
        if self.hasAutoScroll():
            autoScrollMargin = self.autoScrollMargin()
            # determine if cursor position is within the autoscroll margin
            if (cursorPos.y() - viewportRect.top() < autoScrollMargin) or \
                    (viewportRect.bottom() - cursorPos.y() < autoScrollMargin) or \
                    (cursorPos.x() - viewportRect.left() < autoScrollMargin) or \
                    (viewportRect.right() - cursorPos.x() < autoScrollMargin):
                self._autoScrollTimer.start(self.AUTO_SCROLL_TIME_INTERVAL)

    def dragLeaveEvent(self, event):
        """
        Remove any drag-over colours when the cursor leaves the view
        """
        self.setState(QtGui.QAbstractItemView.NoState)
        # stop auto scrolling
        self._autoScrollTimer.stop()
        # invalidate the drop indicator when the drag cursor exits the viewport
        self.__dropIndicatorRect = QtCore.QRect()
        self.viewport().update()

    def dropEvent(self, event):
        """
        Must re-implement this method in order to determine the drop location based on our own dropIndicatorPosition
        """
        if not self.__isValidDragDropEvent(event):
            return

        if not self.__dragDropSameModel(event) and self.__defaultDropAction & QtCore.Qt.CopyAction:
            event.setDropAction(QtCore.Qt.DropAction(QtCore.Qt.CopyAction))

        cursorPos = event.pos()
        dropIndex = self.indexAt(cursorPos)
        indexRect = self.visualRect(dropIndex)
        dropPosition = self._getDropLocation(cursorPos, dropIndex, indexRect, event.mimeData())
        assert dropPosition >= 0
        if dropPosition == QtGui.QAbstractItemView.AboveItem:
            parent = dropIndex.parent()
            row = dropIndex.row()
            col = dropIndex.column()
        elif dropPosition == QtGui.QAbstractItemView.BelowItem:
            parent = dropIndex.parent()
            row = dropIndex.row() + 1
            col = dropIndex.column()
        elif dropPosition == QtGui.QAbstractItemView.OnItem:
            parent = dropIndex
            row = -1
            col = -1
        elif dropPosition == QtGui.QAbstractItemView.OnViewport:
            parent = self.rootIndex()
            row = self.model().rowCount(parent)
            col = 0
        if self.dragDropMode() == QtGui.QAbstractItemView.InternalMove:
            event.setDropAction(QtCore.Qt.MoveAction)
        # create a custom pre-drop event
        # to allow for custom event filters to do any preprocessing of the drop
        preDropEvent = PreDropEvent(event.mimeData(), event.dropAction(), row, col, parent)
        preDropEvent.accept()
        QtGui.QApplication.sendEvent(self, preDropEvent)
        # perform the drop
        if preDropEvent.isAccepted():
            if self.model().dropMimeData(event.mimeData(), event.dropAction(), row, col, parent):
                # data was successfully dropped in the model
                event.accept()
                # create a custom post-drop event
                # to allow for custom event filters to do any postprocessing of the drop
                postDropEvent = PostDropEvent(event.mimeData(), event.dropAction(), row, col, parent)
                postDropEvent.setAccepted(event.isAccepted())
                QtGui.QApplication.sendEvent(self, postDropEvent)
            # TODO: select the dropped indexes
        # stop auto scrolling
        self._autoScrollTimer.stop()
        self.setState(QtGui.QAbstractItemView.NoState)
        # invalidate the drop indicator
        self.invalidateDropIndicatorRect()
        self.viewport().update()

    def invalidateDropIndicatorRect(self):
        self.__dropIndicatorRect = QtCore.QRect()

    ################################################################################################################################
    # DRAG/DROP METHODS
    ################################################################################################################################
    def __renderToPixmap(self, indexes):
        """
        Take a snapshot of the row being dragged and return it as a pixmap

        :parameters:
            indexes : list
                QModelIndexes in a list
        :return:
            pixmap of each row at index <indexes>
        :rtype:
            QtGui.QPixmap
        """
        # take a snapshot of the row being dragged, stored as a pixmap
        rect = QtCore.QRect()
        for idx in indexes:
            rect |= self.visualRect(idx)
        # don't paint indexes outside of the visible viewport
        rect = rect.intersected(self.viewport().rect())
        if rect.width() <= 0 or rect.height() <= 0:
            return QtGui.QPixmap()
        # add room for a 1-pixel outline around the rectangle
        rect.adjust(-1, -1, 1, 1)
        pixmap = QtGui.QPixmap(rect.size())
        painter = QtGui.QPainter(pixmap)
        self.viewport().render(painter, QtCore.QPoint(), QtGui.QRegion(rect))
        # draw 1-pixel outline around the rectangle
        painter.setPen(QtGui.QPen(QtGui.QBrush(self.__dropIndicatorColor), 1))
        painter.drawRect(0, 0, rect.width() - 1, rect.height() - 1)
        painter.end()
        return pixmap

    def _canDecode(self, event):
        """
        Check whether a drag can be dropped on the view

        :parameters:
            event : QDragEnterEvent or QDragMoveEvent
                drag event object
        :return:
            True if drop action is valid
        :rtype:
            bool
        """
        if self.model():
            if event.dropAction() & self.model().supportedDropActions():
                mimeTypes = self.model().mimeTypes()
                mimeData = event.mimeData()
                for mimeType in mimeTypes:
                    if mimeData.hasFormat(mimeType):
                        return True
        return False

    def _getDropLocation(self, cursorPos, dropIndex, indexRect, mimeData):
        """
        Get the position of the drop indicator in relation to the index at the current mouse position

        :parameters:
            cursorPos : QtCore.QPoint
                position of mouse cursor
            dropIndex : QtCore.QModelIndex
                parent index of the index under the cursor
            indexRect : QtCore.QRect
                bounding bix of model item under cursor
            mimeData : wizqt.modelview.model.ModelMimeData
                mimedata of the drag object
        :return:
            The drop indicator position
        :rtype:
             QtGui.QAbstractItemView.DropIndicatorPosition
        """
        # returns the drop index and drop indicator position
        if not dropIndex.isValid():
            # dropping on viewport
            # check if root item can accept drops
            if self.model().indexCanAcceptDrop(dropIndex, mimeData):
                # root item can accept drop
                return QtGui.QAbstractItemView.OnViewport
            # reject the drop
            return -1
        parentIndex = dropIndex.parent()
        # do not allow AboveItem/BelowItem when model is set to maintain sort order
        if not self.model().maintainSorted and self.model().indexCanAcceptDrop(parentIndex, mimeData):
            # parent can accept the drop, so AboveItem/BelowItem are possibilities
            if not self.model().indexCanAcceptDrop(dropIndex, mimeData):
                # drop target cannot accept the drop, so ONLY AboveItem/BelowItem are possible
                if cursorPos.y() < indexRect.center().y():
                    return QtGui.QAbstractItemView.AboveItem
                else:
                    return QtGui.QAbstractItemView.BelowItem
            margin = 2
            if cursorPos.y() - indexRect.top() < margin:
                return QtGui.QAbstractItemView.AboveItem
            elif indexRect.bottom() - cursorPos.y() < margin:
                return QtGui.QAbstractItemView.BelowItem
            else:
                return QtGui.QAbstractItemView.OnItem
        # parent cannot accept the drop, so AboveItem/BelowItem are not possibilities
        # only consider OnItem
        if self.model().indexCanAcceptDrop(dropIndex, mimeData):
            return QtGui.QAbstractItemView.OnItem
        # reject the drop
        return -1

    def getDragPixmap(self, dragIndexes):
        """
        Get the correct pixmap for the number of dragged indexes

        :parameters:
            dragIndexes : list
                list of QtCore.QModelIndex
        :return:
            drag pixmap
        :rtype:
            QtGui.QPixmap
        """
        if len(dragIndexes) == 1:
            # take a snapshot of the indexes being dragged, stored as a pixmap
            pixmap = self.__renderToPixmap(self.selectionModel().selectedIndexes())
        else:
            pixmap = QtGui.QPixmap(icons.ICON_MULTIPLE_ITEMS_LRG)
            # draw a number on the icon indicating the number of items being dragged
            textRect = QtCore.QRect(2, 12, 20, 17)
            painter = QtGui.QPainter(pixmap)
            painter.setPen(QtCore.Qt.black)
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(14)
            font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 85)
            painter.setFont(font)
            painter.drawText(textRect, QtCore.Qt.AlignCenter | QtCore.Qt.TextSingleLine | QtCore.Qt.TextDontClip,
                             str(len(dragIndexes)))
            painter.end()
        return pixmap

    def startDrag(self, supportedActions):
        """
        Start a drag

        :parameters:
            supportedActions : QtCore.Qt.DropActions
        """
        # only allow drag on the specified button ( default is LMB)
        if not QtGui.QApplication.mouseButtons() & self.dragButton:
            return
        # get the currently selected draggable indexes
        dragIndexes = []
        model = self.model()
        for index in self.currentSelection():
            if model.flags(index) & QtCore.Qt.ItemIsDragEnabled:
                dragIndexes.append(index)
        if not dragIndexes:
            return
        # get the mime data from the model
        mimeData = model.mimeData(dragIndexes)
        if not mimeData:
            return
        # create the drag object
        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(self.getDragPixmap(dragIndexes))
        # offset the pixmap from the cursor
        if len(dragIndexes) == 1:
            cursorPos = self.viewport().mapFromGlobal(QtGui.QCursor.pos())
            drag.setHotSpot(QtCore.QPoint(cursorPos.x(), -20))
        # set default drop action
        # FIXME: doesn't work in Nuke (older version of Qt)
        # 		defaultDropAction = QtCore.Qt.IgnoreAction
        # 		if self.defaultDropAction() != QtCore.Qt.IgnoreAction and (supportedActions & self.defaultDropAction()):
        # 			defaultDropAction = self.defaultDropAction()
        # 		elif (supportedActions & QtCore.Qt.CopyAction) and self.dragDropMode() != QtGui.QAbstractItemView.InternalMove:
        # 			defaultDropAction = QtCore.Qt.CopyAction
        # begin the drag operation
        drag.exec_(supportedActions)

    # 		if dropAction == QtCore.Qt.MoveAction:
    # 			# remove the items that were just moved
    # 			indexesToRemove = [QtCore.QPersistentModelIndex(idx) for idx in dragIndexes]
    # 			for pIdx in reversed(sorted(indexesToRemove)):
    # 				idx = QtCore.QModelIndex(pIdx)
    # 				self.model().removeRow(idx.row(), idx.parent())

    ################################################################################################################################
    # IMAGE CYCLING METHODS
    ################################################################################################################################
    def _updateImageCycler(self):
        """
        """
        # determine if the cursor is within an image column
        cursorPos = self.viewport().mapFromGlobal(QtGui.QCursor.pos())
        if self.viewport().rect().contains(cursorPos):
            column = self.columnAt(cursorPos.x())
            if column >= 0:
                dataType = self.model().headerData(column, QtCore.Qt.Horizontal, common.ROLE_TYPE)
                if dataType == common.TYPE_IMAGE:
                    # get the specific index under the cursor
                    index = self.indexAt(cursorPos)
                    if index.isValid():
                        self.itemDelegate().startImageCycling(index)
                        return
        self.itemDelegate().stopImageCycling()

    def viewportEvent(self, event):
        """
        """
        if event.type() in (
        event.Enter, event.Leave, event.HoverEnter, event.HoverLeave, event.MouseMove, event.HoverMove):
            self._updateImageCycler()
            self.__updateEditButton()

    ################################################################################################################################
    # EDITING
    ################################################################################################################################
    def setEditButtonEnabled(self, enabled):
        self.__editButtonEnabled = bool(enabled)
        if not self.__editButtonEnabled:
            self.__setEditButtonIndex(QtCore.QModelIndex())

    def setEditButtonAlignment(self, alignment):
        if alignment not in (QtCore.Qt.AlignLeft, QtCore.Qt.AlignRight):
            raise RuntimeError("Invalid value for edit button alignment: %s" % alignment)
        self.__editButtonAlignment = alignment

    def __updateEditButton(self):
        # determine if the cursor is within an editable cell
        if self.__editButtonEnabled:
            cursorPos = self.viewport().mapFromGlobal(QtGui.QCursor.pos())
            index = self.indexAt(cursorPos)
            self.__setEditButtonIndex(index)

    def __setEditButtonIndex(self, index):
        if index.isValid() and self.model().flags(index) & QtCore.Qt.ItemIsEditable and not self.indexWidget(index):
            self.__editButtonIndex = QtCore.QPersistentModelIndex(index)
            # display the edit button on this cell
            indexRect = self.visualRect(index)
            sizeHint = self.__editButton.sizeHint()
            width = min(sizeHint.width(), sizeHint.height(), indexRect.height(), indexRect.width())
            buttonRect = QtCore.QRect(0, 0, width, width)
            buttonRect.moveCenter(indexRect.center())
            if self.__editButtonAlignment == QtCore.Qt.AlignLeft:
                buttonRect.moveLeft(indexRect.left())
            else:
                buttonRect.moveRight(indexRect.right())
            buttonRect.moveTo(self.viewport().mapTo(self, buttonRect.topLeft()))

            # create the edit button
            if self.__editButton is None:
                self.__editButton = QtGui.QToolButton(self)
                self.__editButton.setIcon(QtGui.QIcon(icons.ICON_EDIT_SML))
                self.__editButton.setToolTip("Click to edit...")
                # self.__editButton.setAutoRaise( True )
                self.__editButton.clicked.connect(self.__editButtonClicked)

            # display the edit button
            self.__editButton.setGeometry(buttonRect)
            self.__editButton.show()
        else:
            self.__editButtonIndex = QtCore.QModelIndex()
            if self.__editButton and self.__editButton.isVisible():
                self.__editButton.hide()

    def __editButtonClicked(self):
        if self.__editButtonIndex.isValid():
            index = QtCore.QModelIndex(self.__editButtonIndex)
            self.setCurrentIndex(index)
            self.edit(index)
            self.__setEditButtonIndex(QtCore.QModelIndex())

    ################################################################################################################################
    # model
    ################################################################################################################################
    def _modelAboutToBeRefreshed(self):
        """
        Capture the current view state before everything is replaced
        """
        # capture current model state
        self.captureState()
        # TODO find out how to do this in pyside
        if QT_API != "pyside":
            # set waiting cursor as this is where queries happen
            QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))

    def _modelRefreshed(self):
        """
        Restore a previous state if there is one for this set of items
        """
        # stop loading thumbnails that haven't already loaded, so the queue doesn't grow each time we refresh
        self.itemDelegate().clearImageLoaderTaskQueue()
        # restore saved model state
        if self.__autoApplyState:
            self.restoreState()
        # TODO find out how to do this in pyside
        if QT_API != "pyside":
            # restore cursor
            QtGui.QApplication.restoreOverrideCursor()

    def doModelRefresh(self, force=False, reload=False):
        """
        Refresh data in the model

        :parameters:
            force : bool
                if True, load model data even if view is not visible
            reload : bool
                tell model to do a full refresh, purging any cached data
        """
        if reload:
            self.__isReloading = reload
        if (force or self.isVisible()) and \
                self._sourceModel and hasattr(self._sourceModel, "requestRefresh"):
            # request a model load
            self._sourceModel.requestRefresh(self.__isReloading)
            # reset the reload state
            self.__isReloading = False

    def sourceModel(self):
        """
        Get the model for this view

        :return:
            the current model
        :rtype:
            wizqt.modelview.model.Model
        """
        return self._sourceModel

    def setModel(self, model):
        """
        Set a new model onto this view

        :parameters:
            model : wizqt.modelview.model.Model
                new model
        """
        # disconnect any existing model
        if self._sourceModel:
            self._sourceModel.modelReset.disconnect(self._initializeColumns)
            self._sourceModel.columnsInserted.disconnect(self._initializeColumns)
            self._sourceModel.columnsRemoved.disconnect(self._initializeColumns)
            self._sourceModel.dataNeedsRefresh.disconnect(self.doModelRefresh)
            self._sourceModel.dataAboutToBeRefreshed.disconnect(self._modelAboutToBeRefreshed)
            self._sourceModel.dataRefreshed.disconnect(self._modelRefreshed)
        # get the source model from the model
        sourceModel = model
        while isinstance(sourceModel, QtGui.QAbstractProxyModel):
            sourceModel = sourceModel.sourceModel()
        if not isinstance(sourceModel, Model):
            raise exc.WizQtError(
                "Only subclasses of Model are supported with AbstractView; tried to add model of type '%s'" % \
                sourceModel.__class__.__name__)
        self._sourceModel = sourceModel
        # set up the source model
        if self._sourceModel:
            self._sourceModel.modelReset.connect(self._initializeColumns)
            self._sourceModel.columnsInserted.connect(self._initializeColumns)
            self._sourceModel.columnsRemoved.connect(self._initializeColumns)
            self._sourceModel.dataNeedsRefresh.connect(self.doModelRefresh)
            self._sourceModel.dataAboutToBeRefreshed.connect(self._modelAboutToBeRefreshed)
            self._sourceModel.dataRefreshed.connect(self._modelRefreshed)
        # set up the columns
        self._initializeColumns()
        # restore model state
        if self.__autoApplyState:
            self.restoreState()
        self._applyHiddenColumns()

    def setSelectionModel(self, selectionModel):
        QtGui.QAbstractItemView.setSelectionModel(self, selectionModel)
        self.selectionModel().selectionChanged.connect(self.__contextMenu._populateSelection)

    ################################################################################################################################
    # ACTIONS
    ################################################################################################################################
    def _createActions(self):
        pass

    def _canSelectAll(self):
        """
        Check if the selection model allows multiple selection

        :rtype:
            bool
        """
        return self.selectionMode() not in [QtGui.QAbstractItemView.SingleSelection,
                                            QtGui.QAbstractItemView.NoSelection]

    def _canCut(self):
        """
        Check that there is mimedata on the indexes and they can be deleted

        :rtype:
            bool
        """
        # determine if the selection can be copied
        if not self.selectionModel().selectedIndexes():
            return False
        for idx in self.selectionModel().selectedIndexes():
            mimeData = self.model().mimeData([idx])
            if not mimeData:
                return False
            item = self.model().itemFromIndex(idx)
            if not item.isDeletable():
                return False
        return True

    def _cutSelected(self):
        """
        Cut an item from the model to the clipboard as mimedata
        """
        if self._canCut():
            self._copySelected()
            self._deleteSelected()

    def _canPaste(self):
        """
        Check there is mimedata in the clipboard and the model supports it

        :rtype:
            bool
        """
        # determine if we can paste what's in the clipboard
        mimeData = QtGui.QApplication.clipboard().mimeData()
        if mimeData and self.model():
            for mimeType in self.model().mimeTypes():
                if mimeData.hasFormat(mimeType):
                    return True
        return False

    def _pasteFromClipboard(self):
        """
        Add a new modelitem from the mimedata on the clipboard
        """
        if self._canPaste():
            mimeData = QtGui.QApplication.clipboard().mimeData()
            selectedIndexes = self.currentSelection()
            if selectedIndexes:
                dropParent = selectedIndexes[0]
            else:
                dropParent = self.rootIndex()
            dropColumn = 0
            dropRow = -1
            self.model().dropMimeData(mimeData, QtCore.Qt.CopyAction, dropRow, dropColumn, dropParent)

    def _canCopy(self):
        """
        Check if the model has mimedata and a current selection

        :rtype:
            bool
        """
        # determine if the selection can be copied
        if not self.selectionModel().selectedIndexes():
            return False
        for idx in self.selectionModel().selectedIndexes():
            mimeData = self.model().mimeData([idx])
            if not mimeData:
                return False
        return True

    def _copySelected(self):
        """
        Copy selected indexes data to the clipboard
        """
        if self._canCopy():
            mimeData = self.model().mimeData(self.selectionModel().selectedIndexes())
            QtGui.QApplication.clipboard().setMimeData(mimeData)

    def _canDelete(self):
        """
        Check if the selected indexes can be deleted from the model

        :rtype:
            bool
        """
        # determine if the selection can be deleted
        if not self.selectionModel().selectedIndexes():
            return False
        for idx in self.selectionModel().selectedIndexes():
            item = self.model().itemFromIndex(idx)
            if not item.isDeletable():
                return False
        return True

    def _deleteSelected(self):
        """
        Delete items from the model
        """
        if self._canDelete():
            itemsToDelete = set()
            for index in self.selectionModel().selectedRows():
                item = self.model().itemFromIndex(index)
                if item.isDeletable():
                    itemsToDelete.add(item)
            self.model().removeItems(list(itemsToDelete))

    ################################################################################################################################
    # TOP HEADER METHODS
    ################################################################################################################################
    def _showHeaderContextMenu(self, pos):
        """
        Show a context menu on the header item at point <pos>

        :parameters:
            pos : QtCore.QPoint
                Generally this will be the mouse cursor position
        """
        # get the specific section that was clicked on
        columnIndex = self.topHeader().logicalIndexAt(pos)
        # create a context menu
        menu = QtGui.QMenu(self)
        self._addHeaderContextMenuItems(menu, columnIndex)
        menu.exec_(self.topHeader().mapToGlobal(pos))

    def _generateColumnShowMenu(self, parentMenu, column):
        showMenu = QtGui.QMenu("Show", parentMenu)
        if not self.topHeader().hiddenSectionCount():
            showMenu.menuAction().setEnabled(False)
        else:
            showActions = []
            for logicalIdx in xrange(self.topHeader().count()):
                if self.topHeader().isSectionHidden(logicalIdx):
                    columnName = self.model().headerData(logicalIdx, QtCore.Qt.Horizontal)
                    if not columnName in self.__currentLockedColumns:
                        showActions.append(
                            common.createAction(
                                self,
                                text=columnName,
                                slot=functools.partial(self._showColumn, logicalIdx, column)
                            )
                        )
            # sort alphabetically by column name
            showActions.sort(sortByText)
            showMenu.addActions(showActions)
        return showMenu

    def _addHeaderContextMenuItems(self, menu, col):
        """
        Add actions to the context menu <menu> at column <col>

        :parameters:
            menu : QtGui.QMenu
                the menu
            col : int
                the column index
        """
        getHeaderData = self.model().headerData
        fieldName = getHeaderData(col, QtCore.Qt.Horizontal)
        fieldCannotHide = getHeaderData(col, QtCore.Qt.Horizontal, common.ROLE_CANNOT_HIDE)
        # CONFIGURE ACTION
        # FIXME: temporarily disabling this since old versions of Qt don't have beginMoveRows() and other necessary functions
        configureAction = common.createAction(
            self,
            text="Configure Columns...",
            icon=QtGui.QIcon(icons.ICON_COG_SML),
            slot=self._configureColumns
        )
        menu.addAction(configureAction)
        # manual sort actions ( because wacom tablets don't left click on header views correctly )
        sortAscAction = common.createAction(
            self,
            text="Sort",
            icon=QtGui.QIcon(icons.ICON_UP_ARROW_SML),
            slot=functools.partial(self.sortByColumn, col, direction=QtCore.Qt.DescendingOrder)
        )
        menu.addAction(sortAscAction)
        sortDescAction = common.createAction(
            self,
            text="Sort",
            icon=QtGui.QIcon(icons.ICON_DOWN_ARROW_SML),
            slot=functools.partial(self.sortByColumn, col, direction=QtCore.Qt.AscendingOrder)
        )
        menu.addAction(sortDescAction)
        menu.addSeparator()
        # SHOW/HIDE ACTIONS
        hideAction = common.createAction(self, text="Hide '%s'" % fieldName,
                                         slot=functools.partial(self._hideColumn, col))
        if (fieldCannotHide or
                self.topHeader().hiddenSectionCount() >= self.topHeader().count() - 1 or
                fieldName in self.__currentLockedColumns):
            hideAction.setEnabled(False)
        menu.addAction(hideAction)
        menu.addMenu(self._generateColumnShowMenu(menu, col))
        menu.addSeparator()
        # AUTOSIZE ACTIONS
        autosizeAction = common.createAction(self, text="Auto size '%s'" % fieldName,
                                             slot=functools.partial(self._resizeColumnToContents, col))
        autosizeAction.setEnabled(self.topHeader().resizeMode(col) == QtGui.QHeaderView.Interactive)
        menu.addAction(autosizeAction)
        autosizeAllAction = common.createAction(self, text="Auto size all columns",
                                                slot=self._resizeAllColumnsToContents)
        menu.addAction(autosizeAllAction)
        # FIXME: we can re-enable the ResizeToContents feature once we are using Qt 4.7.0+, which fixes this bug:
        # https://bugreports.qt.nokia.com/browse/QTBUG-12268
        # 		keepAutosizeAction = common.createAction(
        # 											self,
        # 											text = "Keep '%s' auto sized" % fieldName,
        # 											checkable = True,
        # 											signal = "triggered(bool)",
        # 											slot = lambda auto, i = col: self.topHeader().setResizeMode( i, QtGui.QHeaderView.ResizeToContents if auto else QtGui.QHeaderView.Interactive )
        # 											)
        # 		keepAutosizeAction.setChecked( self.topHeader().resizeMode( col ) == QtGui.QHeaderView.ResizeToContents )
        # 		keepAutosizeAction.setEnabled( fieldType != common.TYPE_IMAGE )
        # 		menu.addAction( keepAutosizeAction )
        # 		keepAllAutosizeAction = common.createAction(
        # 											self,
        # 											text = "Keep all columns auto sized",
        # 											checkable = True,
        # 											signal = "triggered(bool)",
        # 											slot = self._keepAllColumnsAutosized
        # 											)
        # 		isChecked = True
        # 		for i in xrange( self.topHeader().count() ):
        # 			if not self.topHeader().isSectionHidden( i ) and self.topHeader().resizeMode( i ) == QtGui.QHeaderView.Interactive:
        # 				isChecked = False
        # 				break
        # 		keepAllAutosizeAction.setChecked( isChecked )
        # 		menu.addAction( keepAllAutosizeAction )
        menu.addSeparator()

    def setTopHeader(self, headerView):
        if hasattr(self, "setHorizontalHeader"):
            self.setHorizontalHeader(headerView)
        elif hasattr(self, "setHeader"):
            self.setHeader(headerView)
        else:
            return
        # initialise the header with this model/view
        headerView.setClickable(True)
        headerView.setMovable(True)
        headerView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        headerView.customContextMenuRequested.connect(self._showHeaderContextMenu)

    def topHeader(self):
        if hasattr(self, "horizontalHeader"):
            return self.horizontalHeader()
        elif hasattr(self, "header"):
            return self.header()
        return None

    @property
    def imageSize(self):
        for column in xrange(self.model().columnCount()):
            fieldType = self.model().headerData(column, QtCore.Qt.Horizontal, common.ROLE_TYPE)
            if fieldType == common.TYPE_IMAGE and not self.topHeader().isSectionHidden(column):
                return self.topHeader().sectionSize(column)
        return 0

    ################################################################################################################################
    # Column methodscd -
    ################################################################################################################################
    def _initializeColumns(self):
        """
        Set the image size for all image columns
        """
        pass

    def addHiddenColumn(self, columnName):
        """
        Add a logical index to self.__currentHiddenColumns
        """
        self.__currentHiddenColumns.add(columnName)
        self._applyHiddenColumns()

    def removeHiddenColumn(self, columnName):
        """
        Remove a logical index from self.__currentHiddenColumns
        """
        if columnName in self.__currentHiddenColumns:
            self.__currentHiddenColumns.remove(columnName)
        self._applyHiddenColumns()

    def setHiddenColumns(self, newhiddenColumnList):
        """
        Replace the hidden column list with anew one
        """
        self.__currentHiddenColumns = set(newhiddenColumnList)
        self._applyHiddenColumns()

    def _applyHiddenColumns(self):
        """
        Hide the columns specified in the self.__currentHiddenColumns list
        """
        getHeaderData = self.model().headerData

        def getLogicalIndex(name):
            for column in range(self.model().columnCount()):
                if getHeaderData(column, QtCore.Qt.Horizontal) == name:
                    return column
            return -1

        for columnName in self.__currentHiddenColumns:
            i = getLogicalIndex(columnName)
            if i != -1:
                self._hideColumn(i)

    def addLockedColumn(self, columnName):
        """
        Add a logical index to self.__currentLockedColumns
        """
        self.__currentLockedColumns.add(columnName)
        self._applyHiddenColumns()

    def removeLockedColumn(self, columnName):
        """
        Remove a logical index from self.__currentLockedColumns
        """
        if columnName in self.__currentLockedColumns:
            self.__currentLockedColumns.remove(columnName)
        self._applyHiddenColumns()

    def setLockedColumns(self, newLockedColumnList):
        """
        Replace the locked column list with anew one
        """
        self.__currentLockedColumns = set(newLockedColumnList)
        self._applyHiddenColumns()

    def _applyLockedColumns(self):
        """
        Hide the columns specified in the self.__currentLockedColumns list
        """
        getHeaderData = self.model().headerData

        def getLogicalIndex(name):
            for column in range(self.model().columnCount()):
                if getHeaderData(column, QtCore.Qt.Horizontal) == name:
                    return column
            return -1

        for columnName in self.__currentLockedColumns:
            i = getLogicalIndex(columnName)
            if i != -1:
                self._hideColumn(i)

    def _showColumn(self, columnIndex, targetIndex):
        """
        Make a column visible

        :parameters:
            columnIndex : int
                index that the column we want to show is currently at
            targetIndex : int
                index that we want the column to be at when it is made visible
        """
        # first move the column to the target column
        fromIdx = self.topHeader().visualIndex(columnIndex)
        toIdx = self.topHeader().visualIndex(targetIndex)
        if fromIdx < toIdx:
            toIdx -= 1
        self.topHeader().moveSection(fromIdx, toIdx)
        # then show the section
        self.topHeader().showSection(columnIndex)
        self._resizeColumnToContents(self.topHeader().logicalIndex(toIdx))

    def _hideColumn(self, columnIndex):
        """
        Hide a column

        :parameters:
            columnIndex : int
                index that the column we want to show is currently at
        """
        self.topHeader().hideSection(columnIndex)

    def _resizeColumnToContents(self, columnIndex):
        """
        Scale a column's width to fit its widest item

        :parameters:
            columnIndex : int
                index that the column we want to show is currently at
        """
        topHeader = self.topHeader()

        def resizeSection(columnIndex):
            # change the resize mode to fit contents
            topHeader.setResizeMode(columnIndex, QtGui.QHeaderView.ResizeToContents)
            # set size explicitly and restore the resize mode
            topHeader.resizeSection(columnIndex, topHeader.sectionSize(columnIndex))
            topHeader.setResizeMode(columnIndex, QtGui.QHeaderView.Interactive)

        def getRealIndex(logicalIndex):
            getHeaderData = self.model().headerData
            orientation = topHeader.orientation()
            getLogicalIndex = topHeader.logicalIndex
            visibleColumns = [getHeaderData(getLogicalIndex(i), orientation)
                              for i in range(topHeader.count())
                              if not topHeader.isSectionHidden(getLogicalIndex(i))]
            return visibleColumns.index(getHeaderData(logicalIndex, orientation))

        if not topHeader.isSectionHidden(columnIndex) and topHeader.resizeMode(
                columnIndex) == QtGui.QHeaderView.Interactive:
            # if its the last column, swap it, resize, then swap back to fix sizing bug
            columnCount = topHeader.count() - topHeader.hiddenSectionCount()
            if getRealIndex(columnIndex) == columnCount - 1:
                visualIndex = topHeader.visualIndex(columnIndex)
                previousIndex = visualIndex - 1
                topHeader.moveSection(visualIndex, previousIndex)
                resizeSection(topHeader.logicalIndex(previousIndex))
                topHeader.moveSection(previousIndex, visualIndex)
            else:
                resizeSection(columnIndex)

    def _resizeAllColumnsToContents(self):
        """
        Scale all column's widths to fit their widest items
        """
        for index in xrange(self.topHeader().count()):
            self._resizeColumnToContents(index)

    def _keepAllColumnsAutosized(self, enable):
        """
        Allow columns to resize themselves when their contents changes

        :parameters:
            enable : bool
                enabled state
        """
        for i in xrange(self.model().columnCount()):
            if not self.topHeader().isSectionHidden(i):
                resizeMode = self.topHeader().resizeMode(i)
                if enable and resizeMode == QtGui.QHeaderView.Interactive:
                    self.topHeader().setResizeMode(i, QtGui.QHeaderView.ResizeToContents)
                elif not enable and resizeMode == QtGui.QHeaderView.ResizeToContents:
                    self.topHeader().setResizeMode(i, QtGui.QHeaderView.Interactive)

    def _getImageColumnWidth(self, columnIndex, targetHeight):
        """
        Get the pixel width of the image after it has been scaled to
        <targetHeight>, keeping its aspect ratio

        :parameters:
            columnIndex : int
                index of the column
            targetHeight : int
                height to scale the image to
        :return:
            The pixel width of the image after it has been scaled to
            <targetHeight>, keeping its aspect ratio
        :rtype:
            int
        """
        targetWidth = 0
        for row in xrange(min(self.model().rowCount(), 1000)):  # limit the search to the first 1000 rows
            modelIndex = self.model().index(row, columnIndex)
            # get the image for this row
            imageFile = modelIndex.data()
            if imageFile and wizqt.common.pingHost(imageFile) is True:
                if isinstance(imageFile, list):
                    imageFile = imageFile[0]
                _LOGGER.debug("########### READING IMAGE %s ############" % imageFile)
                image = QtGui.QImage(imageFile)
                if not image.isNull():
                    targetSize = image.size()
                    # scale the image to the target height, adjusting width proportionally
                    targetSize.scale(0, targetHeight, QtCore.Qt.KeepAspectRatioByExpanding)
                    targetWidth = targetSize.width()
                    break
        return max(targetWidth, self.topHeader().sectionSizeHint(columnIndex))

    def _configureColumns(self):
        """
        Show the column config dialog
        """
        # NOTE: this is not used by the dependency viewer or the
        # twig/stalk viewer thingyies in ivy browser.
        from wizqt.widget.column_config_dialog import ColumnConfigDialog
        # create new dialog and initialize with the view's current layout
        columnConfigDialog = ColumnConfigDialog(self.model(), self)
        columnConfigDialog.applyLayout(self.getLayout())
        if columnConfigDialog.exec_() == QtGui.QDialog.Accepted:
            layout = columnConfigDialog.getLayout()
            _LOGGER.debug("applying layout: %s" % layout)
            self.applyLayout(layout)

    def sortByColumn(self, column, direction=None):
        """
        sort based on order of <column>

        :parameters:
            column : int
                column to sort by
        :keywords:
            direction : QtCore.Qt.SortOrder
                direction to sort by
        """
        if column < 0:
            return
        if direction is None:
            direction = self.topHeader().sortIndicatorOrder()
        if self.model():
            self.model().sorter.setSortColumns([column], [direction])

    ################################################################################################################################
    # EVENTS
    ################################################################################################################################
    def displayInitEvent(self, event):
        pass

    def displayEvent(self, event):
        """
        Refresh the model when the view is displayed
        """
        self.doModelRefresh()

    def mousePressEvent(self, event):
        """
        Reimplement QAbstractItemView.mousePressEvent
        """
        QtGui.QAbstractItemView.mousePressEvent(self, event)

    def contextMenuEvent(self, event):
        """
        Build and show the context menu
        """
        # self.__contextMenu.clear()
        self._createActions()
        self.__contextMenu.exec_(self.mapToGlobal(event.pos()))

    ################################################################################################################################
    # Access methods
    ################################################################################################################################
    def currentSelection(self, minimal=False):
        """
        Returns an unsorted list of currently-selected QModelIndexes
        For TreeViews, if minimal=True then don't include all selected children of a selected parent.
        This is mainly used when propagateSelection is enabled.

        :keywords:
            minimal	: bool
                don't include childrern of selected items
        """
        selectedIndexes = []
        if self.selectionModel():
            if self.selectionBehavior() == QtGui.QAbstractItemView.SelectRows:
                selectedIndexes.extend(self.selectionModel().selectedRows())
            elif self.selectionBehavior() == QtGui.QAbstractItemView.SelectColumns:
                selectedIndexes.extend(self.selectionModel().selectedColumns())
            else:
                selectedIndexes.extend(self.selectionModel().selectedIndexes())
            if minimal and hasattr(self.selectionModel(),
                                   "propagateSelection") and self.selectionModel().propagateSelection():
                # selection propagation is enabled, only return the parents selected, not their children
                for index in selectedIndexes:
                    parentIndex = index.parent()
                    if parentIndex.isValid() and parentIndex in selectedIndexes:
                        # parent index is selected, remove this index from the set
                        selectedIndexes.remove(index)
        # filter out duplicates by unique id because pyside QModelIndexes are not hashable, and cannot be added to a set
        uniqueIndexes = dict(zip(map(self.model().uniqueIdFromIndex, selectedIndexes), selectedIndexes)).values()
        return sorted(uniqueIndexes)

    def setCurrentSelection(self, indexes, scrollTo=True):
        """
        Select indexes

        :parameters:
            indexes : list
                list of QtCore.QModelIndex
        :keywords:
            scrollTo : bool
                scroll to the new selection
        """
        selection = QtGui.QItemSelection()
        selectionBehavior = self.selectionBehavior()
        # store some methods that will be reused several times
        alreadySelected = selection.contains
        model = self.model()
        indexModel = QtCore.QModelIndex.model
        isValid = QtCore.QModelIndex.isValid

        def indexIsValid(index):
            return isValid(index) and indexModel(index) is model and not alreadySelected(index)

        if self.selectionMode() != QtGui.QAbstractItemView.NoSelection:
            for index in indexes:
                if indexIsValid(index):
                    selection.append(QtGui.QItemSelectionRange(index))
        # replace current selection with this
        selectionFlags = QtGui.QItemSelectionModel.ClearAndSelect
        if selectionBehavior == QtGui.QAbstractItemView.SelectRows:
            selectionFlags |= QtGui.QItemSelectionModel.Rows
        elif selectionBehavior == QtGui.QAbstractItemView.SelectColumns:
            selectionFlags |= QtGui.QItemSelectionModel.Columns
        self.selectionModel().select(selection, selectionFlags)

    # scroll to the first selected index
    # FIXME: this causes branches to expand. figure out how to stop this
    # 		if scrollTo and not selection.isEmpty():
    # 			firstIndex = sorted(selection.indexes())[0]
    # 			self.scrollTo(firstIndex, QtGui.QAbstractItemView.PositionAtCenter)
    # 			# but don't scroll in the horizontal direction
    # 			self.horizontalScrollBar().setValue(0)

    def setDefaultDropAction(self, action):
        """
        Set the default action for drops

        :parameters:
            action : QtCore.Qt.DropAction
                the new default drop action
        """
        # set the default drop action
        if action in [QtCore.Qt.CopyAction, QtCore.Qt.MoveAction]:
            self.__defaultDropAction = action

    ################################################################################################################################
    # PERSISTENT SETTINGS
    ################################################################################################################################
    def saveSettings(self, settings):
        """
        Save the current view settings

        :parameters:
            settings : wizqt.core.settings.Settings
                settings object
        """
        settings["layout"] = self.getLayout()
        # capture current model state
        self.captureState()
        # store saved model states
        settings["state"] = self.__savedStates

    def loadSettings(self, settings):
        """
        Load some new view settings

        :parameters:
            settings : wizqt.core.settings.Settings
                settings object
        """
        layout = settings["layout"]
        if layout and isinstance(layout, dict):
            self.applyLayout(layout)
        # load all saved states
        self.__savedStates = []
        savedStates = settings["state"]
        if savedStates and isinstance(savedStates, list):
            for s in savedStates:
                try:
                    (stateId, state) = s
                except ValueError:
                    continue
                if state:
                    self.__savedStates.append((stateId, state))
        # restore current model state
        self.restoreState()
        self._applyHiddenColumns()

    ################################################################################################################################
    # layout
    ################################################################################################################################
    def getLayout(self):
        """
        Get layout info

        :return:
            column/sorting info etc.
        :rtype:
            dict
        """
        layout = {}

        if self.model():

            # ordered list of columnNames
            visibleColumns = []
            # dictionary of {columnName: widthPixels } for each column
            columnWidths = {}

            for visualIdx in xrange(self.topHeader().count()):
                logicalIdx = self.topHeader().logicalIndex(visualIdx)

                columnName = self.model().headerData(logicalIdx, QtCore.Qt.Horizontal, common.ROLE_NAME)

                # column width
                if self.topHeader().resizeMode(logicalIdx) == QtGui.QHeaderView.ResizeToContents:
                    columnWidths[columnName] = "autosize"

                # ordered list of visible columns
                if not self.topHeader().isSectionHidden(logicalIdx):
                    visibleColumns.append(columnName)
                    if columnName not in columnWidths and self.topHeader().resizeMode(
                            logicalIdx) == QtGui.QHeaderView.Interactive:
                        columnWidth = self.topHeader().sectionSize(logicalIdx)
                        if columnWidth != self.topHeader().defaultSectionSize():
                            columnWidths[columnName] = columnWidth

            if visibleColumns:
                layout["visibleColumns"] = visibleColumns

            if columnWidths:
                layout["columnWidths"] = columnWidths

            # ordered list of sort columns/orders
            if self.isSortingEnabled():
                sortInfo = []

                for (column, direction) in zip(self.model().sorter.sortColumns, self.model().sorter.sortDirections):
                    columnName = self.model().headerData(column, QtCore.Qt.Horizontal, common.ROLE_NAME)
                    directionName = "asc" if direction == QtCore.Qt.AscendingOrder else "desc"
                    sortInfo.append((columnName, directionName))

                if sortInfo:
                    layout["sorted"] = sortInfo

        return layout

    def applyLayout(self, layout):
        """
        Apply layout info

        :parameters:
            column/sorting info etc.
        """
        topHeader = self.topHeader()
        columnCount = topHeader.count()
        columnNameToIdx = dict(
            [(self.model().headerData(i, QtCore.Qt.Horizontal, common.ROLE_NAME), i) for i in xrange(columnCount)])
        # apply column visibility/width
        visibleColumns = layout.get("visibleColumns")
        fixedColumns = list(set(self.__currentLockedColumns).difference(self.__currentHiddenColumns))
        fixedColumnPositions = [columnNameToIdx.get(name, -1) for name in fixedColumns]
        hiddenColumns = set(range(columnCount)).difference(fixedColumnPositions)
        columnWidths = layout.get("columnWidths")
        minimumColumnWidth = topHeader.minimumSectionSize()

        def resizeColumn(columnName, columnWidth):
            try:
                logicalIdx = columnNameToIdx[columnName]
            except KeyError:
                return
            if columnWidth == "autosize":
                pass
            # FIXME: we can re-enable the ResizeToContents feature once we are using Qt 4.7.0+, which fixes this bug:
            # https://bugreports.qt.nokia.com/browse/QTBUG-12268
            # topHeader.setResizeMode(logicalIdx, QtGui.QHeaderView.ResizeToContents)
            elif topHeader.resizeMode(logicalIdx) == QtGui.QHeaderView.Interactive:
                topHeader.resizeSection(logicalIdx, max(minimumColumnWidth, columnWidth))

        if visibleColumns and isinstance(visibleColumns, list):
            targetIndex = 0
            for i, columnName in enumerate(visibleColumns):
                try:
                    logicalIdx = columnNameToIdx[columnName]
                except KeyError:
                    continue
                # make column visible
                topHeader.setSectionHidden(logicalIdx, False)
                hiddenColumns.discard(logicalIdx)
                if columnName in fixedColumns:
                    continue
                while targetIndex in fixedColumnPositions and targetIndex < columnCount:
                    targetIndex += 1
                # move to correct position
                visualIndex = topHeader.visualIndex(logicalIdx)
                topHeader.moveSection(visualIndex, targetIndex)
                if columnWidths is not None and columnWidths.has_key(columnName):
                    resizeColumn(columnName, columnWidths.pop(columnName))
                targetIndex += 1
            # hide hidden sections
            for logicalIdx in hiddenColumns:
                topHeader.setSectionHidden(logicalIdx, True)

        # ensure there is at least one visible column
        if topHeader.count() > 0 and topHeader.count() == topHeader.hiddenSectionCount():
            topHeader.setSectionHidden(0, False)

        # set remaining column widths
        if columnWidths and isinstance(columnWidths, dict):
            for (columnName, columnWidth) in columnWidths.items():
                resizeColumn(columnName, columnWidth)

        # apply sort columns/orders
        if self.model() and self.isSortingEnabled():
            sortInfo = layout.get("sorted")
            sortColumns = []
            sortDirections = []
            if sortInfo and isinstance(sortInfo, list):
                for i in xrange(len(sortInfo)):
                    try:
                        (columnName, directionName) = sortInfo[i]
                    except ValueError:
                        continue
                    try:
                        logicalIdx = columnNameToIdx[columnName]
                    except KeyError:
                        continue
                    if directionName == "asc":
                        direction = QtCore.Qt.AscendingOrder
                    elif directionName == "desc":
                        direction = QtCore.Qt.DescendingOrder
                    else:
                        continue
                    sortColumns.append(logicalIdx)
                    sortDirections.append(direction)
            self.model().sorter.setSortColumns(sortColumns, sortDirections)

    ################################################################################################################################
    # state
    ################################################################################################################################
    def captureState(self):
        """
        Store the current selection and scroll state for the current set of items in the view
        """
        # check if model is populated
        if not (self._sourceModel and self._sourceModel.rowCount()):
            return
        stateId = None
        if hasattr(self._sourceModel, "stateId"):
            stateId = self._sourceModel.stateId
        if not stateId:
            stateId = "DEFAULT"
        # first remove any existing state with this same id
        for i in reversed(xrange(len(self.__savedStates))):
            if self.__savedStates[i][0] == stateId:
                self.__savedStates.pop(i)
        state = self.getState()
        if state:
            _LOGGER.debug(
                "Capturing %s model state: %s" %
                ((self._sourceModel.dataSource or self._sourceModel).__class__.__name__, stateId)
            )
            # insert this state to the beginning of the saved state list
            self.__savedStates.insert(0, (stateId, state))
            # trim off the oldest states from the end
            if len(self.__savedStates) > self.MAX_SAVED_STATES:
                self.__savedStates = self.__savedStates[:self.MAX_SAVED_STATES]

    def getState(self):
        """
        Get the current selection and scroll state for the current set of items in the view

        :return:
            {
                'selected' : list(),
                'scroll' : int()
            }
        :rtype:
            dict
        """
        # check if model is populated
        if not (self._sourceModel and self._sourceModel.rowCount()):
            return None
        state = {}
        # selected indexes
        # FIXME: re-enable this once I figure out how to override the selection from elsewhere (i.e. StemViewer/TwigTypePicker)
        selectedIndexes = self.currentSelection(minimal=True)
        # get the unique ids for each index
        selectedIds = set()
        model = self.model()
        for index in selectedIndexes:
            uniqueId = model.uniqueIdFromIndex(index)
            if uniqueId is not None:
                selectedIds.add(uniqueId)
        state["selected"] = sorted(set(selectedIds))
        # save vertical scroll bar position
        state["scroll"] = self.verticalScrollBar().sliderPosition()
        return state

    def restoreState(self):
        """
        Get a saved state and apply it
        """
        if not self._sourceModel:
            return
        stateId = self._sourceModel.stateId if hasattr(self._sourceModel, "stateId") else "DEFAULT"
        for (id, state) in self.__savedStates:
            if id == stateId:
                _LOGGER.debug(
                    "Restoring %s model state: %s" %
                    ((self._sourceModel.dataSource or self._sourceModel).__class__.__name__, stateId)
                )
                # put in a single shot timer to ensure things like expanding indexes take hold
                apply_state_as_soon_as_in_qt_loop = functools.partial(self.applyState, state)
                QtCore.QTimer.singleShot(0, apply_state_as_soon_as_in_qt_loop)
                break

    def applyState(self, state):
        """
        Apply a state to the view

        :parameters:
            state : dict
                {
                    'selected' : list(),
                    'scroll' : int()
                }
        """
        # selected indexes
        # FIXME: re-enable this once I figure out how to override the selection from elsewhere (i.e. StemViewer/TwigTypePicker)
        if "selected" in state and isinstance(state["selected"], list) and state["selected"] != self.currentSelection(
                minimal=True):
            indexes = []
            indexFromId = self.model().indexFromUniqueId
            for uniqueId in set(state["selected"]):
                index = indexFromId(uniqueId)
                if index.isValid():
                    indexes.append(index)
            self.setCurrentSelection(indexes)
        # restore vertical scroll bar position
        if "scroll" in state and isinstance(state["scroll"], int):
            self.verticalScrollBar().setSliderPosition(state["scroll"])
