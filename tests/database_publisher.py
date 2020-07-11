from qtpy import QtWidgets, QtGui, QtCore
from mongorm import getHandler, getFilter, interfaces
import qdarkstyle
import datetime
import logging
import sys
import os

LOGGER = logging.getLogger('DatabsePublisher')
logging.basicConfig()
LOGGER.setLevel(logging.INFO)


class BaseJinxWidget(QtWidgets.QWidget):
    def __init__(self, schema=None):
        super(BaseJinxWidget, self).__init__()
        self.mainLayout = QtWidgets.QFormLayout(self)
        self.setLayout(self.mainLayout)
        self.schema = schema()
        self.schema_cls = schema
        self.fields = {k: v for k, v in self.schema._fields.iteritems()}
        self.setup_fields()

    def req_wrap(self, field, name):
        req_template = """
            <html>
                <head/>
                    <body>
                        <p>
                            {}<span style=" color:#ff0000;">*</span>
                            <span>: </span>
                        </p>
                    </body>
            </html>
            """
        if field.required:
            return req_template.format(name)
        else:
            return "{}: ".format(name)

    def setup_fields(self):
        self.setup_id(self.fields['_id'])
        self.setup_uuid(self.fields['uuid'])
        self.setup_path(self.fields['path'])
        self.setup_label(self.fields['label'])
        self.setup_created(self.fields['created'])
        self.setup_modified(self.fields['modified'])
        self.setup_job(self.fields['job'])
        self.setup_created_by(self.fields['created_by'])
        self.generate_id()

    def generate_id(self):
        self.schema.generate_id()
        self.idWidget.setText(self.schema.uuid)
        self.uuidWidget.setText(self.idWidget.text())

    def setup_id(self, field):
        self._idWidget = QtWidgets.QWidget()
        self._idLayout = QtWidgets.QHBoxLayout(self._idWidget)
        self._idLayout.setContentsMargins(0, 0, 0, 0)
        self._idWidget.setContentsMargins(0, 0, 0, 0)
        self._idWidget.setLayout(self._idLayout)
        self.idWidget = QtWidgets.QLineEdit()
        self.idWidget.setReadOnly(True)
        self.generateIdButton = QtWidgets.QPushButton('Generate')
        self.generateIdButton.clicked.connect(self.generate_id)
        self._idLayout.addWidget(self.idWidget)
        self._idLayout.addWidget(self.generateIdButton)
        self.mainLayout.addRow(self.req_wrap(field, '_id'), self._idWidget)

    def setup_uuid(self, field):
        self.uuidWidget = QtWidgets.QLineEdit()
        self.uuidWidget.setReadOnly(True)
        self.mainLayout.addRow(self.req_wrap(field, 'UUID'), self.uuidWidget)

    def setup_path(self, field):
        self.pathWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Path'), self.pathWidget)

    def setup_label(self, field):
        self.labelWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Label'), self.labelWidget)

    def setup_created(self, field):
        self.createdWidget = QtWidgets.QDateTimeEdit()
        self.createdWidget.setDateTime(datetime.datetime.now())
        # self.mainLayout.addRow(self.req_wrap(field, 'Created'), self.createdWidget)

    def setup_modified(self, field):
        self.modifiedWidget = QtWidgets.QDateTimeEdit()
        self.modifiedWidget.setDateTime(datetime.datetime.now())
        # self.mainLayout.addRow(self.req_wrap(field, 'Modified'), self.modifiedWidget)

    def setup_job(self, field):
        self.jobWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Job'), self.jobWidget)

    def setup_created_by(self, field):
        self.createdByWidget = QtWidgets.QLineEdit()
        self.createdByWidget.setReadOnly(True)
        self.createdByWidget.setText(os.getenv('USER'))
        self.mainLayout.addRow(self.req_wrap(field, 'Created By'), self.createdByWidget)

    def pre_publish_checks(self, data, field_class):
        if not data and not isinstance(data, bool) and field_class.required:
            raise ValueError, "Field is required: [{}]".format(field_class.__dict__['db_field'])
        elif not data and not field_class.required:
            return
        else:
            LOGGER.info("Publishing field [{}]: {}".format(field_class.__dict__['db_field'], data))
            exec('self.schema.{} = data'.format(field_class.__dict__['db_field']))
            return

    def publish(self):
        self.pre_publish_checks(self.pathWidget.text(), self.fields['path'])
        self.pre_publish_checks(self.labelWidget.text(), self.fields['label'])
        self.pre_publish_checks(datetime.datetime.now(), self.fields['created'])
        self.pre_publish_checks(datetime.datetime.now(), self.fields['modified'])
        self.pre_publish_checks(self.jobWidget.text(), self.fields['job'])
        self.pre_publish_checks(self.createdByWidget.text(), self.fields['created_by'])


