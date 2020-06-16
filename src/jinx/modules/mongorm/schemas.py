import mongoengine
import uuid


class BaseJinxObject(object):
    """
    Site base class schema for MongoDB engine.
    """

    # Required fields
    _id = mongoengine.UUIDField(required=True, primary_key=True)
    uuid = mongoengine.StringField(required=True)
    path = mongoengine.StringField(required=True)
    label = mongoengine.StringField(required=True)
    created = mongoengine.DateTimeField(required=True)
    modified = mongoengine.DateTimeField(required=True)
    job = mongoengine.StringField(required=True)
    created_by = mongoengine.StringField(required=True)

    def generate_id(self):
        self._id = uuid.uuid4()
        self.uuid = self._id.__str__()
        return

    def get_type(self):
        return str(self.__class__.__name__)


class Job(mongoengine.Document):
    """
    Job base class schema for MongoDB engine.
    """
    meta = {
        'collection': 'job'
    }

    # Required fields
    _id = mongoengine.UUIDField(required=True, primary_key=True)
    uuid = mongoengine.StringField(required=True)
    path = mongoengine.StringField(required=True)
    label = mongoengine.StringField(required=True)
    created = mongoengine.DateTimeField(required=True)
    modified = mongoengine.DateTimeField(required=True)
    job = mongoengine.StringField(required=True)
    created_by = mongoengine.StringField(required=True)
    fullname = mongoengine.StringField(required=True)
    state = mongoengine.BooleanField(required=True)
    resolution = mongoengine.ListField(required=True)

    # Optional fields
    description = mongoengine.StringField()
    tags = mongoengine.ListField()
    thumbnail = mongoengine.StringField()

    def __str__(self):
        return "Job Object: {}".format(self.label)

    def generate_id(self):
        """
        Generates a random uuid and sets it to the _id and uuid fields.
        """
        self._id = uuid.uuid4()
        self.uuid = self._id.__str__()
        return

    def get_type(self):
        return str(self.__class__.__name__)

    def shots(self):
        """
        Returns all shot stems associated with this (self) job.
        """
        return Stem.objects(job=self.job, type='shot')

    def sequences(self):
        """
        Returns all sequence stems associated with this (self) job.
        """
        return Stem.objects(job=self.job, type='sequence')

    def assets(self):
        """
        Returns all asset stems associated with this (self) job.
        """
        return Stem.objects(job=self.job, type='asset')


class Stem(BaseJinxObject, mongoengine.Document):
    """
    Stem base class schema for MongoDB engine
    """

    meta = {
        'collection': 'stem'
    }

    # Required fields
    directory = mongoengine.StringField(required=True)    # eg: 'GARB/asset/character', 'GARB/aa_seq/aa1920'
    type = mongoengine.StringField(required=True)       # eg: 'sequence', 'shot', 'asset'
    production = mongoengine.BooleanField(required=True) # Set false for testing / rnd stems

    # Optional fields
    parent_uuid = mongoengine.StringField()
    framerange = mongoengine.ListField()
    thumbnail = mongoengine.StringField()


class Twig(BaseJinxObject, mongoengine.Document):
    """
    Twig base class schema for MongoDB engine
    """

    meta = {
        'collection': 'twig'
    }

    # Required fields
    stem_uuid = mongoengine.UUIDField(required=True)

    # Optional fields
    task = mongoengine.StringField()
    transfix_map = mongoengine.StringField()
    comment = mongoengine.StringField()
    thumbnail = mongoengine.StringField()
    tags = mongoengine.ListField()

    def stalks(self):
        """
        Returns all stalk versions associated with this (self) twig.
        """
        return Stalk.objects(twig_uuid=self.uuid)

    def latest(self):
        """
        Returns the latest version stalk associated with this (self) twig.
        """
        stalks = self.stalks()
        version_dict = []
        for idx, stalk in enumerate(stalks):
            version_dict.append({'idx': idx, 'version': stalk.version})
        version_dict.sort(key=lambda i: i['version'])
        return stalks[version_dict[-1]['idx']]


class Stalk(BaseJinxObject, mongoengine.Document):
    """
    Stalk base class schema for MongoDB engine
    """

    meta = {
        'collection': 'stalk'
    }

    # Required fields
    comment = mongoengine.StringField(required=True)
    status = mongoengine.StringField(required=True)
    version = mongoengine.IntField(required=True)
    twig_uuid = mongoengine.UUIDField(required=True)
    state = mongoengine.StringField(required=True)  # 'complete', 'working', 'failed', eg: ip rendering means 'working'

    # Optional fields
    framerange = mongoengine.ListField()
    thumbnail = mongoengine.StringField()

    def leafs(self):
        """
        Returns all leaf objects associated with this (self) stalk.
        """
        return Leaf.objects(stalk_uuid=self.uuid)


class Leaf(BaseJinxObject, mongoengine.Document):
    """
    Leaf base class schema for MongoDB engine
    """

    meta = {
        'collection': 'leaf'
    }

    # Required fields
    stalk_uuid = mongoengine.UUIDField(required=True)
    format = mongoengine.StringField(required=True)

    # Optional fields
    resolution = mongoengine.ListField()
    framerange = mongoengine.ListField()
    thumbnail = mongoengine.StringField()


class Seed(BaseJinxObject, mongoengine.Document):
    """
    Seed base class schema for MongoDB engine
    """

    meta = {
        'collection': 'seed'
    }

    # Required fields
    pod_stalk_uuid = mongoengine.UUIDField(required=True)
    seed_stalk_uuid = mongoengine.UUIDField(required=True)