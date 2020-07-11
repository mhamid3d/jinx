from qtpy import QtCore

#TODO: to finish this and use it instead of what I'm doing in the twig datasource

class DataTree(object):

    LOAD_UP = "load_up"
    LOAD_ALL = "load_all"
    LOAD_DOWN = "load_down"
    STEM_TO_STEM = "stem_to_stem"
    STEM_TO_TWIG = "stem_to_twig"
    STEM_TO_DEFAULT = STEM_TO_STEM

    def __init__(self, dataObject):
        super(DataTree, self).__init__()
        self._object = dataObject
        self._dataNodeMap = {}
        self._dataNodeList = []
        self._loadDirection = None
        self._mode = None

    treeChanged = QtCore.Signal

    def populate(self, loadDirection, mode):
        self._loadDirection = loadDirection
        self._mode = mode
        dataMap = {}
        if loadDirection == self.LOAD_UP:
            pass

        self.treeChanged.emit()

    def changeRootItem(self, rootItem):
        self._rootItem = rootItem
        self.populate(self._loadDirection, self._mode)

    def topLevelItems(self):
        if not self._dataNodeMap:
            return None
        return self._dataNodeMap.keys()