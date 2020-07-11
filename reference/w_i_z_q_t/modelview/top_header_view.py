"""This view represents the header of a tree or table view.

It can be populated with a single model item.
"""
# Local imports
from wizqt import common

# PyQt imports
from qtswitch import QtGui, QtCore


##################################################################################################
# 	TopHeaderView
##################################################################################################
class TopHeaderView(QtGui.QHeaderView):
    """
    """

    def __init__(self, parent=None):
        self.__dragLogicalIdx = None
        super(TopHeaderView, self).__init__(QtCore.Qt.Horizontal, parent)
        self.__dragTimer = QtCore.QTimer()
        self.__dragTimer.setSingleShot(True)
        # use a slightly smaller font than the default and decrease margins
        self.setStyleSheet("QHeaderView::section { margin: 4px 1px 4px 1px; } QHeaderView { font: 9pt; } ")
        # self.sectionClicked.connect( self._columnClicked )
        self.setMovable(True)

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
            if QtGui.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier:
                sorter.addSortColumn(column, direction)
            else:
                # not multisorting
                sorter.setSortColumns([column], [direction])

    ##################################################################################################
    # 	events
    ##################################################################################################

    def leaveEvent(self, event):
        QtGui.QHeaderView.leaveEvent(self, event)
        self.__dragLogicalIdx = None

    def mouseReleaseEvent(self, event):
        QtGui.QHeaderView.mouseReleaseEvent(self, event)
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
            QtGui.QHeaderView.mousePressEvent(self, event)

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
                QtGui.QHeaderView.mouseMoveEvent(
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
        QtGui.QHeaderView.mouseMoveEvent(self, event)

    def paintSection(self, painter, rect, logicalIndex):
        """
        Re-implementation of QHeaderView.paintSection() to deal with multi-sorting.
        """
        if not rect.isValid():
            return
        painter.save()
        # get the state of the section
        opt = QtGui.QStyleOptionHeader()
        self.initStyleOption(opt)
        state = QtGui.QStyle.State_None
        if self.isEnabled():
            state |= QtGui.QStyle.State_Enabled
        if self.window().isActiveWindow():
            state |= QtGui.QStyle.State_Active
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
                opt.sortIndicator = QtGui.QStyleOptionHeader.SortDown if sortDirections[
                                                                             sortIndex] == QtCore.Qt.AscendingOrder else QtGui.QStyleOptionHeader.SortUp
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
            opt.position = QtGui.QStyleOptionHeader.OnlyOneSection
        elif visual == 0:
            opt.position = QtGui.QStyleOptionHeader.Beginning
        elif visual == self.count() - 1:
            opt.position = QtGui.QStyleOptionHeader.End
        else:
            opt.position = QtGui.QStyleOptionHeader.Middle
        opt.orientation = orientation
        # draw the section
        self.style().drawControl(QtGui.QStyle.CE_Header, opt, painter, self)
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
        size = QtGui.QHeaderView.sectionSizeFromContents(self, logicalIndex)
        if self.model():
            if self.isSortIndicatorShown() and not self.model().headerData(logicalIndex, self.orientation(),
                                                                           common.ROLE_IS_SORTABLE):
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