class BaseJobWidget(BaseJinxWidget):
    def __init__(self, schema=None):
        super(BaseJobWidget, self).__init__(schema)

    def setup_fields(self):
        super(BaseJobWidget, self).setup_fields()
        self.setup_fullname(self.fields['fullname'])
        self.setup_state(self.fields['state'])
        self.setup_resolution(self.fields['resolution'])
        self.setup_description(self.fields['description'])
        self.setup_tags(self.fields['tags'])

    def setup_fullname(self, field):
        self.fullnameWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Fullname'), self.fullnameWidget)

    def setup_state(self, field):
        self.stateWidget = QtWidgets.QCheckBox()
        self.stateWidget.setChecked(True)
        self.mainLayout.addRow(self.req_wrap(field, 'State'), self.stateWidget)

    def setup_resolution(self, field):
        self.resolutionWidget = QtWidgets.QWidget()
        self.resolutionLayout = QtWidgets.QHBoxLayout(self.resolutionWidget)
        self.resolutionWidget.setLayout(self.resolutionLayout)

        self.resolutionWidget.setContentsMargins(0, 0, 0, 0)
        self.resolutionLayout.setContentsMargins(0, 0, 0, 0)
        self.resolutionLayout.setAlignment(QtCore.Qt.AlignLeft)

        self.hResolutionWidget = QtWidgets.QSpinBox()
        self.vResolutionWidget = QtWidgets.QSpinBox()

        self.hResolutionWidget.setMaximum(500000)
        self.vResolutionWidget.setMaximum(500000)
        self.hResolutionWidget.setValue(2560)
        self.vResolutionWidget.setValue(1440)

        self.resolutionLayout.addWidget(self.hResolutionWidget)
        self.resolutionLayout.addWidget(self.vResolutionWidget)

        self.mainLayout.addRow(self.req_wrap(field, 'Resolution'), self.resolutionWidget)

    def setup_description(self, field):
        self.descriptionWidget = QtWidgets.QTextEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Description'), self.descriptionWidget)

    def setup_tags(self, field):
        self.tagsWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Tags (Separated by commas)'), self.tagsWidget)

    def publish(self):
        super(BaseJobWidget, self).publish()
        self.pre_publish_checks(self.fullnameWidget.text(), self.fields['fullname'])
        self.pre_publish_checks(self.stateWidget.isChecked(), self.fields['state'])
        self.pre_publish_checks([self.hResolutionWidget.value(), self.vResolutionWidget.value()], self.fields['resolution'])
        self.pre_publish_checks(self.descriptionWidget.toPlainText(), self.fields['description'])
        self.pre_publish_checks(self.tagsWidget.text().strip().split(','), self.fields['tags'])


