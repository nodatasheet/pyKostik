"""Zooms to selection"""

from pyrevit import forms
from pyrevit import revit, DB
from System.Collections.Generic import List


def merge_bounding_boxes(bboxes):
    # type: (list) -> DB.BoundingBoxXYZ
    """Merges multiple bounding boxes"""
    merged_bb = DB.BoundingBoxXYZ()
    merged_bb.Min = DB.XYZ(min(bboxes, key=lambda bb: bb.Min.X).Min.X,
                           min(bboxes, key=lambda bb: bb.Min.Y).Min.Y,
                           min(bboxes, key=lambda bb: bb.Min.Z).Min.Z)
    merged_bb.Max = DB.XYZ(max(bboxes, key=lambda bb: bb.Max.X).Max.X,
                           max(bboxes, key=lambda bb: bb.Max.Y).Max.Y,
                           max(bboxes, key=lambda bb: bb.Max.Z).Max.Z)
    return merged_bb


uidoc = revit.uidoc
active_view = revit.active_view
selection = revit.get_selection()

# Exclude elements that missing or invisible in active view
selection_ids = List[DB.ElementId](selection.element_ids)
selection_as_filter = DB.ElementIdSetFilter(selection_ids)
zoomable_collector = DB.FilteredElementCollector(revit.doc, active_view.Id)\
    .WherePasses(selection_as_filter)

if zoomable_collector.GetElementCount() > 0:
    if active_view.ViewType == DB.ViewType.Legend:
        zoomable_elems = zoomable_collector.GetElementIterator()
        bboxes = [e.get_BoundingBox(active_view) for e in zoomable_elems]
        merged_bb = merge_bounding_boxes(bboxes)
        ui_view = next(v for v in uidoc.GetOpenUIViews()
                       if v.ViewId == active_view.Id)
        ui_view.ZoomAndCenterRectangle(merged_bb.Min, merged_bb.Max)
    else:
        uidoc.ShowElements(zoomable_collector.ToElementIds())
else:
    forms.alert("None of the selected elements "
                "is suitable for zooming in current view")
