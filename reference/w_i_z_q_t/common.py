"""This module contains common global variables and functions for the scope of the wizqt package."""

# Standard imports
import getpass
import os
import subprocess
import sys
import platform
import re
import socket
import traceback
import types

# Ivy imports
import dndeprecate
from pipeicon import common as icons
from pipetheme import colours
from venom import crosslogging

# PyQt imports
from qtswitch import QtCore, QtGui, QT_API, QT_API_VERSION

from . import _APITRACKER

# Globals
__package = "wizqt"

# Global cross logger for mypackage.
__log = None

###################################################################################################################################
# CONSTANTS / ENUMERATIONS
###################################################################################################################################

HOSTNAME = (socket.getfqdn() or "").split(".")[0]
USERNAME = getpass.getuser()
MACOSX = platform.system() == "Darwin"
IS_PYQT_SIP1 = QT_API == "pyqt" and QT_API_VERSION == 1

# file locations
CONFIG_FILE_EXT = "cfg"
CONFIG_JOB_DIR = "/tools/{0}/data/cfg/wizqt".format(os.getenv('SHOW'))
CONFIG_GLOBAL_DIR = "/tools/SITE/data/cfg/wizqt"
CONFIG_USER_DIR = os.path.join(os.path.expanduser("~"), ".wizqt")

# log settings
# LOG_FORMATTER_CONSOLE = logging.Formatter("%(levelname)s: %(message)s")
# LOG_FORMATTER_FILE = logging.Formatter("[%(asctime)s] %(user)s@%(host)s:%(process)d %(levelname)s: %(message)s")
DEFAULT_LEVEL_CONSOLE = crosslogging.DEBUG
DEFAULT_LEVEL_FILE = crosslogging.DEBUG
DEFAULT_LEVEL_QT = crosslogging.INFO

# Integer limits
# do not use sys.maxint
# the values defined here are compatible with QSpinBox widgets
MINIMUM_INTEGER = -2147483648
MAXIMUM_INTEGER = 2147483647

# Float limits
MINIMUM_FLOAT = -1.7976931348623157e+308
MAXIMUM_FLOAT = 1.7976931348623157e+308

# Default window geometry
DEFAULT_WINDOW_POS = QtCore.QPoint(50, 50)
DEFAULT_WINDOW_SIZE = QtCore.QSize(800, 600)

# log level icons
LEVEL_ICON_MAP = {
    crosslogging.CRITICAL: icons.ICON_ERROR_SML,
    crosslogging.ERROR: icons.ICON_ERROR_SML,
    crosslogging.WARNING: icons.ICON_WARNING_SML,
    crosslogging.INFO: icons.ICON_INFO_SML,
    crosslogging.VERBOSE: icons.ICON_VERBOSE_SML,
    crosslogging.DEBUG: icons.ICON_DEBUG_SML,
}

# cell edit types
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

# ANCHOR ROLE IDENTIFIED
ANCHOR = "ANCHOR"

# GROUP FIELDS
STEM_GROUP = "StemGroup"
TWIG_GROUP = "TwigGroup"

GROUP_TYPES = [STEM_GROUP, TWIG_GROUP]

# color keys, to be passed to getColor() method
COLORKEY_CRITICAL = crosslogging.CRITICAL
COLORKEY_ERROR = crosslogging.ERROR
COLORKEY_WARNING = crosslogging.WARNING
COLORKEY_INFO = crosslogging.INFO
COLORKEY_VERBOSE = crosslogging.VERBOSE
COLORKEY_DEBUG = crosslogging.DEBUG

COLORKEY_INSERT = EDITNAME_INSERT
COLORKEY_DELETE = EDITNAME_DELETE
COLORKEY_REVIVE = EDITNAME_REVIVE
COLORKEY_ENABLE = EDITNAME_ENABLE
COLORKEY_UPDATE = EDITNAME_UPDATE
COLORKEY_MOVE = EDITNAME_MOVE
COLORKEY_MOVEUPDATE = EDITNAME_MOVEUPDATE
COLORKEY_ARCHIVE = EDITNAME_ARCHIVE
COLORKEY_DISABLE = EDITNAME_DISABLE

COLORKEY_NONLOCAL = "nonlocal"
COLORKEY_IGNORED = "ignored"
COLORKEY_DELETED = "deleted"
COLORKEY_ARCHIVED = "archived"


