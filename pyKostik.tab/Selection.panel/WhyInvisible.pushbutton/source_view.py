from Autodesk.Revit import DB
from Autodesk.Revit import Exceptions as REXEP

from System import Enum
import invisible_element as ie
import check_exceptions as che
import c_geometry as geom


class SourceView(object):
    def __init__(self, view):
        # type: (DB.View) -> None
        self._view = view
        self._validate_type(view, DB.View)

    def _validate_type(self, obj, expected):
        # type: (object, type | tuple[type]) -> None
        if not isinstance(obj, expected):
            raise che.TypeValidationError(
                expected=expected,
                provided=type(obj)
            )

    @property
    def doc(self):
        return self._view.Document

    @property
    def id(self):
        return self._view.Id

    @property
    def unwrap(self):
        return self._view

    @property
    def origin(self):
        return self._view.Origin

    @property
    def up_direction(self):
        return self._view.UpDirection

    @property
    def view_direction(self):
        return self._view.ViewDirection

    @property
    def right_direction(self):
        return self._view.RightDirection

    def is_category_hidden(self, cat_id):
        # type: (DB.ElementId) -> None
        return self._view.GetCategoryHidden(cat_id)

    @property
    def is_in_temp_hidden_mode(self):
        # type: () -> bool
        return self._view.IsTemporaryHideIsolateActive()

    def is_workset_visible(self, workset_id):
        # type: (DB.WorksetId) -> bool
        return self._view.IsWorksetVisible(workset_id)

    @property
    def is_crop_box_active(self):
        # type: () -> bool
        return self._view.CropBoxActive

    @property
    def is_anno_crop_active(self):
        # type: () -> bool
        ANNO_CROP_BIP = DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
        anno_crop_param = self._view.get_Parameter(ANNO_CROP_BIP)

        if anno_crop_param is None:
            return False

        return anno_crop_param.AsInteger() == 1

    @property
    def plane(self):
        # type: () -> DB.Plane
        return DB.Plane.CreateByOriginAndBasis(
            self.origin,
            self.right_direction,
            self.up_direction
        )

    @property
    def crop_box(self):
        return self._view.CropBox

    @property
    def is_crop_shape_rectangle(self):
        crop_manager = self._view.GetCropRegionShapeManager()

        if not crop_manager.ShapeSet:
            return True

        crop_shape = list(
            crop_manager.GetCropShape()
        )  # type: list[DB.CurveLoop]

        if not len(crop_shape) == 1:
            return False

        crop_loop = crop_shape[0]

        if not crop_loop.IsRectangular(crop_loop.GetPlane()):
            return False

        for curve in crop_loop:
            direction = curve.GetEndPoint(1) - curve.GetEndPoint(0)
            abs_dot = abs(direction.DotProduct(DB.XYZ.BasisY))
            abs_round_dot = round(abs_dot, 9)
            parallel = abs_round_dot == 1.0
            orthogonal = abs_round_dot == 0

            if parallel or orthogonal:
                return True

        return False

    @property
    def is_crop_shape_split(self):
        return self._view.GetCropRegionShapeManager().Split

    @property
    def scale(self):
        # type: () -> int
        return self._view.Scale

    def get_filters(self):
        # type: () -> list[DB.FilterElement]
        return [self.doc.GetElement(id) for id in self._view.GetFilters()]

    def is_elem_hidden_by_filter(self, elem, filter):
        # type: (ie.InvisibleElement, DB.FilterElement) -> bool
        if not self._view.GetIsFilterEnabled(filter.Id):
            return False

        if self._view.GetFilterVisibility(filter.Id):
            return False

        if isinstance(filter, DB.SelectionFilterElement):
            if filter.Contains(elem.id):
                return True

        if isinstance(filter, DB.ParameterFilterElement):
            element_filter = filter.GetElementFilter()

            if element_filter is None:
                cat = elem.cat

                if isinstance(elem, ie.ViewTag):
                    cat = elem.get_ui_cat()

                if cat is not None:
                    if cat.Id in filter.GetCategories():
                        return True

            if element_filter.PassesFilter(self.doc, elem.id):
                return True

        return False

    def crop_contains_bb(self, bb, tolerance=10e-6):
        # type: (DB.BoundingBoxXYZ, float) -> bool
        crop = self.crop_box
        projection = crop.Transform.Inverse

        xs = []
        ys = []
        for corner in geom.get_all_bb_corners(bb):
            projected_pt = projection.OfPoint(corner)
            xs.append(projected_pt.X)
            ys.append(projected_pt.Y)

        elem_outlilne_on_view = DB.Outline(
            DB.XYZ(min(xs), min(ys), 0),
            DB.XYZ(max(xs), max(ys), 0)
        )

        crop_outline = DB.Outline(
            DB.XYZ(crop.Min.X, crop.Min.Y, 0),
            DB.XYZ(crop.Max.X, crop.Max.Y, 0)
        )

        return crop_outline.Intersects(elem_outlilne_on_view, tolerance)

    def anno_crop_contains_bb(self, bb, tolerance=10e-6):
        # type: (DB.BoundingBoxXYZ, float) -> bool
        crop = self.crop_box
        projection = crop.Transform.Inverse

        xs = []
        ys = []
        for corner in geom.get_all_bb_corners(bb):
            projected_pt = projection.OfPoint(corner)
            xs.append(projected_pt.X)
            ys.append(projected_pt.Y)

        elem_outlilne_on_view = DB.Outline(
            DB.XYZ(min(xs), min(ys), 0),
            DB.XYZ(max(xs), max(ys), 0)
        )

        crop_manager = self._view.GetCropRegionShapeManager()
        anno_outline = DB.Outline(
            DB.XYZ(
                crop.Min.X - crop_manager.LeftAnnotationCropOffset,
                crop.Min.Y - crop_manager.BottomAnnotationCropOffset,
                0
            ),

            DB.XYZ(
                crop.Max.X + crop_manager.RightAnnotationCropOffset,
                crop.Max.Y + crop_manager.TopAnnotationCropOffset,
                0
            )
        )

        return anno_outline.Intersects(elem_outlilne_on_view, tolerance)

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
        return self._view.get_Parameter(DB.BuiltInParameter.VIEW_DISCIPLINE)

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

    def is_phase_status_hidden(self, status):
        # type: (DB.ElementOnPhaseStatus) -> bool
        phase_filter = self.get_phase_filter()

        if phase_filter is not None:
            presentation = phase_filter.GetPhaseStatusPresentation(status)
            return presentation == DB.PhaseStatusPresentation.DontShow

        return False

    def is_phase_status_overridden(self, status):
        # type: (DB.ElementOnPhaseStatus) -> bool
        phase_filter = self.get_phase_filter()

        if phase_filter is not None:
            presentation = phase_filter.GetPhaseStatusPresentation(status)
            return presentation == DB.PhaseStatusPresentation.ShowOverriden

        return False

    def get_view_phase_id(self):
        # type: () -> DB.ElementId | None
        param = self._view.get_Parameter(DB.BuiltInParameter.VIEW_PHASE)
        if param is not None:
            return param.AsElementId()

    def get_phase_filter(self):
        # type: () -> DB.PhaseFilter | None
        PHASE_FILTER_BIP = DB.BuiltInParameter.VIEW_PHASE_FILTER
        param = self._view.get_Parameter(PHASE_FILTER_BIP)
        if param is not None:
            return self.doc.GetElement(param.AsElementId())


