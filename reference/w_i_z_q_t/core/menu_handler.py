"""Class to manage menu actions on a :class:`~wizqt.modelview.abstract_view.AbstractView` derived class.

.. code-block:: python

	class TreeMenuHandler( StandardMenuHandler ):
		def __init__( self, view, parent = None ):
			super( TreeMenuHandler, self ).__init__( view, parent = parent )
			self._staticActions.extend([
				# expand
				Action(
					selectionBased = True,
					text = "Print selection",
					shortcut = "+",
					runFn = self.__printSelected
				),
				# collapse
				Action(
					selectionBased = True,
					text = "Do something else",
					shortcut = "-",
					runFn = self.__doSomethingElse
				)
			])

		def __printSelection( self ):
			print self.parent.selectionModel().selectedIndexes()

		def __doSomethingElse( self ):
			print "Doing something else"

		def _actionOrder( self ):
			return StandardMenuHandler._actionOrder( self )[:] + [
				self.SEPARATOR,
				"Print selection",
				"Do something else",
				self.SEPARATOR
			]
"""
from qtswitch import QtGui, QT_API

import dndeprecate

from .action import Action
from .. import _APITRACKER


class ContextMenu(QtGui.QMenu):

    def __init__(self, parent=None):
        super(ContextMenu, self).__init__(parent=parent)

        self.__menuHandlers = []
        self.__separators = []
        self.__staticActions = []

    def addMenuHandler(self, newHandler):
        """
        Add a menu handler to the end of the list of handlers on this menu.

        :parameters:
            newHandler : MenuHandler object
        """
        self.__menuHandlers.append(newHandler)
        self.__cacheStaticActions()

    def insertMenuHandler(self, index, newHandler):
        """
        Insert a menu handler at index in the list of handlers on this menu.

        :parameters:
            index : int
            newHandler : MenuHandler object
        """
        self.__menuHandlers.insert(index, newHandler)
        self.__cacheStaticActions()

    def setMenuHandlers(self, newHandlers):
        """
        Set the list of menu handlers on this menu.

        :parameters:
            newHandlers : list of MenuHandler objects
        """
        self.__menuHandlers = newHandlers[:]
        self.__cacheStaticActions()

    def _populateSelection(self):
        """
        Populate the selection of each menu handler.
        """
        for handler in self.__menuHandlers:
            handler._selected = handler._getSelected()

    def __cacheStaticActions(self):
        """
        Rebuild static action cache.
        """
        # remove previous static actions from parent
        for a in self.__staticActions:
            self.parent().removeAction(a)

        # clear static action cache
        self.__staticActions = []

        # get action lists
        for handler in self.__menuHandlers:
            # get separators in the highly unlikely case that different handlers use different separator notations
            self.__separators.append(handler.SEPARATOR)

            # get static actions
            self.__staticActions.extend(handler._staticActions)

        # add static actions to parent
        self.parent().addActions(self.__staticActions)

    # @wizqt.TimeIt()
    def __createActions(self):
        """
        Add actions from menu handlers to the menu.
        """
        dynamicActions = []
        actionOrder = []

        for handler in self.__menuHandlers:
            # get dynamic actions
            dynamicActions.extend(handler._dynamicActions())

            # get action order
            for actionName in handler._actionOrder():
                if actionName == handler.SEPARATOR:
                    actionOrder.append(actionName)
                elif actionName not in actionOrder:
                    actionOrder.append(actionName)

        # check dynamic actions don't have keyboard shortcuts
        for a in dynamicActions:
            assert a.shortcuts() == [], 'Dynamic action %s cannot have keyboard shortcut' % a.text()
            a.setShortcuts([])

        actionMap = dict([(action.text(), action) for action in self.__staticActions + dynamicActions])

        # add actions
        for actionName in actionOrder:
            action = None
            if actionName in self.__separators:
                self.addAction(Action(separator=True, parent=self.parent()))
                continue
            if actionMap.has_key(actionName):
                action = actionMap.pop(actionName)
            if action is not None:
                self.addAction(action)

    def exec_(self, pos, action=None):
        """
        Exec the menu at pos.

        :parameters:
            pos : QtCore.QPoint
        """
        # clear the previous actions
        self.clear()

        # create actions
        self.__createActions()

        # show menu
        # HACK: workaround for bug in PySide versions prior to 1.2 - popup the menu rather than exec_
        # http://stackoverflow.com/questions/18297453/pyside-application-crahes-on-qmenu-exec
        # http://openclassrooms.com/forum/sujet/pyside-sigsegv-dans-un-qtgui-qmenu
        if QT_API == "pyside":
            return super(ContextMenu, self).popup(pos, action)
        else:
            return super(ContextMenu, self).exec_(pos, action)


