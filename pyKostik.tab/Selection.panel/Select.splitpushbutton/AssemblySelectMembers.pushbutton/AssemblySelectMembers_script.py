"""Select Members of the Assemblies."""

from pyrevit import revit, DB, forms

assemblies = []
assembly_members = []

selection = revit.get_selection()

if not selection.is_empty:
    for elem in selection.elements:
        if isinstance(elem, DB.AssemblyInstance):
            assemblies.append(elem)

if not assemblies:
    with forms.WarningBar(title='Select Assemblies'):
        assemblies = revit.pick_elements_by_category(
            DB.BuiltInCategory.OST_Assemblies)

if assemblies:
    for assembly in assemblies:
        assembly_members.extend(assembly.GetMemberIds())

if assembly_members:
    selection.set_to(assembly_members)