class SourceViewPlan(SourceView):
    def __init__(self, view):
        # type: (DB.ViewPlan) -> None
        self._view = view
        self._validate_type(view, DB.ViewPlan)

    def get_view_range(self):
        return SourceViewRange(self._view.GetViewRange())

    def is_elevation_below_view_depth(self, elevation):
        # type: (float) -> bool
        view_range = self.get_view_range()

        if view_range.is_depth_unlimited:
            return False

        depth_elevation = view_range.get_view_depth_elev(self.doc)
        if elevation < depth_elevation:
            return True

        return False

    def is_elevation_below_view_bottom(self, elevation):
        # type: (float) -> bool
        view_range = self.get_view_range()

        if view_range.is_bottom_clip_unlimited:
            return False

        depth_elevation = view_range.get_view_bottom_clip_elev(self.doc)
        if elevation < depth_elevation:
            return True

        return False

    def is_elevation_above_view_range(self, elevation):
        # type: (float) -> bool
        view_range = self.get_view_range()

        if view_range.is_top_unlimited:
            return False

        top_elevation = view_range.get_top_elev(self.doc)
        if elevation > top_elevation:
            return True

        return False

    def is_elevation_above_cut_plane(self, elevation):
        # type: (float) -> bool
        view_range = self.get_view_range()

        cut_plane_elev = view_range.get_cut_plane_elev(self.doc)
        if elevation > cut_plane_elev:
            return True

        return False

    def crop_contains_bb(self, bb, tolerance=10e-6):
        # type: (DB.BoundingBoxXYZ, float) -> bool
        elem_top = bb.Max.Z
        elem_bottom = bb.Min.Z

        crop = self.crop_box
        crop_min = crop.Min
        crop_max = crop.Max

        outline_min = DB.XYZ(crop_min.X, crop_min.Y, elem_bottom)
        outline_max = DB.XYZ(crop_max.X, crop_max.Y, elem_top)
        crop_outline = DB.Outline(outline_min, outline_max)

        elem_outline = DB.Outline(bb.Min, bb.Max)

        return crop_outline.Intersects(elem_outline, tolerance)


