from mongorm.core.datainterface import DataInterface
from requests import get
import mongoengine as me
import os


class DbHandler(object):
    _DATABASE = os.getenv('MONGO_DATABASE')
    _PORT = int(os.getenv('MONGO_PORT'))
    _THIS_EXT_IP = get("https://api.ipify.org").text
    _MONGO_EXT_IP = os.getenv('MONGO_EXT_IP')
    _MONGO_INT_IP = os.getenv('MONGO_INT_IP')

    if _THIS_EXT_IP == _MONGO_EXT_IP:
        _HOST = _MONGO_INT_IP
    else:
        _HOST = _MONGO_EXT_IP

    def __init__(self):
        me.connect(db=self._DATABASE, host=self._HOST, port=self._PORT)

    def __getitem__(self, item):
        assert item in self.list_interface_names(), "Invalid interface: {}".format(item)
        return DataInterface(item)

    def list_interface_names(self):
        db = me.connection.get_db()
        return db.list_collection_names()

    def getDataInterface(self, dataInterface):
        return self.__getitem__(dataInterface)
