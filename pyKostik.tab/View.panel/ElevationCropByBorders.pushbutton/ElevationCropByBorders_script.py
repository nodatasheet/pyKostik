"""Crops Elevation or Section view by the borders of specified elements."""

from pyrevit import DB, forms, revit, script
from System.Collections.Generic import List
from System import Type


def is_sec_or_elev(view):
    # type: (DB.View) -> bool
    """Checks whether view is Section or Elevation"""
    return view.ViewType in (DB.ViewType.Elevation, DB.ViewType.Section)


def get_parent_view(viewport):
    # type: (DB.Viewport) -> DB.View
    return doc.GetElement(viewport.ViewId)


def get_views_if_all_elev_or_sec(elements):
    # type: (list[DB.Element]) -> list[DB.View]
    """Gets views from elements if all elements
    belong to elevation or section or viewport of elevation / section.

    Otherwise return empty list."""
    views = []
    for elem in elements:
        if isinstance(elem, DB.View) and is_sec_or_elev(elem):
            views.append(elem)
        elif isinstance(elem, DB.Viewport):
            view = get_parent_view(elem)
            if is_sec_or_elev(view):
                views.append(view)
        else:
            views = []
            break
    return views


def length_to_internal_units(length):
    # type: (float) -> float
    """Convert Length from document units to Revit's internal units"""
    revit_ver = int(app.VersionNumber)
    doc_units = doc.GetUnits()
    if revit_ver < 2021:
        ui_unit = doc_units.GetFormatOptions(DB.UnitType.UT_Length)\
            .DisplayUnits
    else:
        ui_unit = doc_units.GetFormatOptions(DB.SpecTypeId.Length)\
            .GetUnitTypeId()
    return DB.UnitUtils.ConvertToInternalUnits(length, ui_unit)


def get_datum_lines(view, datums):
    # type: (DB.View, list[DB.Level] | list[DB.Grid]) -> list[DB.Line]
    datum_lines = []
    for datum in datums:
        line = datum.GetCurvesInView(DB.DatumExtentType.Model, view)[0]
        datum_lines.append(line)
    return datum_lines


def curve_loop_to_polyline(curve_loop):
    # type: (DB.CurveLoop) -> DB.PolyLine
    points = List[DB.XYZ]()
    [points.AddRange(c.Tessellate()) for c in curve_loop]
    return DB.PolyLine.Create(points)


def get_face_by_normal(solid, face_normal):
    # type: (DB.Solid, DB.XYZ) -> DB.PlanarFace | None
    for face in solid.Faces:
        if isinstance(face, DB.PlanarFace)\
                and face.FaceNormal.IsAlmostEqualTo(face_normal):
            return face


def get_elems_edges_by_normal(elements, face_normal, geom_options):
    # type: (list[DB.Element], DB.XYZ, DB.Options) -> list[DB.CurveLoop]
    curve_loops = []
    for elem in elements:
        geom_elems = elem.get_Geometry(geom_options)
        for geom_elem in geom_elems:
            if isinstance(geom_elem, DB.Solid):
                face = get_face_by_normal(geom_elem, face_normal)
                if face:
                    curve_loops.extend(face.GetEdgesAsCurveLoops())
            elif isinstance(geom_elem, DB.GeometryInstance):
                geom_objects = geom_elem.GetInstanceGeometry()
                for geom_obj in geom_objects:
                    if isinstance(geom_obj, DB.Solid):
                        face = get_face_by_normal(geom_obj, face_normal)
                        if face:
                            curve_loops.extend(face.GetEdgesAsCurveLoops())
    return curve_loops


def pick_vertical_lines(edges):
    # type: (list[DB.CurveLoop]) -> list[DB.Line]
    """Picks lines that parallel to axis Z"""
    vertical_lines = []
    for curve_loop in edges:
        for curve in curve_loop:
            if isinstance(curve, DB.Line):
                dot_prod = curve.Direction.DotProduct(DB.XYZ.BasisZ)
                if round(abs(dot_prod), 6) == 1:
                    vertical_lines.append(curve)
    return vertical_lines


def pick_non_vertical_lines(edges):
    # type: (list[DB.CurveLoop]) -> list[DB.Line]
    """Picks lines that are NOT parallel to axis Z"""
    non_vertical_lines = []
    for curve_loop in edges:
        for curve in curve_loop:
            if isinstance(curve, DB.Line):
                dot_prod = curve.Direction.DotProduct(DB.XYZ.BasisZ)
                if round(abs(dot_prod), 6) != 1:
                    non_vertical_lines.append(curve)
    return non_vertical_lines


