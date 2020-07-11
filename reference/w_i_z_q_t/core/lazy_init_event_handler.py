"""Custom event handler to utilise the custom :meth:`~QtCore.QObject.displayInitEvent`,
which is called the first time a QWidget is displayed.
"""
# PyQt imports
from qtswitch import QtCore


#########################################################################################
#	LazyInitEventHandler
#########################################################################################
class LazyInitEventHandler(QtCore.QObject):
    """
    """
    PROPNAME_DISPLAYED = "widgetHasBeenDisplayed"

    def eventFilter(self, obj, event):
        """
        """
        # respond only to internal (non-spontaneous) show events
        # these occur just before the view is actually shown
        if event.type() == event.Show and not event.spontaneous():
            if not obj.property(self.PROPNAME_DISPLAYED):
                # first time displayed
                obj.displayInitEvent(event)
                obj.setProperty(self.PROPNAME_DISPLAYED, True)
            obj.displayEvent(event)
            return True
        return False