def __getColorKeyMap():
    """
    Get the color key map.

    Moved this inside a method as QtGui.QApplication.palette(), without
    an app initialised, results in a segmentation fault with pyside2
    PTSUP-41486, MAYADEV-855
    """
    colorKeyMap = {
        COLORKEY_CRITICAL: ((255, 255, 255), (170, 0, 0)),
        COLORKEY_ERROR: (colours.COLOR_RED_FG, colours.COLOR_RED_BG),
        COLORKEY_WARNING: (colours.COLOR_YELLOW_FG, colours.COLOR_YELLOW_BG),
        COLORKEY_INFO: (colours.COLOR_BLUE_FG, colours.COLOR_BLUE_BG),
        COLORKEY_DEBUG: (
            QtGui.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text).getRgb(), None),

        COLORKEY_INSERT: (colours.COLOR_GREEN_FG, colours.COLOR_GREEN_BG),
        COLORKEY_DELETE: (colours.COLOR_RED_FG, colours.COLOR_RED_BG),
        COLORKEY_REVIVE: (colours.COLOR_GREEN_FG, colours.COLOR_GREEN_BG),
        COLORKEY_ENABLE: (colours.COLOR_GREEN_FG, colours.COLOR_GREEN_BG),
        COLORKEY_UPDATE: (colours.COLOR_YELLOW_FG, colours.COLOR_YELLOW_BG),
        COLORKEY_MOVE: (colours.COLOR_BLUE_FG, colours.COLOR_BLUE_BG),
        COLORKEY_MOVEUPDATE: (colours.COLOR_PURPLE_FG, colours.COLOR_PURPLE_BG),
        COLORKEY_ARCHIVE: (colours.COLOR_ORANGE_FG, colours.COLOR_ORANGE_BG),

        COLORKEY_NONLOCAL: (
            QtGui.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text).getRgb(), None),
        COLORKEY_IGNORED: (
            QtGui.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text).getRgb(), None),
        COLORKEY_DELETED: (colours.COLOR_RED_FG, colours.COLOR_RED_BG),
        COLORKEY_ARCHIVED: (colours.COLOR_ORANGE_FG, colours.COLOR_ORANGE_BG),
    }

    return colorKeyMap


def getColor(colorKey, foreground=True):
    # lookup color by colorkey
    try:
        colorKeyMap = __getColorKeyMap()
        colorTuple = colorKeyMap[colorKey][0 if foreground else 1]
    except KeyError:
        colorTuple = None
    if colorTuple:
        return QtGui.QColor(*colorTuple)
    return None


def getEditName(editBitMask):
    if editBitMask & EDITBITMASK_INSERT:
        return EDITNAME_INSERT
    elif editBitMask & EDITBITMASK_DELETE:
        return EDITNAME_DELETE
    elif editBitMask & EDITBITMASK_REVIVE:
        return EDITNAME_REVIVE
    elif editBitMask & EDITBITMASK_ENABLE:
        return EDITNAME_ENABLE
    elif editBitMask & EDITBITMASK_UPDATE:
        if editBitMask & EDITBITMASK_MOVE:
            return EDITNAME_MOVEUPDATE
        return EDITNAME_UPDATE
    elif editBitMask & EDITBITMASK_MOVE:
        return EDITNAME_MOVE
    elif editBitMask & EDITBITMASK_ARCHIVE:
        return EDITNAME_ARCHIVE
    elif editBitMask & EDITBITMASK_DISABLE:
        return EDITNAME_DISABLE
    return None


def hideLockedItems(locked, widgets):
    '''
    locked : list
        of widgets to hide
    widgets : list
        of widgets i
    '''
    if isinstance(locked, dict):
        isLocked = lambda key: locked.get(key)
    elif isinstance(locked, list):
        isLocked = lambda key: key in locked
    else:
        raise TypeError("<locked> must be a list or a dict, got {0}".format(type(locked)))
    for widgetKey, widget in widgets.iteritems():
        if hasattr(widget, 'setVisible'):
            hidden = isLocked(widgetKey)
            if hidden is not None:
                widget.setVisible(not hidden)


# custom events
EVENT_PRE_DROP = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())
EVENT_POST_DROP = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())
EVENT_DRAG_HOVER = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())
EVENT_POST_DRAG_MOVE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

# custom ItemDataRoles
ROLE_LAST = QtCore.Qt.UserRole + 1  # use this as starting point for any custom roles specific to a module
# list of roles that should be included in a model's editState
# i.e. any roles that contain real data, as opposed to just decoration
ROLES_EDITSTATE = set([QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.CheckStateRole])


def registerDataRole(trackEdits=False):
    global ROLE_LAST
    global ROLES_EDITSTATE
    ROLE_LAST += 1  # increment the last role
    if trackEdits:
        ROLES_EDITSTATE.add(ROLE_LAST)
    return ROLE_LAST


