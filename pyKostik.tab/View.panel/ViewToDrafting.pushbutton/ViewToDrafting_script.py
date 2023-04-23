"""Converts current view to a drafting view."""

import os
import traceback
import clr
import shutil
import uuid
import tempfile

from System import EventHandler
from System.Collections.Generic import List

from pyrevit import revit, DB, UI, HOST_APP, forms, script

DETAIL_CREATON_FAILURES = (
    DB.BuiltInFailures.CurveFailures.TooShort,
    DB.BuiltInFailures.FilledRegionFailures.CannotDrawFilledRegionError,
    DB.BuiltInFailures.JoinElementsFailures.CannotJoinElementsError,
    DB.BuiltInFailures.SplineFailures.CannotCreateSpline
)

MAX_RECOMMENDED_GEOM_QTY = 100000

doc = HOST_APP.doc  # type: DB.Document
app = HOST_APP.app
uidoc = HOST_APP.uidoc
uiapp = HOST_APP.uiapp
active_view = HOST_APP.active_view
logger = script.get_logger()

drafting_view = None


class InvalidOperationException(Exception):
    """Invalid Operation Exception"""
    pass


class ValidationError(Exception):
    """Base class for Validation Errors"""
    pass


class TypeValidationError(ValidationError):
    """Type Validation Error"""
    pass


def subscribe_dialog_temp_view_mode():
    uiapp.DialogBoxShowing += \
        EventHandler[UI.Events.DialogBoxShowingEventArgs](
            on_dialog_temp_view_mode)


def unsubscribe_dialog_temp_view_mode():
    uiapp.DialogBoxShowing -= \
        EventHandler[UI.Events.DialogBoxShowingEventArgs](
            on_dialog_temp_view_mode)


def on_dialog_temp_view_mode(sender, args):
    # type: (DB.UIApplication, UI.Events.DialogBoxShowingEventArgs) -> None
    """On dialog: Export with Temporary Hide/Isolate
    Choose: Leave the Temporary Hide/Isolate mode on and export"""
    try:
        really_print = 'TaskDialog_Really_Print_Or_Export_Temp_View_Modes'
        if args.DialogId == really_print:
            logger.info('Canceling Export with Temporary Hide/Isolate dialog')
            args.OverrideResult(1002)
            # 1001 call TaskDialogResult.CommandLink1
            # 1002 call TaskDialogResult.CommandLink2
    except Exception as err:
        return InvalidOperationException('Failed canceling dialog.'
                                         '\nerror: {}'.format(err))


class SourceView(object):

    ALLOWED_TYPES = (
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.Elevation,
        DB.ViewType.ThreeD,
        DB.ViewType.DrawingSheet,
        DB.ViewType.DraftingView,
        DB.ViewType.EngineeringPlan,
        DB.ViewType.AreaPlan,
        DB.ViewType.Section,
        DB.ViewType.Detail,
        DB.ViewType.Legend,
        DB.ViewType.Walkthrough
    )  # type: tuple[DB.ViewType]

    TYPES_REQUIRE_SHEET = (
        DB.ViewType.ThreeD,
        DB.ViewType.Walkthrough
    )  # type: tuple[DB.ViewType]

    _view = None

    def __init__(self, source_view):
        # type: (DB.View) -> None
        self._view = source_view

    def hide_dimensions_temporary(self):
        """Temporary hides dimensions in view."""
        self._view.HideCategoryTemporary(
            DB.ElementId(DB.BuiltInCategory.OST_Dimensions))

    def place_on_empty_sheet(self):
        # type: () -> None
        empty_sheet = DB.ViewSheet.Create(doc, DB.ElementId.InvalidElementId)
        view_copy = self._view.Duplicate(
            DB.ViewDuplicateOption.WithDetailing)
        DB.Viewport.Create(doc, empty_sheet.Id, view_copy, DB.XYZ.Zero)
        self._view = empty_sheet
        return self.view

    @property
    def can_convert(self):
        # type: () -> None
        return self.view_type in self.ALLOWED_TYPES

    @property
    def requires_sheet(self):
        # type: () -> bool
        return self.view_type in self.TYPES_REQUIRE_SHEET

    @property
    def view(self):
        # type: () -> DB.View
        return self._view

    @property
    def view_type(self):
        # type: () -> DB.ViewType
        return self._view.ViewType


