from qtpy import QtWidgets, QtGui, QtCore
from jinxqt import base_main_window
from jinxicon import icon_paths


class ProjectManagerInitButton(QtWidgets.QPushButton):
    def __init__(self, label=None, icon=None):
        super(ProjectManagerInitButton, self).__init__()
        self.setIcon(QtGui.QIcon(icon))
        self.setText(label)
        self.setMinimumSize(130, 80)
        self.setIconSize(QtCore.QSize(42, 42))
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("""
                        QPushButton{
                            background: none;
                            border: 3px solid #a6a6a6;
                            border-radius: 15px;
                            font: 20px;
                            padding: 10px;
                        }
                        QPushButton::hover{
                            background: #3e3e3e;
                            border: 3px solid #148CD2
                        }
                    """)


class JinxManagerWindow(base_main_window.BaseMainWindow):
    def __init__(self):
        super(JinxManagerWindow, self).__init__()
        self.setup_init_page()

    def setup_init_page(self):
        self.init_widget = QtWidgets.QWidget()
        self.init_layout = QtWidgets.QHBoxLayout()
        self.init_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.init_layout.setSpacing(20)
        self.init_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.init_widget.setLayout(self.init_layout)
        self.mainLayout.addWidget(self.init_widget)

        self.manage_projects_button = ProjectManagerInitButton(label='Manage Project', icon=icon_paths.ICON_SLIDERS_LRG)
        self.create_project_button = ProjectManagerInitButton(label='Create Project', icon=icon_paths.ICON_SCROLL_LRG)

        self.init_layout.addWidget(self.manage_projects_button)
        self.init_layout.addWidget(self.create_project_button)


if __name__ == '__main__':
    import sys
    import qdarkstyle
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = JinxManagerWindow()
    win.show()
    sys.exit(app.exec_())