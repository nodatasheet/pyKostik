from operator import attrgetter
from pyrevit import revit, forms, DB


doc = revit.doc  # type: DB.Document
active_view = revit.active_view  # type: DB.View


class RevisionCloudArc(object):
    def __init__(self, arc):
        # type: (DB.Arc) -> None
        self._arc = arc

    @property
    def approx_outline(self):
        # type: () -> DB.Outline
        arc_tasselation = self._arc.Tessellate()
        tasselated_polyline = DB.PolyLine.Create(arc_tasselation)
        return tasselated_polyline.GetOutline()

    @property
    def reference(self):
        return self._arc.Reference


class CurveGroups(object):
    """Group curves by connectivity"""

    def __init__(self, curves, connection_tolerance=1e-09):
        # type: (list[DB.Curve], float) -> None
        self._curves = curves
        self._connection_tolerance = connection_tolerance
        self._groups = self._group_by_connectivity()

    def _group_by_connectivity(self):
        # type: () -> list[list[DB.Curve]]
        """Groups curves by their connectivity."""
        curves_dict = {i: v for i, v in enumerate(self._curves)}
        neighbors = self._get_neighbors(curves_dict)
        merged = self._merge_touching_sets(neighbors)
        return [[curves_dict[k] for k in group] for group in merged]

    def _almost_equal(self, a, b, abs_tol=0.0):
        rel_tol = self._connection_tolerance
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    def _are_points_equal(self, pt1, pt2):
        # type: (DB.XYZ, DB.XYZ) -> bool
        return all(
            (self._almost_equal(pt1.X, pt2.X),
             self._almost_equal(pt1.Y, pt2.Y),
             self._almost_equal(pt1.Z, pt2.Z))
        )

    def _are_curves_connected(self, curve1, curve2):
        # type: (DB.Curve, DB.Curve) -> bool
        p11 = curve1.GetEndPoint(0)
        p12 = curve1.GetEndPoint(1)
        p21 = curve2.GetEndPoint(0)
        p22 = curve2.GetEndPoint(1)
        return any(
            (self._are_points_equal(p11, p21),
             self._are_points_equal(p11, p22),
             self._are_points_equal(p12, p21),
             self._are_points_equal(p12, p22))
        )

    def _get_neighbors(self, curves_dict):
        # type: (dict) -> list[set[dict.key]]
        """Gets all neighbors for each curve
            as list of sets of dictionary keys"""
        all_neighbours = []
        for i in curves_dict.keys():
            sub_neighbours = {i}
            for j in curves_dict.keys():
                are_curves_connected = \
                    self._are_curves_connected(curves_dict[i], curves_dict[j])
                if j != i and are_curves_connected:
                    sub_neighbours.add(j)
            all_neighbours.append(sub_neighbours)
        return all_neighbours

    def _merge_touching_sets(self, sets):
        # type: (list[set]) -> list[set]
        """Merges sets with common elements.
            Source: https://stackoverflow.com/a/9400562
        """
        new_group = []
        while len(new_group) != len(sets):
            new_group, sets = sets, []
            for set1 in new_group:
                for set2 in sets:
                    if not set1.isdisjoint(set2):
                        set2.update(set1)
                        break
                else:
                    sets.append(set1)
        return sets

    @property
    def groups(self):
        return self._groups


def get_geometry_instances(elem, geom_options):
    # type: (DB.Element, DB.Options) -> list[DB.GeometryInstance]

    geometry_instances = []
    geom_elems = elem.get_Geometry(geom_options)
    for geom_elem in geom_elems:
        if isinstance(geom_elem, DB.GeometryInstance):
            geom_objects = geom_elem.GetInstanceGeometry()
            for geom_obj in geom_objects:
                geometry_instances.append(geom_obj)
    return geometry_instances


def draw_curve(curve):
    doc.Create.NewDetailCurve(active_view, curve)


def get_circle(center):
    return DB.Arc.Create(center, 1, 0, 2 * 3.14, DB.XYZ.BasisX, DB.XYZ.BasisY)


rev_tag_type_id = DB.FilteredElementCollector(doc) \
    .OfCategory(DB.BuiltInCategory.OST_RevisionCloudTags) \
    .WhereElementIsElementType() \
    .FirstElementId()

if rev_tag_type_id is None:
    forms.alert(
        msg='There is no Revision Cloud Tags in this document.\n'
        'Please load it first.',
        exitscript=True
    )

revision_clouds = list(
    DB.FilteredElementCollector(doc, active_view.Id)
    .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)
    .WhereElementIsNotElementType()
)  # type: list[DB.RevisionCloud]

if not revision_clouds:
    forms.alert(
        msg='No Revision Clouds in This View',
        exitscript=True
    )

existing_revision_tags = list(
    DB.FilteredElementCollector(doc, active_view.Id)
    .OfCategory(DB.BuiltInCategory.OST_RevisionCloudTags)
    .WhereElementIsNotElementType()
)  # type: list[DB.IndependentTag]

tagged_revision_ids = set()
for existing_rev_tag in existing_revision_tags:
    tagged_revision_ids.update(existing_rev_tag.GetTaggedLocalElementIds())

with revit.Transaction('Tag All Revision Clouds'):

    geom_opts = DB.Options()
    geom_opts.View = active_view
    geom_opts.ComputeReferences = True

    for rev_cloud in revision_clouds:
        if rev_cloud.Id not in tagged_revision_ids:
            geom_elems = get_geometry_instances(rev_cloud, geom_opts)

            # Some revision clouds have multiple poligons inside
            # Group them by connectivity
            curve_groups = CurveGroups(geom_elems)

            for group in curve_groups.groups:
                revision_arcs = [RevisionCloudArc(curve) for curve in group]

                top_right_revision_arc = max(
                    revision_arcs,
                    key=attrgetter(
                        'approx_outline.MaximumPoint.X',
                        'approx_outline.MaximumPoint.Y'
                    )
                )

                add_leader = False
                head_position = \
                    top_right_revision_arc.approx_outline.MaximumPoint

                new_tag = DB.IndependentTag.Create(
                    doc,
                    rev_tag_type_id,
                    active_view.Id,
                    top_right_revision_arc.reference,
                    add_leader,
                    DB.TagOrientation.Horizontal,
                    head_position
                )  # type: DB.IndependentTag

                tag_bb = new_tag.get_BoundingBox(active_view)
                new_tag.TagHeadPosition = tag_bb.Max
                new_tag.HasLeader = True