ROLE_NAME = registerDataRole(trackEdits=True)
ROLE_TYPE = registerDataRole(trackEdits=True)
ROLE_CATEGORY = registerDataRole(trackEdits=True)
ROLE_FILE_PATH = registerDataRole(trackEdits=True)
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

# Column types
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
TYPES = set(
    [TYPE_STRING_SINGLELINE, TYPE_STRING_MULTILINE, TYPE_INTEGER, TYPE_UNSIGNED_INTEGER, TYPE_FLOAT, TYPE_BOOLEAN,
     TYPE_DATE, TYPE_DATE_TIME, TYPE_FILE_PATH, TYPE_DN_PATH, TYPE_DN_RANGE, TYPE_RESOLUTION, TYPE_IMAGE, TYPE_ENUM,
     TYPE_LABEL])
TYPE_DEFAULT = TYPE_STRING_SINGLELINE

# Filter operators
OPERATOR_CONTAINS = "contains"
OPERATOR_NOT_CONTAINS = "does not contain"
OPERATOR_EQUALS = "is"
OPERATOR_NOT_EQUALS = "is not"
OPERATOR_STARTS_WITH = "starts with"
OPERATOR_ENDS_WITH = "ends with"
OPERATOR_GREATER_THAN = "is greater than"
OPERATOR_GREATER_THAN_EQUAL_TO = "is greater than or equal to"
OPERATOR_LESS_THAN = "is less than"
OPERATOR_LESS_THAN_EQUAL_TO = "is less than or equal to"
OPERATOR_IN_RANGE = "is in the range"
OPERATOR_TRUE = "is true"
OPERATOR_FALSE = "is false"
OPERATOR_AFTER = "is after"
OPERATOR_BEFORE = "is before"
OPERATOR_IN_LAST = "is in the last"
OPERATOR_NOT_IN_LAST = "is not in the last"
OPERATOR_MATCHES_RE = "matches regular expression"
OPERATOR_NOT_MATCHES_RE = "does not match regular expression"
OPERATOR_IN = "in"
OPERATOR_LIKE = "like"

# #TODO:
# OPERATOR_IN_NEXT = "is in the next"
# OPERATOR_NOT_IN_NEXT = "is not in the next"
# OPERATOR_IN_WEEK = "in calendar week"
# OPERATOR_IN_MONTH = "in calendar month"
# OPERATOR_IN_DAY = "in calendar day"
# OPERATOR_IN_YEAR = "in calendar year"
OPERATOR_EMPTY = "is empty"
OPERATOR_NOT_EMPTY = "is not empty"
OPERATOR_DATE_EQUALS = "date is"
OPERATOR_DATE_NOT_EQUALS = "date is not"
OPERATORS = [OPERATOR_CONTAINS, OPERATOR_NOT_CONTAINS, OPERATOR_EQUALS, OPERATOR_NOT_EQUALS, OPERATOR_STARTS_WITH,
             OPERATOR_ENDS_WITH,
             OPERATOR_GREATER_THAN, OPERATOR_GREATER_THAN_EQUAL_TO, OPERATOR_LESS_THAN, OPERATOR_LESS_THAN_EQUAL_TO,
             OPERATOR_IN_RANGE, OPERATOR_TRUE, OPERATOR_FALSE, OPERATOR_AFTER, OPERATOR_BEFORE,
             OPERATOR_IN_LAST, OPERATOR_NOT_IN_LAST, OPERATOR_EMPTY, OPERATOR_NOT_EMPTY, OPERATOR_DATE_EQUALS,
             OPERATOR_DATE_NOT_EQUALS, OPERATOR_MATCHES_RE, OPERATOR_NOT_MATCHES_RE, OPERATOR_IN, OPERATOR_LIKE]

# Time durations
DURATION_HOURS = "hours"
DURATION_DAYS = "days"
DURATION_WEEKS = "weeks"
DURATION_MONTHS = "months"
DATE_DURATIONS = [DURATION_DAYS, DURATION_WEEKS, DURATION_MONTHS]
DATETIME_DURATIONS = [DURATION_HOURS] + DATE_DURATIONS

# MIME types
MIME_TYPE_PLAIN_TEXT = "text/plain"
MIME_TYPE_HTML = "text/html"
MIME_TYPE_CSV = "text/csv"
MIME_TYPE_MODEL_INDEXES = "application/x-model-indexes"
MIME_TYPE_IVY_ITEMS = "application/x-ivy-items"

