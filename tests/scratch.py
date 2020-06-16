from qtpy import QtWidgets, QtGui, QtCore
import qdarkstyle
import mongorm


class CustomDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent):
        super(CustomDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        main_widget = QtWidgets.QWidget(parent)
        main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(main_layout)
        startFrameSpin = QtWidgets.QSpinBox()
        endFrameSpin = QtWidgets.QSpinBox()
        startFrameSpin.setRange(-9999, 9999)
        endFrameSpin.setRange(-9999, 9999)
        startFrameSpin.setValue(self.stem.framerange[0])
        endFrameSpin.setValue(self.stem.framerange[1])
        main_layout.addWidget(startFrameSpin)
        main_layout.addWidget(endFrameSpin)
        main_widget.setStyleSheet('background: red;')
        return main_widget


class JinxItemModel(QtGui.QStandardItemModel):
    def __init__(self, tree_view=None):
        super(JinxItemModel, self).__init__()
        self.tree_view = tree_view
        self.db_handler = mongorm.DbHandler()
        sequence_header = QtGui.QStandardItem('Sequence')
        sequence_header.setIcon(QtGui.QIcon("/home/mhamid/Downloads/iconmonstr-video-1-64(1).png"))
        modified_header = QtGui.QStandardItem("Modified")
        modified_header.setIcon(QtGui.QIcon("/home/mhamid/Downloads/iconmonstr-time-1-64.png"))
        created_header = QtGui.QStandardItem("Created")
        created_header.setIcon(QtGui.QIcon("/home/mhamid/Downloads/iconmonstr-time-1-64.png"))
        user_header = QtGui.QStandardItem('Created By')
        user_header.setIcon(QtGui.QIcon("/home/mhamid/Downloads/iconmonstr-user-1-64.png"))
        uuid_header = QtGui.QStandardItem("UUID")
        uuid_header.setIcon(QtGui.QIcon("/home/mhamid/Downloads/iconmonstr-tag-3-64.png"))
        framerange_header = QtGui.QStandardItem("Frame Range")
        framerange_header.setIcon(QtGui.QIcon("/home/mhamid/Downloads/iconmonstr-code-1-64.png"))
        self.setHorizontalHeaderItem(0, sequence_header)
        self.setHorizontalHeaderItem(1, modified_header)
        self.setHorizontalHeaderItem(2, created_header)
        self.setHorizontalHeaderItem(3, user_header)
        self.setHorizontalHeaderItem(4, uuid_header)
        self.setHorizontalHeaderItem(5, framerange_header)
        self.root = self.invisibleRootItem()
        for stem in self.db_handler.stem().all():
            label_item = QtGui.QStandardItem(stem.label)
            label_item.setIcon(QtGui.QIcon(stem.thumbnail))
            modified_item = QtGui.QStandardItem(str(stem.modified))
            created_item = QtGui.QStandardItem(str(stem.created))
            created_by_item = QtGui.QStandardItem(stem.created_by)
            uuid_item = QtGui.QStandardItem(str(stem.uuid))
            framerange_item = QtGui.QStandardItem()
            item_list = [
                label_item,
                modified_item,
                created_item,
                created_by_item,
                uuid_item,
                framerange_item
            ]
            for item in item_list:
                item.setEditable(False)
            self.root.appendRow(item_list)

        for row in range(0, self.rowCount()):
            self.tree_view.openPersistentEditor(self.index(row, 1))


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.mainLayout)
        self.resize(1000, 1000)
        self.tree_view = QtWidgets.QTreeView()
        self.jinx_model = JinxItemModel(tree_view=self.tree_view)
        self.tree_view.setModel(self.jinx_model)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setIconSize(QtCore.QSize(48, 48))
        self.tree_view.setItemDelegateForColumn(5, CustomDelegate(self.tree_view))
        self.mainLayout.addWidget(self.tree_view)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())