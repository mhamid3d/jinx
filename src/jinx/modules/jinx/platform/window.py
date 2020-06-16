from qtpy import QtWidgets, QtGui, QtCore
from jinx.platform.ui import (
    ui_base_window,
    ui_stem_viewer,
    ui_search_bar,
    ui_control_box_viewer
    )
import qdarkstyle
import sys


class JinxPlatformMain(ui_base_window.UiBaseWindow):
    def __init__(self):
        super(JinxPlatformMain, self).__init__()

    def create_widgets(self):
        self.stem_control_splitter = QtWidgets.QSplitter()
        self.stem_viewer_widget = ui_stem_viewer.UiStemViewer()
        self.search_bar = ui_search_bar.UiSearchBar()
        self.reload_button = QtWidgets.QPushButton()
        self.control_box_widget = QtWidgets.QWidget()
        self.control_box_viewer = ui_control_box_viewer.UiControlBoxViewer()
        self.search_label = QtWidgets.QLabel("Search")
        self.project_items_label = QtWidgets.QLabel("Project Items")

    def create_layouts(self):
        self.top_search_layout = QtWidgets.QHBoxLayout()
        self.control_box_layout = QtWidgets.QVBoxLayout()

    def edit_widgets(self):
        self.stem_control_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.search_bar.setPlaceholderText("Search for a package...")
        self.reload_button.setIcon(QtGui.QIcon("/home/mhamid/Downloads/jinx_icon/ICON_RELOAD_LRG.png"))
        self.reload_button.setIconSize(QtCore.QSize(24, 24))
        self.reload_button.setFixedSize(self.search_bar.minimumHeight(), self.search_bar.minimumHeight())
        self.control_box_layout.setAlignment(QtCore.Qt.AlignTop)

    def build_layouts(self):
        self.mainLayout.addWidget(self.stem_control_splitter)
        self.stem_control_splitter.addWidget(self.stem_viewer_widget)
        self.control_box_widget.setLayout(self.control_box_layout)
        self.stem_control_splitter.addWidget(self.control_box_widget)
        self.control_box_layout.addWidget(self.search_label)
        self.control_box_layout.addLayout(self.top_search_layout)
        self.top_search_layout.addWidget(self.search_bar)
        self.top_search_layout.addWidget(self.reload_button)
        self.control_box_layout.addWidget(self.h_line())
        self.control_box_layout.addWidget(self.project_items_label)
        self.control_box_layout.addWidget(self.control_box_viewer)

    def setup_styles(self):
        self.reload_button.setStyleSheet("""
            QPushButton{
                min-width: none;
                padding: 0px;
                background: #3e3e3e;
                border-radius: 2px;
            }
            QPushButton::hover{
                background: #4e4e4e;
            }
            QPushButton::pressed{
                background: #1e1e1e;
            }
        """)
        self.control_box_viewer.setStyleSheet("""
            QTreeView{
                border-radius: 2px;
            }
        """)
        self.project_items_label.setStyleSheet("""
            QLabel{
                padding: 0px;
                font: 13pt bold;
                color: #a6a6a6;
            }
        """)
        self.search_label.setStyleSheet("""
            QLabel{
                padding: 0px;
                font: 13pt bold;
                color: #a6a6a6;
            }
        """)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = JinxPlatformMain()
    win.show()
    sys.exit(app.exec_())