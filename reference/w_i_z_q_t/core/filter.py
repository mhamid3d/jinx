import logging

from wizqt import exc, common

_LOGGER = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------------------------------------------------------------------------
# CLASSES
# ----------------------------------------------------------------------------------------------------------------------------------------------------

class FilterError(exc.WizQtError):
    pass


class Filter(object):
    """Class representing a single filter parameter, e.g. ``<fieldName> == 'foo'``"""

    def __init__(self, fieldName, operator, values=None, isEnabled=True):
        if not fieldName:
            raise FilterError("Invalid fieldName '%s'" % fieldName)
        if operator not in common.OPERATORS:
            raise FilterError("Unknown operator '%s'" % operator)
        # if operator not in getTypeHandler(fieldType).getFilterOperators():
        #    raise FilterError("Invalid operator '%s' for type '%s' of field '%s'" % (operator, fieldType, fieldName))

        self.isEnabled = isEnabled
        self.fieldName = fieldName
        self.operator = operator
        self.values = []
        if values is not None:
            if isinstance(values, (list, tuple)):
                self.values.extend(values)
            else:
                self.values.append(values)

    def __hash__(self):
        return hash(tuple([self.fieldName, self.operator, self.isEnabled] + self.values))

    def __str__(self):
        strList = [self.fieldName, self.operator]

        if self.values:
            if self.operator == common.OPERATOR_IN_RANGE:
                valuesStr = "%s - %s" % (self.values[0], self.values[1])
            else:
                valuesStr = " ".join([unicode(v) for v in self.values])

            strList.append("'%s'" % valuesStr)

        return " ".join(strList)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return not self == other


class FilterSet(object):
    """Class representing a group of :class:`Filter` objects."""

    # constants
    OPERATOR_AND = "AND"
    OPERATOR_OR = "OR"

    # properties
    filters = property(lambda self: self.__filters)
    filterSets = property(lambda self: self.__filterSets)

    def __init__(self, operator=OPERATOR_AND):
        self.operator = operator
        self.__filters = []
        self.__filterSets = []

    def addFilter(self, filter):
        if filter not in self.__filters:
            self.__filters.append(filter)

    def addFilterSet(self, filterSet):
        if len(filterSet):
            self.__filterSets.append(filterSet)

    def __len__(self):
        count = len(self.__filters)
        for fs in self.__filterSets:
            count += len(fs)
        return count

    def numEnabledFilters(self):
        count = 0
        for f in self.__filters:
            if f.isEnabled:
                count += 1
        for fs in self.__filterSets:
            count += fs.numEnabledFilters()
        return count

    def __hash__(self):
        return hash(
            tuple([hash(self.operator)] + [hash(f) for f in self.__filters] + [hash(fs) for fs in self.__filterSets]))

    def __str__(self):
        return (" %s " % self.operator).join([str(f) for f in self.__filters if f.isEnabled] + \
                                             ["(%s)" % fs for fs in self.__filterSets if fs.numEnabledFilters()])

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return not self == other

    # ------------------------------------------------------------------------------------------------------------------------------
    # PERSISTENT SETTINGS
    # ------------------------------------------------------------------------------------------------------------------------------
    def saveSettings(self, settings):
        settings["operator"] = self.operator

        if self.__filters:
            filters = []
            for filter in self.__filters:
                f = {"field": filter.fieldName,
                     "operator": filter.operator}
                if len(filter.values) == 1:
                    f["value"] = filter.values[0]
                elif len(filter.values) > 1:
                    f["value"] = filter.values
                if not filter.isEnabled:
                    f["enabled"] = False
                filters.append(f)
            settings["filters"] = filters

        if self.__filterSets:
            filterSets = []
            for filterSet in self.__filterSets:
                fs = {}
                filterSet.saveSettings(fs)
                filterSets.append(fs)
            settings["filterSets"] = filterSets

    def loadSettings(self, settings):
        if "operator" in settings:
            if settings["operator"] in [self.OPERATOR_AND, self.OPERATOR_OR]:
                self.operator = settings["operator"]
            else:
                _LOGGER.error(
                    "Invalid filterSet operator '%s'; possible options: %s" % \
                    (settings["operator"], ", ".join([self.OPERATOR_AND, self.OPERATOR_OR]))
                )
                return

        if "filters" in settings and isinstance(settings["filters"], list):
            for f in settings["filters"]:
                try:
                    filter = Filter(f.get("field"), f.get("operator"), f.get("value"), f.get("enabled", True))
                except FilterError as e:
                    _LOGGER.error("Invalid filter: %s" % str(e))
                else:
                    self.addFilter(filter)

        if "filterSets" in settings and isinstance(settings["filterSets"], list):
            for fs in settings["filterSets"]:
                filterSet = FilterSet()
                filterSet.loadSettings(fs)
                self.addFilterSet(filterSet)
