"""Small data entry widgets to add data to a filter edit line in a filter set.

Not intended to be used directly.
"""
# Local imports
from wizqt import common
from filter import FilterError
from type_handler import IntHandler

# PyQt imports
from qtswitch import QtGui


#########################################################################################
#	FilterValEdit
#########################################################################################
class FilterValEdit(QtGui.QWidget):
    """
    """

    def __init__(self, dataTypeHandler, parent=None):
        super(FilterValEdit, self).__init__(parent)
        self._dataTypeHandler = dataTypeHandler
        # create layout
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # add widgets to layout
        self._inputWidgets = self._createWidgets(layout)
        self.resetVals()
        self.setLayout(layout)

    #########################################################################################
    #	_createWidgets
    #########################################################################################
    def _createWidgets(self, layout):
        """
        """
        widget = self._dataTypeHandler.getInputWidget(self)
        layout.addWidget(widget)
        return [widget]

    #########################################################################################
    #	getVals
    #########################################################################################
    def getVals(self):
        """
        """
        values = []
        for widget in self._inputWidgets:
            values.append(self._dataTypeHandler.getInputValue(widget))
        return values

    #########################################################################################
    #	setVals
    #########################################################################################
    def setVals(self, values):
        """
        """
        assert len(values) == len(self._inputWidgets)
        for i, value in enumerate(values):
            if not self._dataTypeHandler.setInputValue(self._inputWidgets[i], value):
                raise FilterError("Invalid value '%s' for type handler %s" % (value, self._dataTypeHandler.__name__))

    #########################################################################################
    #	resetVals
    #########################################################################################
    def resetVals(self):
        """
        """
        for widget in self._inputWidgets:
            self._dataTypeHandler.resetInputValue(widget)


#########################################################################################
#	IntRangeFilterValEdit
#########################################################################################
class IntRangeFilterValEdit(FilterValEdit):
    """
    """

    #########################################################################################
    #	_createWidgets
    #########################################################################################
    def _createWidgets(self, layout):
        """
        """
        widgetStart = self._dataTypeHandler.getInputWidget(self)
        widgetEnd = self._dataTypeHandler.getInputWidget(self)
        toLabel = QtGui.QLabel("to", self)
        toLabel.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        layout.addWidget(widgetStart)
        layout.addWidget(toLabel)
        layout.addWidget(widgetEnd)
        return [widgetStart, widgetEnd]


#########################################################################################
# 	FloatRangeFilterValEdit
#########################################################################################
class FloatRangeFilterValEdit(FilterValEdit):
    """
    """

    #########################################################################################
    #	_createWidgets
    #########################################################################################
    def _createWidgets(self, layout):
        """
        """
        widgetStart = self._dataTypeHandler.getInputWidget(self)
        widgetEnd = self._dataTypeHandler.getInputWidget(self)
        toLabel = QtGui.QLabel("to", self)
        toLabel.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        layout.addWidget(widgetStart)
        layout.addWidget(toLabel)
        layout.addWidget(widgetEnd)
        return [widgetStart, widgetEnd]


#########################################################################################
# BoolFilterValEdit
#########################################################################################
class BoolFilterValEdit(FilterValEdit):
    """
    """

    #########################################################################################
    #	_createWidgets
    #########################################################################################
    def _createWidgets(self, layout):
        """
        """
        # no visible input widgets for boolean
        return []


#########################################################################################
# DateRangeFilterValEdit
#########################################################################################
class DateRangeFilterValEdit(FilterValEdit):
    """
    """

    #########################################################################################
    #	_createWidgets
    #########################################################################################
    def _createWidgets(self, layout):
        """
        """
        widgetStart = self._dataTypeHandler.getInputWidget(self)
        widgetEnd = self._dataTypeHandler.getInputWidget(self)
        toLabel = QtGui.QLabel("to", self)
        toLabel.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        layout.addWidget(widgetStart)
        layout.addWidget(toLabel)
        layout.addWidget(widgetEnd)
        return [widgetStart, widgetEnd]


#########################################################################################
#	DurationFilterValEdit
#########################################################################################
class DurationFilterValEdit(FilterValEdit):
    """
    """

    #########################################################################################
    #	_createWidgets
    #########################################################################################
    def _createWidgets(self, layout):
        """
        """
        from type_handler import DateTimeHandler
        widgetLength = IntHandler.getInputWidget(self)
        widgetUnits = QtGui.QComboBox(self)
        widgetUnits.addItems(
            common.DATETIME_DURATIONS if self._dataTypeHandler is DateTimeHandler else common.DATE_DURATIONS)
        widgetUnits.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        layout.addWidget(widgetLength)
        layout.addWidget(widgetUnits)
        return [widgetLength, widgetUnits]

    #########################################################################################
    #	getVals
    #########################################################################################
    def getVals(self):
        """
        """
        return [IntHandler.getInputValue(self._inputWidgets[0]), self._inputWidgets[1].currentText()]

    #########################################################################################
    #	setVals
    #########################################################################################
    def setVals(self, values):
        """
        """
        length, units = values
        if not IntHandler.setInputValue(self._inputWidgets[0], length):
            raise FilterError("Invalid value '%s' for type handler %s" % (length, IntHandler.__name__))
        matchingIndex = self._inputWidgets[1].findText(units)
        if matchingIndex == -1:
            raise FilterError("Invalid duration '%s'" % units)
        self._inputWidgets[0].setCurrentIndex(matchingIndex)

    #########################################################################################
    #	resetVals
    #########################################################################################
    def resetVals(self):
        """
        """
        IntHandler.resetInputValue(self._inputWidgets[0])
        self._inputWidgets[1].setCurrentIndex(0)