class DestinationView(object):

    _view = None

    def create_drafting_view(self):
        # type: () -> DB.ViewDrafting
        view_type = self._get_first_drafting_view_type()
        self._view = \
            DB.ViewDrafting.Create(doc, view_type.Id)
        return self.view

    def _get_first_drafting_view_type(self):
        # type: () -> DB.ViewFamilyType
        view_types = \
            DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
        for view_type in view_types:
            if view_type.ViewFamily == DB.ViewFamily.Drafting:
                return view_type

    @property
    def view(self):
        # type: () -> DB.View
        return self._view


class DWGReimporter(object):

    _view = None
    _export_opts = None
    _import_opts = None
    _imported = None
    __temp_dir = None
    __temp_file_name = None
    __temp_file_path = None

    def __init__(self, source_view):
        # type: (str, DB.View) -> None
        self.validate_type(source_view, DB.View)
        self._view = source_view

    def validate_type(self, obj, expected_type):
        # type: (object, type) -> None
        if not isinstance(obj, expected_type):
            raise TypeValidationError(
                'Expected <{}>, got <{}>'.format(expected_type.__name__,
                                                 type(obj).__name__))

    def export_view(self, view=None):
        # type: (DB.View) -> bool
        """Exports view to a temporary DWG file."""
        logger.info('Exporting DWG to {}'.format(self.__temp_file_path))

        self._setup_temp_file_path()
        self._setup_default_export_opts()

        if view is not None:
            self.validate_type(source_view, DB.View)
            self._view = view

        view_id = List[DB.ElementId]()
        view_id.Add(self._view.Id)
        self.__view_exported = doc.Export(self.__temp_dir,
                                          self.__temp_file_name,
                                          view_id,
                                          self._export_opts)

        if self.__view_exported is True:
            return self.temp_file_path
        else:
            raise InvalidOperationException(
                "Could not convert the view due to DWG export failure")

    def _setup_temp_file_path(self):
        self.__temp_dir = tempfile.mkdtemp()
        self.__temp_file_name = str(uuid.uuid4()) + ".dwg"
        self.__temp_file_path = os.path.join(
            self.__temp_dir, self.__temp_file_name)

    def _setup_default_export_opts(self):
        # type: () -> None
        self._export_opts = DB.DWGExportOptions()
        self._export_opts.MergedViews = True
        self._export_opts.Colors = DB.ExportColorMode.TrueColorPerView
        self._export_opts.PreserveCoincidentLines = False

    def import_to_view(self, view):
        # type: (DB.View) -> DB.Element
        """Imports temporary DWG file to the specified view."""
        logger.info('Importing DWG from {}'.format(self.__temp_file_path))

        if self.__temp_file_path is None:
            raise InvalidOperationException(
                'Nothing to Import. Check that view was properly exported '
                'using same instance.')

        if not os.path.exists(self.__temp_file_path):
            raise InvalidOperationException(
                'Nothing to Import. File does not exist.')

        self._setup_default_import_opts()
        imported_id = clr.Reference[DB.ElementId]()
        imported = doc.Import(self.__temp_file_path,
                              self._import_opts,
                              view,
                              imported_id)
        if imported is True:
            self._imported = doc.GetElement(imported_id.Value)
            return self.imported
        else:
            raise InvalidOperationException(
                "Could not convert the view due to DWG import failure.\n"
                "Import file path: {}".format(self.__temp_file_path))

    def delete_import(self):
        doc.Delete(self._imported.Id)

    def _setup_default_import_opts(self):
        # type: () -> None
        self._import_opts = DB.DWGImportOptions()
        self._import_opts.ThisViewOnly = True

    def request_removing_temp_file(self):
        """Silently removes temporary file.
        Returns True if succeeds, False otherwise.
        """
        # type: () -> bool
        if self.__temp_dir is not None:
            shutil.rmtree(self.__temp_dir, True)
            if not os.path.exists(self.__temp_dir):
                self.__temp_dir = None
                self.__temp_file_name = None
                self.__temp_file_path = None
                return False
            else:
                return True

    @property
    def temp_file_path(self):
        # type: () -> str
        return self.__temp_file_path

    @property
    def export_options(self):
        # type: () -> DB.DWGExportOptions
        return self._export_opts

    @property
    def import_options(self):
        # type: () -> DB.DWGImportOptions
        return self._import_opts

    @property
    def imported(self):
        return self._imported