class SourceViewSection(SourceView):
    def __init__(self, view):
        # type: (DB.ViewSection) -> None
        self._view = view
        self._validate_type(view, DB.ViewSection)

    @property
    def is_split(self):
        return self._view.IsSplitSection()

    def any_point_behind_view_pane(self, points):
        # type: (list[DB.XYZ]) -> bool
        return any(self._is_point_behind_border(p, 0) for p in points)

    def all_points_behind_depth(self, points):
        # type: (list[DB.XYZ]) -> bool
        far_clip = self.far_clip_offset
        return all(
            self._is_point_behind_border(p, far_clip) for p in points
        )

    def all_points_behind_depth_cue_end(self, points):
        # type: (list[DB.XYZ]) -> bool
        end_percentage = self._depth_cueing.EndPercentage
        reduced_far_clip = self.far_clip_offset * end_percentage / 100
        return all(
            self._is_point_behind_border(p, reduced_far_clip) for p in points
        )

    def _is_point_behind_border(self,
                                point,
                                view_origin_to_border,
                                tolerance=10e-6):
        # type: (DB.XYZ, float, float) -> bool
        section_direction = self.view_direction.Negate()
        offset_vector = section_direction * view_origin_to_border
        offset_origin = self.origin + offset_vector
        offset_origin_to_point = point - offset_origin

        return self._angle_less_or_eq_90(
            section_direction,
            offset_origin_to_point,
            tolerance
        )

    def _angle_less_or_eq_90(self, vector1, vector2, tolerance):
        # type: (DB.XYZ, DB.XYZ, float) -> bool
        dot_prod = vector1.DotProduct(vector2)
        return dot_prod + tolerance >= 0

    @property
    def no_far_clip(self):
        FAR_CLIPPING_BIP = DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING
        far_clip_param = self._view.get_Parameter(FAR_CLIPPING_BIP)
        return far_clip_param.AsInteger() == 0

    @property
    def far_clip_offset(self):
        # type: () -> float
        FAR_CLIP_OFFSET_BIP = DB.BuiltInParameter.VIEWER_BOUND_OFFSET_FAR
        far_clip_param = self._view.get_Parameter(FAR_CLIP_OFFSET_BIP)
        return far_clip_param.AsDouble()

    @property
    def is_depth_cueing_enabled(self):
        # type: () -> bool
        try:
            return self._depth_cueing.EnableDepthCueing

        except REXEP.InvalidOperationException as io:
            if io.Message == 'This view cannot use Depth Cueing':
                return False

    @property
    def _depth_cueing(self):
        # type: () -> DB.ViewDisplayDepthCueing
        return self._view.GetDepthCueing()


