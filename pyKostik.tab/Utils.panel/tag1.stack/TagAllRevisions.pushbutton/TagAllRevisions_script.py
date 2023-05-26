import re
import itertools
from operator import attrgetter

from pyrevit import revit, forms, DB, script
from pykostik import exceptions as pke

doc = revit.doc  # type: DB.Document
logger = script.get_logger()


class AttemptFailure(Exception):
    pass


class ViewElementsCollector(object):

    def __init__(self, doc, view_wrap):
        # type: (DB.Document, ViewWrap) -> None
        self._doc = doc
        self._view_id = view_wrap.id

    def untagged_revision_clouds(self):
        # type: () -> list[DB.RevisionCloud]
        untagged_revision_clouds = []
        for rev_cloud in self.revision_clouds():
            if rev_cloud.Id not in self.tagged_revision_cloud_ids():
                untagged_revision_clouds.append(rev_cloud)
        return untagged_revision_clouds

    def revision_clouds(self):
        # type: () -> list[DB.RevisionCloud]
        return list(
            DB.FilteredElementCollector(self._doc, self._view_id)
            .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)
            .WhereElementIsNotElementType()
        )

    def tagged_revision_cloud_ids(self):
        # type: () -> set[DB.ElementId]
        tagged_revision_ids = set()
        for tag in self._existing_revision_tags_on_view():
            tagged_revision_ids.update(tag.GetTaggedLocalElementIds())
        return tagged_revision_ids

    def _existing_revision_tags_on_view(self):
        # type: () -> list[DB.IndependentTag]
        return list(
            DB.FilteredElementCollector(self._doc, self._view_id)
            .OfCategory(DB.BuiltInCategory.OST_RevisionCloudTags)
            .WhereElementIsNotElementType()
        )


class Sorter(object):

    def sort_by_attrs(self, iterable, attrs):
        return sorted(
            iterable,
            key=self._cmp_to_key_by_attrs(self._names_comparer, attrs)
        )

    def _cmp_to_key_by_attrs(self, comparer, attrs):
        """Converts a comparer into a key= function
        for multilevel sorting or ordering by supplied attributes.

        Refer to functools.cmp_to_key() and operator.attrgetter().

        Args:
            comparer: a function that compares two arguments and then returns
                a negative value for '<', zero for '==', or a positive for '>'
            attrs (optional): list of attribute strings

        Returns:
            key function:
            a callable that returns a value for sorting or ordering
        """

        class K(object):
            __slots__ = ['_obj']

            def __init__(self, obj, attr):
                self._validate_attr(attr)
                self._obj = self._resolve_attr(obj, attr)

            def _validate_attr(self, attr):
                if not isinstance(attr, str):
                    raise TypeError(
                        'Expected string, got {}'.format(type(attr)))

            def _resolve_attr(self, obj, attr):
                for name in attr.split("."):
                    obj = getattr(obj, name)
                return obj

            def __lt__(self, other):
                return comparer(self._obj, other._obj) < 0

            def __gt__(self, other):
                return comparer(self._obj, other._obj) > 0

            def __eq__(self, other):
                return comparer(self._obj, other._obj) == 0

            def __le__(self, other):
                return comparer(self._obj, other._obj) <= 0

            def __ge__(self, other):
                return comparer(self._obj, other._obj) >= 0

            def __ne__(self, other):
                return comparer(self._obj, other._obj) != 0

            __hash__ = None

        if not hasattr(attrs, '__iter__'):
            raise TypeError('Attributes must be iterable')

        if len(attrs) == 1:
            def call_k(obj):
                return K(obj, attrs[0])

        else:
            def call_k(obj):
                return tuple(K(obj, attr) for attr in attrs)

        return call_k

    def _names_comparer(self, name1, name2):
        # type: (object, object) -> int
        """Compares two objects as strings using Revit's comparison rules"""
        return DB.NamingUtils.CompareNames(str(name1), str(name2))


