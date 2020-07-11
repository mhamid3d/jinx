try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache
import logging
import pwd

from qtswitch import QtCore, QtGui

import datautil
from pipefuncs.submission_history import SubmissionHistory
from pipeicon import common as icons
from pipeicon import util as iconutil
from pipetheme import utils as theme
import spider
from spider.base import ONDISK_NONE, NoResultFound, DataAccessLevel
from spider.orm import DataFilter
from venom.fileformat import getFileFormat
import wizqt
from wizqt.modelview.model_item import ModelItem

import ivyqt
from .dynamic_header_datasource import DynamicHeaderDataSource
from ..filtersource.leaf_filtersource import LeafFilterSource
from ... import shotgun_cache as shotgun_cache
from ...prune_analyser_evaluation import Evaluation

# Globals and Constants

_LOGGER = logging.getLogger(__name__)

# use this for greyed out items that don't match the filter
ROLE_FILTER_OMITTED = wizqt.registerDataRole()

DELETEDFGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_DELETED)
DELETEDBGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_DELETED, foreground=False)
ARCHIVEDFGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_DELETED)
ARCHIVEDBGCOLOUR = theme.getIvyStateColour(wizqt.COLORKEY_DELETED, foreground=False)

PENDING_STALK_STATES = ["new", "pending"]
ERROR_STALK_STATES = ["errored"]
INTERFACES_WITH_DISK_PRESENCE = ["Stalk", "Leaf"]
INTERFACES_WITH_REVIEW_STATUS_COLOURS = ["Stalk", "Twig"]

# debugging helper because we have all these beeping roles
#
ROLE_TO_NAME = {0: 'QtCore.Qt.DisplayRole',
                1: 'QtCore.Qt.DecorationRole',
                3: 'QtCore.Qt.ToolTipRole',
                6: 'QtCore.Qt.FontRole',
                8: 'QtCore.Qt.BackgroundRole',
                9: 'QtCore.Qt.ForegroundRole',
                38: 'wizqt.ROLE_SORT',
                48: 'ivyqt.ROLE_TREE_NODE',
                56: 'self.ROLE_HIDDEN_DATA',
                }

# Site name and field caches to avoid redoing this in each object or call
#
SITES_TO_ONDISKFIELDS = {}
SITE_ONDISKFIELDS = []
for sitedata in ivyqt.DN_SITE_DATA.all_sites:
    short_name = sitedata.short_name
    field_name = sitedata.ondisk_field_name
    SITES_TO_ONDISKFIELDS[short_name] = field_name
    SITE_ONDISKFIELDS.append(field_name)

LOCAL_SITE_ONDISK_FIELD = ivyqt.DN_SITE_DATA.local_site.ondisk_field_name

# Byte units conversion - probably should be in another file if used
# in more than one place in ivyqt, was formally pipefunces.Measure,
# which did it in a way that was far too complicated for what this
# code needs.
#
UNITS = [("k", 1024),
         ("M", 1024 ** 2),
         ("G", 1024 ** 3),
         ("T", 1024 ** 4),
         ("P", 1024 ** 5),
         ("E", 1024 ** 6),
         ("Z", 1024 ** 7),
         ("Y", 1024 ** 8)
         ]

UNIT_PRECISION = {
    "Y": 3,
    "Z": 3,
    "E": 3,
    "P": 3,
    "T": 2,
    "G": 2,
    "M": 1,
    "k": 0
}


#  bytes to human readable sensible units - based on but modified from
#  pipefuncs.measure which was overkill for what this needed.
#
def convert_to_human_readable(numbytes):
    # small numbers of bytes stay as bytes
    if numbytes < 1024:
        return "{0} B".format(numbytes)

    # Choose an appropriate prefix that best fits the size of the number
    for prefix, mag in UNITS:
        if numbytes / float(mag) < 1024:
            value = numbytes / float(mag)
            precision = UNIT_PRECISION[prefix]
            return "{1:.{0}f} {2}iB".format(precision, value, prefix)

    # If it reached here, return it using the biggest prefix we have.
    prefix = UNITS[-1][0]
    mag = UNITS[-1][1]
    value = numbytes / float(mag)
    precision = UNIT_PRECISION[prefix]
    return "{1:.{0}f} {2}iB".format(precision, value, prefix)


