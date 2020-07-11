from copy import deepcopy
import logging
import os
import re
import subprocess

from qtswitch import QtGui, QtCore

from wizqt.core.action import Action

_LOGGER = logging.getLogger(__name__)


###############################################################################
#	OpenWithMenu
###############################################################################
class OpenWithMenu(QtGui.QMenu):
    """
    Menu that offers suggestions of programs to open a file with, and
    remembers history and filetype --> program associations.
    """

    DEFAULT_OPTIONS = []
    DEFAULT_ASSOCIATIONS = {}

    def __init__(self, recentLimit=None, path=None, history=None, defaultAssociations=None):
        """
        Constructor

        :parameters:
            recentLimit : int
                number of recently open programs to remember
            path : str
                Path to a file
            history : list
                list of recently opened programs to start with
            defaultAssociations : dict
                dict of file extension --> program associations to start with
        """
        super(OpenWithMenu, self).__init__()
        self.__re_unfurledExr = re.compile('\.#*?\.exr')
        self._path = path or ""
        self.__history = history or self.DEFAULT_OPTIONS[:]
        self.__associations = deepcopy(defaultAssociations or self.DEFAULT_ASSOCIATIONS)
        self.__lastDir = os.path.expanduser('~')
        self._recentLimit = recentLimit or 5
        self.aboutToShow.connect(self.__populate)
        self.aboutToHide.connect(self.__removeActionsDeferred)

    def __openWith(self, program):
        """
        Open self._path with <program>, and if successful, add that program
        name to the history and file extension associations.

        :parameters:
            program : str
                program launch script name, e.g. "flip"
        """
        if program in self.__history:
            self.__history.remove(program)
        # run program
        success = self._runLaunchCommand(program)
        if success is True:
            self.__history.insert(0, program)  # move to the top of history
            self.__history = self.__history[:self._recentLimit]
            # update file extension --> program associations
            ext = os.path.splitext(self._path)[-1]
            if not self.__associations.has_key(ext):
                self.__associations[ext] = []
            defaultAssociations = self.__associations[ext]
            if program not in defaultAssociations:
                defaultAssociations.insert(0, program)

    def __removeActionsDeferred(self):
        """
        Run a deferred QtGui.QMenu.clear( self ), so that after this menu closes,
        the actions are cleared.
        """
        QtCore.QTimer.singleShot(0, self.clear)

    def __addOpenAction(self, program):
        """
        Add an action to this menu, that runs <program>

        :parameters:
            program : str
                program launch script name, e.g. "flip"
        """
        action = Action(
            text=program.capitalize(),
            runFn=lambda: self.__openWith(program),
            parent=self
        )
        self.addAction(action)

    def __browse(self):
        """
        Browse filesystem for a program executable, and use that as the program to
        attempt opening self._path with.
        """
        file = QtGui.QFileDialog.getOpenFileName(self, "Browse for program...", self.__lastDir)
        if not file:
            return
        self.__lastDir = os.path.dirname(file)
        program = os.path.splitext(os.path.basename(file))[0]
        self.__openWith(program)

    def __addCustomCmd(self):
        """
        Prompt for text input, and use that text as the program to attempt opening self._path with.
        """
        cmd, accepted = QtGui.QInputDialog.getText(
            self,
            "Enter custom shell command",
            'E.g. "kwrite"'
        )
        if cmd and accepted:
            self.__openWith(cmd)

    def __populate(self):
        """
        Populate this menu with actions
        """
        for program in self._getProgramSuggestionList():
            self.__addOpenAction(program)
        # custom open actions
        self.addAction(Action(separator=True, parent=self))
        # browse action
        browseAction = QtGui.QAction('Browse...', self)
        browseAction.triggered.connect(self.__browse)
        self.addAction(browseAction)
        # custom command action
        cmdAction = QtGui.QAction('Custom command...', self)
        cmdAction.triggered.connect(self.__addCustomCmd)
        self.addAction(cmdAction)

    def _runLaunchCommand(self, program):
        """
        Run the command that opens self._path with <program>

        :parameters:
            program : str
                program launch script name, e.g. "flip"
        :return:
            Success state
        :rtype:
            bool
        """
        try:
            subprocess.Popen([program, self._path])
        except Exception as e:
            _LOGGER.error(str(e))
            return False
        return True

    def _getProgramSuggestionList(self):
        """
        Get a list of programs to offer as options for opening self._path

        :return:
            list of prgram launch script names, e.g. [ 'nedit', 'kwrite', 'gedit' ]
        :rtype:
            list
        """
        ext = os.path.splitext(self._path)[-1]
        # First use all the commands associated with the extension of self._path,
        # then if that isn't enough to fill up the history ( self._recentLimit ),
        # the difference is made up from the general history ( self.__history )
        defaultPrograms = self._getFileTypeAssociations(ext)[:self._recentLimit]
        prevPrograms = filter(
            lambda program: program not in defaultPrograms,
            self._getHistory()
        )[:self._recentLimit - len(defaultPrograms)]
        return defaultPrograms + prevPrograms

    def _getHistory(self):
        """
        Get the recently open programs

        :return:
            list of prgram launch script names, e.g. [ 'nedit', 'kwrite', 'gedit' ]
        :rtype:
            list
        """
        return deepcopy(self.__history)

    def _getFileTypeAssociations(self, ext):
        """
        Get the programs associated with a file extension <ext>

        :parameters:
            ext : str
                file extension
        :return:
            list of prgram launch script names, e.g. [ 'nedit', 'kwrite', 'gedit' ]
        :rtype:
            list
        """
        return deepcopy(self.__associations.get(ext, []))

    # def cleanPath( self, inputPath ):
    # 	"""
    # 	.

    # 	:parameters:
    # 		.
    # 	:keywords:
    # 		.
    # 	:return:
    # 		.
    # 	:rtype:
    # 		.
    # 	"""
    # 	# If the path passed in is a valid file, just return it
    # 	path = ""
    # 	if os.path.isfile( inputPath ):
    # 		return inputPath
    # 	# if it's an unfurl sequence we might be able to extract the first frame
    # 	if re.search( self.__re_unfurledExr, inputPath ):
    # 		dirname = os.path.dirname( inputPath )
    # 		filename = os.path.basename( inputPath ).partition('.')[0]
    # 		ext = os.path.splitext( inputPath )[-1]
    # 		if os.path.exists( dirname ):
    # 			for file in sorted( os.listdir( dirname ) or [] ):
    # 				if file.startswith( filename ) and file.endswith( ext ):
    # 					path = os.path.join( dirname, file )
    # 					break
    # 	return path

    def setPath(self, path):
        """
        Set the path to the thing the menu is opening

        :parameters:
            path : str
                Path to a file
        """
        assert os.path.isfile(path), "{0} is not a file".format(path)
        self._path = path
        self.__removeActionsDeferred()

    def resetAssociations(self):
        """
        Reset stored file extension --> program associations
        """
        self.__associations = {}

    def resetHistory(self):
        """
        Clear the stored history
        """
        self.__history = []


