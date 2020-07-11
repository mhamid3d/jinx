from qtpy import QtWidgets, QtGui, QtCore
from jinxicon import icon_paths
from jinx.platform.ui import ui_search_bar
from jinxqt.widget import reload_button, filter_button

from mongorm import DbHandler


class JinxBaseModel(QtGui.QStandardItemModel):
    def __init__(self):
        super(JinxBaseModel, self).__init__()
        self.handler = DbHandler()
        self.job = "GARB"
        self.root_job = QtGui.QStandardItem(self.job)
        self.root_job.setIcon(QtGui.QIcon(icon_paths.ICON_JOB_LRG))
        self.root_job.setEditable(False)
        self.appendRow(self.root_job)
        self.setup_stems()

    def setup_stems(self):
        pass


class JinxProductionModel(JinxBaseModel):
    def __init__(self):
        super(JinxProductionModel, self).__init__()

    def setup_stems(self):
        for stem in self.handler.stem().all():
            if (stem.parent_uuid is None and
            stem.job == self.job and
            stem.type == "sequence"):
                label_item = QtGui.QStandardItem(stem.label)
                label_item.setIcon(QtGui.QIcon(icon_paths.ICON_SEQUENCE_LRG))
                item_list = [label_item]
                for item in item_list:
                    item.setEditable(False)
                self.root_job.appendRow(item_list)
                shots = self.handler.stem(parent_uuid=stem.uuid).all()
                for shot in shots:
                    shot_item = QtGui.QStandardItem(shot.label)
                    shot_item.setIcon(QtGui.QIcon(icon_paths.ICON_SHOT_LRG))
                    shot_list = [shot_item]
                    for item in shot_list:
                        item.setEditable(False)
                    label_item.appendRow(shot_list)


class JinxAssetModel(JinxBaseModel):
    def __init__(self):
        super(JinxAssetModel, self).__init__()

    def setup_stems(self):
        for stem in self.handler.stem().all():
            if (stem.parent_uuid is None and
            stem.job == self.job and
            stem.type == "asset"):
                label_item = QtGui.QStandardItem(stem.label)
                label_item.setIcon(QtGui.QIcon(icon_paths.ICON_ASSET_LRG))
                item_list = [label_item]
                for item in item_list:
                    item.setEditable(False)
                self.root_job.appendRow(item_list)
                shots = self.handler.stem(parent_uuid=stem.uuid).all()
                for shot in shots:
                    shot_item = QtGui.QStandardItem(shot.label)
                    shot_item.setIcon(QtGui.QIcon(icon_paths.ICON_ASSET_LRG))
                    shot_list = [shot_item]
                    for item in shot_list:
                        item.setEditable(False)
                    label_item.appendRow(shot_list)


class StemTree(QtWidgets.QTreeView):
    def __init__(self):
        super(StemTree, self).__init__()
        self.setHeaderHidden(True)
        self.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        self.setIconSize(QtCore.QSize(20, 20))
        self.setUniformRowHeights(True)
        self.setExpandsOnDoubleClick(False)

    # def mousePressEvent(self, event):
    #     super(StemTree, self).mousePressEvent(event)
    #     index = self.indexAt(event.pos())
    #     if index.isValid():
    #         item = self.model().itemFromIndex(index)
    #         children = self.recursiveChildren(item)
    #         sel_model = self.selectionModel()
    #         sel_model.select(index, QtCore.QItemSelectionModel.Select)
    #         for child in children:
    #             sel_model.select(child.index(), QtCore.QItemSelectionModel.Select)

    # def recursiveChildren(self, item):
    #     items = []
    #     for i in range(item.rowCount()):
    #         child = item.child(i)
    #         items.append(child)
    #         items += self.recursiveChildren(child)
    #
    #     return items


