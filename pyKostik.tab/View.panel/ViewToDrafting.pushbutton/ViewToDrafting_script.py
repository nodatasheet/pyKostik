"""Converts current view to a drafting view."""
import os
import clr
import shutil
import uuid
import tempfile

from System import EventHandler
from System.Collections.Generic import List

from pyrevit import revit, DB, UI, HOST_APP, forms, script

ALLOWED_VIEW_TYPES = (
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
    DB.ViewType.Walkthrough
)

doc = HOST_APP.doc
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


class GeometryPacks(object):
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
                'solids': self._solids}

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
        # type: () -> list[DB.Solid]
        return self._other

    @property
    def geometry_element(self):
        # type: () -> DB.GeometryElement
        return self._geometry_elem


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


def export_to_dwg(dir_path, file_name, view, options=DB.DWGExportOptions()):
    # type: (os.path, str, DB.View, DB.DWGExportOptions) -> bool
    """Exports view to AutoCAD DWG file."""
    logger.info(
        'Exporting DWG to {}'.format(os.path.join(dir_path, file_name)))
    view_id = List[DB.ElementId]()
    view_id.Add(view.Id)
    export_result = doc.Export(dir_path, file_name, view_id, options)
    if export_result is True:
        return export_result
    else:
        raise InvalidOperationException(
            "Could not convert the view due to DWG export failure")


def import_dwg(file_path, view):
    # type: (str, DB.View) -> DB.ElementId
    """Imports DWG to a view."""
    logger.info('Importing DWG from {}'.format(file_path))
    imported_id = clr.Reference[DB.ElementId]()
    options = DB.DWGImportOptions()
    options.ThisViewOnly = True
    imported = doc.Import(file_path, options, view, imported_id)
    if imported is True:
        return imported_id.Value
    else:
        raise InvalidOperationException(
            "Could not convert the view due to DWG import failure"
            "\nImport file path: {}".format(file_path))


def get_first_drafting_view_type():
    # type: () -> DB.ViewFamilyType
    view_types = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
    for view_type in view_types:
        if view_type.ViewFamily == DB.ViewFamily.Drafting:
            return view_type


def polyline_to_curve_array(polyline):
    # type: (DB.PolyLine) -> DB.CurveArray
    """Converts a poly line to a curve array
    skipping excessively short curves.
    """
    points = polyline.GetCoordinates()
    curve_array = DB.CurveArray()
    for i in range(len(points) - 1):
        if not is_too_short(points[i].DistanceTo(points[i + 1])):
            line = DB.Line.CreateBound(points[i], points[i + 1])
            curve_array.Append(line)
    return curve_array


def is_too_short(length):
    # type: (float) -> bool
    return length <= app.ShortCurveTolerance


def get_first_filled_region_type():
    # type: () -> DB.Element
    return DB.FilteredElementCollector(doc)\
        .OfClass(DB.FilledRegionType)\
        .FirstElement()


if active_view.ViewType not in ALLOWED_VIEW_TYPES:
    forms.alert('View must be graphical', exitscript=True)

subscribe_dialog_temp_view_mode()

# prepare temp path
temp_dir = tempfile.mkdtemp()
temp_file_name = str(uuid.uuid4()) + ".dwg"
temp_file_path = os.path.join(temp_dir, temp_file_name)

try:

    with revit.TransactionGroup('Convert view to drafting'):
        with revit.DryTransaction('Export DWG'):
            active_view.HideCategoryTemporary(
                DB.ElementId(DB.BuiltInCategory.OST_Dimensions))

            # 3D views need to be exported as 2D
            if active_view.ViewType in (
                    DB.ViewType.ThreeD, DB.ViewType.Walkthrough):
                view_to_export = DB.ViewSheet.Create(
                    doc, DB.ElementId.InvalidElementId)
                view_copy = active_view.Duplicate(
                    DB.ViewDuplicateOption.WithDetailing)
                DB.Viewport.Create(
                    doc, view_to_export.Id, view_copy, DB.XYZ.Zero)
            else:
                view_to_export = active_view

            # setup DWG export options
            dwg_export_options = DB.DWGExportOptions()
            dwg_export_options.MergedViews = True
            dwg_export_options.Colors = DB.ExportColorMode.TrueColorPerView
            dwg_export_options.PreserveCoincidentLines = False

            export_to_dwg(
                temp_dir, temp_file_name, view_to_export, dwg_export_options)

        with revit.Transaction('Import DWG'):
            # import DWG
            drafting_view_type = get_first_drafting_view_type()
            drafting_view = DB.ViewDrafting.Create(doc, drafting_view_type.Id)
            imported_dwg_id = import_dwg(temp_file_path, drafting_view)
            impoted_dwg = doc.GetElement(imported_dwg_id)

            # extract geometry
            geom_options = DB.Options()
            geom_options.View = drafting_view
            geom_elem = impoted_dwg.get_Geometry(geom_options)

            if geom_elem is not None:
                geom_objects = GeometryPacks(geom_elem)

                # draw curves
                for curve in geom_objects.curves:
                    if not is_too_short(curve.Length):
                        doc.Create.NewDetailCurve(drafting_view, curve)

                # draw curve arrays
                for polyline in geom_objects.polylines:
                    curve_array = polyline_to_curve_array(polyline)
                    if not curve_array.IsEmpty:
                        doc.Create.NewDetailCurveArray(drafting_view,
                                                       curve_array)

                # draw filled regions
                filled_region_type = get_first_filled_region_type()
                for solid in geom_objects.solids:
                    for face in solid.Faces:
                        try:
                            fill_region = DB.FilledRegion.Create(
                                doc,
                                filled_region_type.Id,
                                drafting_view.Id,
                                face.GetEdgesAsCurveLoops())
                        except Exception as err:
                            logger.exception(
                                'failed draw filled region: {}'.format(err))
            drafting_view.Scale = active_view.Scale
            doc.Delete(imported_dwg_id)

    shutil.rmtree(temp_dir, True)
    unsubscribe_dialog_temp_view_mode()

    if drafting_view is not None:
        uidoc.RequestViewChange(drafting_view)

except Exception as err:
    shutil.rmtree(temp_dir, True)
    unsubscribe_dialog_temp_view_mode()
    raise Exception(err)