####################################################################################
#	OpenWithAction
####################################################################################
class OpenWithAction(QtGui.QAction):
    """
    Action that launches an OpenWithMenu
    """
    menu = property(lambda self: self.__menu)

    def __init__(
            self,
            text,
            parent,
            icon=None,
            **menuKwargs
    ):
        """
        Constructor

        :parameters:
            text : str
                action text
            parent : QtCore.QObject
                parent of this action
        :keywords:
            icon : QtGui.QIcon
                action icon
            menuKwargs : kwargs
                :See:
                    OpenWithMenu.__init__
        """
        super(OpenWithAction, self).__init__(icon or QtGui.QIcon(), text, parent)
        self.__menu = self._makeMenu(**menuKwargs)
        self.setMenu(self.__menu)

    def _makeMenu(self, recentLimit=None, path=None, history=None, defaultAssociations=None):
        """
        Make the menu that this action opens

        :keywords:
            recentLimit : int
                number of recently open programs to remember
            path : str
                Path to a file
            history : list
                list of recently opened programs to start with
            defaultAssociations : dict
                dict of file extension --> program associations to start with
        :return:
            menu to set as the menu for this action
        :rtype:
            OpenWithMenu
        """
        return self.OpenWithMenu(
            recentLimit=recentLimit,
            path=path,
            history=history,
            defaultAssociations=defaultAssociations
        )

    def setPath(self, path):
        """
        Set the path to the thing the menu is opening

        :parameters:
            path : str
                Path to a file
        """
        self.__menu.setPath(path)

    def resetAssociations(self):
        """
        Reset stored file extension --> program associations
        """
        self.__menu.resetAssociations()

    def resetHistory(self):
        """
        Clear the stored history
        """
        self.__menu.resetHistory()

# def cleanPath( self, path ):
# 	"""
# 	.

# 	:parameters:
# 		.
# 	:keywords:
# 		.
# 	:return:
# 		.
# 	:rtype:
# 		.
# 	"""
# 	return self.__menu.cleanPath( path )


if __name__ == '__main__':
    app = QtGui.QApplication([])
    m = OpenWithMenu()
    b = QtGui.QToolButton()
    b.setPopupMode(b.InstantPopup)
    b.setMenu(m)
    b.show()
    app.exec_()
# m.exec_( QtGui.QCursor().pos() )
