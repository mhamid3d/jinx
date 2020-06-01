from .stem import Stem
import mongoengine
import uuid


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
    label = mongoengine.StringField(required=True)
    fullname = mongoengine.StringField(required=True)
    created = mongoengine.DateTimeField(required=True)
    modified = mongoengine.DateTimeField(required=True)
    job = mongoengine.StringField(required=True)
    state = mongoengine.BooleanField(required=True)
    path = mongoengine.StringField(required=True)
    resolution = mongoengine.ListField(required=True)
    created_by = mongoengine.StringField(required=True)

    # Optional fields
    description = mongoengine.StringField()
    tags = mongoengine.ListField()

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