class RevisionCloudArc(object):
    """Wrapper for Revit `Arc`"""

    def __init__(self, arc):
        # type: (DB.Arc) -> None
        self._arc = arc

    def contains_point(self, point):
        # type: (DB.XYZ) -> bool
        projected_point = self._arc.Project(point).XYZPoint
        return projected_point.IsAlmostEqualTo(point)

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
    """Group of curves by connectivity"""

    def __init__(self, curves):
        # type: (list[DB.Curve]) -> None
        self._curves = curves
        self._groups = self._group_by_connectivity()

    def _group_by_connectivity(self):
        # type: () -> list[list[DB.Curve]]
        """Groups curves by their connectivity."""
        curves_dict = {i: v for i, v in enumerate(self._curves)}
        neighbors = self._get_neighbors(curves_dict)
        merged = self._merge_touching_sets(neighbors)
        return [[curves_dict[k] for k in group] for group in merged]

    def _are_curves_connected(self, curve1, curve2):
        # type: (DB.Curve, DB.Curve) -> bool
        p11 = curve1.GetEndPoint(0)
        p12 = curve1.GetEndPoint(1)
        p21 = curve2.GetEndPoint(0)
        p22 = curve2.GetEndPoint(1)
        return any(
            (p11.IsAlmostEqualTo(p21),
             p11.IsAlmostEqualTo(p22),
             p12.IsAlmostEqualTo(p21),
             p12.IsAlmostEqualTo(p22))
        )

    def _get_neighbors(self, curves_dict):
        # type: (dict) -> list[set[dict.key]]
        """Gets all neighbors for each curve
            as list of sets of dictionary keys"""
        all_neighbours = []
        for i in curves_dict:
            sub_neighbours = {i}
            for j in curves_dict:
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


class ViewSelectionGroup(object):
    """Class combining all instances of `ViewSelectionItem`
    grouped by grouping parameter.
    """

    def __init__(self, name):
        # type: (str) -> None
        self._name = name
        self._view_items = []

    def add_view_item(self, view_item):
        # type: (ViewSelectionItem) -> None
        self._view_items.append(view_item)

    @property
    def view_items(self):
        # type: () -> list[ViewSelectionItem]
        return self._view_items

    @property
    def name(self):
        # type: () -> str
        return self._name


class ViewSelectionGroups(object):
    """Class combining all instances of `ViewSelectionGroup`"""

    _ALL_COMBINED_GROUP_NAME = 'All Views'

    def __init__(self):
        self._view_groups = {}  # type: dict[str: list[ViewSelectionItem]]
        self._make_all_combined_group()

    def _make_all_combined_group(self):
        self._view_groups[self._ALL_COMBINED_GROUP_NAME] = \
            ViewSelectionGroup(self._ALL_COMBINED_GROUP_NAME)

    def group_views(self, view_items):
        # type: (list[ViewSelectionItem]) -> None
        for view_item in view_items:
            self._add_view_item(view_item)

    def get_view_groups(self):
        return {
            grp.name: grp.view_items for grp in self._view_groups.values()
        }

    def _add_view_item(self, view_item):
        # type: (ViewSelectionItem) -> None
        group_name = view_item.grouping_name
        if group_name not in self._view_groups:
            self._add_new_group(group_name)
        self._add_item_to_existing_group(view_item)
        self.all_combined.add_view_item(view_item)

    def _add_new_group(self, group_name):
        # type: (str) -> None
        self._view_groups[group_name] = ViewSelectionGroup(group_name)

    def _get_group_by_name(self, group_name):
        # type: (str) -> ViewSelectionGroup
        return self._view_groups[group_name]

    def _add_item_to_existing_group(self, view_item):
        # type: (ViewSelectionItem) -> None
        existing_group = self._get_group_by_name(view_item.grouping_name)
        existing_group.add_view_item(view_item)

    @property
    def all_combined(self):
        return self._get_group_by_name(self._ALL_COMBINED_GROUP_NAME)


