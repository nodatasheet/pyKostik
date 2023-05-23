import inspect
from pyrevit import revit, script, HOST_APP
from Autodesk.Revit import DB, UI, Exceptions

doc = revit.doc  # type: DB.Document
logger = script.get_logger()


class PickByClassSelectionFilter(UI.Selection.ISelectionFilter):
    """Inherited from `UI.Selection.ISelectionFilter`
    to allow only objects of specific class
    by overwriting standard API functions"""

    def __init__(self, obj_type):
        # type: (type) -> None
        self.obj_type = obj_type

    def AllowElement(self, element):
        # type: (DB.Element) -> bool
        if isinstance(element, self.obj_type):
            return True
        else:
            return False

    def AllowReference(self, refer, point):
        return False


def pick_elements_by_class(obj_type, message=''):
    # type: (type, str) -> list[DB.Element]
    if not inspect.isclass(obj_type):
        raise AttributeError('Object "{}" is not a class'.format(obj_type))

    pick_filter = PickByClassSelectionFilter(obj_type)

    try:
        picked_references = HOST_APP.uidoc.Selection.PickObjects(
            UI.Selection.ObjectType.Element,
            pick_filter,
            message
        )
        return [doc.GetElement(ref) for ref in picked_references]

    except Exceptions.OperationCanceledException:
        logger.info('Selection canceled')


selected_tags = pick_elements_by_class(
    DB.IndependentTag,
    'Select Tags'
)  # type: list[DB.IndependentTag]

if selected_tags:
    with revit.Transaction('Drop Leader Elbow'):
        for tag in selected_tags:
            if tag.HasLeader:
                tag.HasLeader = False
                tag.HasLeader = True
