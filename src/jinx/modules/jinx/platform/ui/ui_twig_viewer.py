from qtpy import QtWidgets, QtGui, QtCore
from jinx.platform.ui import ui_search_bar
from jinxicon import icon_paths
from jinxqt.widget import reload_button, filter_button, settings_button
from mongorm import DbHandler


class JinxBaseModel(QtGui.QStandardItemModel):
    def __init__(self):
        super(JinxBaseModel, self).__init__()
        self.handler = DbHandler()
        self.job = "GARB"
        self.setup_twigs()

    @property
    def twigs(self):
        return self.handler.twig(job=self.job).all()

    def data(self, index, role=None):
        if role == QtCore.Qt.DisplayRole:
            print self.itemFromIndex(index)
            return str(self.twigs[0].label)
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(icon_paths.ICON_VERSION_LRG)
        elif role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(100, 32)

    def setup_twigs(self):
        for twig in self.twigs:
            twig_item = QtGui.QStandardItem()
            twig_item.setData(twig.label, role=QtCore.Qt.DisplayRole)
            twig_item.setIcon(QtGui.QIcon(icon_paths.ICON_PACKAGE_LRG))
            self.appendRow(twig_item)
            for stalk in twig.stalks():
                stalk_item = QtGui.QStandardItem()
                stalk_item.setData(stalk.label, role=QtCore.Qt.DisplayRole)
                stalk_item.setIcon(QtGui.QIcon(icon_paths.ICON_VERSION_LRG))
                twig_item.appendRow(stalk_item)
                for leaf in stalk.leafs():
                    leaf_item = QtGui.QStandardItem()
                    leaf_item.setData(leaf.label, role=QtCore.Qt.DisplayRole)
                    leaf_item.setIcon(QtGui.QIcon(icon_paths.ICON_FILE_LRG))
                    stalk_item.appendRow(leaf_item)


class TwigTree(QtWidgets.QTreeView):
    def __init__(self):
        super(TwigTree, self).__init__()
        self.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setIconSize(QtCore.QSize(18, 18))
        self._model = JinxBaseModel()
        self.setModel(self._model)


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
        self.twig_view = TwigTree()

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
        self.project_items_label.setStyleSheet("""
            QLabel{
                padding: 0px;
                font: 13pt bold;
                color: #a6a6a6;
            }
        """)
        TREE_WIDGET = """
                    QTreeView{
                        outline: 0;
                        background: #1e1e1e;
                        color: #D9D9D9;
                        border: 0px;
                        border-radius: 1px;
                        selection-background-color: transparent;
                    }
                    QTreeView:item{
                        background-color: #3e3e3e;
                        margin: 1px 0px 1px 0px;
                        border: 1px solid #4e4e4e;
                        border-right: 0px;
                    }
                    QTreeView::item:hover{
                        background-color: #807153;
                        color: #D9D9D9
                    }
                    QTreeView::item:selected:hover{
                        color: #D9D9D9;
                    }
                    QTreeView::item:selected{
                        color: #D9D9D9;
                        background-color: #148CD2;
                    }
                    QTreeView::branch:hover{
                        background: #2e2e2e;
                    }
                    QHeaderView::section{
                        background-color: #3e3e3e;
                        color: white;
                    }
                    QScrollBar:vertical{
                        background: #1e1e1e;
                        width: 15px;
                        padding: 1px;
                        margin: 0;
                    }
                    QScrollBar:horizontal{
                        background: #1e1e1e;
                        height: 15px;
                        padding: 1px;
                        margin: 0;
                    }
                    QScrollBar::handle:vertical,
                    QScrollBar::handle:horizontal{
                        background: #3e3e3e;
                    }
                    QScrollBar::handle:vertical:hover,
                    QScrollBar::handle:horizontal:hover{
                        background: #5e5e5e;
                    }
                    QScrollBar::add-line:vertical,
                    QScrollBar::sub-line:vertical,
                    QScrollBar::add-page:vertical,
                    QScrollBar::sub-page:vertical{
                        height: 0px;
                    }
                    QScrollBar::add-line:horizontal,
                    QScrollBar::sub-line:horizontal,
                    QScrollBar::add-page:horizontal,
                    QScrollBar::sub-page:horizontal{
                        width: 0px;
                    }
                """
        self.twig_view.setStyleSheet(TREE_WIDGET)


if __name__ == '__main__':
    import qdarkstyle
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = UiTwigViewer()
    win.show()
    sys.exit(app.exec_())