class BaseStemWidget(BaseJinxWidget):
    def __init__(self, schema=None):
        super(BaseStemWidget, self).__init__(schema)

    def setup_fields(self):
        super(BaseStemWidget, self).setup_fields()
        self.setup_directory(self.fields['directory'])
        self.setup_type(self.fields['type'])
        self.setup_production(self.fields['production'])
        self.setup_parent_uuid(self.fields['parent_uuid'])
        self.setup_framerange(self.fields['framerange'])
        self.setup_thumbnail(self.fields['thumbnail'])

    def setup_directory(self, field):
        self.directoryWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Directory'), self.directoryWidget)

    def setup_type(self, field):
        self.typeWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Type'), self.typeWidget)

    def setup_production(self, field):
        self.productionWidget = QtWidgets.QCheckBox()
        self.productionWidget.setChecked(True)
        self.mainLayout.addRow(self.req_wrap(field, 'Production'), self.productionWidget)

    def setup_parent_uuid(self, field):
        self.parentUuidWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Parent UUID'), self.parentUuidWidget)

    def setup_framerange(self, field):
        MAX = 999999999
        MIN = MAX * -1
        self._framerangeWidget = QtWidgets.QWidget()
        self._framerangeLayout = QtWidgets.QHBoxLayout(self._framerangeWidget)
        self._framerangeLayout.setAlignment(QtCore.Qt.AlignLeft)
        self._framerangeWidget.setLayout(self._framerangeLayout)
        self.beginFrameWidget = QtWidgets.QSpinBox()
        self.endFrameWidget = QtWidgets.QSpinBox()
        self.beginFrameWidget.setMinimum(MIN)
        self.endFrameWidget.setMinimum(MIN)
        self.beginFrameWidget.setMaximum(MAX)
        self.endFrameWidget.setMaximum(MAX)
        self.beginFrameWidget.setValue(1001)
        self.endFrameWidget.setValue(1099)
        self._framerangeLayout.addWidget(self.beginFrameWidget)
        self._framerangeLayout.addWidget(self.endFrameWidget)
        self._framerangeLayout.setContentsMargins(0, 0, 0, 0)
        self._framerangeWidget.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addRow(self.req_wrap(field, 'Frame Range'), self._framerangeWidget)

    def setup_thumbnail(self, field):
        self.thumbnailWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Thumbnail'), self.thumbnailWidget)

    def publish(self):
        super(BaseStemWidget, self).publish()
        self.pre_publish_checks(self.directoryWidget.text(), self.fields['directory'])
        self.pre_publish_checks(self.typeWidget.text(), self.fields['type'])
        self.pre_publish_checks(self.productionWidget.isChecked(), self.fields['production'])
        self.pre_publish_checks(self.parentUuidWidget.text(), self.fields['parent_uuid'])
        self.pre_publish_checks([self.beginFrameWidget.value(), self.endFrameWidget.value()], self.fields['framerange'])
        self.pre_publish_checks(self.thumbnailWidget.text(), self.fields['thumbnail'])


class BaseTwigWidget(BaseJinxWidget):
    def __init__(self, *args, **kwargs):
        super(BaseTwigWidget, self).__init__(*args, **kwargs)

    def setup_fields(self):
        super(BaseTwigWidget, self).setup_fields()
        self.setup_stem_uuid(self.fields['stem_uuid'])
        self.setup_task(self.fields['task'])
        self.setup_transfix_map(self.fields['transfix_map'])
        self.setup_comment(self.fields['comment'])
        self.setup_thumbnail(self.fields['thumbnail'])
        self.setup_tags(self.fields['tags'])

    def setup_stem_uuid(self, field):
        self.stemUuidWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Stem UUID'), self.stemUuidWidget)

    def setup_task(self, field):
        self.taskWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Task'), self.taskWidget)

    def setup_transfix_map(self, field):
        self.transfixMapWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Transfix Map'), self.transfixMapWidget)

    def setup_comment(self, field):
        self.commentWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Comment'), self.commentWidget)

    def setup_thumbnail(self, field):
        self.thumbnailWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Thumbnail'), self.thumbnailWidget)

    def setup_tags(self, field):
        self.tagsWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Tags (Separated by commas)'), self.tagsWidget)

    def publish(self):
        super(BaseTwigWidget, self).publish()
        self.pre_publish_checks(self.stemUuidWidget.text(), self.fields['stem_uuid'])
        self.pre_publish_checks(self.taskWidget.text(), self.fields['task'])
        self.pre_publish_checks(self.transfixMapWidget.text(), self.fields['transfix_map'])
        self.pre_publish_checks(self.commentWidget.text(), self.fields['comment'])
        self.pre_publish_checks(self.thumbnailWidget.text(), self.fields['thumbnail'])
        self.pre_publish_checks(self.tagsWidget.text().strip().split(','), self.fields['tags'])


