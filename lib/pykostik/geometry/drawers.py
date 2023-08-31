from pyrevit import DB, HOST_APP

doc = HOST_APP.doc


def draw_line(view, p1, p2):
    # type: (DB.View, DB.XYZ, DB.XYZ) -> DB.ModelCurve
    line = DB.Line.CreateBound(p1, p2)
    return doc.Create.NewDetailCurve(view, line)


def draw_circle(center, view):
    # type: (DB.XYZ, DB.View) -> None
    plane = DB.Plane.CreateByNormalAndOrigin(view.ViewDirection, center)
    circle = DB.Arc.Create(plane, 0.1, 0, 2 * 3.141592653)
    return doc.Create.NewDetailCurve(view, circle)