def closed_loop_by_points(points):
    # type(list[DB.XYZ]) -> DB.CurveLoop()
    curve_loop = DB.CurveLoop()
    for i in range(len(points) - 1):
        if points[i].DistanceTo(points[i + 1]) > app.ShortCurveTolerance:
            line = DB.Line.CreateBound(points[i], points[i + 1])
            curve_loop.Append(line)
        else:
            forms.alert('Crop border too small', exitscript=True)
    curve_loop.Append(DB.Line.CreateBound(points[-1], points[0]))
    return curve_loop


def line_end_as_uv(line, plane, end_index):
    # type: (DB.Line, DB.Plane, int) -> float
    return plane.Project(line.GetEndPoint(end_index))[0]


def uv_as_xyz(uv, plane):
    # type: (DB.UV, DB.Plane) -> DB.XYZ
    xyz_on_plane = plane.Origin + uv.U * plane.XVec + uv.V * plane.YVec
    return xyz_on_plane


uiapp = revit.HOST_APP.uiapp
app = uiapp.Application
doc = revit.doc
active_view = doc.ActiveView

my_logger = script.get_logger()
my_config = script.get_config()

selected_borders = [x for x in ('walls',
                                'grids',
                                'ceilings',
                                'floors',
                                'levels',)
                    if my_config.get_option(x, False)]

forms.alert_ifnot(selected_borders,
                  'No borders selected.\n\n'
                  'Select them in options\n(Shift-Click on button)',
                  exitscript=True)

crop_offset = length_to_internal_units(my_config.get_option('crop_offset', 0))

selection = revit.get_selection().elements
selected_views = get_views_if_all_elev_or_sec(selection)

views = []
if selected_views:
    use_selection = forms.ask_to_use_selected("Views",
                                              count=len(selected_views),
                                              multiple=True)
    if use_selection is True:
        views = selected_views

if isinstance(active_view, DB.ViewSection) and not views:
    use_active_view = forms.alert("Use current View?", yes=True, no=True)
    if use_active_view is True:
        views.append(active_view)

if not views:
    ask_to_select_views = forms.select_views(
        "Select Section or Elevation views",
        filterfunc=lambda view: is_sec_or_elev(view))
    if ask_to_select_views:
        views = ask_to_select_views

if not views:
    script.exit()

transaction_group = DB.TransactionGroup(doc, "Crop Views by Borders")
transaction_group.Start()

