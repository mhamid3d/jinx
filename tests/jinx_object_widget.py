from qtpy import QtWidgets, QtGui, QtCore
from mongorm import DbHandler
import random
import sys
import os


SEQ_LIST = [
    'aa_seq',
    'bb_seq',
    'cc_seq',
    'dd_seq',
    'ee_seq',
    'ff_seq',
    'gg_seq',
    'hh_seq',
    'ii_seq',
    'jj_seq',
    'kk_seq',
    'll_seq',
    'mm_seq',
    'nn_seq',
    'oo_seq',
    'pp_seq',
    'qq_seq',
    'rr_seq',
    'ss_seq',
    'tt_seq',
    'uu_seq',
    'vv_seq',
    'ww_seq',
    'xx_seq',
    'yy_seq',
    'zz_seq',
    'ab_seq',
    'cd_seq',
    'ef_seq',
    'gh_seq'
]


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.mainLayout = QtWidgets.QGridLayout(self)
        self.setLayout(self.mainLayout)
        self.resize(1000, 1000)
        self.setStyleSheet("""
            QWidget{
                background: #2e2e2e;
            }
        """)
        column = 0
        row = 0
        self.db_handler = DbHandler()
        for i, obj in enumerate(self.db_handler.stem().all()):
            widget = JinxObjectWidget(width=200, object=obj)
            self.mainLayout.addWidget(widget, column, row, alignment=QtCore.Qt.AlignTop)
            row += 1
            if (i + 1) % 6 == 0:
                column += 1
                row = 0


class JinxObjectWidget(QtWidgets.QGroupBox):
    def __init__(self, width=200, object=None):
        super(JinxObjectWidget, self).__init__()
        self.object = object
        self.name = self.object.label
        self.base_size = width
        self.setFixedSize(self.base_size, self.base_size)
        self.setContentsMargins(0, 0, 0, 0)
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QGroupBox{
                background: #2e2e2e;
                border: 2px solid #1e1e1e;
            }
            QGroupBox::indicator:hover{
                border: 2px solid #128ba6;
            }
        """)
        self.setup_top_bar()
        self.setup_frame()

    def setup_top_bar(self):
        self.top_bar_widget = QtWidgets.QWidget()
        self.top_bar_layout = QtWidgets.QHBoxLayout()
        self.top_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.top_bar_widget.setContentsMargins(0, 0, 0, 0)
        self.top_bar_widget.setLayout(self.top_bar_layout)
        self.top_bar_widget.setStyleSheet("""
            QWidget{
                background: #4e4e4e;
                border: 0px;
            }
        """)
        self.top_bar_widget.setFixedHeight(self.base_size / 8)

        self.status_button = QtWidgets.QPushButton()
        self.information_button = QtWidgets.QPushButton()

        path = {
            0: '/home/mhamid/Downloads/iconmonstr-check-mark-6-64.png',
            1: '/home/mhamid/Downloads/iconmonstr-time-16-64.png',
            2: '/home/mhamid/Downloads/iconmonstr-forbidden-3-64.png'
        }
        self.status_button.setIcon(QtGui.QIcon(path[random.randint(0, 2)]))
        self.information_button.setIcon(QtGui.QIcon('/home/mhamid/Downloads/iconmonstr-info-5-64.png'))
        icon_size = self.top_bar_widget.height() * 0.7
        self.status_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.information_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.status_button.setStyleSheet("""
            QPushButton{
                border: 0px;
            }
        """)
        self.information_button.setStyleSheet("""
                    QPushButton{
                        border: 0px;
                    }
                    QPushButton::pressed{
                        background: #2e2e2e;
                    }
                """)

        self.information_button.setFixedSize(self.top_bar_widget.height(), self.top_bar_widget.height())
        self.status_button.setFixedSize(self.top_bar_widget.height(), self.top_bar_widget.height())

        self.top_bar_layout.addWidget(self.status_button, alignment=QtCore.Qt.AlignLeft)
        self.top_bar_layout.addWidget(self.information_button, alignment=QtCore.Qt.AlignRight)

        self.mainLayout.addWidget(self.top_bar_widget, alignment=QtCore.Qt.AlignTop)

    def setup_frame(self):
        self.frame = QtWidgets.QPushButton()
        self.frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.frame.setMouseTracking(True)
        self.frame.installEventFilter(self.frame)
        self.frame.eventFilter = self.frame_eventFilter
        self.frame.setStyleSheet('background: none; border: 0px;')
        thumbnail_path = '/home/mhamid/Downloads/thumbnails'
        thumbnails = ["{}/{}".format(thumbnail_path, x) for x in os.listdir(thumbnail_path)]
        self.frame.setIcon(QtGui.QIcon(self.object.thumbnail))
        self.frame.setIconSize(QtCore.QSize(self.base_size, self.base_size))
        self.frame_layout = QtWidgets.QVBoxLayout(self.frame)
        self.frame.setLayout(self.frame_layout)
        self.frame_layout.setAlignment(QtCore.Qt.AlignTop)
        self.label = QtWidgets.QLabel(self.name)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setGeometry(0, 0, self.base_size, self.base_size*0.2)
        self.frame_layout.addWidget(self.label)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        self.label.setStyleSheet("""
            QLabel{
                color: white;
                font: %spx bold;
                background: #3e3e3e;
                padding: 5px;
            }
        """ % (self.base_size/ 8))
        op = QtWidgets.QGraphicsOpacityEffect(self.label)
        op.setOpacity(0.75)
        self.label.setGraphicsEffect(op)
        self.label.setAutoFillBackground(True)
        self.frame.setCursor(QtCore.Qt.PointingHandCursor)

        self.mainLayout.addWidget(self.frame)

    def frame_eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.HoverEnter:
            self.anim = QtCore.QPropertyAnimation(self.label, b"geometry")
            self.anim.setDuration(100)
            self.anim.setStartValue(QtCore.QRect(0, 0, self.base_size, self.base_size*0.2))
            self.anim.setEndValue(QtCore.QRect(0, 0, self.base_size, self.base_size - self.top_bar_widget.height()))
            self.anim.start()
        elif event.type() == QtCore.QEvent.HoverLeave:
            self.anim = QtCore.QPropertyAnimation(self.label, b"geometry")
            self.anim.setDuration(100)
            self.anim.setStartValue(QtCore.QRect(0, 0, self.base_size, self.base_size - self.top_bar_widget.height()))
            self.anim.setEndValue(QtCore.QRect(0, 0, self.base_size, self.base_size*0.2))
            self.anim.start()

        return super(QtWidgets.QPushButton, self.frame).eventFilter(object, event)



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
