from mongorm.core.dataobject import BaseJinxObject
from jinxicon import icon_paths
import mongorm
import mongoengine


class Job(BaseJinxObject, mongoengine.Document):
    """
    Job base class schema for MongoDB engine.
    """

    _name = "Job"
    meta = {'collection': 'job'}
    INTERFACE_STRING = "job"

    # Required fields
    fullname = mongoengine.StringField(required=True, dispName="Project Full Name")
    state = mongoengine.BooleanField(required=True, dispName="State")
    resolution = mongoengine.ListField(required=True, dispName="Resolution")

    # Optional fields
    description = mongoengine.StringField(dispName="Description")
    tags = mongoengine.ListField(dispName="Tags")
    thumbnail = mongoengine.StringField(dispName="Thumbnail", icon=icon_paths.ICON_IMAGE_SML)

    def children(self, interfaceType):
        super(Job, self).children()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db["stem"], job=self.job)
        stems = db["stem"].all(filt)
        if stems.hasObjects():
            return stems
        else:
            return None

    def siblings(self, includeSelf=False):
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['job'])
        siblings = db['job'].all(filt)
        if not siblings.size() < 2:
            if includeSelf:
                return siblings
            else:
                siblings.remove_object(self)
                return siblings
        else:
            return None


    def shots(self):
        """
        Returns all shot stems associated with this (self) job.
        """
        children = self.children()
        if children:
            for child in children:
                if not child.get("type") == "shot":
                    children.remove_object(child)

        return children

    def sequences(self):
        """
        Returns all sequence stems associated with this (self) job.
        """
        children = self.children()
        if children:
            for child in children:
                if not child.get("type") == "sequence":
                    children.remove_object(child)

        return children

    def assets(self):
        """
        Returns all asset stems associated with this (self) job.
        """
        children = self.children()
        if children:
            for child in children:
                if not child.get("type") == "asset":
                    children.remove_object(child)

        return children


class Stem(BaseJinxObject, mongoengine.Document):
    """
    Stem base class schema for MongoDB engine
    """

    _name = "Stem"
    meta = {'collection': 'stem'}
    INTERFACE_STRING = "stem"

    # Required fields
    directory = mongoengine.StringField(required=True, dispName="Directory")  # eg: 'GARB/asset/character', 'GARB/aa_seq/aa1920'
    type = mongoengine.StringField(required=True, dispName="Type")  # eg: 'sequence', 'shot', 'asset'
    production = mongoengine.BooleanField(required=True, dispName="Active")  # Set false for testing / rnd stems

    # Optional fields
    parent_uuid = mongoengine.StringField(dispName="Parent UUID")
    framerange = mongoengine.ListField(dispName="Frame Range")
    thumbnail = mongoengine.StringField(dispName="Thumbnail", icon=icon_paths.ICON_IMAGE_SML)

    def children(self, interfaceType):
        super(Stem, self).children()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.setInterface(db[interfaceType])
        filt.overrideFilterStrings(
            {"stem_uuid": self.uuid} if interfaceType == "twig" else {"parent_uuid": self.uuid}
        )
        twigs = db[interfaceType].all(filt)
        if twigs.hasObjects():
            return twigs
        else:
            return None

    def parent(self, interfaceType):
        super(Stem, self).parent()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db[interfaceType], uuid=self.parent_uuid)
        job = db[interfaceType].one(filt)

        return job

    def siblings(self, includeSelf=False):
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['stem'], parent_uuid=self.parent_uuid)
        siblings = db['stem'].all(filt)
        if not siblings.size() < 2:
            if includeSelf:
                return siblings
            else:
                siblings.remove_object(self)
                return siblings
        else:
            return None


