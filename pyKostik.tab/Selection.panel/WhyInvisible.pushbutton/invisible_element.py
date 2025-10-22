import itertools
from Autodesk.Revit import DB
from System import Enum
import source_view as sv
import check_exceptions as che
import c_geometry as geom

try:
    from typing import Iterator
except ImportError:
    pass


class InvisibleElement(object):
    def __init__(self, elem):
        # type: (DB.Element) -> None
        self._elem = elem

    @property
    def doc(self):
        return self._elem.Document

    @property
    def id(self):
        return self._elem.Id

    @property
    def cat(self):
        # type: () -> DB.Category | None
        if self.has_category:
            return self._elem.Category

    @property
    def has_category(self):
        # type: () -> bool
        if not hasattr(self._elem, 'Category'):
            return False

        if self._elem.Category is None:
            return False

        return True

    @property
    def is_model_category(self):
        if not self.has_category:
            return False

        if self.cat.CategoryType == DB.CategoryType.Model:
            return True

        return False

    @property
    def is_annotation_category(self):
        if not self.has_category:
            return False

        if self.cat_type == DB.CategoryType.Annotation:
            return True

        return False

    @property
    def cat_type(self):
        # type: () -> DB.CategoryType | None
        if self.has_category:
            return self.cat.CategoryType

    @property
    def unwrap(self):
        return self._elem

    @property
    def workset_id(self):
        return self._elem.WorksetId

    def is_visible(self, view):
        # type: (sv.SourceView) -> bool
        vis_in_view_filter = DB.VisibleInViewFilter(view.doc, view.id)
        return vis_in_view_filter.PassesFilter(self.doc, self.id)

    def is_hidden(self, view):
        # type: (sv.SourceView) -> None
        return self._elem.IsHidden(view.unwrap)

    @property
    def has_phases(self):
        return self._elem.HasPhases()

    @property
    def is_workset_closed(self):
        workset = self._get_workset()
        return not workset.IsOpen

    @property
    def is_viewer(self):
        # type: () -> bool
        if not self.has_category:
            return False

        if self.cat.Id == DB.ElementId(DB.BuiltInCategory.OST_Viewers):
            return True

        return False

    def _get_workset(self):
        # type: () -> DB.Workset
        table = self.doc.GetWorksetTable()
        return table.GetWorkset(self.workset_id)

    @property
    def workset_name(self):
        # type: () -> str
        workset = self._get_workset()
        return workset.Name

    def get_bb(self, view=None):
        # type: (sv.SourceView | None) -> DB.BoundingBoxXYZ | None
        if view is not None:
            view = view.unwrap

        return self._elem.get_BoundingBox(view)

    def get_all_bb_corners(self, view):
        # type: (sv.SourceView) -> list[DB.XYZ]
        bb = self.get_bb(view)
        bb_min = bb.Min
        bb_max = bb.Max
        xs = bb_min.X, bb_max.X
        ys = bb_min.Y, bb_max.Y
        zs = bb_min.Z, bb_max.Z
        corners = []
        for x, y, z in itertools.product(xs, ys, zs):
            p = DB.XYZ(x, y, z)
            corners.append(p)
        return corners

    def get_geom_elem(self, opts=None):
        # type: (DB.Options) -> DB.GeometryElement
        if opts is None:
            opts = DB.Options()
        return self._elem.get_Geometry(opts)

    def yeld_geometry(self, opts=None):
        # type: (DB.Options) -> Iterator[DB.GeometryObject]
        geom_elem = self.get_geom_elem(opts)
        return self._yeld_geom_objects(geom_elem)

    def yeld_transformed_geometry(self, transform, opts=None):
        # type: (DB.Options, DB.Transform) -> Iterator[DB.GeometryObject]
        geom_elem = self.get_geom_elem(opts)
        geom_elem = geom_elem.GetTransformed(transform)
        return self._yeld_geom_objects(geom_elem)

    def _yeld_geom_objects(self, geom_elem):
        # type: (DB.GeometryElement) -> Iterator[DB.GeometryObject]
        for geom_obj in geom_elem:
            if isinstance(geom_obj, DB.GeometryInstance):
                sub_geom_elem = geom_obj.GetInstanceGeometry()
                sub_objects = self._yeld_geom_objects(sub_geom_elem)

                for sub_obj in sub_objects:
                    yield sub_obj

            else:
                yield geom_obj

    @property
    def design_option(self):
        # type: () -> DB.DesignOption | None
        return self._elem.DesignOption

    def get_phase_status(self, view_phase_id):
        # type: (DB.ElementId) -> DB.ElementOnPhaseStatus
        return self._elem.GetPhaseStatus(view_phase_id)


