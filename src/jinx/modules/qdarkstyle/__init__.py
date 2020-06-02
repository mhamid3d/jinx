#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""QDarkStyle is a dark stylesheet for Python and Qt applications.

This module provides a function to load the stylesheets transparently
with the right resources file.

First, start importing our module

.. code-block:: python

    import qdarkstyle

Then you can get stylesheet provided by QDarkStyle for various Qt wrappers
as shown below

.. code-block:: python

    # PySide
    dark_stylesheet = qdarkstyle.load_stylesheet_pyside()
    # PySide 2
    dark_stylesheet = qdarkstyle.load_stylesheet_pyside2()
    # PyQt4
    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt()
    # PyQt5
    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()

Alternatively, from environment variables provided by QtPy, PyQtGraph, Qt.Py

.. code-block:: python

    # QtPy
    dark_stylesheet = qdarkstyle.load_stylesheet()
    # PyQtGraph
    dark_stylesheet = qdarkstyle.load_stylesheet(qt_api=os.environ('PYQTGRAPH_QT_LIB'))
    # Qt.Py
    dark_stylesheet = qdarkstyle.load_stylesheet(qt_api=Qt.__binding__)

Finally, set your QApplication with it

.. code-block:: python

    app.setStyleSheet(dark_stylesheet)

Enjoy!

