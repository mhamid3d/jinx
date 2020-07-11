"""Contains any settings that should be loaded by a widget on startup.

Current session data can be saved in local settings files,
and static settings can also be saved in manually updated files on SITE or to a show.

Reimplement these methods in your class:

.. code-block:: python

	def saveSettings( self, settings ):
		# save own settings
		settings["layout"] = self.getLayout()
		# save child widget's settings
		settings.beginGroup('childWidget')
		self.__childWidget.saveSettings( settings )
		settings.endGroup()

	def loadSettings( self, settings ):
		# load own settings
		self.applyLayout( settings["layout"] )
		# call loadSettings on child widgets
		settings.beginGroup('childWidget')
		self.__childWidget.loadSettings( settings )
		settings.endGroup()
"""
# Standard imports
import datetime
import json
import logging
import os
import re
import uuid
# Local imports
from wizqt import common, exc

_LOGGER = logging.getLogger(__name__)


#######################################################################################################
# SettingsError
#######################################################################################################
class SettingsError(exc.WizQtError):
    pass


#######################################################################################################
#	JSONEncoder
#######################################################################################################
class JSONEncoder(json.JSONEncoder):
    """
    Extend the built-in JSONEncoder, providing serialization of datetime/date objects
    """

    def default(self, obj):  # pylint:disable=method-hidden
        """
        Serialize datetime objects

        :parameters:
            obj : datetime.date or datetime.datetime
                object to serialize
        :return:
            serialized string value
        :rtype:
            str
        """
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%dT%H:%M:%S")
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        return super(JSONEncoder, self).default(obj)


#######################################################################################################
#	jsonDecode
#######################################################################################################
def jsonDecode(d):
    """
    Replace the serialized datetime / environment variable values from a dict
    passed from json.loads with their current values

    :parameters:
        d : dict
            dictionary from a json decoded settings file
    :return:
        the same dict but with serialized datetime / environment variable values
    :rtype:
        dict
    """
    if isinstance(d, list):
        pairs = enumerate(d)
    elif isinstance(d, dict):
        pairs = d.items()
    result = []
    matchRe = re.compile("^\$([A-Za-z]\w*)$")
    for k, v in pairs:
        if isinstance(v, basestring):
            # replace environment variables
            matchObj = re.match(matchRe, v)
            if matchObj:
                v = os.getenv(matchObj.group(1))
            # decode datetime/date objects
            if v is not None:
                try:
                    v = datetime.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    try:
                        v = datetime.datetime.strptime(v, "%Y-%m-%d").date()
                    except ValueError:
                        pass
        elif isinstance(v, (dict, list)):
            v = jsonDecode(v)
        result.append((k, v))
    if isinstance(d, list):
        return [x[1] for x in result]
    elif isinstance(d, dict):
        return dict(result)