class ViewWrap(object):
    """Wrapper for Revit `View`"""

    _VIEW_TYPES_VALID_FOR_REVISION_CLOUD = [
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.Elevation,
        DB.ViewType.DrawingSheet,
        DB.ViewType.DraftingView,
        DB.ViewType.Legend,
        DB.ViewType.EngineeringPlan,
        DB.ViewType.AreaPlan,
        DB.ViewType.Section,
        DB.ViewType.Detail,
    ]

    def __init__(self, view):
        # type: (DB.View) -> None
        self._view = view
        self._view_type = view.ViewType
        self._doc = view.Document

    def get_geometry_options(self):
        geom_opts = DB.Options()
        geom_opts.View = self._view
        geom_opts.ComputeReferences = True
        return geom_opts

    def element_bounding_box(self, element):
        # type: (DB.Element) -> DB.BoundingBoxXYZ
        return element.get_BoundingBox(self._view)

    @property
    def name(self):
        # type: () -> str
        return self._view.Name

    @property
    def is_valid_for_revision_cloud(self):
        return (
            self._view_type in self._VIEW_TYPES_VALID_FOR_REVISION_CLOUD
            and not self._view.IsTemplate
        )

    @property
    def view_type(self):
        return self._view_type

    @property
    def is_template(self):
        return self._view.IsTemplate

    @property
    def family_name(self):
        # type: () -> str
        family_name_param = self._view.get_Parameter(
            DB.BuiltInParameter.VIEW_FAMILY)  # type: DB.Parameter
        if family_name_param:
            return family_name_param.AsValueString()
        raise pke.InvalidOperationException(
            'Failed getting Family Name for {}({})'.format(self.name, self.id)
        )

    @property
    def id(self):
        return self._view.Id

    @property
    def doc(self):
        return self._doc


class ViewSelectionItem(object):
    """`ViewWrap` selection item in UI"""

    def __init__(self, view_wrap):
        # type: (ViewWrap) -> None
        self._view_wrap = view_wrap
        self._view_name = view_wrap.name
        self._type = view_wrap.view_type
        self._is_template = view_wrap.is_template

    def _add_spaces_after_capitals(self, txt):
        # type: (str) -> str
        return re.sub(r"(\w)([A-Z])", r"\1 \2", txt)

    @property
    def readable_type_name(self):
        return self._add_spaces_after_capitals(str(self._type))

    @property
    def grouping_name(self):
        return self._view_wrap.family_name

    @property
    def name(self):
        if self._type == DB.ViewType.DrawingSheet:
            return self._name_for_sheet
        return self._general_name_for_views

    @property
    def _name_for_sheet(self):
        sheet_view = self._view_wrap._view  # type: DB.ViewSheet
        return '{}: {} - {}'.format(
            self.grouping_name,
            sheet_view.SheetNumber,
            sheet_view.Name
        )

    @property
    def _general_name_for_views(self):
        return '{}: {}'.format(self.grouping_name, self._view_name)

    @property
    def view_wrap(self):
        return self._view_wrap


