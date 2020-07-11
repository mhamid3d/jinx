"""Tree view adds tree-specific behaviour to the abstract view.

.. image:: /_static/images/treeViewExample.jpg
"""
# Local imports
from wizqt import common
from wizqt.core.action import Action
from abstract_view import AbstractView, StandardMenuHandler
from wizqt.core.menu_handler import MenuHandler
from delegate import Delegate
# PyQt imports
from qtswitch import QtGui, QtCore


###############################################################################
# TreeSelectionModel
###############################################################################
class TreeSelectionModel(QtGui.QItemSelectionModel):
    """A custom selection model for :class:`TreeView`, which inherits :class:`QtGui.QItemSelectionModel`,
    and adds selection propagation, i.e. when propagation is turned on, by calling ``setPropagateSelection( True )``
    it will select all items below the item that is selected by the mouse.
    """
    STATE_UNSELECTED = 0
    STATE_PARTIALLY_SELECTED = 1
    STATE_SELECTED = 2

    refreshRequested = QtCore.Signal()

    def __init__(self, model, parent=None):
        """
        """
        super(TreeSelectionModel, self).__init__(model, parent)
        self.__propagateSelection = False
        self.__showPartiallySelected = True
        self.__lastselectionflags = 0

    def __propagateSelectionDown(self, selection):
        """
        """
        childSelection = QtGui.QItemSelection()
        indexQueue = selection.indexes()
        while indexQueue:
            index = indexQueue.pop(0)
            if index.isValid():
                numChildren = self.model().rowCount(index)
                childIndexes = [self.model().index(row, 0, index) for row in xrange(numChildren)]
                if childIndexes:
                    # add child indexes to the selection
                    childSelection.append(QtGui.QItemSelectionRange(childIndexes[0], childIndexes[-1]))
                    indexQueue.extend(childIndexes)
        return childSelection

    def _propagateSelectionUp(self, selection, command):
        """
        """
        parentSelection = QtGui.QItemSelection()
        # filter out duplicates by unique id because pyside QModelIndexes are not hashable, and cannot be added to a set
        parentIndexes = map(QtCore.QModelIndex.parent, selection.indexes())
        parentIndexes = dict(zip(map(self.model().uniqueIdFromIndex, parentIndexes), parentIndexes)).values()
        for index in parentIndexes:
            while index.isValid():
                if not (selection.contains(index) or parentSelection.contains(index)):
                    if command & QtGui.QItemSelectionModel.Deselect:
                        # children are being deselected, deselect parents too
                        parentSelection.select(index, index)
                    elif command & QtGui.QItemSelectionModel.Select:
                        # children are being selected, select parent if all children are now selected
                        numChildren = self.model().rowCount(index)
                        if numChildren:
                            numSelected = 0
                            for row in xrange(numChildren):
                                childIndex = self.model().index(row, 0, index)
                                if selection.contains(childIndex) or \
                                        parentSelection.contains(childIndex) or \
                                        (not (command & QtGui.QItemSelectionModel.Clear) and self.isSelected(
                                            childIndex)):
                                    numSelected += 1
                                else:
                                    break
                            if numSelected == numChildren:
                                # all children are selected, select parent too
                                parentSelection.select(index, index)
                index = index.parent()
        return parentSelection

    def setPropagateSelection(self, enabled):
        """
        """
        self.__propagateSelection = bool(enabled)

    def propagateSelection(self):
        """
        """
        return self.__propagateSelection

    def setShowPartiallySelected(self, state):
        self.__showPartiallySelected = bool(state)

    def showPartiallySelected(self):
        return self.__showPartiallySelected

    def setSelectionStates(self, indexes, previous=None):
        """
        go from child up through the parents, setting the ancestors to partially selected
        """
        model = self.model()
        role = common.ROLE_SELECTION_STATE

        def selectUpstream(item, state=self.STATE_PARTIALLY_SELECTED):
            parent = item.parent()
            while parent is not None:
                parent.setData(state, role=role)
                parent = parent.parent()

        itemFromIndex = model.itemFromIndex
        # if there is a previous selection, unselect it
        if previous is not None:
            for index in previous:
                item = itemFromIndex(index)
                # always deselect upstream, in case self.__showPartiallySelected changes between selections
                selectUpstream(item, state=self.STATE_UNSELECTED)
                item.setData(self.STATE_UNSELECTED, role=role)
        # select new
        for item in set(map(itemFromIndex, indexes)):
            # if self.__showPartiallySelected is True, partial-select parents until we hit the root node
            if self.__showPartiallySelected is True:
                selectUpstream(item, state=self.STATE_PARTIALLY_SELECTED)
            item.setData(self.STATE_SELECTED, role=role)
        # emit model data changed signal to trigger view repaint
        model.dataChanged.emit(model.index(0, 0), model.index(model.rowCount(), model.columnCount()))

    def getSelectionFlags(self):
        return self.__lastselectionflags

    def select(self, selection, command):
        """
        Select items

        :parameters:
            selection : QtGui.QItemSelection
                selected model items
            command : QtGui.QItemSelectionModel.SelectionFlags
                NoUpdate: No selection will be made.
                Clear: The complete selection will be cleared.
                Select: All specified indexes will be selected.
                Deselect: All specified indexes will be deselected.
                Toggle: All specified indexes will be selected or deselected depending on their current state.
                Current: The current selection will be updated.
                Rows: All indexes will be expanded to span rows.
                Columns: All indexes will be expanded to span columns.
                SelectCurrent:A combination of Select and Current, provided for convenience.
                ToggleCurrent: A combination of Toggle and Current, provided for convenience.
                ClearAndSelect: A combination of Clear and Select, provided for convenience.
        """
        if self.__propagateSelection:
            # propagate selection to children/parents of selected indexes
            if isinstance(selection, QtCore.QModelIndex):
                selection = QtGui.QItemSelection(selection, selection)
            # propagate selection down to children
            childSelection = self.__propagateSelectionDown(selection)
            # propagate selection up to parents
            parentSelection = self._propagateSelectionUp(selection, command)
            selection.merge(childSelection, QtGui.QItemSelectionModel.SelectCurrent)
            selection.merge(parentSelection, QtGui.QItemSelectionModel.SelectCurrent)

        # NOTE: the 'command' parameter is really the 'selectionFlags'
        self.__lastselectionflags = command
        if (command & QtGui.QItemSelectionModel.Columns):
            # NOTE: I'm not sure anyone ever has this set but just in
            # case for compatibility. In future we should apptrack
            # this and if no one uses column seleciton then this
            # option should be removed.
            previousSelection = self.selectedIndexes()
        else:
            # This saves on many many duplicates in the selection
            previousSelection = self.selectedRows()

        QtGui.QItemSelectionModel.select(self, selection, command)

        # NOTE: the 'command' parameter is really 'selectionFlags'
        if (command & QtGui.QItemSelectionModel.Columns):
            # NOTE: I'm not sure anyone ever has this set but just in
            # case for compatibility. In future we should apptrack
            # this and if no one uses column seleciton then this
            # option should be removed.
            selected_now = self.selectedIndexes()
        else:
            # This saves on many many duplicates in the selection
            selected_now = self.selectedRows()

        self.setSelectionStates(selected_now, previous=previousSelection)

        self.requestRefresh()

    def requestRefresh(self):
        """
        """
        self.refreshRequested.emit()


