from math import pi, sin, cos, atan2

import numpy as np
from qgis._core import QgsWkbTypes
from qgis.core import (NULL, QgsPoint, QgsGeometry, QgsFeature, QgsRectangle, QgsPointXY, QgsDistanceArea,
                       QgsCoordinateTransformContext, QgsSpatialIndex, QgsExpression, QgsFeatureRequest)
from ..tuflowqgis_library import is1dNetwork


class SpacingGenerator:
    """Abstract base class for calculating distances along a linestring for a given method."""

    def __new__(cls, method, at_vertices, at_midpoint, thinning, geom, spacing, crs):
        if method == 'equal_linestring':
            cls = EqualSpacingAlongLine
        elif method == 'equal_segment':
            cls = EqualSpacingAlongSegment
        elif method == 'fixed_linestring':
            cls = FixedSpacingAlongLine
        self = super().__new__(cls)
        self.at_vertices = at_vertices
        self.at_midpoint = at_midpoint
        self.thinning = thinning
        self.geom = geom
        if geom.isMultipart():
            self.verts = geom.asMultiPolyline()[0]
        else:
            self.verts = geom.asPolyline()
        if self.thinning == 'overlap_vertices':
            self.vertex_dists = [0.] + self.internal_vertex_distances() + [self.geom.length()]
            self.tol = 0.2 * spacing
        self.spacing = spacing
        self.crs = crs
        self.da = QgsDistanceArea()
        self.da.setSourceCrs(self.crs, QgsCoordinateTransformContext())
        return self

    def distance(self, p1, p2):
        return self.da.measureLine([p1, p2])

    def segment_length(self, ind):
        return self.distance(self.verts[ind], self.verts[ind + 1])

    def internal_vertex_distances(self):
        if len(self.verts) > 2:
            return [self.geom.distanceToVertex(i) for i, v in enumerate(self.verts) if i != 0 and i != len(self.verts) - 1]
        return []

    def calculate_distances(self):
        if self.at_midpoint:
            return [self.geom.length() / 2]
        return []


class EqualSpacingAlongLine(SpacingGenerator):
    """
    Calculates the spacing along a linestring using equal spacing.
      1. Calculate the total number of perpendicular lines to be created based on the user input spacing
           - at least one perpendicular line will be created for each linestring
      2. Space these lines equally along the linestring
      3. If at_vertices is True, a perpendicular line will be created at each internal vertex
           (start/end vertices are handled by the calling routine)
    """

    def calculate_distances(self):
        distances = super().calculate_distances()
        if self.spacing <= 0:
            return distances
        count = max(1, int(self.geom.length() / self.spacing))
        spacing = self.geom.length() / (count + 1)
        ch = 0
        for i in range(count):
            ch += spacing
            if self.thinning == 'overlap_vertices':
                if np.isclose([ch for _ in range(len(self.verts))], self.vertex_dists, atol=self.tol, rtol=0.).any():
                    continue
            distances.append(ch)
        if self.at_vertices:
            distances.extend(self.internal_vertex_distances())
        return sorted(distances)


class EqualSpacingAlongSegment(SpacingGenerator):
    """
    Calculates the spacing along a linestring using equal spacing along line segments.
      For each segment in the linestring:
        1. Calculate the total number of perpendicular lines to be created based on the user input spacing
             - at least one perpendicular line will be created for each segment only if at_vertices is False
        2. Space these lines equally along the segment
        3. If at_vertices is True, a perpendicular line will be created at each internal vertex
           (start/end vertices are handled by the calling routine)
    """

    def calculate_distances(self):
        distances = super().calculate_distances()
        if self.spacing <= 0:
            return distances
        total_seg_dist, ch = 0., 0.
        for i, v in enumerate(self.verts[:-1]):
            seg_len = self.segment_length(i)
            total_seg_dist += seg_len
            count = int(seg_len / self.spacing)
            if count == 0 and not self.at_vertices:
                count = 1
            if not count:
                continue
            spacing = seg_len / (count + 1)
            for j in range(count):
                ch += spacing
                if self.thinning == 'overlap_vertices':
                    if np.isclose([ch for _ in range(len(self.verts))], self.vertex_dists, atol=self.tol, rtol=0.).any():
                        continue
                distances.append(ch)
            ch = total_seg_dist
        if self.at_vertices:
            distances.extend(self.internal_vertex_distances())
        return sorted(distances)