class Twig(BaseJinxObject, mongoengine.Document):
    """
    Twig base class schema for MongoDB engine
    """

    _name = "Twig"
    meta = {'collection': 'twig'}
    INTERFACE_STRING = "twig"

    # Required fields
    stem_uuid = mongoengine.UUIDField(required=True, dispName="Stem UUID", visible=False)

    # Optional fields
    task = mongoengine.StringField(dispName="Task")
    transfix_map = mongoengine.StringField(dispName="Transfix-Map", visible=False)
    comment = mongoengine.StringField(dispName="Comment", icon=icon_paths.ICON_COMMENT_SML)
    thumbnail = mongoengine.StringField(dispName="Thumbnail", icon=icon_paths.ICON_IMAGE_SML)
    tags = mongoengine.ListField(dispName="Tags")

    def children(self):
        """
        Returns all stalk versions associated with this (self) twig.
        """
        super(Twig, self).children()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['stalk'], twig_uuid=self.uuid)
        stalks = db['stalk'].all(filt)
        if stalks.hasObjects():
            return stalks
        else:
            return None

    def parent(self):
        super(Twig, self).parent()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['stem'], uuid=self.stem_uuid)
        stem = db['stem'].one(filt)

        return stem

    def latest(self):
        """
        Returns the latest version stalk associated with this (self) twig.
        """
        children = self.children()
        if not children:
            return False

        children.sort("version", reverse=True)
        return children[0]

    def siblings(self, includeSelf=True):
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['twig'], stem_uuid=self.stem_uuid)
        siblings = db['twig'].all(filt)
        if not siblings.size() < 2:
            if includeSelf:
                return siblings
            else:
                siblings.remove_object(self)
                return siblings
        else:
            return None


class Stalk(BaseJinxObject, mongoengine.Document):
    """
    Stalk base class schema for MongoDB engine
    """

    _name = 'stalk'
    meta = {'collection': 'stalk'}
    INTERFACE_STRING = "stalk"

    # Required fields
    comment = mongoengine.StringField(required=True, dispName="Comment", icon=icon_paths.ICON_COMMENT_SML)
    status = mongoengine.StringField(required=True, dispName="Status")
    version = mongoengine.IntField(required=True, dispName="Version")
    twig_uuid = mongoengine.UUIDField(required=True, dispName="Twig UUID", visible=False)
    state = mongoengine.StringField(required=True, dispName="State", visible=False)  # 'complete', 'working', 'failed', eg: ip rendering means 'working'

    # Optional fields
    framerange = mongoengine.ListField(dispName="Frame Range")
    thumbnail = mongoengine.StringField(dispName="Thumbnail", icon=icon_paths.ICON_IMAGE_SML)

    def children(self):
        """
        Returns all leaf objects associated with this (self) stalk.
        """
        super(Stalk, self).children()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['leaf'], stalk_uuid=self.uuid)
        leafs = db['leaf'].all(filt)
        if leafs.hasObjects():
            return leafs
        else:
            return None

    def parent(self):
        super(Stalk, self).parent()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['twig'], uuid=self.twig_uuid)
        stem = db['twig'].one(filt)

        return stem

    def siblings(self, includeSelf=True):
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['stalk'], twig_uuid=self.twig_uuid)
        siblings = db['stalk'].all(filt)
        if not siblings.size() < 2:
            if includeSelf:
                return siblings
            else:
                siblings.remove_object(self)
                return siblings
        else:
            return None


class Leaf(BaseJinxObject, mongoengine.Document):
    """
    Leaf base class schema for MongoDB engine
    """

    _name = 'leaf'
    meta = {'collection': 'leaf'}
    INTERFACE_STRING = "leaf"

    # Required fields
    stalk_uuid = mongoengine.UUIDField(required=True, dispName="Stalk UUID", visible=False)
    format = mongoengine.StringField(required=True, dispName="Format")

    # Optional fields
    resolution = mongoengine.ListField(dispName="Resolution")
    framerange = mongoengine.ListField(dispName="Frame Range")
    thumbnail = mongoengine.StringField(dispName="Thumbnail", icon=icon_paths.ICON_IMAGE_SML)

    def parent(self):
        super(Leaf, self).parent()
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['stalk'], uuid=self.stalk_uuid)
        stalk = db['stalk'].one(filt)

        return stalk

    def siblings(self, includeSelf=True):
        db = mongorm.getHandler()
        filt = mongorm.getFilter()
        filt.search(db['leaf'], stalk_uuid=self.stalk_uuid)
        siblings = db['leaf'].all(filt)
        if not siblings.size() < 2:
            if includeSelf:
                return siblings
            else:
                siblings.remove_object(self)
                return siblings
        else:
            return None


class Seed(BaseJinxObject, mongoengine.Document):
    """
    Seed base class schema for MongoDB engine
    """

    _name = 'seed'
    meta = {'collection': 'seed'}
    INTERFACE_STRING = "seed"

    # Required fields
    pod_stalk_uuid = mongoengine.UUIDField(required=True, dispName="Pod Stalk UUID")
    seed_stalk_uuid = mongoengine.UUIDField(required=True, dispName="Seed Stalk UUID")