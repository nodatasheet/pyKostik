"""Selects all members of the Groups and their Subgroups."""

from pyrevit import revit, DB, forms

doc = revit.doc
selection = revit.get_selection()


def deepest_element_ids_extractor(group):
    """Recursively extracts element ids from the group and its subgroups."""
    for member_id in group.GetMemberIds():
        member = doc.GetElement(member_id)
        if isinstance(member, DB.Group):
            for sub_member_id in deepest_element_ids_extractor(member):
                yield sub_member_id
        else:
            yield member_id


groups = []

if not selection.is_empty:
    for elem in selection.elements:
        if isinstance(elem, DB.Group):
            groups.append(elem)

if not groups:
    with forms.WarningBar(title='Select Groups'):
        groups = revit.pick_elements_by_category(
            DB.BuiltInCategory.OST_IOSModelGroups)

if groups:
    deepest_element_ids = []
    for group in groups:
        for id in deepest_element_ids_extractor(group):
            deepest_element_ids.append(id)

    selection.set_to(deepest_element_ids)