"""

# Standard library imports
import logging
import os
import platform
import warnings

# Local imports
from qdarkstyle.palette import DarkPalette

_logger = logging.getLogger(__name__)
logging.basicConfig()

# Folder's path
REPO_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

EXAMPLE_PATH = os.path.join(REPO_PATH, 'example')
IMAGES_PATH = os.path.join(REPO_PATH, 'images')
PACKAGE_PATH = os.path.join(REPO_PATH, 'qdarkstyle')

QSS_PATH = os.path.join(PACKAGE_PATH, 'qss')
RC_PATH = os.path.join(PACKAGE_PATH, 'rc')
SVG_PATH = os.path.join(PACKAGE_PATH, 'svg')

# File names
QSS_FILE = 'style.qss'
QRC_FILE = QSS_FILE.replace('.qss', '.qrc')

MAIN_SCSS_FILE = 'main.scss'
STYLES_SCSS_FILE = '_styles.scss'
VARIABLES_SCSS_FILE = '_variables.scss'

# File paths
QSS_FILEPATH = os.path.join(PACKAGE_PATH, QSS_FILE)
QRC_FILEPATH = os.path.join(PACKAGE_PATH, QRC_FILE)

MAIN_SCSS_FILEPATH = os.path.join(QSS_PATH, MAIN_SCSS_FILE)
STYLES_SCSS_FILEPATH = os.path.join(QSS_PATH, STYLES_SCSS_FILE)
VARIABLES_SCSS_FILEPATH = os.path.join(QSS_PATH, VARIABLES_SCSS_FILE)


def _apply_application_patches(QCoreApplication, QPalette, QColor):
    """
    Apply application level fixes on the QPalette.

    The import names args must be passed here because the import is done
    inside the load_stylesheet() function, as QtPy is only imported in
    that moment for setting reasons.
    """
    # See issue #139
    color = DarkPalette.COLOR_SELECTION_LIGHT
    qcolor = QColor(color)

    # Todo: check if it is qcoreapplication indeed
    app = QCoreApplication.instance()

    if app:
        palette = app.palette()
        palette.setColor(QPalette.Normal, QPalette.Link, qcolor)
        app.setPalette(palette)
    else:
        _logger.warn("No QCoreApplication instance found. "
                     "Application patches not applied. "
                     "You have to call load_stylesheet function after "
                     "instantiation of QApplication to take effect. ")


def _load_stylesheet(qt_api=''):
    """
    Load the stylesheet based on QtPy abstraction layer environment variable.

    If the argument is not passed, it uses the current QT_API environment
    variable to make the imports of Qt bindings. If passed, it sets this
    variable then make the imports.

    Args:
        qt_api (str): qt binding name to set QT_API environment variable.
                      Default is ''. Possible values are pyside, pyside2
                      pyqt4, pyqt5. Not case sensitive.

    Note:
        - Note that the variable QT_API is read when first imported. So,
          pay attention to the import order.
        - If you are using another abstraction layer, i.e PyQtGraph to do
          imports on Qt things you must set both to use the same Qt
          binding (PyQt, PySide).
        - OS, binding and binding version number, and application specific
          patches are applied in this order.

    Returns:
        str: stylesheet string (css).
    """

    if qt_api:
        os.environ['QT_API'] = qt_api

    # Import is made after setting QT_API
    from qtpy.QtCore import QCoreApplication, QFile, QTextStream
    from qtpy.QtGui import QColor, QPalette

    # Then we import resources - binary qrc content
    from qdarkstyle import style_rc

    # Thus, by importing the binary we can access the resources
    package_dir = os.path.basename(PACKAGE_PATH)
    qss_rc_path = ":" + os.path.join(package_dir, QSS_FILE)

    # It gets the qss file from compiled style_rc that was import
    # not from the file QSS as we are using resources
    qss_file = QFile(qss_rc_path)

    if qss_file.exists():
        qss_file.open(QFile.ReadOnly | QFile.Text)
        text_stream = QTextStream(qss_file)
        stylesheet = text_stream.readAll()
    else:
        stylesheet = ""
        # Todo: check this raise type and add to docs
        raise FileNotFoundError("Unable to find QSS file '{}' "
                                "in resources.".format(qss_rc_path))

    # 4. Apply palette fix. See issue #139
    _apply_application_patches(QCoreApplication, QPalette, QColor)

    return stylesheet


def load_stylesheet(*args, **kwargs):
    """
    Load the stylesheet. Takes care of importing the rc module.

    Args:
        pyside (bool): True to load the PySide (or PySide2) rc file,
                       False to load the PyQt4 (or PyQt5) rc file.
                       Default is False.
        or

        qt_api (str): Qt binding name to set QT_API environment variable.
                      Default is '', i.e PyQt5 the default QtPy binding.
                      Possible values are pyside, pyside2 pyqt4, pyqt5.
                      Not case sensitive.

    Raises:
        TypeError: If arguments do not match: type, keyword name nor quantity.

    Returns:
        str: the stylesheet string.
    """

    stylesheet = ""
    arg = None

    try:
        arg = args[0]
    except IndexError:
        # It is already none
        pass

    # Number of arguments are wrong
    if (kwargs and args) or len(args) > 1 or len(kwargs) > 1:
        raise TypeError("load_stylesheet() takes zero or one argument: "
                        "(new) string type qt_api='pyqt5' or "
                        "(old) boolean type pyside='False'.")

    # No arguments
    if not kwargs and not args:
        stylesheet = _load_stylesheet(qt_api='pyqt5')

    # Old API arguments
    elif 'pyside' in kwargs or isinstance(arg, bool):
        pyside = kwargs.get('pyside', arg)

        if pyside:
            stylesheet = _load_stylesheet(qt_api='pyside2')
            if not stylesheet:
                stylesheet = _load_stylesheet(qt_api='pyside')

        else:
            stylesheet = _load_stylesheet(qt_api='pyqt5')
            if not stylesheet:
                stylesheet = _load_stylesheet(qt_api='pyqt4')

    # New API arguments
    elif 'qt_api' in kwargs or isinstance(arg, str):
        qt_api = kwargs.get('qt_api', arg)
        stylesheet = _load_stylesheet(qt_api=qt_api)

    # Wrong API arguments name or type
    else:
        raise TypeError("load_stylesheet() takes only zero or one argument: "
                        "(new) string type qt_api='pyqt5' or "
                        "(old) boolean type pyside='False'.")

    return stylesheet


def load_stylesheet_pyside():
    """
    Load the stylesheet for use in a PySide application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyside')


def load_stylesheet_pyside2():
    """
    Load the stylesheet for use in a PySide2 application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyside2')


def load_stylesheet_pyqt():
    """
    Load the stylesheet for use in a PyQt4 application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyqt4')


def load_stylesheet_pyqt5():
    """
    Load the stylesheet for use in a PyQt5 application.

    Returns:
        str: the stylesheet string.
    """
    return _load_stylesheet(qt_api='pyqt5')


# Deprecation Warning --------------------------------------------------------


def load_stylesheet_from_environment(is_pyqtgraph=False):

    if is_pyqtgraph:
        stylesheet = _load_stylesheet(qt_api=os.environ('PYQTGRAPH_QT_LIB'))
    else:
        stylesheet = _load_stylesheet()

    return stylesheet


# Deprecated ----------------------------------------------------------------
