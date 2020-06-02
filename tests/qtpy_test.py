from qtpy import QtWidgets, QtGui, QtCore
import qdarkstyle


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('My Test Window!')
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.mainLayout)
        for i in range(10):
            btn = QtWidgets.QPushButton('Button #{}'.format(i))
            btn.setMinimumHeight(32)
            self.mainLayout.addWidget(btn)
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(
            [
                'First Option Here',
                'Second Option Here',
                'Third Option Here',
                'Fourth Option Here',
                'Fifth Option Here',
                'Sixth Option Here',
                'Seventh Option Here'
            ]
        )
        self.mainLayout.addWidget(self.combo)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