##############################################################################################################
# 	TwigDataSource
##############################################################################################################
class TwigDataSource(DynamicHeaderDataSource):
    # keeping this list to retain column order
    COLUMN_HEADER_ORDER = [
                              "name",
                              "thumbnail",
                              'path',
                              "version",
                              "client_version",
                              "framerange",
                              "twigtype",
                              "submissionstatus",
                              "reviewstatus",
                              "created_by",
                              "created",
                              "owner",
                              "modified_by",
                              "islocal",
                              "dnuuid",
                              "filesize"
                          ] + SITE_ONDISKFIELDS + [
                              "weed_entry_dnuuid",
                              "weed_assignee",
                              'suggest_for_delete'
                          ]

    # constants
    PROPAGATION_RELATIONSHIPS = {
        "Twig": "Stalk"
    }
    ICON_WIDTH = 16

    # class variables
    __modes = (OMIT, HIGHLIGHT) = ('omit', 'highlight')

    ##############################################################################################################
    # 	_generateCompPixmap
    ##############################################################################################################
    @staticmethod
    def _generateCompPixmap(iconPath):
        # makes a wider pixmap so that there is room to draw the child count
        pixmap = QtGui.QPixmap(iconPath)
        compPixmap = QtGui.QPixmap(pixmap.width() + 32, pixmap.height())  # add pixel width to draw stalk count
        compPixmap.fill(QtGui.QColor(0, 0, 0, 0))
        # twig pixmap
        painter = QtGui.QPainter(compPixmap)
        painter.drawPixmap(QtCore.QPoint(0, 0), pixmap)
        painter.end()
        return compPixmap

    ##############################################################################################################
    # 	_getLeafFileLocation
    ##############################################################################################################
    @staticmethod
    def _getLeafFileLocation(treeNode, isLeaf):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        if isLeaf:
            return treeNode.dataObject().get('location')

        childNodes = [treeNode]
        for node in childNodes:
            dataObj = node.dataObject()
            if dataObj is not None and dataObj.hasAttr('leafname'):
                # if it's not a leaf (it's a stalk), only look for main_proxy0
                if dataObj.get('leafname') == 'main_proxy0':
                    return dataObj.get('location')
            elif node.hasChildren():
                childNodes.extend(node.getChildNodes())

        return None

    ##############################################################################################################
    # 	__init__
    ##############################################################################################################
    def __init__(self, handler, headerOrder=None, parent=None):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        # settings
        self.__TAG_COLUMNS = {}
        self._tag_column_numbers = {}

        self.__disabledTextColour = QtGui.QApplication.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)

        self.__disabledRowAttributes = [
            (ROLE_FILTER_OMITTED, True),
            (QtCore.Qt.ForegroundRole, self.__disabledTextColour),
            (QtCore.Qt.ToolTipRole, 'Omitted by data filter')
        ]

        self.__twigCompPixmap = self._generateCompPixmap(icons.ICON_TWIG_SML)
        self.__stalkCompPixmap = self._generateCompPixmap(icons.ICON_STALK_SML)
        self.__pendingCompPixmap = self._generateCompPixmap(icons.ICON_INCOMPLETE_STALK_SML)
        self.__erroredCompPixmap = self._generateCompPixmap(icons.ICON_ERRORED_STALK_SML)
        self.__podCompPixmap = self._generateCompPixmap(icons.ICON_POD_SML)

        self.__childCountPenColour = QtGui.QPalette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text)

        self.__tree = None
        self.__includeStalks = True
        self.__includeLeaves = True
        self.__includePods = False

        self.__leafFilter = DataFilter.create()
        self.__leaf_handler = handler.getDataInterface('Leaf')
        self.__leafFilter.sort(self.__leaf_handler['leafname'].asc())

        self.__filterMode = self.OMIT
        self.__reviewStatusIconCache = {}
        # This next cache isn't set to {} because it's initialised on first call
        self.__reviewStatus2sgcodeCache = None
        self.__reviewStatus2colourCache = {}
        self.__submissionStatuses = {}
        self.__weedStateIconCache = {}
        self.__weedEvaluations = {}
        self.__fieldiswidgetCache = {}
        self.__ondiskcombosCache = {}
        self.__stalknumberpixmapCache = {}

        # init superclass
        self.__stalk_handler = handler.getDataInterface('Stalk')
        self.__twig_handler = handler.getDataInterface("Twig")
        super(TwigDataSource, self).__init__(
            handler,
            self.__twig_handler,
            additionalInterfaces=[self.__stalk_handler, self.__leaf_handler],
            nonQueryInterfaces=[handler.getDataInterface('TwigType'), handler.getDataInterface('YSubmission')],
            headerOrder=headerOrder,
            enableCaching=False,
            parent=parent
        )

        self.__versionSortFilter = DataFilter.create()
        self.__versionSortFilter.sort(self.__stalk_handler["version"].desc())
        self.__versionSortFilter.sort(self.__stalk_handler["sversion"].desc())

        # set to load in pages
        #
        # TODO: this is the reason the sorting only works on a single
        # page at a time and because its not applied on the search
        # properly?
        self.setLoadMethod(self.LOAD_METHOD_PAGINATED)
        self.setLazyLoadChildren(True)
        self._itemsCheckable = {}

        # Flag to indicate the next call to purge will be the first one
        self._first_purge = True

        # number of columns
        self.column_range_list = range(len(self.fullColumnOrder))

        # Special cases setup
        self._specialCases = None
        self.initSpecialCases()

        # Work out which colns will hold image types.
        #
        # Added displayNames and descriptors too. These seem
        # counterintuitive but looking them up each time around the
        # loop in populateItemFromTreeNode is a waste of work because
        # item.data is slow
        self._imagecols = []
        self._descriptors = []
        # The getData variable is to shorten function lookup. not sure
        # it helps here. haven't confirmed it. but it was in the
        # original code.
        getData = self._headerItem.data
        for column in self.column_range_list:
            if getData(column, wizqt.ROLE_TYPE) == wizqt.TYPE_IMAGE:
                self._imagecols.append(column)
            descriptor = getData(column, role=self.ROLE_COLUMN_DESCRIPTOR)
            self._descriptors.append(descriptor)

        # Cache the other interface names because that's all this
        # actually needs later in populateItemfromTreeNode
        self._nonQueryInterfaceNames = ['TwigType', 'YSubmission']

    def initSpecialCases(self):
        # special case handler mappings - can't put it in the
        # constructor because self, and can't make them class methods
        # because some use self.othermethods. Each takes these args:
        # dataObject, treeNode
        self._specialCases = {'Twig': {'filesize': self.twig_filesize,
                                       'created': self.twig_created,
                                       'twigtype': self.twig_twigtype,
                                       'comment': self.twig_comment,
                                       'status': self.twig_status,
                                       'twigname': self.twig_twigname,
                                       'thumbnail': self.twig_thumbnail,
                                       },
                              'Stalk': {'twigtype': self.stalk_twigtype,
                                        'status': self.stalk_status,
                                        'evaluate_for_delete_state': self.stalk_evaluate_for_delete_state,
                                        'reviewstatus': self.stalk_reviewstatus,
                                        'thumbnail': self.stalk_thumbnail,
                                        'stalkdir_size': self.stalk_stalkdir_size,
                                        'stalkname': self.stalk_stalkname,
                                        'version': self.stalk_version,
                                        'owner': self.stalk_owner,
                                        'suggest_for_delete_to': self.stalk_suggest_for_delete_to,
                                        'ondisk_lon': self.stalk_ondisk_lon,
                                        },
                              'Leaf': {'twigtype': self.leaf_twigtype,
                                       'leafname': self.leaf_leafname,
                                       'thumbnail': self.leaf_thumbnail,
                                       'filesize': self.leaf_filesize,
                                       'ondisk_lon': self.leaf_ondisk_lon,
                                       },
                              }

    ##############################################################################################################
    # 	__purgeStalkQueryCache
    ##############################################################################################################
    def __purgeStalkQueryCache(self):
        """
        Clears the cached twigs, stalks and leaves on jobpicker change.
        """
        # Don't do anything on the first call, because the program has
        # just loaded things up for the first time.
        if (self._first_purge):
            self._first_purge = False
            return

        _LOGGER.debug("Clearing leaf, stalk and twig data caches")
        self.__leaf_handler.clearDataCache()
        self.__stalk_handler.clearDataCache()
        self.__twig_handler.clearDataCache()

    ##############################################################################################################
    # 	__getWeedAnalysisState
    ##############################################################################################################
    # @wizqt.TimeIt()
    def __getWeedAnalysisState(self, stalk):
        emptyState = (state, icon, toolTip) = (None, None, None)
        if self.__weedEvaluations is None:
            return emptyState

        dnuuid = stalk.getUuid()
        if dnuuid not in self.__weedEvaluations:
            return emptyState

        evaluation = self.__weedEvaluations[dnuuid]
        try:
            state = evaluation.state
        except KeyError:
            # PTSUP-65994 - hacky way to determine whether a
            # Stalk has been analysed or not.
            return emptyState
        else:
            icon = self.__getWeedStateIcon(state)
            reasons = evaluation.reasons()
            if reasons:
                toolTip = "Deletion Reasons:"
                for reasonObj in reasons:
                    toolTip += "\n{0}".format(reasonObj.reason)
            return state, icon, toolTip

    def __getWeedStateIcon(self, state):
        if state in self.__weedStateIconCache:
            return self.__weedStateIconCache[state]

        iconPath = iconutil.getWeedAnalysisIcon(state, large=False)
        if not iconPath:
            _LOGGER.error('Invalid weed deletion state: {0}'.format(repr(state)))
            return

        pixmap = QtGui.QPixmap(iconPath)
        self.__weedStateIconCache[state] = pixmap

        return pixmap

    ##############################################################################################################
    # 	__getStalkNodeSize
    ##############################################################################################################
    def __getStalkNodeSize(self, stalkNode):
        totalLeafSize = stalkNode.dataObject().get('stalkdir_size')
        if stalkNode.hasChildren():
            for childNode in stalkNode.getChildNodes():
                if childNode.dataObject().dataInterface() == self.__stalk_handler and childNode.hasChildren():
                    # if its a pod stalk, recurse down
                    totalLeafSize += self.__getStalkNodeSize(childNode)
        return totalLeafSize

    ##############################################################################################################
    # 	Special case methods
    ##############################################################################################################
    def twig_filesize(self, twig, treeNode=None):
        # sum of all stalks
        totalStalkSize = 0
        if treeNode.hasChildren():
            totalStalkSize = sum([self.__getStalkNodeSize(kid) for kid in treeNode.getChildNodes()])
        return [(QtCore.Qt.DisplayRole, convert_to_human_readable(totalStalkSize)), (wizqt.ROLE_SORT, totalStalkSize)]

    def twig_created(self, twig, treeNode=None):
        sourceObject = twig
        if treeNode.hasChildren():
            sourceObject = treeNode.getChildNodes()[0].dataObject()
        return [(QtCore.Qt.DisplayRole, sourceObject.get('created'))]

    def twig_twigtype(self, twig, treeNode=None):
        twigtype = twig.twigtype().get('twigtype')
        return [(QtCore.Qt.DisplayRole, twigtype), (QtCore.Qt.ToolTipRole, twigtype)]

    def twig_comment(self, twig, treeNode=None):
        # Note: this is much faster across 50 calls than using
        # twig.latest().get('comment') to get the latest stalk's
        # comment. mv stands for 'max version'
        mv = -1
        latest = None
        stalknodes = treeNode.getChildNodes()

        for snode in stalknodes:
            stalk = snode.dataObject()
            v = stalk.get('version')
            if mv < v:
                mv = v
                latest = stalk

        if (latest):
            latestStalkComment = latest.get('comment')
        else:
            latestStalkComment = ""

        twigComment = "Object Comment: {0}".format(twig.get('comment'))
        return [(QtCore.Qt.DisplayRole, latestStalkComment), (QtCore.Qt.ToolTipRole, twigComment)]

    def twig_status(self, twig, treeNode=None):
        if treeNode.hasChildren():
            latestStalkNode = treeNode.getChildNodes()[0]
            return self.stalk_status(latestStalkNode.dataObject(), treeNode=latestStalkNode)
        return []

    def twig_twigname(self, twig, treeNode=None):
        twigname = twig.get('twigname')

        if treeNode.hasChildren():
            kids = treeNode.getChildNodes()
            number = len(kids)
            stalkState = kids[0].dataObject().get("state")
        else:
            number = 0
            stalkState = ""

        basePixmap = self.__twigCompPixmap
        if stalkState in PENDING_STALK_STATES:
            basePixmap = self.__pendingCompPixmap
        elif stalkState in ERROR_STALK_STATES:
            basePixmap = self.__erroredCompPixmap

        # TODO: surely we can cache these pixmaps (state+number
        # combos), most are small numbers + states.
        pixmap = QtGui.QPixmap(basePixmap)
        painter = QtGui.QPainter(pixmap)
        painter.setPen(self.__childCountPenColour)
        painter.drawText(self.ICON_WIDTH, self.ICON_WIDTH, str(number))
        painter.end()

        return [(QtCore.Qt.DisplayRole, twigname), (QtCore.Qt.ToolTipRole, twigname),
                (QtCore.Qt.DecorationRole, pixmap)]

    def twig_thumbnail(self, twig, treeNode=None):
        # there is a twig thumbnail field, but it is barely used, so
        # fall back on the latest stalk.
        twigThumbnail = twig.get('thumbnail', '')
        if not twigThumbnail:
            if treeNode.hasChildren():
                latestStalkNode = treeNode.getChildNodes()[0]
                return self.stalk_thumbnail(latestStalkNode.dataObject(), treeNode=latestStalkNode)
        return [(QtCore.Qt.DisplayRole, twigThumbnail)]

    def stalk_twigtype(self, stalk, treeNode=None):
        twigtype = stalk.twig().twigtype().get('twigtype')
        return [(QtCore.Qt.DisplayRole, twigtype), (QtCore.Qt.ToolTipRole, twigtype)]

    def stalk_status(self, stalk, treeNode=None):
        toolTipText = []
        iconList = []
        for category in self.__submissionStatuses.get(stalk.get('dnuuid'), []):
            # TODO: cache these too?
            iconList.append(QtGui.QPixmap(icons.getSubmissionStatusIcon(category)))

            if category == "site transfer":
                text = "Site Transferred"
            elif category == "good to go":
                text = category.capitalize()
            else:
                text = "Submitted to %s" % category.capitalize()
            toolTipText.append(text)

        if iconList:
            composite = iconutil.concatenatePixmaps(iconList)
            return [(QtCore.Qt.DecorationRole, composite), (QtCore.Qt.ToolTipRole, "\n".join(toolTipText))]

        return []

    def stalk_evaluate_for_delete_state(self, stalk, treeNode=None):
        state, icon, tooltip = self.__getWeedAnalysisState(stalk)
        return [(QtCore.Qt.DecorationRole, icon), (QtCore.Qt.DisplayRole, state), (QtCore.Qt.ToolTipRole, tooltip)]

    def stalk_reviewstatus(self, stalk, treeNode=None):
        iconimage = None
        # get foreground colour for review status
        reviewstatus = stalk.get('reviewstatus')
        # get status icon
        if reviewstatus:
            # get the image from the cache if it has already been made
            image = self.__reviewStatusIconCache.get(reviewstatus)
            if image is None:
                try:
                    code = shotgun_cache.getShotgunCodeForReviewStatus(reviewstatus)
                except KeyError:
                    code = ""

                if code:
                    image = QtGui.QPixmap(icons.getReviewStatusIcon(code))
                    if image.isNull():
                        image = QtGui.QPixmap(24, 24)
                        image.fill(QtCore.Qt.transparent)
                        painter = QtGui.QPainter(image)
                        factor = 24.0 / painter.fontMetrics().width(code)
                        if factor < 1.0 or factor > 1.25:
                            font = painter.font()
                            font.setPointSizeF(QtGui.QFontInfo(font).pointSizeF() * factor)
                            painter.setFont(font)
                        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
                        painter.drawText(image.rect(), QtCore.Qt.AlignCenter, code)
                        painter.end()
                    # save the image into the cache
                    self.__reviewStatusIconCache[reviewstatus] = image

            iconimage = QtGui.QIcon(image)

        return [(QtCore.Qt.DisplayRole, reviewstatus), (QtCore.Qt.ToolTipRole, reviewstatus),
                (QtCore.Qt.DecorationRole, iconimage)]

    def stalk_thumbnail(self, stalk, treeNode=None):
        # get exr header image if there is no normal thumbnail
        data = stalk.get('thumbnail') or self._getLeafFileLocation(treeNode, isLeaf=False)
        return [(QtCore.Qt.DisplayRole, data)]

    def stalk_stalkdir_size(self, stalk, treeNode=None):
        return [(QtCore.Qt.DisplayRole, convert_to_human_readable(stalk.get('stalkdir_size'))),
                (wizqt.ROLE_SORT, stalk.get("stalkdir_size"))]

    def stalk_stalkname(self, stalk, treeNode=None):
        stalkname = stalk.get('stalkname')
        # stalk under another stalk is a pod
        parentNode = treeNode.getParentNode()

        # is this a pod - TODO: surely this could be passed in?
        isPod = parentNode is not None and parentNode.dataObject().dataInterface() == self.__stalk_handler

        stalkState = stalk.get("state")
        number = str(len(treeNode.getChildNodes()) if treeNode.hasChildren() else 0)

        # check the cache before making another pixmap
        key = "{0}{1}".format(stalkState, number)
        if key not in self.__stalknumberpixmapCache:

            # make a pixmap, and cache it for laters
            basePixmap = self.__stalkCompPixmap
            if isPod:
                basePixmap = self.__podCompPixmap
            elif stalkState in PENDING_STALK_STATES:
                basePixmap = self.__pendingCompPixmap
            elif stalkState in ERROR_STALK_STATES:
                basePixmap = self.__erroredCompPixmap

            pixmap = QtGui.QPixmap(basePixmap)
            painter = QtGui.QPainter(pixmap)
            painter.setPen(self.__childCountPenColour)

            painter.drawText(self.ICON_WIDTH,
                             self.ICON_WIDTH,
                             number
                             )
            painter.end()
            self.__stalknumberpixmapCache[key] = pixmap

        pixmap = self.__stalknumberpixmapCache[key]

        return [(QtCore.Qt.DisplayRole, stalkname), (QtCore.Qt.ToolTipRole, stalkname),
                (QtCore.Qt.DecorationRole, pixmap)]

    def stalk_version(self, stalk, treeNode=None):
        return [(QtCore.Qt.DisplayRole, str(stalk.get('version')))]

    def stalk_owner(self, stalk, treeNode=None):
        owner = stalk.get("owner").split("@", 1)[0]
        name = self.__getUserFullName(owner)
        return [(QtCore.Qt.DisplayRole, name), (wizqt.ROLE_SORT, name)]

    def stalk_suggest_for_delete_to(self, stalk, treeNode=None):
        login = stalk.get("suggest_for_delete_to").split("@", 1)[0]
        name = self.__getUserFullName(login)
        return [(QtCore.Qt.DisplayRole, name)]

    def stalk_ondisk_lon(self, stalk, treeNode=None):
        toolTipText = []
        opacityList = []
        sites = []

        for siteName, ondiskField in SITES_TO_ONDISKFIELDS.items():
            ondiskState = stalk.get(ondiskField)

            if ondiskState != "None":
                sites.append(siteName)
                toolTipText.append("{0}: {1}".format(siteName, ondiskState))

                opacity = 1.0
                if ondiskState == "Partial":
                    opacity = 0.4
                opacityList.append(opacity)

        if sites:
            iconlistname = "{0}{1}".format("".join(sites), "".join([str(x) for x in opacityList]))
            if iconlistname not in self.__ondiskcombosCache:
                # Make it and store it in the cache for laters
                iconList = []

                for site in sites:
                    iconList.append(QtGui.QPixmap(iconutil.getSiteIcon(siteCode=site)))

                composite = iconutil.concatenatePixmaps(iconList, opacityList=opacityList)
                self.__ondiskcombosCache[iconlistname] = composite

            composite = self.__ondiskcombosCache[iconlistname]

            return [(QtCore.Qt.DecorationRole, composite), (QtCore.Qt.ToolTipRole, "\n".join(toolTipText))]

        return []

    def leaf_twigtype(self, leaf, treeNode=None):
        twigtype = leaf.stalk().twig().twigtype().get('twigtype')
        return [(QtCore.Qt.DisplayRole, twigtype), (QtCore.Qt.ToolTipRole, twigtype)]

    def leaf_leafname(self, leaf, treeNode=None):
        icon = icons.getFileIcon(getFileFormat(leaf.get('location')))
        leafname = leaf.get('leafname')
        resolution = leaf.get('resolution')

        leafresname = leafname
        if resolution:
            leafresname = '{0} ({1})'.format(leafname, resolution)
        return [(QtCore.Qt.DecorationRole, QtGui.QIcon(icon)), (QtCore.Qt.ToolTipRole, leafname),
                (QtCore.Qt.DisplayRole, leafresname)]

    def leaf_thumbnail(self, leaf, treeNode=None):
        # get exr header image if there is one
        data = self._getLeafFileLocation(treeNode, isLeaf=True)
        return [(QtCore.Qt.DisplayRole, data)]

    def leaf_filesize(self, leaf, treeNode=None):
        return [(QtCore.Qt.DisplayRole, convert_to_human_readable(leaf.get('filesize'))),
                (wizqt.ROLE_SORT, leaf.get('filesize'))]

    def leaf_ondisk_lon(self, leaf, treeNode=None):
        flagList = []
        for siteName, ondiskField in SITES_TO_ONDISKFIELDS.items():
            if int(leaf.get(ondiskField)):
                flagList.append(QtGui.QPixmap(iconutil.getSiteIcon(siteCode=siteName)))

        if flagList:
            # TODO: caching the various combinations of this might be
            # another places to speed things up in future. Although
            # the number of leafs per stalk is small enough that it
            # probably doesn't matter unless there are lots and lots
            # of stalks expanded.
            composite = iconutil.concatenatePixmaps(flagList)
            return [(QtCore.Qt.DecorationRole, composite)]
        return []

    @lru_cache()
    def __getUserFullName(self, username):
        """Get the full name corresponding to a username.

        Args:
            username (str): The username of the user to get a full name for.

        Returns:
            str: The full name of the user.
            This will default to the username if
            the full name could not be found.
        """
        fullName = username.capitalize()

        # There's no point tryin to look up an empty login
        if username:
            try:
                fullName = pwd.getpwnam(username).pw_gecos
            except KeyError:
                try:
                    uh = self._handler["User"]
                    fullName = uh.value(uh["mailname"], uh["login"] == username)
                except NoResultFound:
                    pass

        return fullName

    def __cacheRelatedInterfaces(self):
        """
        Store a data container of all the submission
        """

        # collect stalks in view
        stalks = self.__tree.getObjectsOfInterface(self.__stalk_handler)

        if stalks:
            # cache submission status histories
            try:
                for s in SubmissionHistory.createBatch(stalks, sh=self._handler):
                    self.__submissionStatuses[s.dnuuid] = s.categories
            except Exception as e:
                _LOGGER.exception("")

            # Cache weed evaluations.
            # This loads the weed things and caches them for laters.
            # Note: This Evaluation class is the cutdown ivyqt local
            # one that does not contain any weed Reasons or ReasonLists.
            #
            try:
                for e in Evaluation.createBatch(self._handler, dataObjects=list(stalks), defer=False):
                    self.__weedEvaluations[e.stalk.getUuid()] = e
            except Exception as e:
                _LOGGER.exception("")

    # Stolen/copied/based on isWidgetField() from dynamic_header_datasource.py
    #
    def isWidgetFieldForTwig(self, descriptor, dataObject, dataInterfaceName=None):

        field = descriptor.fields.get(dataInterfaceName)
        if field is None:
            return False

        name = field.name()
        if name not in self.__fieldiswidgetCache:
            self.__fieldiswidgetCache[name] = (field.getProperty("display_type") == 'multi_line_text')

        return self.__fieldiswidgetCache[name]

    def __populateDirectly(self, descriptor, dataInterfaceName, dataObject, node, special_cases):
        setdata = []

        field = descriptor.fields.get(dataInterfaceName)
        # TODO: invert this to simplify it if it stays here
        if field is not None:

            fieldName = field.name()
            getdatamethod = special_cases.get(fieldName)
            if getdatamethod is not None:
                setdata = getdatamethod(dataObject, treeNode=node)
            else:
                data = dataObject.get(fieldName)

                # flattened setCellData
                iswidget = False
                if fieldName not in self.__fieldiswidgetCache:
                    # TODO: this only seems to match 'metadata', so
                    # could be just check the field name instead of
                    # all this?
                    self.__fieldiswidgetCache[fieldName] = (field.getProperty("display_type") == 'multi_line_text')
                iswidget = self.__fieldiswidgetCache[fieldName]

                if iswidget:
                    if isinstance(data, str):
                        if not data:
                            data = None  # filter out empty strings
                        else:
                            data = unicode(data, errors='replace').encode('ascii', 'xmlcharrefreplace')
                    if data:
                        setdata = [(self.ROLE_HIDDEN_DATA, data)]

                else:
                    # NOTE: there are only 2 values in this list
                    setdata = [(QtCore.Qt.DisplayRole, data), (QtCore.Qt.ToolTipRole, data)]

        return setdata

    def __populateFromPropagatedInterface(self, descriptor, propagateInterfaceName, latestChildNode, latestChildObject,
                                          latestChildKeys, dataObject, dataInterfaceName, special_cases):
        setdata = []
        propagationField = descriptor.fields.get(propagateInterfaceName)
        if propagationField is not None:
            propagationFieldName = propagationField.name()

            # propagate up the stalk's special case method if there is one
            getdatamethod = special_cases.get(propagationFieldName)
            if getdatamethod is not None:
                setdata = getdatamethod(latestChildObject, treeNode=latestChildNode)
                return setdata

            if propagationFieldName in latestChildKeys:
                # else fall back on the object's data
                data = latestChildObject.get(propagationFieldName)
                # flattened setcelldata
                iswidget = False
                field = descriptor.fields.get(dataInterfaceName)
                if field is not None:
                    fieldName = field.name()
                    if fieldName not in self.__fieldiswidgetCache:
                        self.__fieldiswidgetCache[fieldName] = (field.getProperty("display_type") == 'multi_line_text')
                    iswidget = self.__fieldiswidgetCache[fieldName]

                if iswidget:
                    if isinstance(data, str):
                        if not data:
                            data = None  # filter out empty strings
                        else:
                            data = unicode(data, errors='replace').encode('ascii', 'xmlcharrefreplace')
                    if data:
                        setdata = [(self.ROLE_HIDDEN_DATA, data)]
                else:
                    setdata = [(QtCore.Qt.DisplayRole, data), (QtCore.Qt.ToolTipRole, data)]

        return setdata

    def _populateItemFromTreeNode(self, node, headerLen, dataInterfaceName, special_cases, parentIsFiltered=False,
                                  disable_this_one=False, disabled_colour=None):
        """
        """
        dataObject = node.dataObject()

        apply_to_all = []
        if parentIsFiltered or disable_this_one:
            # disable_this_one is for: mark non-matching stalks (this
            # is only if highlight mode is on, but that's dealt with
            # by the caller atm).
            # The disabled row attributes are:
            #   ( ROLE_FILTER_OMITTED, True ),
            #   ( QtCore.Qt.ForegroundRole, self.__disabledTextColour ),
            #   ( QtCore.Qt.ToolTipRole, 'Omitted by data filter' )
            apply_to_all.extend(self.__disabledRowAttributes)
        else:
            # Is this archived?
            try:
                isArchived = bool(dataObject.get("archived"))
            except ValueError:
                isArchived = False
            if isArchived:
                fgColor = ARCHIVEDFGCOLOUR
                bgColor = ARCHIVEDBGCOLOUR
                # Note: this blats over the isDeleted setting from above.
                # I think that's deliberate because archived superceeds
                # deleted.
                apply_to_all = [(QtCore.Qt.BackgroundRole, bgColor), (QtCore.Qt.ForegroundRole, fgColor)]
            else:
                # Is this deleted?
                try:
                    isDeleted = bool(dataObject.get("deleted"))
                except ValueError:
                    isDeleted = False
                if isDeleted:
                    fgColor = DELETEDFGCOLOUR
                    bgColor = DELETEDBGCOLOUR
                    apply_to_all = [(QtCore.Qt.BackgroundRole, bgColor), (QtCore.Qt.ForegroundRole, fgColor)]

        # TODO: this may duplicate some apply to alls already on the list
        if dataInterfaceName in INTERFACES_WITH_DISK_PRESENCE:
            # colour nonlocal leaves - not deleted and not on local disk
            if not dataObject.get("deleted", datautil.DataValueType.BOOL) and dataObject.get(
                    LOCAL_SITE_ONDISK_FIELD) == ONDISK_NONE:
                # flattened applynonlocalcolours
                if disabled_colour is None:
                    disabled_colour = theme.getIvyStateColour(wizqt.COLORKEY_NONLOCAL)
                font = QtGui.QApplication.font()
                font.setItalic(True)
                apply_to_all.extend([(QtCore.Qt.FontRole, font), (QtCore.Qt.ForegroundRole, disabled_colour)])

        # stalk to twig propagation is a special case for the twig datasource
        latestChildObject = None
        latestChildKeys = None
        latestChildNode = None
        child_special_cases = special_cases

        propagateInterfaceName = self.PROPAGATION_RELATIONSHIPS.get(dataInterfaceName)
        if propagateInterfaceName is not None:
            childNodes = node.getChildNodes()
            if len(childNodes) != 0:
                latestChildNode = childNodes[0]
                if latestChildNode:
                    latestChildObject = latestChildNode.dataObject()
                    latestChildKeys = latestChildObject.keys()
                    child_special_cases = self._specialCases.get(propagateInterfaceName, {})

        # Colour the item if it's a stalk with a review status with a
        # colour set for it, e.g. 'Element In Pipe' or 'Element
        # Approved'. Or also colour the item if it's a twig who's
        # latest stalk also has a review status with a colour set for
        # it.
        if dataInterfaceName in INTERFACES_WITH_REVIEW_STATUS_COLOURS:
            if dataInterfaceName == 'Stalk':
                reviewstatus = dataObject.get('reviewstatus')
            elif latestChildObject is not None:
                reviewstatus = latestChildObject.get('reviewstatus')
            else:
                reviewstatus = None

            if reviewstatus:
                # Get the colour from the cache, if it has already
                # been looked up
                if reviewstatus not in self.__reviewStatus2colourCache:
                    colour = theme.getAutoReviewStatusColour(status=reviewstatus)
                    self.__reviewStatus2colourCache[reviewstatus] = colour

                colour = self.__reviewStatus2colourCache[reviewstatus]
                if colour:
                    apply_to_all.append((QtCore.Qt.ForegroundRole, colour))

        # Populate columns
        #
        itemdata = [None for n in self.column_range_list]
        for column in self.column_range_list:

            descriptor = self._descriptors[column]
            # TODO: invert this to simplify the indents
            if descriptor is not None:

                # init the dict for this coln - TODO: really want to
                # do this last
                d = {}
                if column == 0:
                    d[ivyqt.ROLE_TREE_NODE] = node
                if column not in self._imagecols:
                    for i in apply_to_all:
                        r = i[0]
                        v = i[1]
                        d[r] = v

                # populate normally...
                datasofar = self.__populateDirectly(descriptor, dataInterfaceName, dataObject, node, special_cases)
                if datasofar:
                    for i in datasofar:
                        r = i[0]
                        v = i[1]
                        d[r] = v
                    itemdata[column] = d
                    continue

                # if there are fields for this key, just not for this
                # object's data interface, get it's real name from the
                # descriptor, and see if we have any other special
                # case methods to handle it, e.g. Stalk submission status
                if descriptor.fields:
                    # Note: This gets used for TwigType.twigtype and
                    # YSubmission.status
                    datasofar = None
                    for otherInterfaceName in self._nonQueryInterfaceNames:
                        field = descriptor.fields.get(otherInterfaceName)
                        if field is not None:
                            fieldName = field.name()
                            getdatamethod = special_cases.get(fieldName)
                            if getdatamethod is not None:
                                datasofar = getdatamethod(dataObject, treeNode=node)
                                break

                    if datasofar:
                        for i in datasofar:
                            r = i[0]
                            v = i[1]
                            d[r] = v
                        itemdata[column] = d
                        continue

                # If there is no specified field for the data
                # interface of the data object, we check if we are
                # propagating a child item's data up.
                if propagateInterfaceName and latestChildNode and not self.isWidgetFieldForTwig(descriptor,
                                                                                                latestChildObject,
                                                                                                propagateInterfaceName):
                    datasofar = self.__populateFromPropagatedInterface(descriptor, propagateInterfaceName,
                                                                       latestChildNode,
                                                                       latestChildObject, latestChildKeys, dataObject,
                                                                       dataInterfaceName,
                                                                       child_special_cases)

                    if datasofar:
                        for i in datasofar:
                            r = i[0]
                            v = i[1]
                            d[r] = v
                        itemdata[column] = d
                        continue

            else:
                # It might be a tag column?
                if column in self._tag_column_numbers:
                    # It is a tag column, so just stick it's value in,
                    # if it has one.
                    data = None
                    if dataObject.hasTagAttr(fieldName):
                        data = dataObject.getDataTagAttribute(fieldName).value()
                    itemdata[column] = {QtCore.Qt.DisplayRole: data,
                                        QtCore.Qt.ToolTipRole: data}

        # Making the model item with bulk data setting form
        #
        item = ModelItem(headerLen, uniqueId=dataObject.get('dnuuid'), dataObject=dataObject, itemData=itemdata,
                         dataType=dataInterfaceName)

        return item

    ##############################################################################################################
    # 	_updateFilter
    ##############################################################################################################
    def _updateFilter(self):
        filter = self._filter.clone()
        filter.resetSearch()
        filter.resetTagSearch()
        leafFilter = self.__leafFilter.clone()
        leafFilter.resetSearch()
        leafFilter.resetTagSearch()
        isValid = True
        omitDeleted = True
        searchTags = False
        for (filterSource, required) in self._filterSources:
            if filterSource.isValid:
                if isinstance(filterSource, LeafFilterSource):
                    leafFilter.update(filterSource.filter)
                else:
                    if not filterSource.filter.getOmitDeleted():
                        omitDeleted = False
                    if filterSource.filter.getSearchTags():
                        searchTags = True
                    filter.update(filterSource.filter)
            elif required:
                isValid = False
        # HACK: force the omit deleted flag to always be applied if one exists
        filter.omitDeleted(omitDeleted)
        filter.searchTags(searchTags)
        if isValid != self._isValid or filter != self._filter or leafFilter != self.__leafFilter:
            self._filter = filter
            self.__leafFilter = leafFilter
            self._isValid = isValid
            self.setPage(0)  # reset to first page
            self.setNeedToRefresh(True)

    ##############################################################################################################
    # 	FETCH METHODS
    ##############################################################################################################
    # 	@wizqt.TimeIt( verbose = True, mean = False, total = False )
    def _ivyFetchBatch(self, parentIndex, offset, limit, reload):
        """
        Return a list of ModelItem entities to the model.

        :parameters:
            parentIndex : QtGui.QModelIndex
                checks the index of the parent item is valid (?)
            offset : int
                page offset
            limit : int
                limit of results per page
            reload : bool
                reload existing results
        :return:
            list of model items to be displayed
        :rtype:
            list
        """
        assert not parentIndex.isValid()

        self._filter.offset(offset)
        self._filter.limit(limit)
        self._filter.reload(reload)

        findTotal = self._loadMethod != self.LOAD_METHOD_ALL
        self._filter.findTotal(findTotal)

        result = True
        itemList = []
        totalCount = 0
        try:
            accesskey = self.handler.createAccessKey(DataAccessLevel.PIPELINE)
            with self.handler.requestAccess(accesskey):
                result, log = self._interface.isValidDataFilter(self._filter)
        except Exception as e:
            pass

        if result:
            sortFields = [op.dataField().name() for op in self._filter.getSort()]
            versionSortFields = [op.dataField().name() for op in self.__versionSortFilter.getSort()]
            # If we are sorting on the same field as one of the ones
            # in the version sort filter, we can't get the cached
            # results because they will be sorted wrongly.
            if set(sortFields).intersection(versionSortFields):
                self._filter.reload(True)

            if self.cachingEnabled():
                filterStateDesc = "filterMode:{0}, leafFilter:{1}".format(
                    self.resultFilterMode(),
                    self.__leafFilter.getFilterString(self.__leaf_handler)
                )
                (itemList, totalCount) = self._cache.getItems(
                    self._interface,
                    self._queryType,
                    self._filter,
                    filterStateDesc
                )
            else:
                (itemList, dataContainer) = self._createNewItems()
                totalCount = dataContainer.getTotalFound() if findTotal else dataContainer.size()
            # apply custom style
            if self._customStyleFunction:
                itemList = self._customStyleFunction(itemList, self.headerItem, self._handler)
        # else:
        #  There are no results returned at all! This will blank the twig viewer

        # update total count
        self._setTotalCount(totalCount)

        # Clear cache to prevent slowdown over time. And doing this
        # creates a slowdown on start up, so check that some items
        # were found above before calling the purge.
        if (totalCount > 0):
            self.__purgeStalkQueryCache()

        return itemList

    def _getSortField(self, descriptor):
        # don't allow sorting on leaf interface as it takes too long
        sortInterfaces = ['Stalk', 'Twig', 'TwigType', 'YSubmission']

        # Note: the YSubmission interface in Grouped versions mode
        # results in unqueryable queries when sorting by Submission
        # Status.

        # make sure the current top level interface is checked first
        if self.topLevelInterfaceName in sortInterfaces:
            sortInterfaces.remove(self.topLevelInterfaceName)
        sortInterfaces.insert(0, self.topLevelInterfaceName)

        # get the field from the interface
        for interfaceName in sortInterfaces:
            if descriptor.fields.has_key(interfaceName):
                return descriptor.fields.get(interfaceName)

        return None

    def _getColumnType(self, columnCode, ivyDataType):
        if columnCode in ('filesize', 'stalkdir_size', 'version'):
            return wizqt.TYPE_STRING_SINGLELINE
        return super(TwigDataSource, self)._getColumnType(columnCode, ivyDataType)

    def canFetchMore(self, parentIndex):
        """
        Check whether the parentIndex needs to be populated. This applies only to
        incremental loading or lazy population of children

        :parameters:
            parentIndex : QtCore.QModelIndex
                model index to be queried
        :return:
            True if item needs to be populated
        :rtype:
            bool
        """
        if not self._lazyLoadChildren:
            return False
        item = self._model.itemFromIndex(parentIndex)
        if item.data(role=ivyqt.ROLE_TREE_NODE) is None:
            return False
        # if totalChildCount is uninitialized (-1), item is unpopulated

        return item.totalChildCount() < 0

    # 	@wizqt.TimeIt( verbose = True, mean = False, total = False )
    def fetchMore(self, parentIndex):
        """
        This method only gets called when canFetchMore() returns True
        should only be for incremental loading or lazy population of children

        :parameters:
            parentIndex : QtCore.QModelIndex
                model index to be queried
        """

        item = self._model.itemFromIndex(parentIndex)
        if item is None:
            return
        node = item.data(role=ivyqt.ROLE_TREE_NODE)
        if node is None:
            return
        nodeChildren = list(node.getChildNodes())
        childCount = len(nodeChildren)
        item.setTotalChildCount(childCount)
        if childCount == 0:
            return
        interface = node.dataObject().dataInterface()
        if interface == self.__twig_handler:
            if self.__includeStalks:
                self._model.appendItems(self.__makeStalkItems(nodeChildren), parentIndex)
        elif interface == self.__stalk_handler:
            # split up leaves and pods
            leaves = []
            pods = []
            for child in nodeChildren:
                childInterface = child.dataObject().dataInterface()
                if childInterface == self.__leaf_handler:
                    leaves.append(child)
                elif childInterface == self.__stalk_handler:
                    pods.append(child)
                else:
                    raise TypeError(
                        'Unsupported object of type "{0}" added as child of Stalk object'.format(childInterface.name()))
            if self.__includeLeaves:
                self._model.appendItems(self.__makeLeafItems(leaves, parentItem=item), parentIndex)
            if self.__includePods:
                self._model.appendItems(self.__makePodItems(pods, parentItem=item), parentIndex)

    ##############################################################################################################
    # 	__makeLeafItems
    ##############################################################################################################
    # @wizqt.TimeIt( mean = False, total = False, printFn = wizqt.TimeIt.stdout )
    def __makeLeafItems(self, leafNodes, parentItem=None):
        """
        """
        # This is called when a stalk is expanded
        headerLen = len(self._headerItem)
        leafItems = []
        disabled_colour = theme.getIvyStateColour(wizqt.COLORKEY_NONLOCAL)
        dataInterfaceName = "Leaf"
        special_cases = self._specialCases.get(dataInterfaceName, {})

        # check if the parent stalk is greyed out
        parentIsFiltered = (parentItem is not None and parentItem.data(role=ROLE_FILTER_OMITTED) is True)
        for leafNode in leafNodes:

            leafItem = self._populateItemFromTreeNode(leafNode, headerLen, dataInterfaceName, special_cases,
                                                      parentIsFiltered=parentIsFiltered,
                                                      disabled_colour=disabled_colour)
            leafItem.setTotalChildCount(0)

            if self._itemsCheckable:
                leafItem.setCheckable(self._itemsCheckable["leafs"])

            leafItems.append(leafItem)

        if self._customStyleFunction is not None:
            return self._customStyleFunction(leafItems, self.headerItem, self._handler)

        return leafItems

    ##############################################################################################################
    # 	__makePodItems
    ##############################################################################################################
    # 	@wizqt.TimeIt( mean = False, total = False, printFn = wizqt.TimeIt.stdout )
    def __makePodItems(self, podNodes, parentItem=None):
        headerLen = len(self._headerItem)
        dataInterfaceName = "Stalk"
        special_cases = self._specialCases.get(dataInterfaceName, {})
        podItems = []
        disabled_colour = theme.getIvyStateColour(wizqt.COLORKEY_NONLOCAL)
        parentIsFiltered = (parentItem is not None and parentItem.data(role=ROLE_FILTER_OMITTED) is True)

        for podNode in podNodes:

            item = self._populateItemFromTreeNode(podNode, headerLen, dataInterfaceName, special_cases,
                                                  parentIsFiltered=parentIsFiltered, disabled_colour=disabled_colour)
            if self.__includeLeaves is False:
                item.setTotalChildCount(0)

            podItems.append(item)

            if self._itemsCheckable:
                item.setCheckable(self._itemsCheckable["pods"])

        if self._customStyleFunction is not None:
            return self._customStyleFunction(podItems, self.headerItem, self._handler)

        return podItems

    ##############################################################################################################
    # 	__makeStalkItems
    ##############################################################################################################
    # @wizqt.TimeIt( mean = False, total = False, printFn = wizqt.TimeIt.stdout )
    def __makeStalkItems(self, stalkNodes):
        """
        This gets called to lazy load stalks when the top level interface is Twig
        """
        stalkFilter = self.__versionSortFilter.clone()
        stalkFilter.update(self._filter.extractFilter('Stalk'), True, True, False)
        highlight_mode = self.__filterMode == self.HIGHLIGHT
        disabled_colour = theme.getIvyStateColour(wizqt.COLORKEY_NONLOCAL)
        headerLen = len(self._headerItem)
        dataInterfaceName = "Stalk"
        special_cases = self._specialCases.get(dataInterfaceName, {})

        stalkItems = []
        for stalkNode in stalkNodes:
            stalk = stalkNode.dataObject()

            disable_this = highlight_mode and not stalkFilter.isDataObjectMatch(stalk)

            item = self._populateItemFromTreeNode(stalkNode, headerLen, dataInterfaceName, special_cases,
                                                  disable_this_one=disable_this, disabled_colour=disabled_colour)
            if self.__includeLeaves is False and self.__includePods is False:
                item.setTotalChildCount(0)

            stalkItems.append(item)

            if self._itemsCheckable:
                item.setCheckable(self._itemsCheckable["stalks"])

        if self._customStyleFunction is not None:
            return self._customStyleFunction(stalkItems, self.headerItem, self._handler)

        return stalkItems

    ##############################################################################################################
    # 	makeItems
    ##############################################################################################################
    # 	@wizqt.TimeIt( mean = False, total = False, printFn = wizqt.TimeIt.stdout )
    def makeItems(self, dataContainer):
        """
        """
        interfaceName = dataContainer.dataInterface().name()

        # get tree components
        self.__tree = spider.orm.DataTree.create(self._handler)
        rootNodeContainer = spider.orm.DataTreeNodeContainer.create(dataContainer)
        createTreeLoader = spider.orm.DataTreeLoader.create
        down = spider.orm.DataTreeLoadDirection.DOWN
        # get the interfaces now
        stalkInterface = self.__stalk_handler
        twigInterface = self.__twig_handler
        # load data as tree
        loaders = []
        # stalk loader
        if self.resultFilterMode() == self.OMIT:
            stalkFilter = self.__versionSortFilter.clone()
            stalkFilter.update(self._filter.extractFilter('Stalk'), True, True, False)  # args:
        else:
            stalkFilter = self.__versionSortFilter
        # propagate the omit deleted/archived flags
        stalkFilter.update(self._filter, False, False, False, True)
        loaders.append(createTreeLoader(twigInterface, "stalk", down, stalkFilter))
        stalkLoaders = []
        stalkLoaderFilters = []
        # leaf loader
        stalkLoaders.append("leaf")
        # propagate the omit deleted/archived flags
        self.__leafFilter.update(self._filter, False, False, False, True)
        stalkLoaderFilters.append(self.__leafFilter)
        # pod loader - only add this one if we really need it
        if self.__includePods:
            stalkLoaders.append("pod")
            stalkLoaderFilters.append(DataFilter.create().search(self._handler['Seed']['dependency_type'] == 'view'))
        # add loaders to the tree
        loaders.append(createTreeLoader(stalkInterface, stalkLoaders, down, stalkLoaderFilters))
        map(self.__tree.addLoader, loaders)
        self.__tree.setRootNodes(rootNodeContainer)
        self.__tree.load(grow=True)

        # now preload relationships..
        t = self.__tree.getObjectsOfInterface(self.__twig_handler)
        t.twigtypes()

        s = self.__tree.getObjectsOfInterface(self.__stalk_handler)
        st = s.twigs()
        st.twigtypes()

        l = self.__tree.getObjectsOfInterface(self.__leaf_handler)
        l.stalks()

        # purge cache..
        self.__submissionStatuses = {}
        self.__weedEvaluations = {}

        self.__cacheRelatedInterfaces()

        # modelitem list
        items = []
        if not self.__tree.empty():
            istwig = interfaceName == 'Twig'

            headerLen = len(self._headerItem)
            special_cases = self._specialCases.get(interfaceName, {})

            disabled_colour = theme.getIvyStateColour(wizqt.COLORKEY_NONLOCAL)

            for node in rootNodeContainer:
                item = self._populateItemFromTreeNode(node, headerLen, interfaceName, special_cases,
                                                      disabled_colour=disabled_colour)
                if istwig:
                    # a twig
                    if self.__includeStalks is False:
                        item.setTotalChildCount(0)
                else:
                    # a stalk
                    if self.__includeLeaves is False and self.__includePods is False:
                        item.setTotalChildCount(0)

                if self._itemsCheckable:
                    item.setCheckable(self._itemsCheckable["%ss" % interfaceName.lower()])

                items.append(item)

        if self._customStyleFunction is not None:
            return self._customStyleFunction(items, self.headerItem, self._handler)

        return items

    ##############################################################################################################
    # 	setIncludeStalks
    ##############################################################################################################
    def setIncludeStalks(self, state):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        self.__includeStalks = state
        self.setNeedToRefresh(True)

    ##############################################################################################################
    # 	setIncludePods
    ##############################################################################################################
    def setIncludePods(self, state):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        if state is True:
            self.__includeStalks = True
        self.__includePods = state
        self.setNeedToRefresh(True)

    ##############################################################################################################
    # 	setIncludeLeaves
    ##############################################################################################################
    def setIncludeLeaves(self, state):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        if state is True:
            self.__includeStalks = True
        self.__includeLeaves = state
        self.setNeedToRefresh(True)

    ##############################################################################################################
    # 	resultFilterMode
    ##############################################################################################################
    def resultFilterMode(self):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        return self.__filterMode

    ##############################################################################################################
    # 	setResultFilterMode
    ##############################################################################################################
    def setResultFilterMode(self, mode):
        """

        :parameters:

        :keywords:

        :return:

        :rtype:

        """
        assert mode in self.__modes, 'Filter result display mode must be one of : %s, %s, %s' % self.__modes
        if self.resultFilterMode() != mode:
            self.__filterMode = mode
            self.setNeedToRefresh(True)

    ##############################################################################################################
    # 	Tag Columns
    ##############################################################################################################
    # TODO combine with column config dialog
    def addTagColumns(self, columns, noRefresh=False):
        """
        """
        # remove unicode
        columns = dict([(int(k), str(v)) for k, v in columns.iteritems()])  # map( str, columns )
        # change mapping dict
        self.__TAG_COLUMNS = columns
        currentColumns = map(self._headerItem.data, range(len(self._headerItem)))

        # remove old tag columns
        tagColumns = currentColumns[:]
        map(tagColumns.remove, self.fullColumnOrder)
        for tagColumn in reversed(tagColumns):
            index = currentColumns.index(tagColumn)
            self._headerItem.removeColumns(index, 1)
            self._model.removeColumns(index, 1)

        # add new empty columns
        nonTagColumnCount = len(self._headerItem)
        newColumnCount = len(columns)
        self._model.insertColumns(nonTagColumnCount, newColumnCount)

        # populate columns
        currentColumnIndex = nonTagColumnCount

        setHeaderData = self._headerItem.setData
        for name in columns.values():
            # Add the tag column to the header data
            setHeaderData(name, column=currentColumnIndex)
            setHeaderData(name, column=currentColumnIndex, role=wizqt.ROLE_NAME)
            setHeaderData(False, column=currentColumnIndex, role=wizqt.ROLE_IS_SORTABLE)
            setHeaderData(QtGui.QIcon(icons.ICON_TAG_SML), column=currentColumnIndex, role=QtCore.Qt.DecorationRole)

            # Add the tag column to the internal caches
            self.column_range_list.append(currentColumnIndex)
            self._descriptors.append(None)
            self._tag_column_numbers[currentColumnIndex] = True

            currentColumnIndex += 1

        # refresh to populate columns
        needToReferesh = tagColumns != columns.values()
        if noRefresh is False and needToReferesh is True:
            self.setNeedToRefresh(True)

    def currentTagColumns(self):
        return self.__TAG_COLUMNS.copy()

    ##############################################################################################################
    # 	interface setting
    ##############################################################################################################
    def setInterface(self, interfaceName):
        """
        Set the data interface to search on

        :parameters:

        """
        # implementation
        changed = self._interface != self._handler[interfaceName]
        if changed:
            self._interface = self._handler[interfaceName]
            self._handler = spider.getHandler(datainst=self._interface)
            # Note: reload = True to force the DataTree to be rebuilt when
            # the interface is changed
            self.model.requestRefresh(reload=True)

            # reapply sorting
            # NOTE: this relies on suitably new versions of wizqt that
            # support the refresh parameter.
            self.model.doSort(refresh=False)

    def toggleInterface(self):
        """
        """
        self.setInterface('Stalk' if self.topLevelInterfaceName == 'Twig' else 'Twig')

    @property
    def topLevelInterfaceName(self):
        """
        """
        return self._interface.name()
