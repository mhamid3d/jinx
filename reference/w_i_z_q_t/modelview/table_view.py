"""
The table view is a single level cell based view.

.. image:: /_static/images/tableViewExample.jpg
"""
import logging

# Local imports
from abstract_view import AbstractView
# PyQt imports
from qtswitch import QtGui

_LOGGER = logging.getLogger(__name__)


###############################################################################################################################
# 	TableView
###############################################################################################################################
class TableView(AbstractView, QtGui.QTableView):
    """
    """

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        AbstractView.__init__(self)
        self.__resizeHeightToContents = False

    def __singleValueRowsChanged(self, newSingleValueRows, newMultiValueRows):
        """
        """
        _LOGGER.debug("singleValueRowsChanged(new=%s, old=%s)" % (newSingleValueRows, newMultiValueRows))
        for row in newSingleValueRows:
            self.setSpan(row, 0, 1, self.__sourceModel.columnCount())
        for row in newMultiValueRows:
            self.setSpan(row, 0, 1, 1)

    def __updateHeightFromContents(self):
        """
        """
        # FIXME
        _LOGGER.error("__updateHeightFromContents")
        extra = 2 * self.frameWidth()
        headerSize = self.topHeader().sizeHint()
        hExtra = 0
        if self.model():
            for row in xrange(self.model().rowCount()):
                hExtra += self.rowHeight(row)
        height = headerSize.height() + extra + hExtra
        self.setFixedHeight(height)

    def setResizeHeightToContents(self, resizeHeightToContents):
        """
        """
        self.__resizeHeightToContents = resizeHeightToContents
        if resizeHeightToContents:
            self.sideHeader().sectionCountChanged.connect(self.__updateHeightFromContents)
            self.sideHeader().sectionResized.connect(self.__updateHeightFromContents)
        else:
            self.sideHeader().sectionCountChanged.disconnect(self.__updateHeightFromContents)
            self.sideHeader().sectionResized.disconnect(self.__updateHeightFromContents)

    def setModel(self, model):
        QtGui.QTableView.setModel(self, model)
        AbstractView.setModel(self, model)
        # load the model data
        self.doModelRefresh()

    ###############################################################################################################################
    # TOP HEADER METHODS
    ###############################################################################################################################
    def sizeHintForColumn(self, column):
        """
        This method overrides the QTableView implementation in order to fix a Qt bug in which QHeaderView::ResizeToContents only
        takes in to account rows currently visible in the viewport: https://bugreports.qt.nokia.com//browse/QTBUG-4206
        """
        if not self.model():
            return -1
        self.ensurePolished()
        option = self.viewOptions()
        hint = 0
        getIndex = self.model().index
        sideHeader = self.sideHeader()
        # limit to the first 1000 items or else this will be too slow
        numRows = min(self.model().rowCount(), 1000)
        for row in xrange(numRows):
            logicalRow = sideHeader.logicalIndex(row)
            if sideHeader.isSectionHidden(logicalRow):
                continue
            index = getIndex(logicalRow, column)
            editor = self.indexWidget(index)
            if editor is not None:
                hint = max(hint, editor.sizeHint().width())
                hint = max(hint, editor.minimumSize().width())
                hint = min(hint, editor.maximumSize().width())
            hint = max(hint, self.itemDelegate(index).sizeHint(option, index).width())
        if self.showGrid():
            hint += 1
        return hint

    ###############################################################################################################################
    # SIDE HEADER METHODS
    ###############################################################################################################################
    def setSideHeader(self, headerView):
        """
        """
        self.setVerticalHeader(headerView)

    def sideHeader(self):
        """
        """
        return self.verticalHeader()

    ###############################################################################################################################
    # EVENTS
    ###############################################################################################################################
    def paintEvent(self, event):
        QtGui.QTableView.paintEvent(self, event)
        AbstractView.paintEvent(self, event)

    def viewportEvent(self, event):
        AbstractView.viewportEvent(self, event)
        return QtGui.QTableView.viewportEvent(self, event)

    def scrollContentsBy(self, dx, dy):
        QtGui.QTableView.scrollContentsBy(self, dx, dy)
        self._updateImageCycler()

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.clearSelection()
        QtGui.QTableView.mousePressEvent(self, event)