class BaseStalkWidget(BaseJinxWidget):
    def __init__(self, *args, **kwargs):
        super(BaseStalkWidget, self).__init__(*args, **kwargs)

    def setup_fields(self):
        super(BaseStalkWidget, self).setup_fields()
        self.setup_comment(self.fields['comment'])
        self.setup_status(self.fields['status'])
        self.setup_version(self.fields['version'])
        self.setup_twig_uuid(self.fields['twig_uuid'])
        self.setup_state(self.fields['state'])
        self.setup_framerange(self.fields['framerange'])
        self.setup_thumbnail(self.fields['thumbnail'])

    def setup_comment(self, field):
        self.commentWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Comment'), self.commentWidget)

    def setup_status(self, field):
        self.statusWidget = QtWidgets.QComboBox()
        self.statusWidget.addItems(['Declined', 'In Progress', 'Available', 'Approved'])
        self.statusWidget.setCurrentIndex(1)
        self.mainLayout.addRow(self.req_wrap(field, 'Status'), self.statusWidget)

    def setup_version(self, field):
        self.versionWidget = QtWidgets.QSpinBox()
        self.versionWidget.setMaximum(9999999)
        self.versionWidget.setMinimum(1)
        self.mainLayout.addRow(self.req_wrap(field, 'Version'), self.versionWidget)

    def setup_twig_uuid(self, field):
        self.twigUuidWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Twig UUID'), self.twigUuidWidget)

    def setup_state(self, field):
        self.stateWidget = QtWidgets.QComboBox()
        self.stateWidget.addItems(['Complete', 'Working', 'Failed'])
        self.stateWidget.setCurrentIndex(0)
        self.mainLayout.addRow(self.req_wrap(field, 'State'), self.stateWidget)

    def setup_framerange(self, field):
        MAX = 999999999
        MIN = MAX * -1
        self._framerangeWidget = QtWidgets.QWidget()
        self._framerangeLayout = QtWidgets.QHBoxLayout(self._framerangeWidget)
        self._framerangeWidget.setLayout(self._framerangeLayout)
        self._framerangeLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.beginFrameWidget = QtWidgets.QSpinBox()
        self.endFrameWidget = QtWidgets.QSpinBox()
        self.beginFrameWidget.setMinimum(MIN)
        self.endFrameWidget.setMinimum(MIN)
        self.beginFrameWidget.setMaximum(MAX)
        self.endFrameWidget.setMaximum(MAX)
        self.beginFrameWidget.setValue(1001)
        self.endFrameWidget.setValue(1099)
        self._framerangeLayout.addWidget(self.beginFrameWidget)
        self._framerangeLayout.addWidget(self.endFrameWidget)
        self._framerangeLayout.setContentsMargins(0, 0, 0, 0)
        self._framerangeWidget.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addRow(self.req_wrap(field, 'Frame Range'), self._framerangeWidget)

    def setup_thumbnail(self, field):
        self.thumbnailWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Thumbnail'), self.thumbnailWidget)

    def publish(self):
        super(BaseStalkWidget, self).publish()
        self.pre_publish_checks(self.commentWidget.text(), self.fields['comment'])
        self.pre_publish_checks(self.statusWidget.currentText(), self.fields['status'])
        self.pre_publish_checks(self.versionWidget.value(), self.fields['version'])
        self.pre_publish_checks(self.twigUuidWidget.text(), self.fields['twig_uuid'])
        self.pre_publish_checks(self.stateWidget.currentText(), self.fields['state'])
        self.pre_publish_checks([self.beginFrameWidget.value(), self.endFrameWidget.value()], self.fields['framerange'])
        self.pre_publish_checks(self.thumbnailWidget.text(), self.fields['thumbnail'])


