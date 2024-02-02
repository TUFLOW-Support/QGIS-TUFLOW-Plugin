import re
from PyQt5.QtCore import QObject, pyqtSignal
from qgis.core import QgsVectorLayer, NULL, QgsProject, QgsFeature, QgsField
from datetime import datetime


MAX_FIELD_LENGTH_PRE_2020_01_AB = 12
MAX_FIELD_LENGTH = 36  # maximum id length - since 2020-01-AB
MAX_ITERATIONS = 1000  # used to cap 'while' loops


class FeatKey:

    def __init__(self, lyr, feat):
        self.feat = feat
        self.lyr = lyr
        self.index = datetime.timestamp(datetime.now())
        self.id = str(self.lyr.id()) + str(self.feat.id()) + str(self.index)

    def __hash__(self):
        return object.__hash__(self.id)


class DuplicateRule:
    """
    Rule for determining how to deal with duplicate channel ids and how
    to modify the name.
    """

    def __init__(self, **kwargs):
        self.append_letter = kwargs['append_letter'] if 'append_letter' in kwargs else False
        self.append_number = kwargs['append_number'] if 'append_number' in kwargs else False
        self.delimiter = kwargs['delimiter'] if 'delimiter' in kwargs else '_'
        self.max_id_length = MAX_FIELD_LENGTH

        if 'duplicate_rule' in kwargs and isinstance(kwargs['duplicate_rule'], DuplicateRule):
            rule = kwargs['duplicate_rule']
            self.append_letter = rule.append_letter
            self.append_number = rule.append_number
            self.delimiter = rule.delimiter
            self.max_id_length = rule.max_id_length

        if not self.append_letter and not self.append_number:
            self.append_letter = True

    def __generate_suffix__(self, suffix, suffix_count):
        """Generate list of suffixes to use. Will append to the existing list and return the new count."""
        if self.append_letter:
            j = int(suffix_count / 26)
            if j > 0:
                suffix2 = ['{0}{1}'.format(suffix[j-1], chr(x)) for x in range(97, 123)]
            else:
                suffix2 = [chr(x) for x in range(97, 123)]
            suffix.extend(suffix2)
            return suffix_count + 26
        elif self.append_number:
            j = int(suffix_count / 100) + 1
            jstart = max(0, 100*(j-1)) + 1
            jend = j*100 + 1
            suffix2 = ['{0}{1}'.format(self.delimiter, x) for x in range(jstart, jend)]
            suffix.extend(suffix2)
            return suffix_count + 100

    def unique_name(self, existing_name, used_names):
        """Create a new name based on the defined rules."""
        suffix_count = 0
        suffix = []

        new_name = existing_name
        i = 0
        while new_name in used_names:
            if i + 1 > suffix_count:
                suffix_count = self.__generate_suffix__(suffix, suffix_count)
                if i + 1 > suffix_count:
                    return None  # something has gone wrong

            new_name = '{0}{1}'.format(existing_name, suffix[i])
            if len(new_name) > self.max_id_length:
                new_name = '{0}{1}'.format(existing_name[:self.max_id_length-len(new_name)], suffix[i])

            i += 1

            if i + 1 > MAX_ITERATIONS:
                return None  # something has gone wrong

        return new_name


class CreateNameRule:
    """Rules for determining how to create a new channel ID."""

    def __init__(self, **kwargs):
        self.duplicate_rule = DuplicateRule(**kwargs)
        self.default_rule = kwargs['default_rule'] if 'default_rule' in kwargs else False
        self.type = kwargs['type'] if 'type' in kwargs else None
        self.prefix = kwargs['prefix'] if 'prefix' in kwargs else None

    def __eq__(self, other):
        if type(other) is not str:
            return False
        if not self.type:
            return False
        return other.lower() in [x.lower() for x in self.type.split(',')]

    def create_name(self, fid):
        """Create new name based on defined rules."""
        return '{0}{1}'.format(self.prefix, fid)