class FixedSpacingAlongLine(SpacingGenerator):
    """
    Calculates the spacing along a linestring using fixed spacing along the entire linestring.
    1. Calculate the total number of perpendicular lines to be created based on the user input spacing
         - at least one perpendicular line will be created for each segment only if at_vertices is False
    2. Space these at the user input interval
    3. If at_vertices is True, a perpendicular line will be created at each internal vertex
    """

    def calculate_distances(self):
        distances = super().calculate_distances()
        if self.spacing <= 0:
            return distances
        count = int(self.geom.length() / self.spacing)
        ch = 0
        for i in range(count):
            ch += self.spacing
            if self.thinning == 'overlap_vertices':
                if np.isclose([ch for _ in range(len(self.verts))], self.vertex_dists, atol=self.tol, rtol=0.).any():
                    continue
            distances.append(ch)
        if self.at_vertices:
            distances.extend(self.internal_vertex_distances())
        return sorted(distances)


class PerpendicularLines:

    def __init__(self):
        self.at_ends = True
        self.at_midpoint = False
        self.length = 100.
        self.spacing = 0.
        self.method = 'equal_segment'
        self.at_vertices = False
        self.thinning = 'none'
        self.middle_vertex = False
        self.attr_callback = None
        self.total_steps = 0
        self.lyr = None
        self.lyr_is_nwk_type = False
        self.clip_lyr = None
        self.clip_si = None
        self.si = None
        self.out_feats = {}
        self.out_si = QgsSpatialIndex()
        self.crs = None
        self.id = 0
        self.nrem = 0
        self.exp = QgsExpression()

    def iter(self, count_only=False):
        self.total_steps = 0
        feat_req = QgsFeatureRequest(self.exp)
        for i, feat in enumerate(self.lyr.getFeatures(feat_req)):
            geom = feat.geometry()
            if geom.isEmpty():  # skip if geometry is empty
                continue

            # generator class for calculating the perpendicular line distances based on the method and other settings
            spacing_gen = SpacingGenerator(
                self.method, self.at_vertices, self.at_midpoint, self.thinning, geom, self.spacing, self.crs
            )

            # first vertex only if it is the most upstream channel
            if self.at_ends and not self.is_snapped(feat, spacing_gen.verts[0]):
                self.total_steps += 1
                if not count_only:
                    feat_ = self.perpendicular_feature(feat, 0, None)
                    if feat_:
                        self.out_feats[feat_.id()] = feat_
                        self.out_si.addFeature(feat_)
                        yield feat_

            # step through calculated insert distances
            for dist in spacing_gen.calculate_distances():
                self.total_steps += 1
                if not count_only:
                    feat_ = self.perpendicular_feature(feat, -1, dist)
                    if feat_:
                        self.out_feats[feat_.id()] = feat_
                        self.out_si.addFeature(feat_)
                        yield feat_

            # on last vertex - if snapped to another line, take average angle of in/out lines
            self.total_steps += 1
            if self.at_ends and not count_only:
                feat_ = self.perpendicular_feature(feat, len(spacing_gen.verts) - 1, None, avg_angle=True)
                if feat_:
                    self.out_feats[feat_.id()] = feat_
                    self.out_si.addFeature(feat_)
                    yield feat_

    def validate(self):
        self.lyr_is_nwk_type = is1dNetwork(self.lyr) and self.lyr.dataProvider().fieldNameIndex('Type') != -1
        if self.length <= 0:
            self.length = 100.

    def count_lines(self):
        _ = [x for x in self.iter(count_only=True)]
        return self.total_steps

    def perpendicular_feature(self, feat, vert_ind, distance, avg_angle=False):
        geom = self.perpendicular_geometry(feat, vert_ind, distance, avg_angle)
        if geom is None:
            return
        if self.clip_lyr:
            if self.clip_lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                geom = self.clip_geometry(geom)
            elif self.clip_lyr.geometryType() == QgsWkbTypes.LineGeometry:
                geom = self.clip_geometry_line(geom)
            else:
                geom = None
            if not geom:
                return
        if 'overlap' in self.thinning and self.overlaps_existing(geom):
            self.nrem += 1
            return
        self.id += 1
        feat = QgsFeature()
        feat.setId(self.id)
        feat.setGeometry(geom)
        if self.attr_callback:
            self.attr_callback(feat, geom, self.id)
        return feat

    def perpendicular_geometry(self, feat, vert_ind, distance, avg_angle=False):
        geom = feat.geometry()
        if vert_ind != -1:  # use vertex index argument
            angle = geom.angleAtVertex(vert_ind)
            point = geom.vertexAt(vert_ind)
        else:  # use distance argument
            angle = geom.interpolateAngle(distance)
            point = geom.interpolate(distance)
            if point.isEmpty():
                return
            point = point.asPoint()
        if avg_angle:  # take average angle of in/out lines combined with downstream line if snapped
            dnstrm_line = self.is_snapped(feat, point)
            if dnstrm_line and not dnstrm_line.geometry().isEmpty():
                angle = self.average_angle([angle, dnstrm_line.geometry().angleAtVertex(0)])
        angle += pi / 2  # rotate 90 degrees
        x1 = point.x() - (self.length / 2) * sin(angle)
        y1 = point.y() - (self.length / 2) * cos(angle)
        x2 = point.x() + (self.length / 2) * sin(angle)
        y2 = point.y() + (self.length / 2) * cos(angle)
        return QgsGeometry.fromPolyline([QgsPoint(x1, y1), QgsPoint(point.x(), point.y()), QgsPoint(x2, y2)])

    def clip_geometry(self, line_geom):
        vmid = line_geom.vertexAt(1)  # middle vertex
        for fid in self.clip_si.intersects(line_geom.boundingBox()):
            poly_geom = self.clip_lyr.getFeature(fid).geometry()
            res_geom = line_geom.intersection(poly_geom)
            if res_geom.isEmpty():
                continue
            if res_geom.isMultipart():
                res_verts = sum(res_geom.asMultiPolyline(), [])
            else:
                res_verts = res_geom.asPolyline()
            if len(res_verts) < 3:
                return
            try:
                i = [i for i, x in enumerate(res_verts) if np.isclose([x.x(), x.y()], [vmid.x(), vmid.y()], atol=0.0001, rtol=0).all()][0]
            except IndexError:
                return line_geom
            return QgsGeometry.fromPolyline([QgsPoint(x) for x in res_verts[i - 1:i + 2]])
        return line_geom

    def clip_geometry_line(self, line_geom):
        vmid = QgsPointXY(line_geom.vertexAt(1))  # middle vertex
        res_verts = []
        for fid in self.clip_si.intersects(line_geom.boundingBox()):
            line_geom2 = self.clip_lyr.getFeature(fid).geometry()
            res_geom = line_geom.intersection(line_geom2)
            if res_geom.isEmpty():
                continue
            if res_geom.isMultipart():
                res_verts.extend(res_geom.asMultiPoint())
            else:
                res_verts.append(res_geom.asPoint())
        if not res_verts:
            return line_geom
        dist_to_mid = line_geom.lineLocatePoint(QgsGeometry.fromPointXY(vmid))
        if len(res_verts) == 1:
            dist = line_geom.lineLocatePoint(QgsGeometry.fromPointXY(res_verts[0]))
            if dist < dist_to_mid:
                res_verts = [res_verts[0], vmid, line_geom.vertexAt(2)]
            else:
                res_verts = [line_geom.vertexAt(0), vmid, res_verts[0]]
        else:
            dist = {i: (x, line_geom.lineLocatePoint(QgsGeometry.fromPointXY(x))) for i, x in enumerate(res_verts)}
            imid = len(dist)
            dist[imid] = (vmid, dist_to_mid)
            dists = sorted(dist.keys(), key=lambda x: dist[x][1])
            i = dists.index(imid)
            res_verts = [dist[dists[i-1]][0], vmid, dist[dists[i+1]][0]]
        res_verts = [QgsPointXY(x) for x in res_verts]
        return QgsGeometry.fromPolylineXY(res_verts)

    def overlaps_existing(self, geom):
        for fid in self.out_si.intersects(geom.boundingBox()):
            other = self.out_feats[fid].geometry()
            if geom.intersects(other):
                return True
        return False

    def is_snapped(self, feat, point):
        qgsrect = QgsRectangle(QgsPointXY(point), QgsPointXY(point))
        qgsrect = qgsrect.buffered(0.1)
        for fid in self.si.intersects(qgsrect):
            if fid == feat.id():
                continue
            feat_ = self.lyr.getFeature(fid)
            if feat_.geometry().isMultipart():
                verts = feat_.geometry().asMultiPolyline()[0]
            else:
                verts = feat_.geometry().asPolyline()
            if self.points_snapped(point, verts[0]) or self.points_snapped(point, verts[-1]):
                return feat_

    def average_angle(self, angles):
        sum_sin = 0
        sum_cos = 0
        for a in angles:
            sum_sin += sin(a)
            sum_cos += cos(a)
        return atan2(sum_sin, sum_cos)

    @staticmethod
    def points_snapped(p1, p2):
        return bool(np.isclose([p1.x(), p1.y()], [p2.x(), p2.y()], atol=0.0001, rtol=0).all())
