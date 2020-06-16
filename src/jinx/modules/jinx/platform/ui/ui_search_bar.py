from qtpy import QtWidgets, QtGui, QtCore


class UiSearchBar(QtWidgets.QLineEdit):
    def __init__(self, height=42):
        super(UiSearchBar, self).__init__()
        self.setMinimumHeight(height)
        self.setIcon(QtGui.QIcon('/home/mhamid/Downloads/jinx_icon/ICON_SEARCH_LRG.png'))
        self.setStyleSheet("""
                    QLineEdit{
                        border-radius: 2px;
                    }
                """)

    def setIcon(self, qicon):
        self.icon = qicon
        if not self.icon.isNull() and isinstance(self.icon, QtGui.QIcon):
            self.setTextMargins(self.minimumHeight(), 1, 1, 1)
        else:
            self.setTextMargins(1, 1, 1, 1)

    def paintEvent(self, event):
        super(UiSearchBar, self).paintEvent(event)
        if not self.icon.isNull():
            self.painter = QtGui.QPainter(self)
            self.pixmap = self.icon.pixmap(self.height() - 16, self.height() - 16)
            x = 8
            cx = self.pixmap.width()
            self.painter.drawPixmap(x, 8, self.pixmap)
            self.painter.setPen(QtGui.QColor(90, 90, 90))
            self.painter.drawLine(cx + x*1.5, 1, cx + x*1.5, self.height() - 1)
            self.painter.end()


if __name__ == '__main__':
    import sys
    import qdarkstyle

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win = UiSearchBar()
    win.show()
    sys.exit(app.exec_())