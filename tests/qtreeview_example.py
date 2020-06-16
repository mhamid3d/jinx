import sys
from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy.QtWidgets import *


class MyModel(QStandardItemModel):
    def __init__(self):
        super(MyModel, self).__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(['Col 1', 'Col2 2', 'Col 3'])


class ComboDelegate(QItemDelegate):
    def __init__(self, parent):
        QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        main_widget = QWidget(parent)
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        startFrameSpin = QSpinBox()
        endFrameSpin = QSpinBox()
        startFrameSpin.setRange(-9999, 9999)
        endFrameSpin.setRange(-9999, 9999)
        # startFrameSpin.setValue(self.stem.framerange[0])
        # endFrameSpin.setValue(self.stem.framerange[1])
        main_layout.addWidget(startFrameSpin)
        main_layout.addWidget(endFrameSpin)
        return main_widget


if __name__ == '__main__':
    myapp = QApplication(sys.argv)
    model = MyModel()
    view = QTreeView()
    view.setUniformRowHeights(True)
    view.setModel(model)
    view.setItemDelegateForColumn(1, ComboDelegate(view))
    view.show()

    for n in [['q','w','e'],['r','t','y']]:
        item_a = QStandardItem(unicode(n[0]))
        item_b = QStandardItem(unicode(n[1]))
        item_c = QStandardItem(unicode(n[2]))
        model.appendRow([item_a, item_b, item_c])

    for row in range(0, model.rowCount()):
        view.openPersistentEditor(model.index(row, 1))

    myapp.exec_()