class GeometryPackages(object):
    """Packs element geometry objects according to geometry type."""

    _curves = []
    _edges = []
    _faces = []
    _meshes = []
    _points = []
    _polylines = []
    _profiles = []
    _solids = []
    _other = []

    def __init__(self, geometry_element):
        # type: (DB.GeometryElement) -> None
        self.validate_type(geometry_element, DB.GeometryElement)
        self._geometry_elem = geometry_element
        geom_objects = list(self._geometry_elem)
        if geom_objects:
            self._pack_geometry_objects(geom_objects)

    def validate_type(self, obj, expected_type):
        # type: (object, type) -> None
        if not isinstance(obj, expected_type):
            raise TypeValidationError(
                'Expected <{}>, got <{}>'.format(expected_type.__name__,
                                                 type(obj).__name__))

    def _pack_geometry_objects(self, geom_objects):
        # type: (list[DB.GeometryObject]) -> None
        for geom in geom_objects:
            if isinstance(geom, DB.GeometryInstance):
                self._pack_geometry_objects(geom.GetInstanceGeometry())
            elif isinstance(geom, DB.Solid):
                self._solids.append(geom)
            elif isinstance(geom, DB.Curve):
                self._curves.append(geom)
            elif isinstance(geom, DB.Edge):
                self._edges.append(geom)
            elif isinstance(geom, DB.Face):
                self._faces.append(geom)
            elif isinstance(geom, DB.Mesh):
                self._meshes.append(geom)
            elif isinstance(geom, DB.Point):
                self._points.append(geom)
            elif isinstance(geom, DB.PolyLine):
                self._polylines.append(geom)
            elif isinstance(geom, DB.Profile):
                self._profiles.append(geom)

    @property
    def all_geometry(self):
        # type: () -> dict[str: DB.GeometryObject]
        return {'curves': self._curves,
                'edges': self._edges,
                'faces': self._faces,
                'meshes': self._meshes,
                'points': self._points,
                'polylines': self._polylines,
                'profiles': self._profiles,
                'solids': self._solids,
                'other': self._other}

    @property
    def total_qty(self):
        # type: () -> int
        """Quantity of all geometry objects in all packs."""
        return sum([len(geom) for geom in self.all_geometry.values()])

    @property
    def curves(self):
        # type: () -> list[DB.Curve]
        return self._curves

    @property
    def edges(self):
        # type: () -> list[DB.Edge]
        return self._edges

    @property
    def faces(self):
        # type: () -> list[DB.Face]
        return self._faces

    @property
    def meshes(self):
        # type: () -> list[DB.Mesh]
        return self._meshes

    @property
    def points(self):
        # type: () -> list[DB.Point]
        return self._points

    @property
    def polylines(self):
        # type: () -> list[DB.PolyLine]
        return self._polylines

    @property
    def profiles(self):
        # type: () -> list[DB.Profile]
        return self._profiles

    @property
    def solids(self):
        # type: () -> list[DB.Solid]
        return self._solids

    @property
    def other(self):
        # type: () -> list[DB.GeometryObject]
        return self._other

    @property
    def geometry_element(self):
        # type: () -> DB.GeometryElement
        return self._geometry_elem


