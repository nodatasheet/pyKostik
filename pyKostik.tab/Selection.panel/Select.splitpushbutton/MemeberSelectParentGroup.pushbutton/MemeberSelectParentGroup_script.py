"""Selects beam system by child beam"""

from pyrevit import DB, revit, forms

SELECTION_TXT = 'Select Group Member(s)'

selection = revit.get_selection()
group_ids = set()


def get_group_ids(elems):
    # type: (list[DB.Element]) -> set[DB.ElementId]
    group_ids = set()
    for elem in elems:
        group_id = elem.GroupId
        if group_id is not None:
            group_ids.add(group_id)
    return group_ids


if not selection.is_empty:
    group_ids = get_group_ids(selection)

if not group_ids:
    with forms.WarningBar(title=SELECTION_TXT):
        members = revit.pick_elements(message=SELECTION_TXT)
        if members is not None:
            if hasattr(members, '__iter__'):
                group_ids.update(get_group_ids(members))
            else:
                group_ids.update(get_group_ids([members]))
            if not group_ids:
                forms.alert('Selected elements do not belong to any group')

if group_ids:
    selection.set_to(group_ids)
