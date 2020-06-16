from qtpy import QtWidgets, QtGui, QtCore


class UiBaseWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(UiBaseWindow, self).__init__()
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setLayout(self.mainLayout)
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.resize(1300, 1000)
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
        pass

    def create_layouts(self):
        pass

    def edit_widgets(self):
        pass

    def handle_signals(self):
        pass

    def build_layouts(self):
        pass

    def setup_styles(self):
        pass