class DetailAnnotationDrawer(object):
    """Base class to draw detail annotations."""

    def __init__(self, view):
        # type: (DB.View) -> None
        self._parent_view = view
        self._doc = self._parent_view.Document
        self._app = self._doc.Application
        self._min_length = app.ShortCurveTolerance

    def _is_too_short(self, length):
        # type: (float) -> bool
        return length < self._min_length


class DetailCurveDrawer(DetailAnnotationDrawer):
    """Class helping to draw detail curves on specified view."""

    def draw_curve(self, curve, skip_short=False, skip_errors=False):
        # type: (DB.Curve, bool, bool) -> DB.DetailCurve
        try:
            if not self._is_too_short(curve.Length) or not skip_short:
                return self._doc.Create.NewDetailCurve(self._parent_view,
                                                       curve)
        except Exception as err:
            if skip_errors:
                logger.info('skipped curve due to error: {}'.format(err))
            else:
                err


class DetailPolyLineDrawer(DetailAnnotationDrawer):
    """Class helping to draw detail polyline on specified view."""

    def draw_polyline(self, polyline, skip_short=False, skip_errors=False):
        # type: (DB.PolyLine, bool, bool) -> DB.DetailCurveArray
        """Draws a polyline as a detail curve array.
        Set skip_short to True to skip excessively short lines.
        """
        try:
            curve_array = self._polyline_to_curve_array(polyline, skip_short)
            if not curve_array.IsEmpty:
                return doc.Create.NewDetailCurveArray(self._parent_view,
                                                      curve_array)
        except Exception as err:
            if skip_errors:
                logger.info('skipped polyline due to error: {}'.format(err))
            else:
                err

    def _polyline_to_curve_array(self, polyline, skip_short):
        # type: (DB.PolyLine, bool) -> DB.CurveArray
        """Converts a polyline to a curve array.
        Set skip_short to True to skip excessively short lines.
        """
        points = polyline.GetCoordinates()
        if skip_short:
            points = self._overly_close_points_dropper(points)
        curve_array = DB.CurveArray()
        for pt1, pt2 in self._pairwise(points):
            line = DB.Line.CreateBound(pt1, pt2)
            curve_array.Append(line)
        return curve_array

    def _overly_close_points_dropper(self, points):
        """Drops points that are too close to each other acc to Revit API."""
        it = iter(points)
        pt1 = next(it, None)
        if pt1 is not None:
            yield pt1
        for pt2 in it:
            if not self._is_too_short(pt1.DistanceTo(pt2)):
                yield pt2
                pt1 = pt2

    def _pairwise(self, iterable):
        """_pairwise('ABCD') --> 'AB', 'BC', 'CD'
        Similar to itertools.pairwise:
        https://stackoverflow.com/a/20415373
        """
        it = iter(iterable)
        a = next(it, None)
        for b in it:
            yield (a, b)
            a = b


class RegionDrawer(DetailAnnotationDrawer):
    """Class helping to draw regions on specified view."""

    _default_region_type = None

    def draw_filled_region(self, curve_loops, skip_errors=False):
        # type: (list[DB.CurveLoop], bool) -> DB.FilledRegion
        """Draws a filled region. Set skip_errors to True to ignore errors."""
        self._set_filled_region_type_id()
        try:
            return DB.FilledRegion.Create(doc,
                                          self._default_region_type,
                                          self._parent_view.Id,
                                          curve_loops)
        except Exception as err:
            if not skip_errors:
                err
            logger.info('skipped filled region due to error: {}'.format(err))

    def _set_filled_region_type_id(self):
        """Sets self._filled_region_type_id if it has not been set yet.
        """
        if self._default_region_type is None:
            self._default_region_type = \
                self._get_first_filled_region_type_id()

    def _get_first_filled_region_type_id(self):
        # type: () -> DB.ElementId
        filled_region_type_id = DB.FilteredElementCollector(doc)\
            .OfClass(DB.FilledRegionType)\
            .FirstElementId()

        if filled_region_type_id is not None:
            return filled_region_type_id

        raise InvalidOperationException(
            'Failed getting filled region type from the document')


