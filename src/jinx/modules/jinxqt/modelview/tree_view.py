from __future__ import print_function

from qtpy import QtCore, QtWidgets, QtGui
from top_header import TopHeaderView
from jinxqt.modelview.delegate import Delegate
from jinxqt import common
from model import Model


class TreeDelegate(Delegate):

    MARGIN = 25

    def sizeHint(self, option, index):
        widget = self._view.indexWidget(index)
        if widget:
            hint = widget.sizeHint()
            gridSize = 1 if self._view.showGrid() else 0
            return QtCore.QSize(hint.width(), hint.height() + gridSize)

        hint = Delegate.sizeHint(self, option, index)

        if self._view.showGrid():
            if self.MARGIN is None:
                self.MARGIN = QtWidgets.QApplication.style().pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, None)
            margin = self.MARGIN
            minimumHeight = max(QtWidgets.QApplication.globalStrut().height(), option.fontMetrics.height() + margin)
            return QtCore.QSize(hint.width(), max(hint.height(), minimumHeight))

        return hint

    def paint(self, painter, option, index):
        origRect = QtCore.QRect(option.rect)
        if self._view.showGrid():
            option.rect.setRight(option.rect.right() - 1)
            option.rect.setBottom(option.rect.bottom() - 1)

        Delegate.paint(self, painter, option, index)

        if self._view.showGrid():
            painter.save()
            gridHint = QtWidgets.QApplication.style().styleHint(QtWidgets.QStyle.SH_Table_GridLineColor, option, self._view,
                                                            None)
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            painter.drawLine(origRect.right(), origRect.top(), origRect.right(), origRect.bottom())
            painter.restore()


class TreeView(QtWidgets.QTreeView):

    LOCKED_COLUMNS = []

    def __init__(self):
        super(TreeView, self).__init__()
        self._showGrid = True
        self.setHeader(TopHeaderView(self))
        self.setItemDelegate(TreeDelegate(self))
        self.resize(1300, 1080)
        self.setSortingEnabled(True)
        self.setAnimated(True)
        self.expanded.connect(self._expanded)
        self.collapsed.connect(self._collapsed)

    def _expanded(self, index):
        self._resizeColumnToContents(index.column())

    def _collapsed(self, index):
        self._resizeColumnToContents(index.column())

    def _resizeColumnToContents(self, columnIndex):
        topHeader = self.header()

        def resizeSection(columnIndex):
            # change the resize mode to fit contents
            topHeader.setSectionResizeMode(columnIndex, QtWidgets.QHeaderView.ResizeToContents)
            # set size explicitly and restore the resize mode
            topHeader.resizeSection(columnIndex, topHeader.sectionSize(columnIndex))
            topHeader.setSectionResizeMode(columnIndex, QtWidgets.QHeaderView.Interactive)

        def getRealIndex(logicalIndex):
            getHeaderData = self.model().headerData
            orientation = topHeader.orientation()
            getLogicalIndex = topHeader.logicalIndex
            visibleColumns = [getHeaderData(getLogicalIndex(i), orientation)
                              for i in range(topHeader.count())
                              if not topHeader.isSectionHidden(getLogicalIndex(i))]
            return visibleColumns.index(getHeaderData(logicalIndex, orientation))

        if not topHeader.isSectionHidden(columnIndex) and topHeader.sectionResizeMode(
                columnIndex) == QtWidgets.QHeaderView.Interactive:
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

        for index in range(self.header().count()):
            self._resizeColumnToContents(index)

    def sizeHintForColumn(self, column):
        return QtWidgets.QTreeView.sizeHintForColumn(self, column) + (1 if self._showGrid else 0)

    def showGrid(self):
        return self._showGrid

    def setShowGrid(self, show):
        if show != self._showGrid:
            self._showGrid = show
            self.viewport().update()

    def visualRect(self, index):
        rect = QtWidgets.QTreeView.visualRect(self, index)
        if self._showGrid and rect.isValid():
            rect.setRight(rect.right() - 1)
            rect.setBottom(rect.bottom() - 1)
        return rect

    def drawRow(self, painter, option, index):
        selectionState = index.model().itemFromIndex(index).data(role=common.ROLE_SELECTION_STATE)
        if selectionState == 1:
            palette = self.palette()
            selectionColor = palette.color(palette.Highlight)
            selectionColor.setAlpha(127)
            painter.save()
            painter.fillRect(option.rect, selectionColor)
            painter.restore()

        QtWidgets.QTreeView.drawRow(self, painter, option, index)

        if self._showGrid:
            painter.save()
            gridHint = self.style().styleHint(QtWidgets.QStyle.SH_Table_GridLineColor, self.viewOptions(), self, None)
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))

            painter.drawLine(option.rect.left(), option.rect.bottom(), option.rect.right(), option.rect.bottom())
            painter.restore()

    def drawBranches(self, painter, rect, index):
        QtWidgets.QTreeView.drawBranches(self, painter, rect, index)
        if self._showGrid:
            painter.save()
            gridHint = QtWidgets.QApplication.style().styleHint(QtWidgets.QStyle.SH_Table_GridLineColor, self.viewOptions(),
                                                            self, None)
            gridColor = QtGui.QColor.fromRgb(gridHint & 0xffffffff)
            painter.setPen(QtGui.QPen(gridColor, 0, QtCore.Qt.SolidLine))
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
            painter.restore()


if __name__ == '__main__':
    import sys
    import qdarkstyle
    from jinxqt.modelview.datasource.interfaces.twig import TwigDataSource
    import mongorm
    db = mongorm.getHandler()
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = TreeView()
    model = Model()
    handler = mongorm.getHandler()
    filter = mongorm.getFilter()
    datasource = TwigDataSource(handler)
    datasource._filter.search(datasource._interface)
    model.setDataSource(datasource)
    win.setModel(model)

    win.header().moveSection(0, 1)
    win.header().setFirstSectionMovable(True)

    win._resizeAllColumnsToContents()
    win.show()
    sys.exit(app.exec_())