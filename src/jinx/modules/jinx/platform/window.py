from qtpy import QtWidgets, QtGui, QtCore
from jinxicon import icon_paths
from jinx.platform.ui import (
    ui_stem_viewer,
    ui_twig_viewer,
    )
from jinxqt.widget import base_main_window
import qdarkstyle
import sys


class JinxPlatformMain(base_main_window.BaseMainWindow):
    def __init__(self):
        super(JinxPlatformMain, self).__init__()

    def create_widgets(self):
        self.stem_control_splitter = QtWidgets.QSplitter()
        self.stem_viewer_widget = ui_stem_viewer.UiStemViewer()
        self.twig_viewer_widget = ui_twig_viewer.UiTwigViewer()

    def create_layouts(self):
        pass

    def edit_widgets(self):
        self.stem_control_splitter.setOrientation(QtCore.Qt.Horizontal)

    def build_layouts(self):
        self.mainLayout.addWidget(self.stem_control_splitter)
        self.stem_control_splitter.addWidget(self.stem_viewer_widget)
        self.stem_control_splitter.addWidget(self.twig_viewer_widget)

    def setup_styles(self):
        pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = JinxPlatformMain()
    win.show()
    sys.exit(app.exec_())