source_view = SourceView(active_view)
geom_skipped = 0

if not source_view.can_convert:
    forms.alert('View must be graphical', exitscript=True)

view_elems = DB.FilteredElementCollector(doc, source_view.view.Id)\
    .WhereElementIsNotElementType()

tmp_geom_options = DB.Options()
tmp_geom_options.View = source_view.view
geom_counter = 0
for elem in view_elems:
    if hasattr(elem, 'get_Geometry'):
        tmp_geom = elem.get_Geometry(tmp_geom_options)
        if tmp_geom is not None:
            tmp_geom_pkg = GeometryPackages(tmp_geom)
            geom_counter += tmp_geom_pkg.total_qty

if geom_counter > MAX_RECOMMENDED_GEOM_QTY:
    many_elems_msg = (
        'Current view potentially has more than {} geometry objects. '
        'Which can take too long time and fail to convert. \n\n'
        'Are you sure you want to proceed?'
    ).format(MAX_RECOMMENDED_GEOM_QTY)

    warn_too_many_elems = forms.alert(msg=many_elems_msg, yes=True, no=True)
    if not warn_too_many_elems:
        script.exit()

subscribe_dialog_temp_view_mode()
try:
    with revit.TransactionGroup('Convert view to drafting'):
        with revit.DryTransaction('Export DWG'):
            source_view.hide_dimensions_temporary()

            if source_view.requires_sheet:
                source_view.place_on_empty_sheet()

            # export DWG
            reimporter = DWGReimporter(source_view.view)
            reimporter.export_view()

        with revit.Transaction('Import DWG'):
            dest_view = DestinationView()
            dest_view.create_drafting_view()
            drafting_view = dest_view.view
            impoted_dwg = reimporter.import_to_view(drafting_view)

        with revit.Transaction(
                name='Convert geometry',
                clear_after_rollback=True,
                swallow_errors=True):

            # extract geometry
            geom_options = DB.Options()
            geom_options.View = drafting_view
            geom_elem = impoted_dwg.get_Geometry(geom_options)

            # draw extracted geometry
            if geom_elem is not None:
                curves_qty = 0
                polylines_qty = 0
                filled_regions_qty = 0
                geom_packs = GeometryPackages(geom_elem)
                curve_drawer = DetailCurveDrawer(drafting_view)
                polyline_drawer = DetailPolyLineDrawer(drafting_view)
                region_drawer = RegionDrawer(drafting_view)

                for curve in geom_packs.curves:
                    curve = curve_drawer.draw_curve(curve,
                                                    skip_short=True,
                                                    skip_errors=True)
                    if curve:
                        curves_qty += 1

                for poliline in geom_packs.polylines:
                    polyline = polyline_drawer.draw_polyline(poliline,
                                                             skip_short=True,
                                                             skip_errors=True)
                    if poliline:
                        polylines_qty += 1

                for solid in geom_packs.solids:
                    for face in solid.Faces:
                        curve_loops = face.GetEdgesAsCurveLoops()
                        filled_region = region_drawer.draw_filled_region(
                            curve_loops,
                            skip_errors=True
                        )
                        if filled_region:
                            filled_regions_qty += 1

                geom_drawn = curves_qty + polylines_qty + filled_regions_qty
                geom_skipped = geom_packs.total_qty - geom_drawn

            drafting_view.Scale = source_view.view.Scale
            reimporter.delete_import()

    if drafting_view is not None:
        uidoc.RequestViewChange(drafting_view)

    reimporter.request_removing_temp_file()
    unsubscribe_dialog_temp_view_mode()

except Exception:
    geom_skipped = 0
    reimporter.request_removing_temp_file()
    unsubscribe_dialog_temp_view_mode()
    raise Exception(traceback.format_exc())

if geom_skipped:
    result_msg = \
        'Completed with {} skipped geometry objects'.format(geom_skipped)
    forms.alert(msg=result_msg)
