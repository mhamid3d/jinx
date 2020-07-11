"""The wizqt package is a library of general purpose Qt widgets for use within the pipeline."""

# Standard imports
import os
import sys
import types

# DNeg imports
import qtswitch
import apitrack.v1

version_filepath = os.path.join(__path__[0], "VERSION")
with open(version_filepath) as version_file:
    __version__ = version_file.read().strip()

# Set up apitracking for this package
_APITRACKER = apitrack.v1.Client(__name__, __version__)
_APITRACKER.track_import(-1)

# Local imports
from . import common, exc
from .exc import WizQtError


class _LazyCommonImportHandler(types.ModuleType):
    """This handler is used to issue a dndeprecate warning anytime one of the
    listed attributes is accessed. This is a way of partially wrapping some of
    the symbols in this module as deprecated, but not all.
    """
    # Caching the dir(common) call for the attributes we care about
    # because calling dir(common) and startswith("_") over and over is
    # really expensively slow.
    #
    COMMON_DIR_CACHE = [attr for attr in dir(common) if not attr.startswith("_")]

    def __getattr__(self, attribute):
        if attribute in self.COMMON_DIR_CACHE:
            return getattr(common, attribute)
        return getattr(_old_module, attribute)

    def __dir__(self):
        return dir(_old_module) + self.COMMON_DIR_CACHE


# Please don't garbage collect me :)
_old_module = sys.modules[__name__]

_new_module = sys.modules[__name__] = _LazyCommonImportHandler(__name__)
_new_module.__dict__.update({
    "__file__": __file__,
    "__package__": __name__,
    "__path__": __path__,
    "__doc__": __doc__,
    "__all__": [attr for attr in dir(_new_module) if not attr.startswith("_")]
})
