from mongoengine.errors import MultipleObjectsReturned


class QuerySuperposition(object):
    def __init__(self, query_result=None):
        self.query_result = query_result

    def one(self):
        if self.query_result:
            try:
                assert len(self.query_result) == 1
                return self.query_result[0]
            except AssertionError:
                raise MultipleObjectsReturned
        else:
            return None

    def all(self):
        return self.query_result