from qtpy import QtWidgets, QtGui, QtCore
from jinxicon import icon_paths


class SettingsButton(QtWidgets.QToolButton):
    def __init__(self):
        super(SettingsButton, self).__init__()
        self.setIcon(QtGui.QIcon(icon_paths.ICON_SLIDERS_LRG))
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
                    QToolButton::menu-button{
                        border-radius: 0px;
                        border: 0;
                        width: 12px;
                        outline: none;
                    }
                    QToolButton::menu-arrow{
                        top: 6px;
                        left: 2px;
                    }
                """)
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.setup_menu()

    def setup_menu(self):
        self._menu = QtWidgets.QMenu()
        self._byUserAction = self._menu.addAction("My Items")
        self._byApprovedAction = self._menu.addAction("Approved")
        self._byDeclinedAtion = self._menu.addAction("Declined")
        self.setMenu(self._menu)