class MenuHandler(object):
    """Class for creating and ordering actions, intended to be inherited by gui classes."""
    SEPARATOR = 'separator'

    @property
    def allActions(self):
        return self.__getActions(recursive=True)

    @property
    def actions(self):
        return self.__getActions(recursive=False)

    @property
    def view(self):
        return self.__view

    @property
    def parent(self):
        return self.__parent

    @staticmethod
    def __getActionOrMenuText(obj):
        """
        String representation for the action

        :parameters:
            obj : QAction/QMenu
        :return:
            string name of action
        :rtype:
            string
        """
        if isinstance(obj, QtGui.QMenu):
            return obj.title()
        if isinstance(obj, QtGui.QAction):
            return obj.text()

    @staticmethod
    def _uniquifyList(seq):
        """
        Return a list of unique items, preserving insertion order.

        :parameters:
            seq : iterable
        :return:
            list
        :rtype:
            list
        """
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    @_APITRACKER.track_calls(-1)
    def _track_parent_kwarg(self):
        dndeprecate.warn(
            "The parent kwarg is now deprecated. The parent is now always set "
            "to the view."
        )

    def __init__(self, view, parent="NOTAREALTHING"):
        """
        :Parameters:
            view : AbstractView
            parent : deprecated, no longer used
        """
        # local import to avoid cyclic import
        assert hasattr(view, 'contextMenu') and type(
            view.__class__.contextMenu) == property, 'Argument 1 must have property "contextMenu"'

        if parent != "NOTAREALTHING":
            self._track_parent_kwarg()

        self._selected = {}
        self._staticActions = []
        self.__dynamicActions = []
        self.__extraActions = []
        self.__view = view
        self.__connectedSignals = []
        self.__parent = view

    def __getActions(self, recursive=True):
        """
        Return a list of all actions in this menu handler.

        :Parameters:
            recursive : bool
        """

        def getActions(actions):
            allActions = []
            for action in actions:
                if action.menu():
                    allActions.extend(getActions(action.menu().actions()))
                else:
                    allActions.append(action)
            return allActions

        return getActions(self._staticActions[:] + self._dynamicActions())

    def _getSelected(self):
        """
        Re-implement in subclasses to return a dict of the selected items in the view.

        :return:
            dict of the selected items
        :rtype:
            dict
        """
        return {}

    def _dynamicActions(self):
        """
        Actions that are created on request e.g when a menu is opened.

        :return:
            list of dynamic actions
        :rtype:
            list(Action)
        """
        return []

    def _actionOrder(self):
        """
        Create a list of action names to determine the order that the actions are added in.

        :return:
            ordered list of action names
        :rtype:
            list(string)
        """
        return []

    def hasAction(self, name):
        """
        Check if this menu handler has a static action with the given text name.

        :parameters:
            name : string
        :return:

        :rtype:
            bool
        """
        for action in self._staticActions:
            if action.text() == name:
                return True
        return False

    def getAction(self, name):
        """
        Return the static action with the given text name

        :parameters:
            name : string
        :return:
            action
        :rtype:
            Action
        """
        for action in self._staticActions:
            if action.text() == name:
                return action
        return None

    def replaceAction(self, oldName, newAction):
        """
        Replace a static action oldName with newAction.

        :parameters:
            oldName : string
            newAction : Action
        """
        for i, action in enumerate(self._staticActions):
            if action.text() == oldName:
                self._staticActions.pop(i)
                self._staticActions.insert(i, newAction)
                return

    def removeAction(self, name):
        """
        Remove a static action from this menu handler.

        :parameters:
            name : string
        """
        for i, action in enumerate(self._staticActions):
            if action.text() == name:
                self._staticActions.pop(i)
                return
