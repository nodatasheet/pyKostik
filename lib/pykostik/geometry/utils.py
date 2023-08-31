"""Utilities for geometry objects."""
from Autodesk.Revit import DB


def are_numbers_close(a, b, rel_tol=1e-09, abs_tol=0.0):
    """A function for testing approximate equality of two numbers.
    Same as math.isclose in Python v3.5 (and newer)
    https://www.python.org/dev/peps/pep-0485
    """
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def merge_bounding_boxes(bboxes):
    # type: (list[DB.BoundingBoxXYZ]) -> DB.BoundingBoxXYZ
    """Merges multiple bounding boxes"""
    merged_bb = DB.BoundingBoxXYZ()
    merged_bb.Min = DB.XYZ(
        min(bboxes, key=lambda bb: bb.Min.X).Min.X,
        min(bboxes, key=lambda bb: bb.Min.Y).Min.Y,
        min(bboxes, key=lambda bb: bb.Min.Z).Min.Z
    )
    merged_bb.Max = DB.XYZ(
        max(bboxes, key=lambda bb: bb.Max.X).Max.X,
        max(bboxes, key=lambda bb: bb.Max.Y).Max.Y,
        max(bboxes, key=lambda bb: bb.Max.Z).Max.Z
    )
    return merged_bb


def bounding_box_by_points(revit_points):
    # type: (list[DB.XYZ]) -> DB.BoundingBoxXYZ
    bb = DB.BoundingBoxXYZ()
    bb.Min = DB.XYZ(
        min(p.X for p in revit_points),
        min(p.Y for p in revit_points),
        min(p.Z for p in revit_points),
    )
    bb.Max = DB.XYZ(
        max(p.X for p in revit_points),
        max(p.Y for p in revit_points),
        max(p.Z for p in revit_points),
    )
    return bb
