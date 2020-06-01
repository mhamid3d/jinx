from jinx.modules.database.base.query_superposition import QuerySuperposition
from jinx.modules.database import schemas
from mongoengine.errors import MultipleObjectsReturned
import mongoengine as me
from requests import get
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

    def job(self, **kwargs):
        result = schemas.Job.objects(**kwargs)
        return QuerySuperposition(query_result=result)

    def stem(self, **kwargs):
        result = schemas.Stem.objects(**kwargs)
        return QuerySuperposition(query_result=result)

    def twig(self, **kwargs):
        result = schemas.Twig.objects(**kwargs)
        return QuerySuperposition(query_result=result)

    def stalk(self, **kwargs):
        result = schemas.Stalk.objects(**kwargs)
        return QuerySuperposition(query_result=result)

    def leaf(self, **kwargs):
        result = schemas.Leaf.objects(**kwargs)
        return QuerySuperposition(query_result=result)

    def seed(self, **kwargs):
        result = schemas.Seed.objects(**kwargs)
        return QuerySuperposition(query_result=result)

    def get_from_uuid(self, uuid):
        result = []
        for query_type in [self.job, self.stem, self.twig, self.stalk, self.leaf, self.seed]:
            for object in query_type(uuid=uuid).all():
                result.append(object)
        if result:
            try:
                assert len(result) == 1
                return result[0]
            except AssertionError:
                raise MultipleObjectsReturned
        else:
            return None
