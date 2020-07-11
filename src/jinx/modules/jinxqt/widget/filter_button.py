from qtpy import QtWidgets, QtGui, QtCore
from jinxicon import icon_paths


class FilterButton(QtWidgets.QToolButton):
    def __init__(self):
        super(FilterButton, self).__init__()
        self.setIcon(QtGui.QIcon(icon_paths.ICON_FILTER_LRG))
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
        self._menu.setStyleSheet("""
            QCheckBox {
              background-color: red;
              color: green;
              spacing: 4px;
              outline: none;
              padding-top: 4px;
              padding-bottom: 4px;
            }
            
            QCheckBox:focus {
              border: none;
            }
            
            QCheckBox QWidget:disabled {
              background-color: #2B2B2B;
              color: #787878;
            }
            
            QCheckBox::indicator {
              margin-left: 4px;
              height: 16px;
              width: 16px;
            }
        """)
        self._byUserAction = self._menu.addAction("My Items")
        self._byApprovedAction = self._menu.addAction("Approved")
        self._byDeclinedAtion = self._menu.addAction("Declined")
        self._byApprovedAction.setCheckable(True)
        self._byDeclinedAtion.setCheckable(True)
        self.setMenu(self._menu)
