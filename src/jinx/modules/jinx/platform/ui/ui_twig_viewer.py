from qtpy import QtWidgets, QtGui, QtCore
from jinx.platform.ui import ui_search_bar
from jinxicon import icon_paths
from jinxqt.platform import reload_button, filter_button, settings_button


class UiTwigViewer(QtWidgets.QWidget):
    def __init__(self):
        super(UiTwigViewer, self).__init__()
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.mainLayout)
        self.resize(800, 800)
        self.setup_ui()

    def h_line(self):
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.HLine)
        frame.setFixedHeight(2)
        frame.setStyleSheet("""
            QFrame{
                background: #3e3e3e;
                border: 0px;
            }""")
        return frame

    def setup_ui(self):
        self.create_widgets()
        self.create_layouts()
        self.edit_widgets()
        self.handle_signals()
        self.build_layouts()
        self.setup_styles()

    def create_widgets(self):
        self.project_items_label = QtWidgets.QLabel("Project Items")
        self.search_bar = ui_search_bar.UiSearchBar(height=30)
        self.reload_button = reload_button.ReloadButton()
        self.filter_button = filter_button.FilterButton()
        self.settings_button = settings_button.SettingsButton()
        self.twig_view = QtWidgets.QTreeView()

    def create_layouts(self):
        self.top_search_layout = QtWidgets.QHBoxLayout()

    def edit_widgets(self):
        self.search_bar.setPlaceholderText("Search for a package...")
        self.mainLayout.setAlignment(QtCore.Qt.AlignTop)
        self.size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.size_policy.setHorizontalStretch(1)
        self.setSizePolicy(self.size_policy)

    def handle_signals(self):
        pass

    def build_layouts(self):
        self.mainLayout.addWidget(self.project_items_label)
        self.mainLayout.addWidget(self.h_line())
        self.mainLayout.addLayout(self.top_search_layout)
        self.top_search_layout.addWidget(self.search_bar)
        self.top_search_layout.addWidget(self.reload_button)
        self.top_search_layout.addWidget(self.filter_button)
        self.top_search_layout.addWidget(self.settings_button)
        self.mainLayout.addWidget(self.twig_view)

    def setup_styles(self):
        self.twig_view.setStyleSheet("""
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


if __name__ == '__main__':
    import qdarkstyle
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = UiTwigViewer()
    win.show()
    sys.exit(app.exec_())