class CreateNameRules:
    """Container to store all 'CreateNameRules'"""

    def __init__(self, create_name_rules=()):
        self.create_name_rules = create_name_rules
        self.default_rule = [x for x in self.create_name_rules if x.default_rule]
        self.default_rule = self.default_rule[0] if self.default_rule else None

    def create_name(self, type_, fid):
        """Create new name based on defined rules."""
        new_name = None
        for rule in self.create_name_rules:
            if rule == type_:
                new_name = rule.create_name(fid)

        if new_name is None and self.default_rule is not None:
            new_name = self.default_rule.create_name(fid)

        return new_name


class UniqueIds(QObject):
    """
    Class for handing 1D ids. With this class, can
    check for unique ids, or even use rules to provide
    unique ids.

    Inherit from QObject so it can run on a separate thread (using QThreads)
    and the main GUI can use a progress bar.
    """

    updated = pyqtSignal()
    finished = pyqtSignal(QObject)

    def __init__(self, iface=None, outputLyr=None):
        QObject.__init__(self)
        self.iface = iface
        self.outputLyr = outputLyr
        self.gis_layers = []
        self.ids = []
        self.duplicate_ids = []
        self.duplicate_feats = {}
        self.null_id_count = 0
        self.null_id_feats = {}

        self.errMessage = None
        self.errStatus = None
        self.hasRun = False
        self.tmpLyrs = []
        self.tmplyr2oldlyr = {}

    def __check_has_run__(self):
        """Check checkForDuplicates has been run."""

        # reset errors
        self.errMessage = None
        self.errStatus = None

        if not self.hasRun:
            self.errMessage = 'Unexpected error - unable to run tools'
            self.errStatus = 'Unexpected error - unable to run tools'
            self.finished.emit(self)
            return False

        return True

    def __create_output_layer__(self):
        """Create output GIS layer if it doesn't exist."""

        # take information from first gis layer that has a valid crs for output layer settings
        # otherwise take crs from project
        if self.outputLyr is None:
            crs = None
            for layer in self.gis_layers:
                if layer.crs().isValid():
                    crs = layer.crs()
                    break
            if crs is None:
                if QgsProject.instance().crs().isValid():
                    crs = QgsProject.instance().crs()
            uri = "point"
            if crs is not None:
                uri = '{0}?crs={1}'.format(uri, crs.authid().lower())
            uri = '{0}&field=Warning:string&field=Message:string&field=Tool:string&field=Magnitude:double'.format(uri)
            self.outputLyr = QgsVectorLayer(uri, 'output', 'memory')

        if not self.outputLyr.isValid():
            self.errStatus = 'Error: Unexpected error creating output layer'
            self.errMessage = 'An error occurred creating the temporary output layer'
            self.finished.emit(self)
            return False

        return True

    def checkForDuplicates(self, gis_layers, **kwargs):
        """
        Checks for duplicate channel IDs, NULL IDs, or empty IDs.
        Will check against all other layers in 'gis_layers'.
        """

        # turn off write duplicate errors if this is a collection tool rather than a check
        write_duplicate_errors = kwargs['write_duplicate_errors'] if 'write_duplicate_errors' in kwargs else True

        self.gis_layers = gis_layers[:]
        self.ids.clear()
        self.duplicate_ids.clear()
        for gis_layer in self.gis_layers:
            if gis_layer is None or type(gis_layer) is not QgsVectorLayer or not gis_layer.isValid():
                continue

            is_gpkg = gis_layer.storageType() == 'GPKG'
            iid = 1 if is_gpkg else 0
            if gis_layer.fields().count() < iid + 1:
                continue

            for feat in gis_layer.getFeatures():
                id_ = feat.attributes()[iid]
                feat_key = FeatKey(gis_layer, feat)
                if feat.attributes()[iid+1] != NULL and feat.attributes()[iid+1].lower() != 'x' and (id_ == NULL or id_.strip() == ''):
                    self.null_id_count += 1
                    self.null_id_feats[feat_key] = feat_key
                elif feat.attributes()[iid+1] != NULL and feat.attributes()[iid+1].lower() != 'x' and id_ not in self.ids:
                    self.ids.append(id_)
                elif feat.attributes()[iid + 1] != NULL and feat.attributes()[iid + 1].lower() != 'x':
                    self.duplicate_ids.append(id_)
                    self.duplicate_feats[feat_key] = feat_key

                self.updated.emit()

        if self.errMessage is None and write_duplicate_errors:
            if self.duplicate_ids:
                self.errStatus = 'Error: Duplicate IDs found in channel layer(s)'
                self.errMessage = '{0} duplicate IDs found in channel layer(s)'.format(len(self.duplicate_ids))
            if self.null_id_count:
                msg = 'NULL IDs found in channel layer(s)'
                if self.errStatus is None:
                    self.errStatus = 'Error: {0}'.format(msg)
                else:
                    self.errStatus = '{0}... {1}'.format(self.errStatus, msg)
                msg = '{0} NULL IDs found in channel layer(s)'.format(self.null_id_count)
                if self.errMessage is None:
                    self.errMessage = msg
                else:
                    self.errMessage = '{0}\n{1}'.format(self.errMessage, msg)
            if self.errMessage is not None:
                msg = 'Each channel must have a unique ID and cannot be NULL (except for \'x\' type channels). Run \'Channel ID\' tool to automate correction.'
                self.errMessage = '{0}\n\n{1}'.format(self.errMessage, msg)

        self.hasRun = True
        self.finished.emit(self)

    def findNonCompliantIds(self):
        """
        Create an output layer and create features at each location where
        there is a duplicate id or null id.

        Assumes checkForDuplicates has already been run
        """

        # check that 'checkForDuplicates' has already been run
        if not self.__check_has_run__():
            return

        # create output layer if it doesn't already exist
        if not self.__create_output_layer__():
            return

        new_feats = []
        for feat_key in self.duplicate_feats:
            feat = feat_key.feat
            if not feat.geometry().isEmpty():
                is_gpkg = self.duplicate_feats[feat_key].lyr.storageType() == 'GPKG'
                iid = 1 if is_gpkg else 0
                new_feat = QgsFeature()
                new_feat.setGeometry(feat.geometry().pointOnSurface())
                new_feat.setAttributes([
                    'Duplicate ID: {0}'.format(feat.attributes()[iid]),
                    'Duplicate ID: {0}'.format(feat.attributes()[iid]),
                    'Channel ID: find duplicate ID tool',
                    1.0
                ])
                new_feats.append(new_feat)
            self.updated.emit()
        for feat_key in self.null_id_feats:
            feat = feat_key.feat
            if not feat.geometry().isEmpty():
                new_feat = QgsFeature()
                new_feat.setGeometry(feat.geometry().pointOnSurface())
                new_feat.setAttributes([
                    'NULL or empty ID',
                    'NULL or empty ID',
                    'Channel ID: find NULL or empty ID tool',
                    1.0
                ])
                new_feats.append(new_feat)
            self.updated.emit()

        if new_feats:
            self.outputLyr.dataProvider().addFeatures(new_feats)
            self.outputLyr.updateExtents()
            self.outputLyr.triggerRepaint()

        self.finished.emit(self)

    def fixChannelIDs(self, duplicate_rule, create_name_rule):
        """
        Create an output layer that has a unique ID for
        each channel and does not contain any NULL of
        empty IDs.
        """

            # check that 'checkForDuplicates' has already been run
        if not self.__check_has_run__():
            return

        # create output layer if it doesn't already exist - this is the output logging layer
        if not self.__create_output_layer__():
            return

        # loop through once to get unique ids
        ids = []
        ok_feats = {}
        bad_lyrs = []
        for layer in self.gis_layers:
            is_gpkg = layer.storageType() == 'GPKG'
            iid = 1 if is_gpkg else 0
            itype = iid + 1
            for feat in layer.getFeatures():
                is_x_connector = feat[itype] != NULL and feat[itype].lower() == 'x'
                if not is_x_connector:
                    id_ = feat[iid]
                    if id_ is not NULL and id_ and id_ not in ids:
                        ids.append(id_)
                        if layer.id() not in ok_feats:
                            ok_feats[layer.id()] = []
                        ok_feats[layer.id()].append(feat.id())
                    else:
                        bad_lyrs.append(layer.id())

        # loop through and write out channels with ID name corrections
        output_feats = []  # logging features
        for layer in self.gis_layers:
            if layer.id() not in bad_lyrs:
                continue

            ok_feats_ = ok_feats[layer.id()]

            # id field index
            is_gpkg = layer.storageType() == 'GPKG'
            iid = 1 if is_gpkg else 0

            # create tmp output 1d_nwk layer
            uri = 'linestring?crs={0}'.format(layer.crs().authid())

            lyrnames = [x.name() for _, x in QgsProject.instance().mapLayers().items()]
            cnt = 1
            tempLyrName = '{0}_ID{1}'.format(layer.name(), cnt)
            while tempLyrName in lyrnames:
                cnt += 1
                tempLyrName = '{0}_ID{1}'.format(layer.name(), cnt)

            nwk = QgsVectorLayer(uri, tempLyrName, 'memory')
            if not nwk.isValid():
                self.errMessage = 'Unexpected error occurred creating temporary 1d_nwk ' \
                                  'layer output for {0}'.format(layer.name())
                self.errStatus = 'Error: Unexpected error occurred creating output layer'
                self.finised.emit(self)
                return
            self.tmpLyrs.append(nwk)
            self.tmplyr2oldlyr[nwk.id()] = layer.id()

            # copy fields
            fields = [x for x in layer.fields()][iid:]
            # make sure id field has a field length of 36 - id length allowed in latest TUFLOW release
            id_field = QgsField(fields[0])
            id_field.setLength(MAX_FIELD_LENGTH)
            fields[0] = id_field
            # add field definitions to new layer
            nwk.dataProvider().addAttributes(fields)
            nwk.updateFields()

            # loop through features
            nwk_feats = []
            for feat in layer.getFeatures():
                new_feat = QgsFeature(feat)

                is_x_connector = new_feat[1] != NULL and new_feat[1].lower() == 'x'

                # check for NULL or empty id
                if not is_x_connector and (new_feat[0] == NULL or not new_feat[0].strip()):
                    # fix id
                    new_feat[0] = create_name_rule.create_name(new_feat[1], feat.id())
                    if new_feat[0] is None:
                        self.errMessage = 'Could not create a new name for feature ID: {0}'.format(feat.id())
                        self.errStatus = 'Could not create a new name'
                        self.finished.emit(self)
                        return

                    # log this change in output GIS layer
                    log_feat = QgsFeature()
                    log_feat.setGeometry(feat.geometry().pointOnSurface())
                    log_feat.setAttributes([
                        'Created Name: {0}'.format(new_feat[0]),
                        'Created Name for feature (FID = {0}): {1}'.format(feat.id(), new_feat[iid]),
                        'Channel ID: create new name tool',
                        1.0
                    ])
                    output_feats.append(log_feat)

                # check for duplicate id
                # if not is_x_connector and new_feat[0] in ids:
                if not is_x_connector and feat.id() not in ok_feats_:
                    # fix id
                    new_feat[0] = duplicate_rule.unique_name(new_feat[0], ids)
                    if new_feat[0] is None:
                        self.errMessage = 'Could not create a unique name for feature with id: {0}'.format(feat[iid])
                        self.errStatus = 'Could not create a unique name'
                        self.finished.emit(self)
                        return

                    # log this change in output GIS layer
                    log_feat = QgsFeature()
                    log_feat.setGeometry(feat.geometry().pointOnSurface())
                    log_feat.setAttributes([
                        'Renamed Channel ID to {0}'.format(new_feat[0]),
                        'Renamed Channel (FID = {2}) ID from {0} to {1}'.format(feat[iid], new_feat[0], feat.id()),
                        'Channel ID: rename duplicate tool',
                        1.0
                    ])
                    output_feats.append(log_feat)
                    ids.append(new_feat[0])

                # ids.append(new_feat[0])
                nwk_feats.append(new_feat)

                self.updated.emit()  # update progress bar

            nwk.dataProvider().addFeatures(nwk_feats)
            nwk.updateExtents()
            QgsProject.instance().addMapLayer(nwk)

        if bad_lyrs:
            self.outputLyr.dataProvider().addFeatures(output_feats)
            self.outputLyr.updateExtents()

        self.finished.emit(self)
