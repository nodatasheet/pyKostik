"""Selects all elements in current view"""

from pyrevit import DB, forms, framework, script, revit

doc = revit.doc
view = doc.ActiveView
view_id = view.Id

MAX_RECOMMENDED_ELEM_QTY = 10000
CAM_AND_BOX_CATS = framework.List[DB.BuiltInCategory](
    [DB.BuiltInCategory.OST_Cameras,
     DB.BuiltInCategory.OST_SectionBox])

# Camera and Section Box only meaningful in 3D views.
# In other views they are redundant.
non_cam_and_box_filter = DB.ElementMulticategoryFilter(CAM_AND_BOX_CATS, True)
elems_in_view = list(
    DB.FilteredElementCollector(doc, view_id)
    .WherePasses(non_cam_and_box_filter)
    .WhereElementIsNotElementType()
)

elems_qty = len(elems_in_view)
if elems_qty > MAX_RECOMMENDED_ELEM_QTY:
    many_elems_msg = (
        'Current view contains {} elements. \n'
        'It can take too long time or fail to select them all. \n\n'
        'Are you sure you want to proceed?'
    ).format(elems_qty)

    warn_too_many_elems = forms.alert(msg=many_elems_msg, yes=True, no=True)
    if not warn_too_many_elems:
        script.exit()

if doc.IsFamilyDocument is True:
    to_select = elems_in_view

else:
    to_select = []
    for elem in elems_in_view:
        if not (hasattr(elem, 'Name') and elem.Name == "ExtentElem"):
            to_select.append(elem.Id)

    if view.ViewType == DB.ViewType.ThreeD:
        # Adding Crop Region (which is Camera for 3DView)
        # and Section Box to selection if they are visible
        cam_and_box_filter = DB.ElementMulticategoryFilter(CAM_AND_BOX_CATS)
        visibility_filter = DB.VisibleInViewFilter(doc, view_id)
        and_filter = DB.LogicalAndFilter(cam_and_box_filter, visibility_filter)
        camera_and_box = view.GetDependentElements(and_filter)
        to_select.extend(camera_and_box)

selection = revit.get_selection().set_to(to_select)