# Text for 'all jobs' item in job picker combo
ALL_JOBS = "<ALL>"

DATETIME_JSON_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


###################################################################################################################################
# FUNCTIONS
###################################################################################################################################

@_APITRACKER.track_calls(-1)
def getLog():
    """
    Returns the global logger associated with the wizqt library.

    :return: Global wizqt logger instance.
    :rtype: C{CrossLogger}
    """

    global __log

    if not __log:
        __log = crosslogging.setupCrossLogging(__package)
        __log.setLevel(crosslogging.ERROR)

    return __log


@_APITRACKER.track_calls(-1)
def getLogs():
    """
    Returns a temporary crosslogger group with the wizqt global logger attached.

    This method is here for backwards compatibility.
    There is now only one log associated with the wizqt library.

    :return: Temporary crosslogger group with global wizqt logger instance attached.
    :rtype: C{CrossLoggerGroup}
    """

    dndeprecate.warn(
        "The getLogs() function is deprecated as only a single log exists for the wizqt library now. Use getLog() instead.")

    temp_crossloggergroup = crosslogging.CrossLoggerGroup()
    temp_crossloggergroup.addLogger(getLog())

    return temp_crossloggergroup


@_APITRACKER.track_calls(-1)
def getPackage():
    """
        Returns the name of the package.

        @return:	Package name.
        @rtype:		string
    """

    return __package


@_APITRACKER.track_calls(-1)
def startLogging(*args):
    """
    Redirects to crosslogging.startCrossLogging( log, *args ).
    """

    crosslogging.startCrossLogging(getLog(), *args)


@_APITRACKER.track_calls(-1)
def stopLogging(*args):
    """
    Redirects to crosslogging.stopCrossLogging( log, *args ).
    """

    crosslogging.stopCrossLogging(getLog(), *args)


