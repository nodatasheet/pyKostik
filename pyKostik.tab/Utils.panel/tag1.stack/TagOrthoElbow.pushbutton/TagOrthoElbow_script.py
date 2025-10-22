from pyrevit import DB, UI, HOST_APP, revit, script, forms
from Autodesk.Revit.Exceptions import OperationCanceledException


class TagFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, elem):
        if isinstance(elem, DB.IndependentTag):
            return True

        return False

    def AllowReference(self, reference, position):
        return True


class TagDTO(object):
    def __init__(self, tag, center, endrefs):
        # type: (DB.IndependentTag, DB.XYZ, list[tuple[DB.XYZ, DB.Reference]]) -> None  # noqa
        self._tag = tag
        self._center = center
        self._endrefs = endrefs

    @property
    def tag(self):
        return self._tag

    @property
    def center(self):
        return self._center

    def get_end(self, ref):
        # type: (DB.Reference) -> DB.Reference | None
        for end, endref in self._endrefs:
            if endref.EqualTo(ref):
                return end


def uv_as_xyz(uv, plane):
    # type: (DB.UV, DB.Plane) -> DB.XYZ
    xyz_on_plane = plane.Origin + uv.U * plane.XVec + uv.V * plane.YVec
    return xyz_on_plane


def get_center(tag):
    # type: (DB.IndependentTag) -> DB.XYZ | None
    """Only do it in Dry Transaction!"""

    for ref in tag.GetTaggedReferences():
        end = tag.GetLeaderEnd(ref)
        head = tag.TagHeadPosition
        tag.HasLeader = False
        move_dir = end - head
        DB.ElementTransformUtils.MoveElement(tag.Document, tag.Id, move_dir)
        bb = tag.get_BoundingBox(active_view)
        moved_center = (bb.Max + bb.Min) / 2
        return moved_center - move_dir


uidoc = HOST_APP.uidoc  # type: UI.UIDocument
doc = HOST_APP.doc  # type: DB.Document
selection = uidoc.Selection
active_view = doc.ActiveView
button_title = script.get_button().get_title()

tags = [
    doc.GetElement(eid) for eid in selection.GetElementIds()
    if isinstance(doc.GetElement(eid), DB.IndependentTag)
]

if not tags:
    try:
        picked = selection.PickObjects(
            UI.Selection.ObjectType.Element,
            TagFilter(),
            "Select Tags"
        )
        tags = [doc.GetElement(ref) for ref in picked]  # type: list[DB.IndependentTag]  # noqa

    except OperationCanceledException:
        script.exit()

view_plane = DB.Plane.CreateByOriginAndBasis(
    active_view.Origin,
    active_view.RightDirection,
    active_view.UpDirection
)

tag_dtos = []  # type: list[TagDTO]
with revit.DryTransaction("collect tag centers"):
    for tag in tags:
        if not tag.HasLeader:
            continue

        tag.LeaderEndCondition = DB.LeaderEndCondition.Free
        end_refs = [
            (tag.GetLeaderEnd(ref), ref)
            for ref in tag.GetTaggedReferences()
        ]
        center = get_center(tag)

        if center:
            tag_dtos.append(TagDTO(tag, center, end_refs))


with revit.Transaction(button_title):
    for tag_dto in tag_dtos:
        tag = tag_dto.tag
        center = tag_dto.center

        if tag.MergeElbows:
            tag.MergeElbows = False

        for ref in tag.GetTaggedReferences():
            end = tag_dto.get_end(ref)
            end_projection = view_plane.Project(end)[0]
            center_projection = view_plane.Project(center)[0]

            is_horizontal = abs(end_projection.V - center_projection.V) < 1e-9
            is_vertical = abs(end_projection.U - center_projection.U) < 1e-9

            if not (is_horizontal or is_vertical):
                elbow_on_plane = DB.UV(end_projection.U, center_projection.V)
                elbow = uv_as_xyz(elbow_on_plane, view_plane)
                tag.SetLeaderElbow(ref, elbow)