class BaseLeafWidget(BaseJinxWidget):
    def __init__(self, *args, **kwargs):
        super(BaseLeafWidget, self).__init__(*args, **kwargs)

    def setup_fields(self):
        super(BaseLeafWidget, self).setup_fields()
        self.setup_stalk_uuid(self.fields['stalk_uuid'])
        self.setup_format(self.fields['format'])
        self.setup_resolution(self.fields['resolution'])
        self.setup_framerange(self.fields['framerange'])
        self.setup_thumbnail(self.fields['thumbnail'])

    def setup_stalk_uuid(self, field):
        self.stalkUuidWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Stalk UUID'), self.stalkUuidWidget)

    def setup_format(self, field):
        self.formatWidget = QtWidgets.QLineEdit()
        self.formatWidget.setMaximumWidth(50)
        self.mainLayout.addRow(self.req_wrap(field, 'Format'), self.formatWidget)

    def setup_resolution(self, field):
        self.resolutionWidget = QtWidgets.QWidget()
        self.resolutionLayout = QtWidgets.QHBoxLayout(self.resolutionWidget)
        self.resolutionWidget.setLayout(self.resolutionLayout)

        self.resolutionWidget.setContentsMargins(0, 0, 0, 0)
        self.resolutionLayout.setContentsMargins(0, 0, 0, 0)
        self.resolutionLayout.setAlignment(QtCore.Qt.AlignLeft)

        self.hResolutionWidget = QtWidgets.QSpinBox()
        self.vResolutionWidget = QtWidgets.QSpinBox()

        self.hResolutionWidget.setMaximum(500000)
        self.vResolutionWidget.setMaximum(500000)
        self.hResolutionWidget.setValue(2560)
        self.vResolutionWidget.setValue(1440)

        self.resolutionLayout.addWidget(self.hResolutionWidget)
        self.resolutionLayout.addWidget(self.vResolutionWidget)

        self.mainLayout.addRow(self.req_wrap(field, 'Resolution'), self.resolutionWidget)

    def setup_framerange(self, field):
        MAX = 999999999
        MIN = MAX * -1
        self._framerangeWidget = QtWidgets.QWidget()
        self._framerangeLayout = QtWidgets.QHBoxLayout(self._framerangeWidget)
        self._framerangeWidget.setLayout(self._framerangeLayout)
        self._framerangeLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.beginFrameWidget = QtWidgets.QSpinBox()
        self.endFrameWidget = QtWidgets.QSpinBox()
        self.beginFrameWidget.setMinimum(MIN)
        self.endFrameWidget.setMinimum(MIN)
        self.beginFrameWidget.setMaximum(MAX)
        self.endFrameWidget.setMaximum(MAX)
        self.beginFrameWidget.setValue(1001)
        self.endFrameWidget.setValue(1099)
        self._framerangeLayout.addWidget(self.beginFrameWidget)
        self._framerangeLayout.addWidget(self.endFrameWidget)
        self._framerangeLayout.setContentsMargins(0, 0, 0, 0)
        self._framerangeWidget.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addRow(self.req_wrap(field, 'Frame Range'), self._framerangeWidget)

    def setup_thumbnail(self, field):
        self.thumbnailWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Thumbnail'), self.thumbnailWidget)

    def publish(self):
        super(BaseLeafWidget, self).publish()
        self.pre_publish_checks(self.stalkUuidWidget.text(), self.fields['stalk_uuid'])
        self.pre_publish_checks(self.formatWidget.text(), self.fields['format'])
        self.pre_publish_checks([self.hResolutionWidget.value(), self.vResolutionWidget.value()], self.fields['resolution'])
        self.pre_publish_checks([self.beginFrameWidget.value(), self.endFrameWidget.value()], self.fields['framerange'])
        self.pre_publish_checks(self.thumbnailWidget.text(), self.fields['thumbnail'])


