"""Classes for handling each column data type (as defined in :data:`wizqt.common.TYPES`)

These act as wrappers for the classes in :mod:`~wizqt.core.filter` which can be used to edit model data.
The :func:`getTypeHandler` function retrieves the correct editor for the data type.
The ``dataType`` argument is one of the globals in :mod:`wizqt.common`:

- :data:`~wizqt.common.TYPE_STRING_SINGLELINE`
- :data:`~wizqt.common.TYPE_STRING_MULTILINE`
- :data:`~wizqt.common.TYPE_INTEGER`
- :data:`~wizqt.common.TYPE_UNSIGNED_INTEGER`
- :data:`~wizqt.common.TYPE_FLOAT`
- :data:`~wizqt.common.TYPE_BOOLEAN`
- :data:`~wizqt.common.TYPE_DATE`
- :data:`~wizqt.common.TYPE_DATE_TIME`
- :data:`~wizqt.common.TYPE_FILE_PATH`
- :data:`~wizqt.common.TYPE_IMAGE`
- :data:`~wizqt.common.TYPE_ENUM`
"""
# Standard imports
import datetime
import sys
# Local imports
from wizqt import common, exc
# Dneg imports
from dnpath import DnPath, DnRange
from wizmo.wizutil import toUtf8
# PyQt imports
from qtswitch import QtGui, QtCore, QT_API


class AbstractTypeHandler(object):

    @classmethod
    def resolveValue(cls, value):
        raise NotImplementedError

    @classmethod
    def toString(cls, value):
        raise NotImplementedError

    @classmethod
    def toCardsActionData(cls, value):
        raise NotImplementedError

    @classmethod
    def compare(cls, left, right):
        """
        Returns a negative integer if left < right, 0 if left == right, or a positive integer if left > right.
        """
        raise NotImplementedError

    @classmethod
    def getInputWidget(cls, parentWidget):
        raise NotImplementedError

    @classmethod
    def getInputValue(cls, widget):
        raise NotImplementedError

    @classmethod
    def setInputValue(cls, widget, value):
        raise NotImplementedError

    @classmethod
    def resetInputValue(cls, widget):
        raise NotImplementedError

    @classmethod
    def getFilterOperators(cls):
        raise NotImplementedError

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        """
        Returns a dictionary mapping from operator to filterEdit widget
        """
        raise NotImplementedError


class LabelHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python unicode object
        """
        if value is None:
            return ("", True)
        try:
            return (unicode(value), True)
        except ValueError:
            return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return value
        return ""

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = ''
        right, ok = cls.resolveValue(right)
        if not ok:
            right = ''
        return cmp(left.lower(), right.lower())  # case insensitive comparison

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QLabel(parentWidget)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.text())
        if ok:
            return value
        return ''

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setText(value)
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.clear()

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_CONTAINS,
                common.OPERATOR_NOT_CONTAINS,
                common.OPERATOR_EQUALS,
                common.OPERATOR_NOT_EQUALS,
                common.OPERATOR_STARTS_WITH,
                common.OPERATOR_ENDS_WITH,
                common.OPERATOR_MATCHES_RE,
                common.OPERATOR_NOT_MATCHES_RE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import FilterValEdit
        stringEdit = FilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            operatorMap[operator] = stringEdit
        return operatorMap


class StringSinglelineHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python unicode object
        """
        if value is None:
            return ("", True)
        try:
            return (unicode(value), True)
        except ValueError:
            return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return value
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.string, value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = ''
        right, ok = cls.resolveValue(right)
        if not ok:
            right = ''
        return cmp(left.lower(), right.lower())  # case insensitive comparison

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QLineEdit(parentWidget)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.text())
        if ok:
            return value
        return ''

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setText(value)
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.clear()

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_CONTAINS,
                common.OPERATOR_NOT_CONTAINS,
                common.OPERATOR_EQUALS,
                common.OPERATOR_NOT_EQUALS,
                common.OPERATOR_STARTS_WITH,
                common.OPERATOR_ENDS_WITH,
                common.OPERATOR_MATCHES_RE,
                common.OPERATOR_NOT_MATCHES_RE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import FilterValEdit
        stringEdit = FilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            operatorMap[operator] = stringEdit
        return operatorMap