class ViewRevisionCloud(object):
    """Wrapper for Revit `RevisionCloud`"""

    def __init__(self, revision_cloud):
        # type: (DB.RevisionCloud) -> None
        self._revision_cloud = revision_cloud
        self._doc = revision_cloud.Document
        self._view_id = revision_cloud.OwnerViewId

    def existing_tag_wraps(self):
        # type: () -> list[TagWrap]
        and_filter = self._bic_rev_tags_filter()
        tag_wraps = []
        for id in self._revision_cloud.GetDependentElements(and_filter):
            tag_wrap = TagWrap(
                self._doc.GetElement(id)
            )
            tag_wraps.append(tag_wrap)
        return tag_wraps

    def _bic_rev_tags_filter(self):
        viis_on_view_filter = DB.VisibleInViewFilter(self._doc, self._view_id)
        bic_rev_tags_filter = DB.ElementCategoryFilter(
            DB.BuiltInCategory.OST_RevisionCloudTags
        )
        return DB.LogicalAndFilter(
            viis_on_view_filter,
            bic_rev_tags_filter
        )

    def get_subclouds(self):
        geometric_arcs = self._get_geometric_arcs()
        arc_groups = CurveGroups(geometric_arcs).groups
        return [
            ViewRevisionSubCloud(arcs) for arcs in arc_groups
        ]

    def _get_geometric_arcs(self):
        # type: () -> list[DB.Arc]
        geom_opts = self._get_geometry_options()
        geometric_arcs = []
        geom_elems = self._revision_cloud.get_Geometry(geom_opts)
        for geom_elem in geom_elems:
            if isinstance(geom_elem, DB.GeometryInstance):
                geom_objects = geom_elem.GetInstanceGeometry()
                for geom_obj in geom_objects:
                    geometric_arcs.append(geom_obj)
        return geometric_arcs

    def _get_geometry_options(self):
        geom_opts = DB.Options()
        geom_opts.View = self._doc.GetElement(self._revision_cloud.OwnerViewId)
        geom_opts.ComputeReferences = True
        return geom_opts

    @property
    def id(self):
        return self._revision_cloud.Id


class ViewRevisionSubCloud(object):
    """"Group of `RevisionCloudArc` connected together."""
    _is_tagged = False

    def __init__(self, arcs):
        # type: (DB.Arc) -> None
        self._arcs = [RevisionCloudArc(arc) for arc in arcs]

    def is_point_on_group(self, point):
        # type: (DB.XYZ) -> bool
        for arc in self._arcs:
            if arc.contains_point(point):
                return True
        return False

    @property
    def top_right_arc(self):
        return max(
            self._arcs,
            key=attrgetter(
                'approx_outline.MaximumPoint.X',
                'approx_outline.MaximumPoint.Y'
            )
        )

    @property
    def is_tagged(self):
        return self._is_tagged

    @is_tagged.setter
    def is_tagged(self, value):
        # type: (bool) -> None
        self._is_tagged = value


class TagWrap(object):
    """Wrapper for Revit `IndependentTag`"""

    def __init__(self, tag):
        # type: (DB.IndependentTag) -> None
        self._tag = tag

    @classmethod
    def tag_sub_cloud(cls, tag_type_id, view_wrap, revision_sub_cloud):
        # type: (DB.ElementId, ViewWrap, ViewRevisionSubCloud) -> TagWrap
        try:
            add_leader = False
            top_right_arc = revision_sub_cloud.top_right_arc

            new_tag = DB.IndependentTag.Create(
                view_wrap.doc,
                tag_type_id,
                view_wrap.id,
                top_right_arc.reference,
                add_leader,
                DB.TagOrientation.Horizontal,
                top_right_arc.approx_outline.MaximumPoint
            )  # type: DB.IndependentTag

            tag_bb = view_wrap.element_bounding_box(new_tag)
            new_tag.TagHeadPosition = tag_bb.Max
            new_tag.HasLeader = True
            return cls(new_tag)
        except Exception as err:
            raise AttemptFailure(err)

    def make_leader_attached(self):
        self._tag.HasLeader = True
        self._tag.LeaderEndCondition = DB.LeaderEndCondition.Attached
        self._tag.LeaderEndCondition = DB.LeaderEndCondition.Free

    def make_leader_free(self):
        self._tag.LeaderEndCondition = DB.LeaderEndCondition.Free

    def get_leader_ends(self):
        # type: () -> list[DB.XYZ]
        tag_refs = self._tag.GetTaggedReferences()
        return [
            self._tag.GetLeaderEnd(ref) for ref in tag_refs
        ]

    @property
    def id(self):
        return self._tag.Id


