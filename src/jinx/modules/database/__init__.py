import os
import logging
from jinx.modules.database.base.db_handler import DbHandler

LOGGER = logging.getLogger(__name__)
logging.basicConfig()


def getHandler():
    return DbHandler()
