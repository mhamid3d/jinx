from qtpy import QtWidgets, QtGui, QtCore
from jinxicon import icon_paths


class ReloadButton(QtWidgets.QToolButton):
    def __init__(self):
        super(ReloadButton, self).__init__()
        self.setIcon(QtGui.QIcon(icon_paths.ICON_RELOAD_LRG))
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.setMinimumSize(30, 30)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("""
                    QToolButton{
                        padding: 0px;
                        background: none;
                        border: none;
                        border-radius: 2px;
                    }
                    QToolButton::hover{
                        border: 1px solid #148CD2;
                        background: #3e3e3e;
                    }
                    QToolButton::pressed{
                        background: #1e1e1e;
                    }
                """)