class ViewTag(InvisibleElement):
    def get_parent_view(self):
        # type: () -> DB.View | None
        PARENT_BIPS = (
            DB.BuiltInParameter.SECTION_PARENT_VIEW_NAME,
            DB.BuiltInParameter.VIEW_FIXED_SKETCH_PLANE
        )

        for bip in PARENT_BIPS:
            param = self._elem.get_Parameter(bip)

            if param is not None:
                parent_id = param.AsElementId()

                if parent_id != DB.ElementId.InvalidElementId:
                    parent = self.doc.GetElement(parent_id)

                    if isinstance(parent, DB.SketchPlane):
                        return self.doc.GetElement(parent.OwnerViewId)

                    return parent

    def is_visible_at_scale(self, scale):
        # type: (int) -> bool
        hide_at_coarser_param = self.get_coarser_scale_param()
        return hide_at_coarser_param.AsInteger() >= scale

    def get_coarser_scale_param(self):
        # type: () -> DB.Parameter
        METRIC = DB.BuiltInParameter.SECTION_COARSER_SCALE_PULLDOWN_METRIC
        IMPERIAL = DB.BuiltInParameter.SECTION_COARSER_SCALE_PULLDOWN_IMPERIAL

        hide_at_coarser_param = self._elem.get_Parameter(METRIC)

        if hide_at_coarser_param is None:
            hide_at_coarser_param = self._elem.get_Parameter(IMPERIAL)

        if hide_at_coarser_param is None:
            raise che.ElementError(
                elem_id=str(self.id),
                msg=(
                    'View tag does not have parameter'
                    '"Hide at scales coarser than"'
                )
            )

        return hide_at_coarser_param

    @property
    def coarser_scale_is_custom(self):
        # type: () -> bool
        coarser_scale_param = self.get_coarser_scale_param()
        if coarser_scale_param is not None:
            return coarser_scale_param.AsInteger() == -1

    @property
    def is_callout(self):
        # type: () -> bool
        tagged_view = self.get_tagged_view()

        if tagged_view is not None:
            return tagged_view.IsCallout

        return False

    @property
    def is_section(self):
        # type: () -> bool
        tagged_view = self.get_tagged_view()

        if tagged_view is not None:
            return tagged_view.ViewType == DB.ViewType.Section

        return False

    @property
    def is_detail(self):
        # type: () -> bool
        tagged_view = self.get_tagged_view()

        if tagged_view is not None:
            return tagged_view.ViewType == DB.ViewType.Detail

        return False

    @property
    def is_elevation(self):
        # type: () -> bool
        tagged_view = self.get_tagged_view()

        if tagged_view is not None:
            return tagged_view.ViewType == DB.ViewType.Elevation

        return False

    def get_tagged_view(self):
        # type: () -> DB.View | None
        SKETCH_PLANE_BIP = DB.BuiltInParameter.VIEW_FIXED_SKETCH_PLANE
        sketch_plane_param = self._elem.get_Parameter(SKETCH_PLANE_BIP)

        if sketch_plane_param is not None:
            sketch_plane_id = sketch_plane_param.AsElementId()
            sketch_plane = self.doc.GetElement(sketch_plane_id)

            if isinstance(sketch_plane, DB.SketchPlane):
                return self.doc.GetElement(sketch_plane.OwnerViewId)

    @property
    def shown_in_parent_view_only(self):
        ONE_VIEW_BIP = DB.BuiltInParameter.SECTION_SHOW_IN_ONE_VIEW_ONLY
        param = self._elem.get_Parameter(ONE_VIEW_BIP)

        if param is None:
            return False

        return param.AsInteger() == 1

    @property
    def has_discipline(self):
        # type: () -> bool
        return self.get_discipline() is not None

    def get_discipline(self):
        # type: () -> DB.ViewDiscipline | None
        param = self._get_discipline_param()

        if param is not None:
            return self._parce_enum_value(DB.ViewDiscipline, param.AsInteger())

    def _get_discipline_param(self):
        # type: () -> DB.Parameter | None
        return self._elem.get_Parameter(DB.BuiltInParameter.VIEW_DISCIPLINE)

    def _parce_enum_value(self, enum, number):
        # type: (Enum, int) -> Enum | None
        for value in Enum.GetValues(enum):
            if int(value) == number:
                return value

    def get_discipline_txt(self):
        # type: () -> str | None
        param = self._get_discipline_param()

        if param is not None:
            return param.AsValueString()

    def get_ui_cat(self):
        # type: () -> DB.Category | None
        """
        Gets the category that is presented to user, e.g. `Callouts`.

        Unlike accessed via `Element.Category` property,
        which is always based on `BuiltInCategory.OST_Viewers`.
        """

        cat_getter = DB.Category.GetCategory

        if self.is_callout:
            return cat_getter(self.doc, DB.BuiltInCategory.OST_Callouts)

        if self.is_elevation:
            return cat_getter(self.doc, DB.BuiltInCategory.OST_Elev)

        if self.is_section or self.is_detail:
            return cat_getter(self.doc, DB.BuiltInCategory.OST_Sections)

    def get_tagged_view_cuboid(self):
        view = self.get_tagged_view()

        if view is None:
            return

        if not view.CropBoxActive:
            return

        transform = DB.Transform.Identity
        transform.BasisZ = view.ViewDirection
        transform.BasisY = view.UpDirection
        transform.BasisX = view.RightDirection
        transform.Origin = view.Origin

        return geom.bb_to_cuboid(view.CropBox, transform)

    def get_tagged_view_bb(self):
        cube = self.get_tagged_view_cuboid()

        if cube is not None:
            internal_bb = cube.GetBoundingBox()
            transform = internal_bb.Transform

            total_bb = DB.BoundingBoxXYZ()
            total_bb.Min = transform.OfPoint(internal_bb.Min)
            total_bb.Max = transform.OfPoint(internal_bb.Max)

            return total_bb


def wrap_to_invisible_element(rvt_elem):
    # type: (DB.Element | any) -> InvisibleElement
    CAT_TYPES_TO_CHECK = (
        DB.CategoryType.Annotation,
        DB.CategoryType.Model,
        DB.CategoryType.Internal
    )

    if not isinstance(rvt_elem, DB.Element):
        raise che.TypeValidationError(
            expected=DB.Element,
            provided=type(rvt_elem)
        )

    invisible_elem = InvisibleElement(rvt_elem)

    if not invisible_elem.has_category:
        raise che.ElementCategoryError(
            'element id <{}> does not have category'
            .format(invisible_elem.id)
        )

    if invisible_elem.cat_type not in CAT_TYPES_TO_CHECK:

        raise che.ElementCategoryError(
            elem_id=invisible_elem.id,
            msg='Category type ({}) can not be checked. '
            .format(invisible_elem.cat_type, )
        )

    if type(rvt_elem) is DB.Element and invisible_elem.is_viewer:
        invisible_elem = ViewTag(rvt_elem)

    return invisible_elem