class StringMultilineHandler(StringSinglelineHandler):

    @classmethod
    def getInputWidget(cls, parentWidget):
        from wizqt.widget.auto_expanding_text_edit import AutoExpandingTextEdit
        widget = AutoExpandingTextEdit(parentWidget)
        widget.setAcceptRichText(False)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.toPlainText())
        if ok:
            return value
        return ""


class IntHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python int object
        """
        if value is None:
            return (0, True)
        try:
            return (int(value), True)
        except (ValueError, TypeError):
            return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return str(value)
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.int, value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = common.MINIMUM_INTEGER
        right, ok = cls.resolveValue(right)
        if not ok:
            right = common.MINIMUM_INTEGER
        return left - right

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QSpinBox(parentWidget)
        widget.setMinimum(common.MINIMUM_INTEGER)
        widget.setMaximum(common.MAXIMUM_INTEGER)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        return widget.value()

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setValue(value)
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setValue(0)

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_EQUALS,
                common.OPERATOR_NOT_EQUALS,
                common.OPERATOR_GREATER_THAN,
                common.OPERATOR_GREATER_THAN_EQUAL_TO,
                common.OPERATOR_LESS_THAN,
                common.OPERATOR_LESS_THAN_EQUAL_TO,
                common.OPERATOR_IN_RANGE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import FilterValEdit, IntRangeFilterValEdit
        intEdit = FilterValEdit(cls, parentWidget)
        intRangeEdit = IntRangeFilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            if operator == common.OPERATOR_IN_RANGE:
                operatorMap[operator] = intRangeEdit
            else:
                operatorMap[operator] = intEdit
        return operatorMap


class UIntHandler(IntHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python int object
        """
        (value, ok) = IntHandler.resolveValue(value)
        if ok and value < 0:
            ok = False
        return (value, ok)

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QSpinBox(parentWidget)
        widget.setMinimum(0)
        widget.setMaximum(common.MAXIMUM_INTEGER)
        return widget


class FloatHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python float object
        """
        if value is None:
            return (0.0, True)
        try:
            return (float(value), True)
        except (ValueError, TypeError):
            return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return str(value)
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.float, value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = common.MINIMUM_FLOAT
        right, ok = cls.resolveValue(right)
        if not ok:
            right = common.MINIMUM_FLOAT
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QDoubleSpinBox(parentWidget)
        widget.setDecimals(20)
        widget.setMinimum(-sys.float_info.max)
        widget.setMaximum(sys.float_info.max)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        return widget.value()

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setValue(value)
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setValue(0)

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_EQUALS,
                common.OPERATOR_NOT_EQUALS,
                common.OPERATOR_GREATER_THAN,
                common.OPERATOR_GREATER_THAN_EQUAL_TO,
                common.OPERATOR_LESS_THAN,
                common.OPERATOR_LESS_THAN_EQUAL_TO,
                common.OPERATOR_IN_RANGE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import FilterValEdit, FloatRangeFilterValEdit
        floatEdit = FilterValEdit(cls, parentWidget)
        floatRangeEdit = FloatRangeFilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            if operator == common.OPERATOR_IN_RANGE:
                operatorMap[operator] = floatRangeEdit
            else:
                operatorMap[operator] = floatEdit
        return operatorMap


class BoolHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python bool object
        """
        if isinstance(value, basestring):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    pass
        try:
            return (bool(value), True)
        except (ValueError, TypeError):
            return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return str(value)
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.bool, value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = -1
        right, ok = cls.resolveValue(right)
        if not ok:
            right = -1
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QCheckBox(parentWidget)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        return widget.isChecked()

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setChecked(value)
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setChecked(False)

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_TRUE,
                common.OPERATOR_FALSE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import BoolFilterValEdit
        boolEdit = BoolFilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            operatorMap[operator] = boolEdit
        return operatorMap


class DateHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python datetime.date object
        """
        if isinstance(value, datetime.date):
            return (value, True)
        elif isinstance(value, QtCore.QDate):
            if value.isValid():
                value = value.toPyDate() if QT_API == "pyqt" else value.toPython()
                return (value, True)
        elif isinstance(value, datetime.datetime):
            return (value.date(), True)
        elif isinstance(value, basestring):
            # try to parse string into date
            # assume YYYY-MM-DD format
            try:
                return (datetime.datetime.strptime(value, "%Y-%m-%d").date(), True)
            except ValueError:
                pass
        return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return value.strftime("%Y-%m-%d")
        return ""

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = datetime.date.min
        right, ok = cls.resolveValue(right)
        if not ok:
            right = datetime.date.min
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QDateEdit(parentWidget)
        widget.setDisplayFormat("yyyy-MM-dd")
        widget.setCalendarPopup(True)
        widget.calendarWidget().show()
        return widget

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.date())
        if ok:
            return value
        return None

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setDate(QtCore.QDate(value.year, value.month, value.day))
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setDate(QtCore.QDate.currentDate())

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_EQUALS,
                common.OPERATOR_NOT_EQUALS,
                common.OPERATOR_AFTER,
                common.OPERATOR_BEFORE,
                # TODO: re-enable when supported by ivy
                # common.OPERATOR_IN_LAST,
                # common.OPERATOR_NOT_IN_LAST,
                common.OPERATOR_IN_RANGE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import FilterValEdit, DateRangeFilterValEdit, DurationFilterValEdit
        dateEdit = FilterValEdit(cls, parentWidget)
        dateRangeEdit = DateRangeFilterValEdit(cls, parentWidget)
        # durationEdit = DurationFilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            if operator == common.OPERATOR_IN_RANGE:
                operatorMap[operator] = dateRangeEdit
            # elif operator in [common.OPERATOR_IN_LAST, common.OPERATOR_NOT_IN_LAST]:
            # 	operatorMap[operator] = durationEdit
            else:
                operatorMap[operator] = dateEdit
        return operatorMap


class DateTimeHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python datetime.datetime object
        """
        if isinstance(value, QtCore.QDateTime):
            if value.isValid():
                value = value.toPyDateTime() if QT_API == "pyqt" else value.toPython()
                return (value, True)
        elif isinstance(value, datetime.datetime):
            return (value, True)
        elif isinstance(value, basestring):
            # try to parse string into datetime
            # assume YYYY-MM-DD HH:MM:SS format
            try:
                return (datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S"), True)
            except ValueError:
                pass
        elif isinstance(value, datetime.date):
            return (datetime.datetime.combine(value, datetime.time(0)), True)
        return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return ""

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = datetime.datetime.min
        right, ok = cls.resolveValue(right)
        if not ok:
            right = datetime.datetime.min
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QDateTimeEdit(parentWidget)
        widget.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        widget.setCalendarPopup(True)
        widget.calendarWidget().show()
        return widget

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.dateTime())
        if ok:
            return value
        return None

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setDateTime(QtCore.QDateTime(QtCore.QDate(value.year, value.month, value.day),
                                                QtCore.QTime(value.hour, value.minute, value.second)))
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setDateTime(QtCore.QDateTime.currentDateTime())

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_DATE_EQUALS,
                common.OPERATOR_DATE_NOT_EQUALS,
                common.OPERATOR_AFTER,
                common.OPERATOR_BEFORE,
                # TODO: re-enable when supported by ivy
                # common.OPERATOR_IN_LAST,
                # common.OPERATOR_NOT_IN_LAST,
                common.OPERATOR_EMPTY,
                common.OPERATOR_NOT_EMPTY,
                common.OPERATOR_IN_RANGE]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import FilterValEdit, DateRangeFilterValEdit, DurationFilterValEdit
        dateTimeEdit = FilterValEdit(cls, parentWidget)
        dateEdit = FilterValEdit(DateHandler, parentWidget)
        dateTimeRangeEdit = DateRangeFilterValEdit(cls, parentWidget)
        # durationEdit = DurationFilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            if operator in [common.OPERATOR_DATE_EQUALS, common.OPERATOR_DATE_NOT_EQUALS]:
                operatorMap[operator] = dateEdit
            elif operator == common.OPERATOR_IN_RANGE:
                operatorMap[operator] = dateTimeRangeEdit
            # elif operator in [common.OPERATOR_IN_LAST, common.OPERATOR_NOT_IN_LAST]:
            # 	operatorMap[operator] = durationEdit
            elif operator in (common.OPERATOR_EMPTY, common.OPERATOR_NOT_EMPTY):
                from filter_edit import BoolFilterValEdit
                operatorMap[operator] = BoolFilterValEdit(cls, parentWidget)
            else:
                operatorMap[operator] = dateTimeEdit
        return operatorMap