#######################################################################################################
#	Settings
#######################################################################################################
class Settings(object):
    # global path values
    DEFAULT_SETTINGS_DIR = os.path.join(common.CONFIG_GLOBAL_DIR, "widget_defaults")
    JOB_SETTINGS_DIR = os.path.join(common.CONFIG_JOB_DIR, "widget_defaults")
    USER_SETTINGS_DIR = os.path.join(common.CONFIG_USER_DIR, "widget_settings")
    # property
    widgetId = property(lambda self: self.__widgetId)

    def __init__(self, widgetId):
        # validate widget id
        try:
            widgetUuid = uuid.UUID(widgetId)
        except:
            raise SettingsError("Invalid widget id '%s'; expected a UUID string" % widgetId)
        self.__widgetId = str(widgetUuid)
        settingsFilename = "%s.%s" % (self.__widgetId, common.CONFIG_FILE_EXT)
        # load user settings from file
        self.__userSettingsFile = os.path.join(self.USER_SETTINGS_DIR, settingsFilename)
        self.__userSettings = {}
        if os.path.isfile(self.__userSettingsFile):
            try:
                with open(self.__userSettingsFile) as f:
                    self.__userSettings = json.load(f, object_hook=jsonDecode)
            except Exception:
                _LOGGER.error("Failed reading widget settings from file '%s'" % self.__userSettingsFile, exc_info=True)
            else:
                if not isinstance(self.__userSettings, dict):
                    _LOGGER.error(
                        "Invalid widget settings in file '%s'; root level is not a dictionary" % self.__userSettingsFile)
                    self.__userSettings = {}
        self.__userSettingsPtr = self.__userSettings
        # load default settings from file
        self.__defaultSettingsFile = os.path.join(self.DEFAULT_SETTINGS_DIR, settingsFilename)
        self.__jobSettingsFile = os.path.join(self.JOB_SETTINGS_DIR, settingsFilename)
        self.__defaultSettings = {}

        def loadDefaults(path):
            if os.path.isfile(path):
                try:
                    with open(path) as f:
                        self.__defaultSettings.update(json.load(f, object_hook=jsonDecode))
                except Exception:
                    _LOGGER.error("Failed reading widget settings from file '%s'" % path, exc_info=True)
                else:
                    if not isinstance(self.__defaultSettings, dict):
                        _LOGGER.error(
                            "Invalid widget settings in file '%s'; root level is not a dictionary" % self.__defaultSettingsFile)
                        self.__defaultSettings = {}

        loadDefaults(self.__defaultSettingsFile)
        loadDefaults(self.__jobSettingsFile)
        self.__defaultSettingsPtr = self.__defaultSettings
        self.__currGroup = []

    def pprint(self, current=False):
        """
        print out the settings in a nicely formatted way

        :keywords:
            current : bool
                only print the current group, instead of the full settings dict
        """
        from pprint import pformat
        if current is True:
            user = self.__userSettingsPtr
            default = self.__defaultSettingsPtr
            option = 'current'
        else:
            user = self.__userSettings
            default = self.__defaultSettings
            option = 'all'
        print """
###########################################################################
# User Settings ({option})
###########################################################################
{user}

###########################################################################
# Default Settings ({option})
###########################################################################
{default}
		""".format(option=option, user=pformat(user), default=pformat(default))

    def __contains__(self, key):
        """
        Check whether the key is in either the user or the default settings

        :parameters:
            key : ?
                any hashable type
        :return:
            True if it is in either dict else False
        :rtype:
            bool
        """
        # first look in user settings
        if key in self.__userSettingsPtr:
            return True
        if key in self.__defaultSettingsPtr:
            return True
        return False

    def __iter__(self):
        """
        Get the keys as a generator expression
        """
        keys = set()
        keys.update(self.__userSettingsPtr.keys())
        keys.update(self.__defaultSettingsPtr.keys())
        for key in keys:
            if not key.endswith(".overridable"):
                yield key

    def __getitem__(self, key):
        """
        Try and get the key from the user settings, fall back on default settings

        :parameters:
            key : ?
                any hashable type
        :return:
            the value
        :rtype:
            any
        """
        # first look in user settings
        if self.isOverridable(key):
            try:
                val = self.__userSettingsPtr[key]
                # _LOGGER.debug("Settings value %s/%s: '%s' from User file '%s'" % ("/".join(self.__currGroup), key, val, self.__userSettingsFile))
                return val
            except (KeyError, TypeError):
                pass
        # next look in default settings
        try:
            val = self.__defaultSettingsPtr[key]
            # _LOGGER.debug("Settings value %s/%s: '%s' from Default file '%s'" % ("/".join(self.__currGroup), key, val, self.__defaultSettingsFile))
            return val
        except (KeyError, TypeError):
            pass
        return None

    def __setitem__(self, key, value):
        """
        Set a key to a value in the user settings

        :parameters:
            key : ?
                any hashable type
            value : ?
                anything
        """
        # set value on user settings
        if self.isOverridable(key):
            self.__userSettingsPtr[key] = value

    def isOverridable(self, key):
        """
        check the key is overridable, based on the presence of a "<key>.overridable" key in the dict

        :parameters:
            key : ?
                any hashable type
        :return:
            whether the key is overridable
        :rtype:
            bool
        """
        # check if default settings key is overridable
        overridableKey = "%s.overridable" % key
        try:
            return bool(self.__defaultSettingsPtr[overridableKey])
        except (KeyError, TypeError):
            # default to true
            return True

    def clear(self):
        """
        clears the settings
        """
        self.__currGroup = []
        self.__userSettingsPtr = self.__userSettings = {}
        self.__defaultSettingsPtr = self.__defaultSettings = {}

    def save(self):
        """
        save the user settings to a file
        """
        dirname = os.path.dirname(self.__userSettingsFile)
        try:
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(self.__userSettingsFile, "w") as f:
                json.dump(self.__userSettings, f, indent=4, cls=JSONEncoder)
        except Exception:
            _LOGGER.error("Failed writing widget settings to file '%s'" % self.__userSettingsFile, exc_info=True)

    def get(self, key, fallback):
        """
        Return the value corresponding to key, else return fallback
        """
        if self[key] is not None:
            return self[key]
        else:
            return fallback

    def beginGroup(self, groupName):
        """
        Set the settings pointer dicts to the dict found under the current one's <groupname> key
        e.g.
        >>> print self.__userSettingsPtr
        { 'a' : { 'b' : 'b' } }

        >>> self.beginGroup('a')
        >>> print self.__userSettingsPtr
        { 'b' : 'b' }

        :parameters:
            groupName : str
                name of sub dict to begin
        """
        # update the user settings pointer
        if groupName not in self.__userSettingsPtr:
            self.__userSettingsPtr[groupName] = {}
        if not isinstance(self.__userSettingsPtr[groupName], dict):
            raise SettingsError(
                "Cannot begin group named '%s' at '%s' in user settings; name conflict with another attribute" % \
                (groupName, "/".join(self.__currGroup)))
        self.__userSettingsPtr = self.__userSettingsPtr[groupName]
        # update the default settings pointer
        if groupName not in self.__defaultSettingsPtr:
            self.__defaultSettingsPtr[groupName] = {}
        if not isinstance(self.__defaultSettingsPtr[groupName], dict):
            raise SettingsError(
                "Cannot begin group named '%s' at '%s' in default settings; name conflict with another attribute" % \
                (groupName, "/".join(self.__currGroup)))
        self.__defaultSettingsPtr = self.__defaultSettingsPtr[groupName]
        self.__currGroup.append(groupName)

    def endGroup(self):
        """
        Go back up one level to the group that contains this one
        """
        try:
            self.__currGroup.pop()
        except (ValueError, IndexError):
            return
        # update the pointers
        self.__userSettingsPtr = self.__userSettings
        self.__defaultSettingsPtr = self.__defaultSettings
        for k in self.__currGroup:
            self.__userSettingsPtr = self.__userSettingsPtr[k]
            self.__defaultSettingsPtr = self.__defaultSettingsPtr[k]
