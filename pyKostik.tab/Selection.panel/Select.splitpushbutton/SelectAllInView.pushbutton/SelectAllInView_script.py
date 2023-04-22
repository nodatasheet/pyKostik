"""Selects all elements in current view"""

from pyrevit import revit, DB
from System.Collections.Generic import List

doc = revit.doc
view = doc.ActiveView
view_id = view.Id

CAM_AND_BOX_CATS = List[DB.BuiltInCategory](
    [DB.BuiltInCategory.OST_Cameras,
     DB.BuiltInCategory.OST_SectionBox])

# Camera and Section Box only meaningful in 3D views.
# In other views they are redundant.
non_cam_and_box_filter = DB.ElementMulticategoryFilter(CAM_AND_BOX_CATS, True)
collector = DB.FilteredElementCollector(doc, view_id)\
    .WherePasses(non_cam_and_box_filter)\
    .WhereElementIsNotElementType()

if doc.IsFamilyDocument is True:
    to_select = collector.ToElementIds()

else:
    to_select = []
    for elem in collector.ToElements():
        if hasattr(elem, 'Name') and elem.Name == "ExtentElem":
            pass
        else:
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
