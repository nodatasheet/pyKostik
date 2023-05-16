from pyrevit import revit, script, DB, HOST_APP, forms


active_view = HOST_APP.active_view
logger = script.get_logger()


class ElementMovingPoint(object):
    def __init__(self, elem):
        # type: (DB.Element) -> None
        self._elem = elem

    def get_location_point(self):
        # type: () -> DB.XYZ
        return self._elem.Location.Point

    def get_location_curve_midpoint(self):
        # type: () -> DB.XYZ
        location_curve = self._get_loctaion_curve()
        curve_parameter = 0.5
        is_normalized = True
        return location_curve.Evaluate(curve_parameter, is_normalized)

    def get_origin(self):
        # type: () -> DB.XYZ
        return getattr(self._elem, 'Origin')

    def get_bounding_box_center(self):
        # type: () -> DB.XYZ
        elem_bb = self._elem.get_BoundingBox(HOST_APP.active_view)
        return (elem_bb.Min + elem_bb.Max) / 2

    def _get_loctaion_curve(self):
        # type: () -> DB.Curve
        return self._elem.Location.Curve

    def _is_xyz(self, obj):
        return isinstance(obj, DB.XYZ)

    @property
    def has_origin(self):
        # type: () -> bool
        try:
            origin = self.get_origin()
            return self._is_xyz(origin)
        except Exception:
            pass

    @property
    def has_location_point(self):
        # type: () -> bool
        try:
            return self._is_xyz(self.get_location_point())
        except Exception:
            pass

    @property
    def has_location_curve(self):
        # type: () -> bool
        try:
            return isinstance(self._get_loctaion_curve(), DB.Curve)
        except Exception:
            pass


picked_elem = revit.pick_element('Select element to move')  # type: DB.Element
agree_to_move = True

if picked_elem:

    if hasattr(picked_elem, 'Host'):
        if getattr(picked_elem, 'Host') is not None:
            forms.alert('Can not move host based elements', exitscript=True)

    elem_moving_point = ElementMovingPoint(picked_elem)

    if elem_moving_point.has_origin:
        elem_moving_point = elem_moving_point.get_origin()
        logger.info('got origin: {}'.format(elem_moving_point))

    elif elem_moving_point.has_location_point:
        elem_moving_point = elem_moving_point.get_location_point()
        logger.info('got location point: {}'.format(elem_moving_point))

    elif elem_moving_point.has_location_curve:
        elem_moving_point = elem_moving_point.get_location_curve_midpoint()
        logger.info(
            'got middle of location line: {}'
            .format(elem_moving_point)
        )

    else:
        elem_moving_point = elem_moving_point.get_bounding_box_center()
        logger.info('got bounding box center: {}'.format(elem_moving_point))

        ask_use_geom_center = forms.alert(
            msg=(
                'Could not get element\'s origin.\n'
                'Will use center of geometry.'
            ),
            ok=True,
            cancel=True
        )

        if not ask_use_geom_center:
            agree_to_move = False

if agree_to_move:
    with revit.Transaction('Move to Origin'):
        transform = DB.XYZ.Zero - elem_moving_point
        DB.ElementTransformUtils.MoveElement(
            HOST_APP.doc,
            picked_elem.Id,
            transform
        )