class SourceViewRange(object):
    def __init__(self, view_range):
        # type: (DB.PlanViewRange) -> None
        self._view_range = view_range

    @property
    def is_depth_unlimited(self):
        return self._is_unlimited(DB.PlanViewPlane.ViewDepthPlane)

    @property
    def is_bottom_clip_unlimited(self):
        return self._is_unlimited(DB.PlanViewPlane.BottomClipPlane)

    @property
    def is_top_unlimited(self):
        return self._is_unlimited(DB.PlanViewPlane.TopClipPlane)

    def get_top_elev(self, doc):
        # type: (DB.Document) -> float
        return self._get_elevation(doc, DB.PlanViewPlane.TopClipPlane)

    def get_cut_plane_elev(self, doc):
        # type: (DB.Document) -> float
        return self._get_elevation(doc, DB.PlanViewPlane.CutPlane)

    def get_view_bottom_clip_elev(self, doc):
        # type: (DB.Document) -> float
        return self._get_elevation(doc, DB.PlanViewPlane.BottomClipPlane)

    def get_view_depth_elev(self, doc):
        # type: (DB.Document) -> float
        return self._get_elevation(doc, DB.PlanViewPlane.ViewDepthPlane)

    def _is_unlimited(self, plan_view_plane):
        # type: (DB.PlanViewRange) -> bool
        UNLIMITED_ID = DB.PlanViewRange.Unlimited
        return self._view_range.GetLevelId(plan_view_plane) == UNLIMITED_ID

    def _get_elevation(self, doc, plan_view_plane):
        # type: (DB.Document, DB.PlanViewRange) -> float
        top_lvl_id = self._view_range.GetLevelId(plan_view_plane)
        lvl = doc.GetElement(top_lvl_id)  # type: DB.Level
        lvl_elevation = lvl.ProjectElevation
        offset = self._view_range.GetOffset(plan_view_plane)
        return lvl_elevation + offset


class Source3DView(SourceView):
    def __init__(self, view):
        # type: (DB.View3D) -> None
        self._view = view
        self._validate_type(view, DB.View)

    def section_box_contains_elem(self, elem, tolerance=10e-6):
        # type: (ie.InvisibleElement, float) -> bool
        section_box = self._view.GetSectionBox()
        section_cube = geom.bb_to_cuboid(section_box, section_box.Transform)
        intersect_filter = DB.ElementIntersectsSolidFilter(section_cube)
        return intersect_filter.PassesFilter(elem.doc, elem.id)

    @property
    def is_section_box_active(self):
        return self._view.IsSectionBoxActive


def wrap_to_source_view(rvt_view):
    # type: (DB.View) -> SourceView
    if not isinstance(rvt_view, DB.View):
        raise che.TypeValidationError(
            expected=DB.View,
            provided=type(rvt_view)
        )

    if isinstance(rvt_view, DB.ViewPlan):
        return SourceViewPlan(rvt_view)

    if isinstance(rvt_view, DB.ViewSection):
        return SourceViewSection(rvt_view)

    if isinstance(rvt_view, DB.View3D):
        return Source3DView(rvt_view)

    raise che.ViewError(
        str(rvt_view.Id),
        'There is no check for this kind of view.'
    )
