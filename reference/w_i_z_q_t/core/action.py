"""High level subclass of :class:`~QtGui.QAction`, which can have child actions added.

Can be set as selection based and validate selection before running the callback.
"""
# PyQt imports
from qtswitch import QtGui, QtCore

# TODO: change this to a separate metrics module once it becomes available

# NOTE: not setting an app prefix here. It'll default apps.wizqt from
# the local library, but it will be set to something else in
# ivybrowser when a single metrics library is being used (and other
# apps, eventually, hopefully) so these calls will appear as
# ivybrowser where sensible which is what we want, we think.
from .. import metrics


##############################################################################
# 	Action
##############################################################################
class Action(QtGui.QAction):
    """
    """
    completed = QtCore.Signal(bool, list)

    def __init__(self,
                 text=None,
                 icon=None,
                 tip=None,
                 shortcut=None,
                 shortcutContext=QtCore.Qt.WidgetShortcut,
                 menu=None,
                 checkable=False,
                 separator=False,
                 selectionBased=False,
                 signal="triggered()",
                 enabled=True,
                 isValidFn=None,
                 runFn=None,
                 parent=None):

        super(Action, self).__init__(parent)

        if text:
            self.setText(text)

        if icon:
            self.setIcon(icon)

        if tip:
            self.setToolTip(tip)
            self.setStatusTip(tip)

        if shortcut:
            if isinstance(shortcut, list):
                shortcuts = [QtGui.QKeySequence(key) for key in shortcut]
                self.setShortcuts(shortcuts)
            else:
                self.setShortcut(QtGui.QKeySequence(shortcut))
            self.setShortcutContext(shortcutContext)

        if menu:
            self.setMenu(menu)

        self.setCheckable(checkable)
        self.setEnabled(enabled)
        self.setSeparator(separator)

        self.__selectionBased = selectionBased
        self.__isValidFn = isValidFn
        self.__runFn = runFn

        self.connect(self, QtCore.SIGNAL(signal), self.run)

        self.__subActions = []

    ###########################################################################
    # 	isSelectionBased
    ###########################################################################
    def isSelectionBased(self):
        return self.__selectionBased

    ###########################################################################
    # 	isValid
    ###########################################################################
    def isValid(self):
        if self.__isValidFn:
            return self.__isValidFn()
        return True

    ###########################################################################
    # 	run
    ###########################################################################
    def run(self, *args):
        status = False
        info = []

        if self.isValid() and self.__runFn:

            if metrics.METRICS_ARE_ON:
                # Record metrics for the action we're going to run
                try:
                    # This'll work for a normal function or lambda
                    action_name = self.__runFn.__name__
                except AttributeError:
                    # This'll work for a functools.partial, which will
                    # have thrown an AttributeError.
                    action_name = self.__runFn.func.__name__

                if action_name == '<lambda>':
                    action_name = self.text().replace(' ', '_')
                metrics.incr('menuactions.{0}'.format(action_name))

            # Run the action function
            info = self.__runFn(*args)
            if info:
                if not isinstance(info, list):
                    info = [info]
            else:
                info = []

            status = True

        self.completed.emit(status, info)

    ###########################################################################
    # 	custom event system for using with custom wizqt toolbar
    ###########################################################################
    def event(self, event):
        ret = QtGui.QAction.event(self, event)
        return ret

    def eventFilter(self, obj, event):
        return QtCore.QObject.eventFilter(self, obj, event)

    def addSubActions(self, actions):
        self.__subActions.extend(actions)

    def addSubAction(self, action):
        self.addSubActions([action])

    def getSubActions(self):
        return self.__subActions


if __name__ == "__main__":
    app = QtGui.QApplication([])
    w = QtGui.QWidget()
    menu = QtGui.QMenu(w)
    a = Action(parent=w, text="foo")
    a.setMenu(menu)
    w.addAction(a)
    print "associated widgets =", a.associatedWidgets()
    print "menu =", a.menu()
    w.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
    # w.customContextMenuRequested.connect(lambda pos, par=w: showMenu(pos,par))
    w.show()
    app.exec_()