class FilePathHandler(StringSinglelineHandler):

    @classmethod
    def getInputWidget(cls, parentWidget):
        from wizqt.widget.file_path_line_edit import FilePathLineEdit
        widget = FilePathLineEdit(parentWidget)
        return widget


class DnPathHandler(FilePathHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a DnPath object
        """
        if isinstance(value, DnPath):
            return (value, True)
        elif isinstance(value, basestring):
            return (DnPath(toUtf8(value)), True)
        return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return value.getSingleHashRangeStylePath()
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData.fromDnPath(value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        left = left.dnpath().lower() if ok else ""
        right, ok = cls.resolveValue(right)
        right = right.dnpath().lower() if ok else ""
        return cmp(left, right)

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.text())
        if ok:
            return value
        return None

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setText(value.dnpath())
        return ok


class DnRangeHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a DnPath object
        """
        if isinstance(value, basestring):
            if not value:
                return (None, False)
            try:
                value = DnRange.fromString(str(value))
            except:
                pass
        if isinstance(value, DnRange) and len(value) > 0:
            return (value, True)
        return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return value.str()
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.DnRange, value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        left = (left.start(), left.end()) if ok else None
        right, ok = cls.resolveValue(right)
        right = (right.start(), right.end()) if ok else None
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        from wizqt.widget.framerange_editor import FrameRangeEditor
        return FrameRangeEditor(parentWidget)

    @classmethod
    def getInputValue(cls, widget):
        return widget.range()

    @classmethod
    def setInputValue(cls, widget, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            widget.setRange(value)
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setRange(None)


class ResolutionHandler(AbstractTypeHandler):
    class ResolutionInputWidget(QtGui.QWidget):
        """
        A simple composite widget for editing a resolution.
        Provide 2 text fields for: width, height
        """

        def __init__(self, parent=None):
            super(ResolutionHandler.ResolutionInputWidget, self).__init__(parent)

            intValidator = QtGui.QIntValidator(self)
            intValidator.setBottom(0)

            self.width = QtGui.QLineEdit(self)
            self.width.setFrame(False)
            self.width.setValidator(intValidator)
            self.height = QtGui.QLineEdit(self)
            self.height.setValidator(intValidator)
            self.height.setFrame(False)

            layout = QtGui.QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(self.width)
            layout.addWidget(QtGui.QLabel("x", self))
            layout.addWidget(self.height)
            self.setLayout(layout)

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a DnPath object
        """
        from venom.resolution import Resolution
        if isinstance(value, Resolution):
            return (value, True)
        elif isinstance(value, (tuple, list)):
            try:
                (width, height) = value
                return (Resolution(width, height), True)
            except ValueError:
                pass
        elif isinstance(value, basestring):
            try:
                return (Resolution.fromString(value), True)
            except ValueError:
                pass
        return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return str(value)
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.user_class, value)
        return None

    @classmethod
    def compare(cls, left, right):
        from venom.resolution import Resolution
        left, ok = cls.resolveValue(left)
        if not ok:
            left = Resolution(0, 0)
        right, ok = cls.resolveValue(right)
        if not ok:
            right = Resolution(0, 0)
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        return cls.ResolutionInputWidget(parentWidget)

    @classmethod
    def getInputValue(cls, widget):
        (value, ok) = cls.resolveValue((widget.width.text(), widget.height.text()))
        if ok:
            return value
        return None

    @classmethod
    def setInputValue(cls, widget, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            widget.width.setText(str(value.w))
            widget.height.setText(str(value.h))
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.width.setText("0")
        widget.height.setText("0")


class ImageHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        return value

    @classmethod
    def toString(cls, value):
        return ""

    @classmethod
    def compare(cls, left, right):
        return 0

    @classmethod
    def getInputWidget(cls, parentWidget):
        return None

    @classmethod
    def getInputValue(cls, widget):
        return None

    @classmethod
    def setInputValue(cls, widget, value):
        return True

    @classmethod
    def resetInputValue(cls, widget):
        pass

    @classmethod
    def getFilterOperators(cls):
        return [common.OPERATOR_EMPTY,
                common.OPERATOR_NOT_EMPTY]

    @classmethod
    def getFilterEditWidgets(cls, parentWidget):
        from filter_edit import BoolFilterValEdit
        boolEdit = BoolFilterValEdit(cls, parentWidget)
        operatorMap = {}
        for operator in cls.getFilterOperators():
            operatorMap[operator] = boolEdit
        return operatorMap


class EnumHandler(AbstractTypeHandler):

    @classmethod
    def resolveValue(cls, value):
        """
        Converts value to a Python unicode object
        """
        if value is None:
            return ("", True)
        try:
            return (unicode(value), True)
        except ValueError:
            return (value, False)

    @classmethod
    def toString(cls, value):
        (value, ok) = cls.resolveValue(value)
        if ok:
            return unicode(value)
        return ""

    @classmethod
    def toCardsActionData(cls, value):
        from cards.core import ActionData, ActionDataType
        (value, ok) = cls.resolveValue(value)
        if ok:
            return ActionData(ActionDataType.string, value)
        return None

    @classmethod
    def compare(cls, left, right):
        left, ok = cls.resolveValue(left)
        if not ok:
            left = ''
        right, ok = cls.resolveValue(right)
        if not ok:
            right = ''
        return cmp(left, right)

    @classmethod
    def getInputWidget(cls, parentWidget):
        widget = QtGui.QComboBox(parentWidget)
        return widget

    @classmethod
    def getInputValue(cls, widget):
        value, ok = cls.resolveValue(widget.currentText())
        if ok:
            return value
        return ''

    @classmethod
    def setInputValue(cls, widget, value):
        value, ok = cls.resolveValue(value)
        if ok:
            widget.setCurrentIndex(widget.findText(value))
        return ok

    @classmethod
    def resetInputValue(cls, widget):
        widget.setCurrentIndex(-1)


# 	@classmethod
# 	def getFilterOperators(cls):
# 		return [common.OPERATOR_CONTAINS,
# 				common.OPERATOR_NOT_CONTAINS,
# 				common.OPERATOR_EQUALS,
# 				common.OPERATOR_NOT_EQUALS,
# 				common.OPERATOR_STARTS_WITH,
# 				common.OPERATOR_ENDS_WITH]
#
# 	@classmethod
# 	def getFilterEditWidgets(cls, parentWidget):
# 		from filter_edit import FilterValEdit
# 		stringEdit = FilterValEdit(cls, parentWidget)
# 		operatorMap = {}
# 		for operator in cls.getFilterOperators():
# 			operatorMap[operator] = stringEdit
# 		return operatorMap

TYPE_HANDLER_MAP = {
    common.TYPE_STRING_SINGLELINE: StringSinglelineHandler,
    common.TYPE_STRING_MULTILINE: StringMultilineHandler,
    common.TYPE_INTEGER: IntHandler,
    common.TYPE_UNSIGNED_INTEGER: UIntHandler,
    common.TYPE_FLOAT: FloatHandler,
    common.TYPE_BOOLEAN: BoolHandler,
    common.TYPE_DATE: DateHandler,
    common.TYPE_DATE_TIME: DateTimeHandler,
    common.TYPE_FILE_PATH: FilePathHandler,
    common.TYPE_DN_PATH: DnPathHandler,
    common.TYPE_DN_RANGE: DnRangeHandler,
    common.TYPE_RESOLUTION: ResolutionHandler,
    common.TYPE_IMAGE: ImageHandler,
    common.TYPE_ENUM: EnumHandler,
    common.TYPE_LABEL: LabelHandler
}


def getTypeHandler(dataType):
    try:
        return TYPE_HANDLER_MAP[dataType]
    except KeyError:
        if dataType in common.TYPES:
            errorMsg = "No type handler is registered for data type '%s'" % dataType
        else:
            errorMsg = "Unknown data type '%s'" % dataType
        raise exc.WizQtError(errorMsg)