def pingHost(filePath):
    """
    Check for a response from a host. this is important because loading image files
    from an unresponsive host will cause a permananet hang.

    :parameters:
        filePath : str
            Any filepath, this function will check if it begins with /hosts/,
            and if it doesn't will return True ( if we can't check if it is
            valid, assume it is ).
    :return:
        True if the host can be reached, or the path given is not a /hosts/ path
    :rtype:
        bool
    """
    match = re.search('(?<=/hosts/).*?(?=/)', filePath)
    if match is None:
        return True  # we can't find hostname, so allow it through
    hostname = match.group(0)
    if MACOSX:
        p = subprocess.Popen(
            ['ping', hostname, '-c', '1', '-t', '1'],  # -c == ping count, -t == timeout ( sec )
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    else:
        p = subprocess.Popen(
            ['ping', '-c', '1', '-w', '1', hostname],  # -c == ping count, -w == timeout ( sec )
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    stdout, stderr = p.communicate()
    if stderr:
        getLog().warning('Host "{0}" not found: {1}'.format(hostname, stderr))
        return False
    return True


def separatorAction(widget):
    action = QtGui.QAction(widget)
    action.setSeparator(True)
    widget.addAction(action)


def createAction(parentWidget, text=None, slot=None, shortcut=None, shortcutContext=QtCore.Qt.WidgetShortcut,
                 icon=None, menu=None, tip=None, checkable=False, signal="triggered()"):
    action = QtGui.QAction(parentWidget)
    if text is not None:
        action.setText(text)
    if icon is not None:
        action.setIcon(icon)
    if menu is not None:
        action.setMenu(menu)
    if shortcut:
        if isinstance(shortcut, list):
            action.setShortcuts(shortcut)
        else:
            action.setShortcut(shortcut)
        action.setShortcutContext(shortcutContext)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if slot is not None:
        QtCore.QObject.connect(action, QtCore.SIGNAL(signal), slot)
    action.setCheckable(checkable)
    return action


def addAction(widget, action, prepend=False):
    beforeAction = widget.actions()[0] if (widget.actions() and prepend) else None
    widget.insertAction(beforeAction, action)


def insertAction(widget, beforeText, action, prepend=False):
    # check the before action exists
    beforeAction = getAction(widget, beforeText)
    if beforeAction is not None:
        if prepend:
            # put it above this action
            widget.insertAction(beforeAction, action)
            return
        # put it below
        currentActions = widget.actions()
        widget.insertAction(currentActions[currentActions.index(beforeAction)] or beforeAction, action)
        return
    widget.addAction(action)


def addActions(widget, actions, prepend=False):
    beforeAction = widget.actions()[0] if (widget.actions() and prepend) else None
    widget.insertActions(beforeAction, actions)


def getAction(widget, actionText):
    actionText = actionText.replace("&", "")
    for action in widget.actions():
        if action.text().replace("&", "") == actionText:
            return action
    return None


def removeAction(widget, actionText):
    action = getAction(widget, actionText)
    if action:
        widget.removeAction(action)


def replaceAction(widget, actionText, action, prepend=False):
    oldAction = getAction(widget, actionText)
    if oldAction:
        widget.insertAction(oldAction, action)
        widget.removeAction(oldAction)
    else:
        addAction(widget, action, prepend=prepend)


def verticalSeparator(parentWidget):
    separator = QtGui.QFrame(parentWidget)
    separator.setFrameStyle(QtGui.QFrame.VLine | QtGui.QFrame.Sunken)
    return separator


def horizontalSeparator(parentWidget):
    separator = QtGui.QFrame(parentWidget)
    separator.setFrameStyle(QtGui.QFrame.HLine | QtGui.QFrame.Sunken)
    return separator


def imageFormatIsAnimatable(path):
    """
    Checks the path is either an mng or a gif
    """
    animFormats = ('.gif', '.mng')
    return path is not None and os.path.splitext(path)[-1] in animFormats


def centerWindowInScreen(widget):
    if widget.parent():
        return

    window = widget.window()
    desktop = QtGui.QApplication.desktop()

    screenGeom = desktop.availableGeometry(window)

    window.move(screenGeom.center() - window.rect().center())


def __newMessageBox(parent, title, text, detailedText, standardButtons, defaultButton, iconPixmap=None):
    msgBox = QtGui.QMessageBox(QtGui.QMessageBox.NoIcon, title, text, standardButtons, parent)
    if iconPixmap:
        msgBox.setIconPixmap(iconPixmap)

    if detailedText:
        msgBox.setDetailedText(detailedText)

    defaultBtn = msgBox.button(defaultButton)
    if defaultBtn:
        msgBox.setDefaultButton(defaultBtn)

    return msgBox


def exceptionDialog(parent, exc_info, text="", title="Uncaught Exception", standardButtons=QtGui.QMessageBox.Ok,
                    defaultButton=QtGui.QMessageBox.NoButton):
    if not text:
        text = "An error occurred. %s: %s" % (exc_info[0].__name__, exc_info[1])
    msgBox = __newMessageBox(parent, title, text, None, standardButtons, defaultButton,
                             QtGui.QPixmap(icons.ICON_ERROR_LRG))
    # put exception stack trace as detailed text
    msgBox.setDetailedText("".join(traceback.format_exception(*exc_info)))
    return msgBox


def errorDialog(parent, text, title="Error", detailedText=None, standardButtons=QtGui.QMessageBox.Ok,
                defaultButton=QtGui.QMessageBox.NoButton):
    return __newMessageBox(parent, title, text, detailedText, standardButtons, defaultButton,
                           QtGui.QPixmap(icons.ICON_ERROR_LRG))


def warningDialog(parent, text, title="Warning", detailedText=None, standardButtons=QtGui.QMessageBox.Ok,
                  defaultButton=QtGui.QMessageBox.NoButton):
    return __newMessageBox(parent, title, text, detailedText, standardButtons, defaultButton,
                           QtGui.QPixmap(icons.ICON_WARNING_LRG))


def infoDialog(parent, text, title="", detailedText=None, standardButtons=QtGui.QMessageBox.Ok,
               defaultButton=QtGui.QMessageBox.NoButton):
    return __newMessageBox(parent, title, text, detailedText, standardButtons, defaultButton,
                           QtGui.QPixmap(icons.ICON_INFO_LRG))


def questionDialog(parent, text, title="", detailedText=None,
                   standardButtons=QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, defaultButton=QtGui.QMessageBox.No):
    return __newMessageBox(parent, title, text, detailedText, standardButtons, defaultButton,
                           QtGui.QPixmap(icons.ICON_QUESTION_LRG))


# Guard function for older qt verions used in nuke
def isCurrentQt():
    # pyside check here
    if os.environ.get("QT_API") == "pyside":
        return True
    # pyqt check here
    parts = QtCore.__version__.split(".")
    majorVersion = int(parts[0])
    minorVersion = int(parts[1])
    if majorVersion <= 4 and minorVersion < 6:
        return False
    return True


RE_URL = re.compile("^https?://", re.IGNORECASE)


def urlsFromMimeData(mimeData):
    """Utility method to extract URL strings from QMimeData.

    This is necessary because the QMimeData.urls() method does not behave reliably
    across all versions of PyQt and PySide. Sometimes it returns garbage, for unknown
    reasons but probably a bug in interpreting the null-terminated character array.
    So instead we read from the 'text/plain' mime type and parse the URLs out of it.
    """
    urls = []
    # hasUrls() is a good first check to make sure that 'text/uri-list' is one of the
    # included formats. But to get the data, we read from 'text/plain'.
    if mimeData.hasUrls() and mimeData.hasText():
        for line in mimeData.text().splitlines():
            line = line.strip()
            if RE_URL.match(line):
                urls.append(line)
    return urls


# Deprecated references
COLOR_RED_FG = colours.COLOR_RED_FG
COLOR_RED_BG = colours.COLOR_RED_BG
COLOR_YELLOW_FG = colours.COLOR_YELLOW_FG
COLOR_YELLOW_BG = colours.COLOR_YELLOW_BG
COLOR_BLUE_FG = colours.COLOR_BLUE_FG
COLOR_BLUE_BG = colours.COLOR_BLUE_BG
COLOR_GREEN_FG = colours.COLOR_GREEN_FG
COLOR_GREEN_BG = colours.COLOR_GREEN_BG
COLOR_PURPLE_FG = colours.COLOR_PURPLE_FG
COLOR_PURPLE_BG = colours.COLOR_PURPLE_BG
COLOR_ORANGE_FG = colours.COLOR_ORANGE_FG
COLOR_ORANGE_BG = colours.COLOR_ORANGE_BG
COLOR_GRAY_FG = colours.COLOR_GRAY_FG
ICON_ACCEPT_SML = icons.ICON_ACCEPT_SML
ICON_ADD_SML = icons.ICON_ADD_SML
ICON_ADD_MED = icons.ICON_ADD_MED
ICON_ARROW_SML = icons.ICON_ARROW_SML
ICON_AUTO_REFRESH_SML = icons.ICON_AUTO_REFRESH_SML
ICON_CHAIN_LRG = icons.ICON_CHAIN_LRG
ICON_CLOCK_SML = icons.ICON_CLOCK_SML
ICON_CLOSE_MED = icons.ICON_CLOSE_MED
ICON_CLIPBOARD_SML = icons.ICON_CLIPBOARD_SML
ICON_COLORKEY_MED = icons.ICON_COLORKEY_MED
ICON_COMPUTER_SML = icons.ICON_COMPUTER_SML
ICON_COPY_SML = icons.ICON_COPY_SML
ICON_DATATYPE_DICT_MED = icons.ICON_DATATYPE_DICT_MED
ICON_DELETE_SML = icons.ICON_DELETE_SML
ICON_DRAG_MED = icons.ICON_DRAG_MED
ICON_EDIT_SML = icons.ICON_EDIT_SML
ICON_EMBLEM_DISABLE_SML = icons.ICON_EMBLEM_DISABLE_SML
ICON_EMBLEM_NEW_SML = icons.ICON_EMBLEM_NEW_SML
ICON_ENABLE_SML = icons.ICON_ENABLE_SML
ICON_ERROR_SML = icons.ICON_ERROR_SML
ICON_EXIT_SML = icons.ICON_EXIT_SML
ICON_FILE_NEW_SML = icons.ICON_FILE_NEW_SML
ICON_FILTER_SML = icons.ICON_FILTER_SML
ICON_FILTER_SHARED_SML = icons.ICON_FILTER_SHARED_SML
ICON_FOLDER_SML = icons.ICON_FOLDER_SML
ICON_GREEN_ARROW_LRG = icons.ICON_GREEN_ARROW_LRG
ICON_HELP_SML = icons.ICON_HELP_SML
ICON_INFO_SML = icons.ICON_INFO_SML
ICON_JOB_SML = icons.ICON_JOB_SML
ICON_LOCK_SML = icons.ICON_LOCK_SML
ICON_LOG_VIEWER_SML = icons.ICON_LOG_VIEWER_SML
ICON_NO_MED = icons.ICON_NO_MED
ICON_PAUSE_SML = icons.ICON_PAUSE_SML
ICON_PASTE_SML = icons.ICON_PASTE_SML
ICON_QUESTION_SML = icons.ICON_QUESTION_SML
ICON_REFRESH_SML = icons.ICON_REFRESH_SML
ICON_REFRESH_MED = icons.ICON_REFRESH_MED
ICON_REJECT_SML = icons.ICON_REJECT_SML
ICON_RESET_SML = icons.ICON_RESET_SML
ICON_SAVE_SML = icons.ICON_SAVE_SML
ICON_SEARCH_SML = icons.ICON_SEARCH_SML
ICON_SELECT_ALL_SML = icons.ICON_SELECT_ALL_SML
ICON_SETTINGS_SML = icons.ICON_SETTINGS_SML
ICON_SHOT_SML = icons.ICON_SHOT_SML
ICON_SYSTEM_SML = icons.ICON_COG_SML
ICON_UNIT_SML = icons.ICON_UNIT_SML
ICON_UP_ARROW_SML = icons.ICON_UP_ARROW_SML
ICON_USER_SML = icons.ICON_USER_SML
ICON_WARNING_SML = icons.ICON_WARNING_SML
ICON_WARNING_LRG = icons.ICON_WARNING_LRG
ICON_YES_MED = icons.ICON_YES_MED
getFileIcon = icons.getFileIcon
compositePixmaps = icons.compositePixmaps


class _DeprecatedReferenceHandler(types.ModuleType):
    """This handler is used to issue a dndeprecate warning anytime one of the
    listed attributes is accessed. This is a way of partially wrapping some of
    the symbols in this module as deprecated, but not all.
    """

    _ATTRIBUTES = {
        "COLOR_RED_FG": (COLOR_RED_FG, "pipetheme.colours"),
        "COLOR_RED_BG": (COLOR_RED_BG, "pipetheme.colours"),
        "COLOR_YELLOW_FG": (COLOR_YELLOW_FG, "pipetheme.colours"),
        "COLOR_YELLOW_BG": (COLOR_YELLOW_BG, "pipetheme.colours"),
        "COLOR_BLUE_FG": (COLOR_BLUE_FG, "pipetheme.colours"),
        "COLOR_BLUE_BG": (COLOR_BLUE_BG, "pipetheme.colours"),
        "COLOR_GREEN_FG": (COLOR_GREEN_FG, "pipetheme.colours"),
        "COLOR_GREEN_BG": (COLOR_GREEN_BG, "pipetheme.colours"),
        "COLOR_PURPLE_FG": (COLOR_PURPLE_FG, "pipetheme.colours"),
        "COLOR_PURPLE_BG": (COLOR_PURPLE_BG, "pipetheme.colours"),
        "COLOR_ORANGE_FG": (COLOR_ORANGE_FG, "pipetheme.colours"),
        "COLOR_ORANGE_BG": (COLOR_ORANGE_BG, "pipetheme.colours"),
        "COLOR_GRAY_FG": (COLOR_GRAY_FG, "pipetheme.colours"),
        "ICON_ACCEPT_SML": (ICON_ACCEPT_SML, "pipeicon.common"),
        "ICON_ADD_SML": (ICON_ADD_SML, "pipeicon.common"),
        "ICON_ADD_MED": (ICON_ADD_MED, "pipeicon.common"),
        "ICON_ARROW_SML": (ICON_ARROW_SML, "pipeicon.common"),
        "ICON_AUTO_REFRESH_SML": (ICON_AUTO_REFRESH_SML, "pipeicon.common"),
        "ICON_CHAIN_LRG": (ICON_CHAIN_LRG, "pipeicon.common"),
        "ICON_CLOCK_SML": (ICON_CLOCK_SML, "pipeicon.common"),
        "ICON_CLOSE_MED": (ICON_CLOSE_MED, "pipeicon.common"),
        "ICON_CLIPBOARD_SML": (ICON_CLIPBOARD_SML, "pipeicon.common"),
        "ICON_COLORKEY_MED": (ICON_COLORKEY_MED, "pipeicon.common"),
        "ICON_COMPUTER_SML": (ICON_COMPUTER_SML, "pipeicon.common"),
        "ICON_COPY_SML": (ICON_COPY_SML, "pipeicon.common"),
        "ICON_DATATYPE_DICT_MED": (ICON_DATATYPE_DICT_MED, "pipeicon.common"),
        "ICON_DELETE_SML": (ICON_DELETE_SML, "pipeicon.common"),
        "ICON_DRAG_MED": (ICON_DRAG_MED, "pipeicon.common"),
        "ICON_EDIT_SML": (ICON_EDIT_SML, "pipeicon.common"),
        "ICON_EMBLEM_DISABLE_SML": (ICON_EMBLEM_DISABLE_SML, "pipeicon.common"),
        "ICON_EMBLEM_NEW_SML": (ICON_EMBLEM_NEW_SML, "pipeicon.common"),
        "ICON_ENABLE_SML": (ICON_ENABLE_SML, "pipeicon.common"),
        "ICON_ERROR_SML": (ICON_ERROR_SML, "pipeicon.common"),
        "ICON_EXIT_SML": (ICON_EXIT_SML, "pipeicon.common"),
        "ICON_FILE_NEW_SML": (ICON_FILE_NEW_SML, "pipeicon.common"),
        "ICON_FILTER_SML": (ICON_FILTER_SML, "pipeicon.common"),
        "ICON_FILTER_SHARED_SML": (ICON_FILTER_SHARED_SML, "pipeicon.common"),
        "ICON_FOLDER_SML": (ICON_FOLDER_SML, "pipeicon.common"),
        "ICON_GREEN_ARROW_LRG": (ICON_GREEN_ARROW_LRG, "pipeicon.common"),
        "ICON_HELP_SML": (ICON_HELP_SML, "pipeicon.common"),
        "ICON_INFO_SML": (ICON_INFO_SML, "pipeicon.common"),
        "ICON_JOB_SML": (ICON_JOB_SML, "pipeicon.common"),
        "ICON_LOCK_SML": (ICON_LOCK_SML, "pipeicon.common"),
        "ICON_LOG_VIEWER_SML": (ICON_LOG_VIEWER_SML, "pipeicon.common"),
        "ICON_NO_MED": (ICON_NO_MED, "pipeicon.common"),
        "ICON_PAUSE_SML": (ICON_PAUSE_SML, "pipeicon.common"),
        "ICON_PASTE_SML": (ICON_PASTE_SML, "pipeicon.common"),
        "ICON_QUESTION_SML": (ICON_QUESTION_SML, "pipeicon.common"),
        "ICON_REFRESH_SML": (ICON_REFRESH_SML, "pipeicon.common"),
        "ICON_REFRESH_MED": (ICON_REFRESH_MED, "pipeicon.common"),
        "ICON_REJECT_SML": (ICON_REJECT_SML, "pipeicon.common"),
        "ICON_RESET_SML": (ICON_RESET_SML, "pipeicon.common"),
        "ICON_SAVE_SML": (ICON_SAVE_SML, "pipeicon.common"),
        "ICON_SEARCH_SML": (ICON_SEARCH_SML, "pipeicon.common"),
        "ICON_SELECT_ALL_SML": (ICON_SELECT_ALL_SML, "pipeicon.common"),
        "ICON_SETTINGS_SML": (ICON_SETTINGS_SML, "pipeicon.common"),
        "ICON_SHOT_SML": (ICON_SHOT_SML, "pipeicon.common"),
        "ICON_SYSTEM_SML": (ICON_SYSTEM_SML, "pipeicon.common"),
        "ICON_UNIT_SML": (ICON_UNIT_SML, "pipeicon.common"),
        "ICON_UP_ARROW_SML": (ICON_UP_ARROW_SML, "pipeicon.common"),
        "ICON_USER_SML": (ICON_USER_SML, "pipeicon.common"),
        "ICON_WARNING_SML": (ICON_WARNING_SML, "pipeicon.common"),
        "ICON_WARNING_LRG": (ICON_WARNING_LRG, "pipeicon.common"),
        "ICON_YES_MED": (ICON_YES_MED, "pipeicon.common"),
        "getFileIcon": (getFileIcon, "pipeicon.util"),
        "compositePixmaps": (compositePixmaps, "pipeicon.util"),
    }

    @_APITRACKER.track_calls(-1)
    def _track_deprecated_constant(self, attribute, new_location):
        # This lets us tracks dndeprecate calls without any updates to
        # dndeprecate. It's used here to track some of the __getattr__
        # calls, the ones that try to access a deprecated constant
        # from the list above.
        dndeprecate.warn(
            "{0}.{1} has moved; please update all references to import from {2} instead".format(__name__, attribute,
                                                                                                new_location))

    def __getattr__(self, attribute):
        if attribute in self._ATTRIBUTES:
            (symbol, new_location) = self._ATTRIBUTES[attribute]
            # Track that a deprecated reference/constat was used.
            self._track_deprecated_constant(attribute, new_location)
            return symbol

        return getattr(_old_module, attribute)

    def __dir__(self):
        return dir(_old_module)


# Please don't garbage collect me :)
_old_module = sys.modules[__name__]

_new_module = sys.modules[__name__] = _DeprecatedReferenceHandler(__name__)
_new_module.__dict__.update({
    "__file__": __file__,
    "__package__": "wizqt",
    "__doc__": __doc__,
    "__all__": [attr for attr in dir(_new_module) if not attr.startswith("_")]
})