class UiStemViewer(QtWidgets.QWidget):
    def __init__(self):
        super(UiStemViewer, self).__init__()
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.resize(400, 800)
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
        self.populate_stems()

    def create_widgets(self):
        self.project_browser_label = QtWidgets.QLabel('Project Browser')
        self.assets_button = QtWidgets.QPushButton()
        self.production_button = QtWidgets.QPushButton()
        self.search_bar = ui_search_bar.UiSearchBar(height=30)
        self.stem_type_button_grp = QtWidgets.QButtonGroup()
        self.stem_tree = StemTree()
        self.reload_button = reload_button.ReloadButton()
        self.filter_button = filter_button.FilterButton()

    def create_layouts(self):
        self.header_layout = QtWidgets.QHBoxLayout()
        self.stem_type_layout = QtWidgets.QHBoxLayout()
        self.search_bar_layout = QtWidgets.QHBoxLayout()

    def edit_widgets(self):
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.stem_type_layout.setContentsMargins(0, 0, 0, 0)
        self.stem_type_layout.setAlignment(QtCore.Qt.AlignRight)
        self.stem_type_layout.setSpacing(0)

        self.assets_button.setMinimumSize(32, 32)
        self.assets_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.assets_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.assets_button.setIcon(QtGui.QIcon(icon_paths.ICON_ASSET_LRG))
        self.assets_button.setCheckable(True)
        self.assets_button.setToolTip("Assets")

        self.production_button.setMinimumSize(32, 32)
        self.production_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.production_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.production_button.setIcon(QtGui.QIcon(icon_paths.ICON_SEQUENCE_LRG))
        self.production_button.setCheckable(True)
        self.production_button.setChecked(True)
        self.production_button.setToolTip("Production")

        self.stem_type_button_grp.addButton(self.assets_button)
        self.stem_type_button_grp.addButton(self.production_button)

        self.search_bar.setPlaceholderText("Search for an asset, sequence, or shot...")

    def handle_signals(self):
        self.stem_type_button_grp.buttonClicked.connect(self.populate_stems)
        self.reload_button.clicked.connect(self.populate_stems)

    def populate_stems(self):
        if self.assets_button.isChecked():
            self.stem_tree.setModel(JinxAssetModel())
        elif self.production_button.isChecked():
            self.stem_tree.setModel(JinxProductionModel())
        self.stem_tree.expand(self.stem_tree.model().index(0, 0))

    def build_layouts(self):
        self.mainLayout.addLayout(self.header_layout)
        self.header_layout.addWidget(self.project_browser_label)
        self.header_layout.addLayout(self.stem_type_layout)
        self.stem_type_layout.addWidget(self.assets_button)
        self.stem_type_layout.addWidget(self.production_button)
        self.mainLayout.addWidget(self.h_line())
        self.mainLayout.addLayout(self.search_bar_layout)
        self.search_bar_layout.addWidget(self.search_bar)
        self.search_bar_layout.addWidget(self.reload_button)
        self.search_bar_layout.addWidget(self.filter_button)
        self.mainLayout.addWidget(self.stem_tree)

    def setup_styles(self):
        stem_type_button_style = """
            QPushButton{
                color: #d9d9d9;
                padding: 4px;
                background: #3e3e3e;
                border: 0px;
                border-radius: 0px;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QPushButton::checked{
                background: #0e6497;
            }
            QPushButton::!checked:hover{
                background: #5e5e5e;
            }
            QPushButton::hover{
            
            }
        """
        self.assets_button.setStyleSheet(stem_type_button_style.replace("right-radius: 4px;", "right-radius: 0px;"))
        self.production_button.setStyleSheet(stem_type_button_style.replace("left-radius: 4px;", "left-radius: 0px;"))
        self.project_browser_label.setStyleSheet("""
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
                        padding: 2px;
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
        self.stem_tree.setStyleSheet(TREE_WIDGET)


if __name__ == '__main__':
    import sys
    import qdarkstyle
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = UiStemViewer()
    win.show()
    sys.exit(app.exec_())