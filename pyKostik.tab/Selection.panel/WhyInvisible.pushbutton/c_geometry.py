import itertools
from Autodesk.Revit import DB
from System.Collections.Generic import List


def circular_pairwise(iterable):
    """
    circular_pairwise('ABCD') --> AB BC CD DA

    https://stackoverflow.com/a/36927946
    """
    a, b = itertools.tee(iterable)
    first = next(b, None)
    return zip(a, itertools.chain(b, (first,)))


def bb_to_cuboid(bb, transform=None):
    # type: (DB.BoundingBoxXYZ, DB.Transform | None) -> DB.Solid
    rectangle = bb_bottom_rectangle(bb, transform)
    profile = List[DB.CurveLoop]()
    profile.Add(rectangle)
    direction = DB.XYZ.BasisZ
    distance = abs(bb.Max.Z - bb.Min.Z)

    if transform is not None:
        direction = transform.OfVector(direction)

    return DB.GeometryCreationUtilities.CreateExtrusionGeometry(
        profile,
        direction,
        distance
    )


def bb_bottom_rectangle(bb, transform=None):
    # type: (DB.BoundingBoxXYZ, DB.Transform | None) -> DB.CurveLoop
    bb_min = bb.Min
    bb_max = bb.Max

    bottom_corners = (
        bb_min,
        DB.XYZ(bb_min.X, bb_max.Y, bb_min.Z),
        DB.XYZ(bb_max.X, bb_max.Y, bb_min.Z),
        DB.XYZ(bb_max.X, bb_min.Y, bb_min.Z),
    )

    if transform is not None:
        bottom_corners = (transform.OfPoint(p) for p in bottom_corners)

    curve_loop = DB.CurveLoop()
    for end1, end2 in circular_pairwise(bottom_corners):
        line = DB.Line.CreateBound(end1, end2)
        curve_loop.Append(line)

    return curve_loop


def get_all_bb_corners(bb):
    # type: (DB.BoundingBoxXYZ) -> list[DB.XYZ]
    bb_min = bb.Min
    bb_max = bb.Max
    xs = bb_min.X, bb_max.X
    ys = bb_min.Y, bb_max.Y
    zs = bb_min.Z, bb_max.Z

    return [DB.XYZ(x, y, z) for x, y, z in itertools.product(xs, ys, zs)]