class OutputResult(object):
    _output = None

    def __init__(self, view_name, view_id, rev_cloud_id):
        # type: (str, DB.ElementId, DB.ElementId, DB.ElementId) -> None
        if self._output is None:
            self._output = script.get_output()
        self._general_txt = '{} (id {}) for cloud (id {}): '.format(
            view_name,
            self._output.linkify(view_id),
            self._output.linkify(rev_cloud_id)
        )

    def print_result(self, symbol, tag_id=None, fail_txt=None):
        # type: (str, DB.ElementId, str) -> None
        if tag_id is not None:
            tag_link = 'added tag (id {}) {}'.format(
                self._output.linkify(tag_id),
                symbol
            )
        else:
            tag_link = ''

        if fail_txt is None:
            fail_txt = ''
        else:
            fail_txt = '{} failed to tag with error: {}'.format(
                symbol,
                fail_txt
            )

        result = self._general_txt + tag_link + fail_txt

        self._output.print_md(result)


def mark_tagged_sub_clouds(tag_wraps, sub_clouds):
    # type: (list[TagWrap], list[ViewRevisionSubCloud]) -> None
    """Sets sub-clouds as tagged if any of tags refer to them"""
    for tag_wrap, sub_cloud in itertools.product(tag_wraps, sub_clouds):
        tag_wrap.make_leader_attached()
        tag_wrap.make_leader_free()
        tag_leader_ends = tag_wrap.get_leader_ends()
        for end in tag_leader_ends:
            if sub_cloud.is_point_on_group(end):
                sub_cloud.is_tagged = True


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


selected_views = []  # type: list[ViewSelectionItem]

all_views = list(
    DB.FilteredElementCollector(doc)
    .OfClass(DB.View)
    .WhereElementIsNotElementType()
)

view_items = []
for view in all_views:
    view_wrap = ViewWrap(view)
    if view_wrap.is_valid_for_revision_cloud:
        view_item = ViewSelectionItem(view_wrap)
        view_items.append(view_item)

sorted_view_items = Sorter().sort_by_attrs(
    view_items,
    ['grouping_name', 'name']
)  # type: list[ViewSelectionItem]

view_selection_groups = ViewSelectionGroups()
view_selection_groups.group_views(sorted_view_items)

selected_views = forms.SelectFromList.show(
    context=view_selection_groups.get_view_groups(),
    title='Select Views With Revision Clouds',
    multiselect=True,
    button_name='Tag Revision Clouds on Selected Views',
    name_attr='name',
    group_selector_title='View Groups',
    default_group=view_selection_groups.all_combined.name
)  # type: list[ViewSelectionItem]


if selected_views:
    with revit.TransactionGroup('Tag All Revision Clouds'):
        for view_item in selected_views:
            view_wrap = view_item.view_wrap
            view_collector = ViewElementsCollector(doc, view_wrap)
            revision_clouds = view_collector.revision_clouds()
            clouds = [
                ViewRevisionCloud(cloud) for cloud in revision_clouds
            ]

            for cloud in clouds:
                existing_tags = cloud.existing_tag_wraps()
                sub_clouds = cloud.get_subclouds()
                if existing_tags:
                    if len(sub_clouds) == 1:
                        sub_clouds[0].is_tagged = True
                    elif len(sub_clouds) > 1:
                        with revit.DryTransaction():
                            mark_tagged_sub_clouds(existing_tags, sub_clouds)

                with revit.Transaction():
                    for sub_cloud in sub_clouds:
                        if not sub_cloud.is_tagged:
                            result = OutputResult(
                                view_name=view_item.name,
                                view_id=view_wrap.id,
                                rev_cloud_id=cloud.id
                            )
                            try:
                                new_tag_wrap = TagWrap.tag_sub_cloud(
                                    tag_type_id=rev_tag_type_id,
                                    view_wrap=view_wrap,
                                    revision_sub_cloud=sub_cloud
                                )
                                success_mark = ':white_heavy_check_mark:'
                                result.print_result(
                                    symbol=success_mark,
                                    tag_id=new_tag_wrap.id
                                )
                            except AttemptFailure as err:
                                failure_mark = ':cross_mark:'
                                result.print_result(
                                    symbol=failure_mark,
                                    fail_txt=err
                                )