################################################################################################################
# TreeDelegate
################################################################################################################
class TreeDelegate(Delegate):
    """Inherits :class:`~wizqt.modelview.delegate.Delegate`,
    and adds vertical grid lines, and custom column sizing for thumbnail column.
    """

    MARGIN = None

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

        hint = Delegate.sizeHint(self, option, index)

        if self._view.showGrid():
            if self.MARGIN is None:
                self.MARGIN = QtGui.QApplication.style().pixelMetric(QtGui.QStyle.PM_HeaderMargin, None)
            margin = self.MARGIN
            minimumHeight = max(QtGui.QApplication.globalStrut().height(), option.fontMetrics.height() + margin)
            return QtCore.QSize(hint.width(), max(hint.height(), minimumHeight))

        return hint

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
        Delegate.paint(self, painter, option, index)

        # draw the vertical grid lines (horizontal lines are painted
        # in TreeView.drawRow())
        if self._view.showGrid():
            painter.save()
            gridHint = QtGui.QApplication.style().styleHint(QtGui.QStyle.SH_Table_GridLineColor, option, self._view,
                                                            None)
            # must ensure that the value is positive before
            # constructing a QColor from it
            # http://www.riverbankcomputing.com/pipermail/pyqt/2010-February/025893.html
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            # paint the vertical line
            painter.drawLine(origRect.right(), origRect.top(), origRect.right(), origRect.bottom())
            painter.restore()


