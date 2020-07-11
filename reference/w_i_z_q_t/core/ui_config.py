"""A dictionary which only allows certain keys, and cannot be edited.

This is passed into widgets' initialisers, and contains settings.
For example it may contain selection modes, or certain control's locked/unlocked states.
"""
from qtswitch import QtCore


class Config(dict):
    registered_keys = {
        'job': str,
        'locked': (list, dict),
        'dockposition': QtCore.Qt.DockWidgetArea
    }

    def __init__(self, *args, **kwargs):
        input = args[0] if args and type(args[0]) is dict else dict()
        input.update(kwargs)
        for k, v in input.iteritems():
            if k not in self.registered_keys:
                self.__invalidKey(k)
            expectedType = self.registered_keys[k]
            if not isinstance(v, expectedType):
                self.__typeError(k, type(v), expectedType)
        dict.__init__(self, input)

    ########################################################################################
    #	Banned special methods
    ########################################################################################
    def __setitem__(self, k, v):
        self.__prohibitedAction()

    def __delattr__(self, attr):
        self.__prohibitedAction()

    def __delitem__(self, item):
        self.__prohibitedAction()

    ########################################################################################
    #	Exceptions
    ########################################################################################
    def __invalidKey(self, key):
        raise KeyError('Config object should not be used with unregistered key "{0}". Valid keys: {1}'.format(
            key,
            ', '.join(sorted(self.registered_keys.keys()))))

    def __prohibitedAction(self):
        raise UserWarning('Config object is read only')

    def __typeError(self, name, invalidType, expectedType):
        raise TypeError('Passed object of {invalidType} for "{name}", expected {expectedType}.'.format(
            invalidType=invalidType,
            name=name,
            expectedType=expectedType))

    ########################################################################################
    #	Reimplemented banned methods
    ########################################################################################
    def update(self, d):
        self.__prohibitedAction()

    def clear(self):
        self.__prohibitedAction()

    def pop(self, k):
        self.__prohibitedAction()

    def popitem(self):
        self.__prohibitedAction()

    def setdefault(self, k, default=None):
        self.__prohibitedAction()
