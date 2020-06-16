from qtpy import QtWidgets, QtGui, QtCore
from . import ui_search_bar


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

    def create_widgets(self):
        self.project_browser_label = QtWidgets.QLabel('Project Browser')
        self.assets_button = QtWidgets.QPushButton('Assets')
        self.production_button = QtWidgets.QPushButton('Production')
        self.search_bar = ui_search_bar.UiSearchBar(height=30)
        self.stem_type_button_grp = QtWidgets.QButtonGroup()
        self.stem_tree = QtWidgets.QTreeView()

    def create_layouts(self):
        self.header_layout = QtWidgets.QHBoxLayout()
        self.stem_type_layout = QtWidgets.QHBoxLayout()

    def edit_widgets(self):
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.stem_type_layout.setContentsMargins(0, 0, 0, 0)
        self.stem_type_layout.setSpacing(0)
        self.assets_button.setMinimumHeight(32)
        self.production_button.setMinimumHeight(32)
        self.assets_button.setCheckable(True)
        self.production_button.setCheckable(True)
        self.stem_type_button_grp.addButton(self.assets_button)
        self.stem_type_button_grp.addButton(self.production_button)
        self.production_button.setChecked(True)
        self.assets_button.setIcon(QtGui.QIcon('/home/mhamid/Downloads/jinx_icon/ICON_ASSET_LRG.png'))
        self.production_button.setIcon(QtGui.QIcon('/home/mhamid/Downloads/jinx_icon/ICON_PRODUCTION_LRG.png'))
        self.stem_tree.setHeaderHidden(True)
        self.search_bar.setPlaceholderText("Search for an asset, sequence, or shot...")

    def handle_signals(self):
        pass

    def build_layouts(self):
        self.mainLayout.addLayout(self.header_layout)
        self.header_layout.addWidget(self.project_browser_label)
        self.header_layout.addLayout(self.stem_type_layout)
        self.stem_type_layout.addWidget(self.assets_button)
        self.stem_type_layout.addWidget(self.production_button)
        self.mainLayout.addWidget(self.h_line())
        self.mainLayout.addWidget(self.search_bar)
        self.mainLayout.addWidget(self.h_line())
        self.mainLayout.addWidget(self.stem_tree)

    def setup_styles(self):
        stem_type_button_style = """
            QPushButton{
                color: #d9d9d9;
                padding: 4px;
                background: #3e3e3e;
                border: 0px;
                border-radius: 0px;
                min-width: 90px;
            }
            QPushButton::checked{
                background: #128ba6;
            }
            QPushButton::!checked:hover{
                background: #5e5e5e;
            }
            QPushButton::hover{
            
            }
        """
        self.assets_button.setStyleSheet(stem_type_button_style)
        self.production_button.setStyleSheet(stem_type_button_style)
        self.project_browser_label.setStyleSheet("""
            QLabel{
                padding: 0px;
                font: 13pt bold;
                color: #a6a6a6;
            }
        """)
        self.stem_tree.setStyleSheet("""
            QTreeView{
                border-radius: 1px;
            }
        """)


if __name__ == '__main__':
    import sys
    import qdarkstyle
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = UiStemViewer()
    win.show()
    sys.exit(app.exec_())