###############################################################################
# TreeMenuHandler
###############################################################################
class TreeMenuHandler(MenuHandler):
    """Inherits :class:`~wizqt.core.menu_handler.MenuHandler`, and adds
    ``Keep All Expanded``, ``Expand``, ``Collapse``, ``Expand all`` and  ``Collapse all`` actions.
    """

    def __init__(self, view, parent=None):
        super(TreeMenuHandler, self).__init__(view, parent=parent)
        self.__expandOnLoadAction = Action(
            selectionBased=False,
            text="Keep All Expanded",
            checkable=True,
            runFn=self.__setExpandOnLoad
        )
        self._staticActions = [
            Action(
                selectionBased=True,
                text="Toggle Expanded",
                runFn=self.view._toggleExpanded
            ),
            Action(
                selectionBased=True,
                text="Expand",
                shortcut=QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                isValidFn=self.__canExpand,
                runFn=self.expandSelected
            ),
            Action(
                selectionBased=True,
                text="Collapse",
                shortcut=QtGui.QKeySequence(QtCore.Qt.Key_Minus),
                isValidFn=self.__canCollapse,
                runFn=self.collapseSelected
            ),
            Action(
                selectionBased=True,
                text="Expand all",
                runFn=self.view.expandAll
            ),
            Action(
                selectionBased=True,
                text="Collapse all",
                runFn=self.view.collapseAll
            ),
            self.__expandOnLoadAction
        ]

    def expandSelected(self):
        """Named function for specific menu action."""
        self.view._setSelectedExpanded(True)

    def collapseSelected(self):
        """Named function for specific menu action."""
        self.view._setSelectedExpanded(False)

    def __canExpand(self):
        ''' determine if the selection can be expanded '''
        indexes = self.view.selectionModel().selectedIndexes()
        if not indexes:
            return False
        for idx in indexes:
            if self.view.model().hasChildren(idx) and not self.view.isExpanded(idx):
                return True
        return False

    def __canCollapse(self):
        ''' determine if the selection can be collapsed '''
        indexes = self.view.selectionModel().selectedIndexes()
        if not indexes:
            return False
        for idx in indexes:
            if self.view.model().hasChildren(idx) and self.view.isExpanded(idx):
                return True
        return False

    def __setExpandOnLoad(self):
        state = self.__expandOnLoadAction.isChecked()
        self.__expandOnLoadAction.setChecked(state)
        self.parent.setExpandOnLoad(-1 if state else 0)

    def _actionOrder(self):
        return [
            self.SEPARATOR,
            "Expand",
            "Collapse",
            "Toggle Expanded",
            "Expand all",
            "Collapse all",
            "Keep All Expanded",
            self.SEPARATOR
        ]