class BaseSeedWidget(BaseJinxWidget):
    def __init__(self, *args, **kwargs):
        super(BaseSeedWidget, self).__init__(*args, **kwargs)

    def setup_fields(self):
        super(BaseSeedWidget, self).setup_fields()
        self.setup_pod_stalk_uuid(self.fields['pod_stalk_uuid'])
        self.setup_seed_stalk_uuid(self.fields['seed_stalk_uuid'])

    def setup_pod_stalk_uuid(self, field):
        self.podStalkUuidWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Pod Stalk UUID'), self.podStalkUuidWidget)

    def setup_seed_stalk_uuid(self, field):
        self.seedStalkUuidWidget = QtWidgets.QLineEdit()
        self.mainLayout.addRow(self.req_wrap(field, 'Seed Stalk UUID'), self.seedStalkUuidWidget)

    def publish(self):
        super(BaseSeedWidget, self).publish()
        self.pre_publish_checks(self.podStalkUuidWidget.text(), self.fields['pod_stalk_uuid'])
        self.pre_publish_checks(self.seedStalkUuidWidget.text(), self.fields['seed_stalk_uuid'])


class DatabasePublisher(QtWidgets.QWidget):
    def __init__(self):
        super(DatabasePublisher, self).__init__()
        self.setWindowTitle('Jinx Database Publisher')
        self.resize(900, 500)
        self.setWindowIcon(QtGui.QIcon('/home/mhamid/Pictures/jinx-pipe-icon.png'))
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.mainLayout)
        self.schemasTabWidget = QtWidgets.QTabWidget()
        self.publishLayout = QtWidgets.QHBoxLayout()
        self.publishButton = QtWidgets.QPushButton('Publish')
        self.publishButton.setFixedSize(200, 42)
        self.publishAllButton = QtWidgets.QPushButton('Publish All')
        self.publishAllButton.setFixedSize(200, 42)
        self.mainLayout.addWidget(self.schemasTabWidget)
        self.mainLayout.addLayout(self.publishLayout)
        self.publishLayout.setAlignment(QtCore.Qt.AlignRight)
        self.publishLayout.addWidget(self.publishButton, alignment=QtCore.Qt.AlignRight)
        self.publishLayout.addWidget(self.publishAllButton, alignment=QtCore.Qt.AlignRight)
        self.setup_tabs()
        self.publishButton.clicked.connect(self.publish)
        self.publishAllButton.clicked.connect(lambda: self.publish(all=True))
        self.dbHandler = getHandler()
        self.allTabs = [self.schemasTabWidget.widget(i) for i in range(self.schemasTabWidget.count())]

    def setup_tabs(self):
        self.schemasTabWidget.addTab(BaseJobWidget(schema=interfaces.Job), 'Job')
        self.schemasTabWidget.addTab(BaseStemWidget(schema=interfaces.Stem), 'Stem')
        self.schemasTabWidget.addTab(BaseTwigWidget(schema=interfaces.Twig), 'Twig')
        self.schemasTabWidget.addTab(BaseStalkWidget(schema=interfaces.Stalk), 'Stalk')
        self.schemasTabWidget.addTab(BaseLeafWidget(schema=interfaces.Leaf), 'Leaf')
        self.schemasTabWidget.addTab(BaseSeedWidget(schema=interfaces.Seed), 'Seed')

    def publish(self, all=False):
        publish_widget = self.allTabs if all else [self.schemasTabWidget.currentWidget()]
        for schema_widget in publish_widget:
            schema_widget.publish()
            schema_widget.schema.save()
            schema_widget.schema = schema_widget.schema_cls()
            schema_widget.generate_id()


def run_cli():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    font = QtGui.QFont()
    win = DatabasePublisher()
    win.show()
    sys.exit(app.exec_())


def run_maya():
    win = DatabasePublisher()
    win.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    win.show()


run_cli()