for view in views:
    view_name = view.Name
    view_dir = view.ViewDirection  # type: DB.XYZ
    if view.CropBoxActive is not True:
        ask_activate_crop = forms.alert(
            'View Crop Region should be enabled.'
            ' Enable Crop Region for View "{}?"'.format(view_name),
            yes=True,
            no=True)
        if ask_activate_crop is True:
            with revit.Transaction("Enable Crop Region"):
                view.CropBoxActive = True
        else:
            transaction_group.RollBack()
            script.exit()

    shape_manager = view.GetCropRegionShapeManager()

    if shape_manager.Split is True:
        ask_remove_split = forms.alert(
            'View with View Breaks not supported.'
            ' Remove all the View Breaks for View "{}"?'.format(view_name),
            exitscript=True)
        if ask_remove_split is True:
            with revit.Transaction("Remove View's Crop Splits"):
                shape_manager.RemoveSplit()
        else:
            transaction_group.RollBack()
            script.exit()

    crop_shape = shape_manager.GetCropShape()
    crop_polyline = curve_loop_to_polyline(crop_shape[0])
    crop_outline = crop_polyline.GetOutline()  # type: DB.Outline
    crop_as_solid = DB.GeometryCreationUtilities\
        .CreateExtrusionGeometry(crop_shape,
                                 - view_dir,
                                 1e-9)

    outline_intersection_filter = DB.BoundingBoxIntersectsFilter(crop_outline)
    solid_intersection_filter = DB.ElementIntersectsSolidFilter(crop_as_solid)

    floor_ceiling_classes = List[Type]()

    if 'ceilings' in selected_borders:
        floor_ceiling_classes.Add(DB.Ceiling)

    if 'floors' in selected_borders:
        floor_ceiling_classes.Add(DB.Floor)

    if floor_ceiling_classes:
        multiclass_filter = DB.ElementMulticlassFilter(floor_ceiling_classes)
        floors_and_ceilings = DB.FilteredElementCollector(doc, view.Id)\
            .WherePasses(multiclass_filter)\
            .WherePasses(outline_intersection_filter)\
            .WherePasses(solid_intersection_filter)\
            .ToElements()
    else:
        floors_and_ceilings = List[DB.Element]()

    if 'walls' in selected_borders:
        walls = DB.FilteredElementCollector(doc, view.Id)\
            .OfClass(DB.Wall)\
            .WherePasses(outline_intersection_filter)\
            .WherePasses(solid_intersection_filter)\
            .ToElements()
    else:
        walls = List[DB.Element]()

    parts = DB.FilteredElementCollector(doc, view.Id)\
        .OfClass(DB.Part)\
        .WherePasses(outline_intersection_filter)\
        .ToElements()
    # .WherePasses(solid_intersection_filter)  # did not work with parts

    for part in parts:
        parent_cat_id = part.OriginalCategoryId
        if parent_cat_id == DB.ElementId(DB.BuiltInCategory.OST_Walls)\
                and 'walls' in selected_borders:
            walls.Add(part)
        if parent_cat_id == DB.ElementId(DB.BuiltInCategory.OST_Floors)\
                and 'floors' in selected_borders:
            floors_and_ceilings.Add(part)
        if parent_cat_id == DB.ElementId(DB.BuiltInCategory.OST_Ceilings)\
                and 'ceilings' in selected_borders:
            floors_and_ceilings.Add(part)

    if 'levels' in selected_borders:
        levels = DB.FilteredElementCollector(doc, view.Id)\
            .OfClass(DB.Level)\
            .ToElements()
        level_lines = get_datum_lines(view, levels)
    else:
        level_lines = []

    if 'grids' in selected_borders:
        levels = DB.FilteredElementCollector(doc, view.Id)\
            .OfClass(DB.Grid)\
            .ToElements()
        grid_lines = get_datum_lines(view, levels)
    else:
        grid_lines = []

    geom_options = DB.Options()
    geom_options.View = view

    horizontal_border_edges = get_elems_edges_by_normal(floors_and_ceilings,
                                                        view_dir,
                                                        geom_options)

    vertical_border_edges = get_elems_edges_by_normal(walls,
                                                      view_dir,
                                                      geom_options)

    vertical_lines = pick_vertical_lines(vertical_border_edges)
    vertical_lines.extend(grid_lines)

    non_vertical_lines = pick_non_vertical_lines(horizontal_border_edges)
    non_vertical_lines.extend(level_lines)

    # redefine the crop plane so its origin is at outline origin
    outline_origin = (crop_outline.MinimumPoint
                      + crop_outline.MaximumPoint) / 2
    crop_shape_normal = view_dir
    basiz_z = DB.XYZ.BasisZ
    crop_plane = DB.Plane.CreateByOriginAndBasis(
        outline_origin,
        basiz_z.CrossProduct(view_dir),
        basiz_z)

    # projecting line ends to crop plane
    u_coords = [
        line_end_as_uv(line, crop_plane, 0).U for line in vertical_lines]
    # floor can be sloped, use its top point
    v_coords = [max(line_end_as_uv(line, crop_plane, ind).V for ind in (0, 1))
                for line in non_vertical_lines]

    # add old border maxs and mins
    old_min_uv = crop_plane.Project(crop_outline.MinimumPoint)[0]
    old_max_uv = crop_plane.Project(crop_outline.MaximumPoint)[0]
    for uv in (old_min_uv, old_max_uv):
        u_coords.append(uv.U)
        v_coords.append(uv.V)

    # pick closest border coords to crop origin UV(0, 0))
    left = max((u for u in u_coords if u < 0)) - crop_offset
    right = min((u for u in u_coords if u >= 0)) + crop_offset
    top = min((v for v in v_coords if v >= 0)) + crop_offset
    bottom = max((v for v in v_coords if v < 0)) - crop_offset

    crop_corners_uv = [DB.UV(left, bottom),
                       DB.UV(left, top),
                       DB.UV(right, top),
                       DB.UV(right, bottom)]

    crop_corners_xyz = [uv_as_xyz(uv, crop_plane) for uv in crop_corners_uv]
    new_crop = closed_loop_by_points(crop_corners_xyz)

    with revit.Transaction('Crop View by Borders'):
        shape_manager.SetCropShape(new_crop)

try:
    transaction_group.Assimilate()

except Exception as errmsg:
    transaction_group.Rollback()
    my_logger.error('Error in TransactionGroup Commit: rolled back.')
    my_logger.error('Error: %s', errmsg)
