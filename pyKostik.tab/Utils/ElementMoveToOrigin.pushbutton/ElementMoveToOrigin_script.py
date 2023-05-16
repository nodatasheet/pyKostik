from pyrevit import revit, DB, HOST_APP


active_view = HOST_APP.active_view

picked_elem = revit.pick_element('Select Element to move')  # type: DB.Element

if picked_elem:
    with revit.Transaction('Move to Origin'):
        elem_bb = picked_elem.get_BoundingBox(active_view)
        elem_origin = (elem_bb.Min + elem_bb.Max) / 2
        view_origin = active_view.Origin
        DB.ElementTransformUtils.MoveElement(
            HOST_APP.doc,
            picked_elem.Id,
            view_origin - elem_origin
        )