################################################################################################################
# TreeView
################################################################################################################
class TreeView(AbstractView, QtGui.QTreeView):
    """The TreeView view shows a list of model item rows, which can be nested under each other."""

    AUTO_EXPAND_DELAY = 250  # milliseconds
    itemDoubleClicked = QtCore.Signal(list)
    allExpanded = QtCore.Signal()
    allCollapsed = QtCore.Signal()
    # MENU_HANDLER_CLASS = TreeMenuHandler
    expandOnLoad = property(lambda self: self.__expandOnLoad)

    def __init__(self, parent=None):
        """
        """
        QtGui.QTreeView.__init__(self, parent)
        AbstractView.__init__(self)
        self.addMenuHandler(TreeMenuHandler(self, parent=self))
        self.addMenuHandler(StandardMenuHandler(self, parent=self))
        # use custom delegate
        self.setItemDelegate(TreeDelegate(self))
        # properties
        self.__refreshOnNextCtrlRelease = False
        self.__showGrid = False
        # timer for auto-expanding branches on drag/drop
        self.__openTimer = QtCore.QTimer(self)
        self.__openTimer.timeout.connect(self.__doAutoExpand)
        # set default values for properties
        self.setAutoExpandDelay(self.AUTO_EXPAND_DELAY)
        # persistent expansion state using model's uniqueId
        self.__expandOnLoad = 0
        self.__expandAllIsExpanded = False
        # cache of the number of things in model, -1 means we haven't
        # set this yet, see setModel
        self.modelrows = -1

    def setModel(self, model):
        """
        """
        # disconnect any existing model
        oldModel = self.model()
        if oldModel:
            oldModel.modelReset.disconnect(self.applyExpandOnLoad)
        QtGui.QTreeView.setModel(self, model)
        AbstractView.setModel(self, model)
        # tree-specific model setup
        newModel = self.model()
        # update the number of rows we think the model has because the
        # model changed, the can be updated in expandAll() if the model
        # has changed when that is called
        self.modelrows = newModel.num_items()
        newModel.modelReset.connect(self.applyExpandOnLoad)
        # set custom selection model
        self.setSelectionModel(TreeSelectionModel(newModel, self))
        # load the model data
        self.doModelRefresh()

    def selectAll(self):
        """
        """
        if not isinstance(self.selectionModel(), TreeSelectionModel):
            return QtGui.QTreeView.selectAll(self)
        # store parameters
        selectionModel = self.selectionModel()
        model = self.model()
        getIndex = model.index
        columnCount = model.columnCount(QtCore.QModelIndex())
        selection = QtGui.QItemSelection()
        propagate = selectionModel.propagateSelection()
        oldSelection = selectionModel.selection()

        def selectChildRange(parentIndex):
            rowCount = model.rowCount(parentIndex)
            firstIndex = getIndex(0, 0, parentIndex)
            lastIndex = getIndex(rowCount - 1, columnCount - 1, parentIndex)
            selection.select(firstIndex, lastIndex)

        def recursiveSelect(parentIndex):
            selectChildRange(parentIndex)
            if propagate is True:  # if we skip this check it will always select child rows.
                for row in range(model.rowCount(parentIndex)):
                    index = getIndex(row, 0, parentIndex)
                    if index.isValid():
                        recursiveSelect(index)

        # prepare
        block = selectionModel.blockSignals(True)
        self.setUpdatesEnabled(False)
        if propagate is True:
            selectionModel.setPropagateSelection(False)
        # do selection
        if self.selectionMode() == QtGui.QAbstractItemView.SingleSelection:
            selection.select(
                model.index(0, 0, QtCore.QModelIndex()),
                model.index(0, columnCount - 1, QtCore.QModelIndex())
            )
        else:
            recursiveSelect(QtCore.QModelIndex())
        selectionModel.select(selection, QtGui.QItemSelectionModel.Select)
        # restore previous settings
        self.setUpdatesEnabled(True)
        selectionModel.setPropagateSelection(propagate)
        selectionModel.blockSignals(block)
        # refresh view
        QtGui.QApplication.processEvents()
        selectionModel.selectionChanged.emit(selection, oldSelection)

    ###########################################################################
    # PERSISTENT SETTINGS
    ###########################################################################

    def getState(self):
        """
        """
        state = AbstractView.getState(self)
        if state is None:
            return None
        state['expandOnLoad'] = self.__expandOnLoad
        if not self.__expandOnLoad:
            # expanded indexes
            expandedIds = []
            # the expanded index list must be in order so that when we restore the expanded state,
            # parents are expanded before their children
            indexQueue = [self.rootIndex()]
            while indexQueue:
                parentIndex = indexQueue.pop(0)
                # iterate over all children of this index
                numChildren = self.model().rowCount(parentIndex)
                for i in xrange(numChildren):
                    childIndex = self.model().index(i, 0, parentIndex)
                    if childIndex.isValid() and self.isExpanded(childIndex):
                        uniqueId = self.model().uniqueIdFromIndex(childIndex)
                        if uniqueId is not None:
                            expandedIds.append(uniqueId)
                            indexQueue.append(childIndex)
            state["expanded"] = expandedIds
        return state

    def restoreState(self):
        blockSignals = self.selectionModel().blockSignals
        block = blockSignals(True)
        AbstractView.restoreState(self)
        blockSignals(block)
        self.applyExpandOnLoad()

    def applyState(self, state):
        """
        """
        # expand indexes before calling superclass to ensure selected items are properly scrolled to
        expandOnLoad = state.get('expandOnLoad', 0)
        if type(expandOnLoad) == bool:
            expandOnLoad = -1 if expandOnLoad else 0
        self.setExpandOnLoad(expandOnLoad)
        self.applyExpandOnLoad()
        state = state or {}
        if "expanded" in state and isinstance(state["expanded"], list):
            indexFromUniqueId = self.model().indexFromUniqueId
            blocked = self.blockSignals(True)
            for uniqueId in state["expanded"]:
                index = indexFromUniqueId(uniqueId)
                if index.isValid() and not self.isExpanded(index):
                    # IMPORTANT: must layout the view before calling setExpanded() for lazy-loaded
                    # trees, otherwise expand() will not call fetchMore() and child indexes will not be loaded
                    self.executeDelayedItemsLayout()
                    self.setExpanded(index, True)
            self.blockSignals(blocked)
        AbstractView.applyState(self, state)
        if self.selectionModel() and hasattr(self.selectionModel(), "requestRefresh"):
            self.selectionModel().requestRefresh()

    ###########################################################################
    # GRID METHODS
    ###########################################################################
    def showGrid(self):
        """
        """
        return self.__showGrid

    def setShowGrid(self, show):
        """
        """
        if show != self.__showGrid:
            self.__showGrid = show
            self.viewport().update()

    def visualRect(self, index):
        """
        """
        rect = QtGui.QTreeView.visualRect(self, index)
        if self.__showGrid and rect.isValid():
            # remove 1 pixel from right and bottom edge of rect, to account for grid lines
            rect.setRight(rect.right() - 1)
            rect.setBottom(rect.bottom() - 1)
        return rect

    def drawRow(self, painter, option, index):
        """
        """
        # draw the partially selected rows a lighter colour
        selectionState = index.model().itemFromIndex(index).data(role=common.ROLE_SELECTION_STATE)
        if selectionState == 1:
            palette = self.palette()
            selectionColor = palette.color(palette.Highlight)
            selectionColor.setAlpha(127)
            painter.save()
            painter.fillRect(option.rect, selectionColor)
            painter.restore()

        QtGui.QTreeView.drawRow(self, painter, option, index)

        # draw the grid line
        if self.__showGrid:
            painter.save()
            gridHint = self.style().styleHint(QtGui.QStyle.SH_Table_GridLineColor, self.viewOptions(), self, None)
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

        QtGui.QTreeView.drawBranches(self, painter, rect, index)
        # draw the grid line
        if self.__showGrid:
            painter.save()
            gridHint = QtGui.QApplication.style().styleHint(QtGui.QStyle.SH_Table_GridLineColor, self.viewOptions(),
                                                            self, None)
            # must ensure that the value is positive before
            # constructing a QColor from it
            # http://www.riverbankcomputing.com/pipermail/pyqt/2010-February/025893.html
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            # paint the horizontal line
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
            painter.restore()

    def sizeHintForColumn(self, column):
        """
        """
        return QtGui.QTreeView.sizeHintForColumn(self, column) + (1 if self.__showGrid else 0)

    def scrollContentsBy(self, dx, dy):
        """
        """
        QtGui.QTreeView.scrollContentsBy(self, dx, dy)
        self._updateImageCycler()

    ###########################################################################
    # EVENTS
    ###########################################################################
    def paintEvent(self, event):
        """
        """
        QtGui.QTreeView.paintEvent(self, event)
        AbstractView.paintEvent(self, event)

    def viewportEvent(self, event):
        """
        """
        AbstractView.viewportEvent(self, event)
        return QtGui.QTreeView.viewportEvent(self, event)

    def keyReleaseEvent(self, event):
        # if we've postponed the refresh during a multiselect, and ctrl has now been released,
        # emit the selection changed signal.
        if event.key() == QtCore.Qt.Key_Control and self.__refreshOnNextCtrlRelease:
            self.selectionModel().requestRefresh()
            self.__refreshOnNextCtrlRelease = False
        QtGui.QTreeView.keyReleaseEvent(self, event)

    def keyPressEvent(self, event):
        """
        """

        def getHashableShortcut(action):
            # QKeySequence not hashable in pyside
            shortcut = action.shortcut()
            if isinstance(shortcut, QtGui.QKeySequence):
                return shortcut.toString()
            return shortcut

        # handle shortcut keys of actions
        if event.key():
            QtGui.QTreeView.keyPressEvent(self, event)
            if event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                if self.selectionModel() and hasattr(self.selectionModel(), "requestRefresh"):
                    self.selectionModel().requestRefresh()
                self.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            QtGui.QTreeView.keyPressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Reimplemented for parent-only selection on alt+click when selection is propagated to children.
        Ctrl+alt+click adds the single item to the selection when selection is propagated to children.

        :parameters:
            event : QMouseEvent
        """
        modifiers = event.modifiers()
        button = event.button()
        if button == QtCore.Qt.LeftButton:
            selectionModel = self.selectionModel()
            if modifiers & (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier):
                # only ctrl is pressed - default behaviour
                if modifiers == QtCore.Qt.ControlModifier:
                    if self.selectionModel() and hasattr(self.selectionModel(), "requestRefresh"):
                        self.__refreshOnNextCtrlRelease = True
                        QtGui.QTreeView.mouseReleaseEvent(self, event)
                        return
                else:
                    # store current propagation state
                    propagationState = selectionModel.propagateSelection()
                    if propagationState:
                        # set propagation to false so that only the item clicked is selected
                        selectionModel.setPropagateSelection(False)
                        # both alt and ctrl are pressed - add single item to selection
                        if modifiers == (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier):
                            selectionModel.setCurrentIndex(self.indexAt(event.pos()), QtGui.QItemSelectionModel.Select)
                        # only alt is pressed - clear selection and select single item
                        elif modifiers == QtCore.Qt.AltModifier:
                            selectionModel.setCurrentIndex(self.indexAt(event.pos()),
                                                           QtGui.QItemSelectionModel.ClearAndSelect)
                        # restore propagation state
                        selectionModel.setPropagateSelection(propagationState)
        QtGui.QTreeView.mouseReleaseEvent(self, event)
        if self.selectionModel() and hasattr(self.selectionModel(), "requestRefresh"):
            self.selectionModel().requestRefresh()

    def mousePressEvent(self, event):
        """
        Reimplement QAbstractItemView.mousePressEvent
        """
        # Note: Uncomment this and the section at the end of this
        #       function if you want profile the selection in
        #       twig/stalk etc widgets. Do Not leave this uncomented
        #       in production.
        #
        # import time
        # import cProfile
        # prof = cProfile.Profile()
        # prof.enable()
        # statsfile = 'selection.pstats'
        # start = time.time()

        QtGui.QTreeView.mousePressEvent(self, event)

    # Note: Uncomment this and the section at the start of this
    #       function if you want profile the selection in
    #       twig/stalk etc widgets. Do Not leave this uncomented
    #       in production.
    #
    # print( 'wzq::m::tv::mousePressEvent: {0:11.8f} ({1})'.format( time.time()-start, statsfile ) )
    # prof.disable()
    # prof.dump_stats(statsfile)

    def mouseDoubleClickEvent(self, event):
        """
        Mouse double click event
        """
        if self.model():
            indexes = self.currentSelection(minimal=False)
            items = [self.model().itemFromIndex(i) for i in indexes]
            self.itemDoubleClicked.emit(items)
        super(TreeView, self).mouseDoubleClickEvent(event)

    # 	def _canExpand( self ):
    # 		"""
    # 		"""
    # 		# determine if the selection can be expanded
    # 		indexes = self.selectionModel().selectedIndexes()
    # 		if not indexes:
    # 			return False
    # 		for idx in indexes:
    # 			if self.model().hasChildren( idx ) and not self.isExpanded( idx ):
    # 				return True
    # 		return False
    #
    # 	def _canCollapse( self ):
    # 		"""
    # 		"""
    # 		# determine if the selection can be collapsed
    # 		indexes = self.selectionModel().selectedIndexes()
    # 		if not indexes:
    # 			return False
    # 		for idx in indexes:
    # 			if self.model().hasChildren( idx ) and self.isExpanded( idx ):
    # 				return True
    # 		return False

    ###########################################################################
    # EXPAND/COLLAPSE METHODS
    ###########################################################################

    def _toggleExpanded(self):
        selection = self.currentSelection()
        if not selection:
            return
        # make them all do the same thing, not some expand and others collapse
        expanded = not self.isExpanded(selection[0])
        for index in selection:
            self.setExpanded(index, expanded)
            if (not expanded):
                self.__expandAllIsExpanded = False

    def _setSelectedExpanded(self, expanded):
        """
        """
        for index in self.currentSelection():
            self.setExpanded(index, expanded)
            if (not expanded):
                self.__expandAllIsExpanded = False

    def _expandOneBranch(self, index, depth):
        """
        """
        model = self.model()
        # use depth < 0 for infinite depth
        if depth != 0 and self.model().hasChildren(index):
            if not self.isExpanded(index):
                model.modelReset.disconnect(self.applyExpandOnLoad)
                self.expand(index)
                model.modelReset.connect(self.applyExpandOnLoad)
            for row in xrange(model.rowCount(index)):
                childIndex = model.index(row, index.column(), parentIndex=index)
                if childIndex != index:
                    self._expandOneBranch(
                        childIndex,
                        depth - 1
                    )

    def expandAll(self, always_expand=False):
        # Only bother expanding all, if either:
        #  * we have not already expanded all the things, or
        #  * the number of things has changed since we expanded all
        # The modelrows check was added to cope with the model contents
        # changing underneath the tree_view. There's probably a better
        # way to fix it, but this works for now.
        if (not self.__expandAllIsExpanded or (self.modelrows != self.model().num_items()) or always_expand):
            self.modelrows = self.model().num_items()
            self.__expandAllIsExpanded = True
            super(TreeView, self).expandAll()
            self.allExpanded.emit()

    def collapseAll(self):
        self.__expandAllIsExpanded = False
        super(TreeView, self).collapseAll()
        self.allCollapsed.emit()

    def applyExpandOnLoad(self):
        """
        """
        if self.__expandOnLoad:
            model = self.model()
            root = QtCore.QModelIndex()
            getIndex = lambda row: model.index(row, 0, root)
            rowCount = model.rowCount(root)
            for row in xrange(0, rowCount + 1):
                self._expandOneBranch(getIndex(row), self.__expandOnLoad)

    def setExpandOnLoad(self, value):
        """
        """
        if type(value) is not int:
            value = -1 if value else 0
        enabled = value != 0
        # 		self._expandOnLoadAction.setChecked( enabled )
        self.__expandOnLoad = value
        if enabled:
            self.applyExpandOnLoad()

    def expand(self, index):
        model = self.model()
        if model.canFetchMore(index):
            model.fetchMore(index)
        super(TreeView, self).expand(index)
        self.__expandAllIsExpanded = False

    def expandToSelected(self):
        """
        """
        model = self.model()
        propagateSelection = self.selectionModel().propagateSelection()

        # remove duplicates
        def removeIndexDuplicates(indexList):
            return filter(QtCore.QModelIndex.isValid,
                          map(model.indexFromItem, set(
                              map(model.itemFromIndex, indexList)
                          )))

        # index has no parent
        def isTopLevel(index):
            return not index.parent().isValid()

        # get selected indexes
        indexes = removeIndexDuplicates(filter(QtCore.QModelIndex.isValid, self.selectionModel().selectedIndexes()))
        # if no selection, expand one level
        if not indexes:
            self._expandOneBranch(model.index(0, 0, QtCore.QModelIndex()), 1)
            return
        block = self.blockSignals(True)
        # if the top level is selected, it's quicker to just expand all
        if propagateSelection is True and filter(isTopLevel, indexes):
            self.__expandAllIsExpanded = False
            self.expandAll()
            self.blockSignals(block)
            return
        # expand back up the hierarchy to reveal the selected index
        for index in indexes:
            while index.isValid() and not self.isExpanded(index):
                self.setExpanded(index, True)
                index = index.parent()
        self.blockSignals(block)

    ###########################################################################
    # DRAG/DROP METHODS
    ###########################################################################
    def dragMoveEvent(self, event):
        """
        """
        # re-implemented so we can customise the autoExpandDelay behaviour
        if self.autoExpandDelay() >= 0:
            self.__openTimer.start(self.autoExpandDelay())
        AbstractView.dragMoveEvent(self, event)

    def __doAutoExpand(self):
        """
        """
        pos = self.viewport().mapFromGlobal(QtGui.QCursor.pos())
        if self.state() == QtGui.QAbstractItemView.DraggingState and self.viewport().rect().contains(pos):
            index = self.indexAt(pos)
            # only expand branches, never collapse them
            if not self.isExpanded(index):
                self.setExpanded(index, True)
        self.__openTimer.stop()

    def loadSettings(self, settings):
        AbstractView.loadSettings(self, settings)
        # allow 'expand on load' to be passed from SITE cfg file.
        # 'state' is usually stored and read from the local cfg, which will override a SITE default being set
        self.setExpandOnLoad(settings['expandOnLoad'] or 0)
