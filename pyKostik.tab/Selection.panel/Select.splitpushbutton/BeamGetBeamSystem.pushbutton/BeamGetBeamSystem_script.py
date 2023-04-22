"""Selects beam system by child beam"""

from pyrevit import DB, revit, forms

selection = revit.get_selection()
beam_system_ids = set()


def get_beam_systems(elems):
    # type: (list[DB.Element]) -> set[DB.ElementId]
    beam_system_ids = set()
    for elem in elems:
        elem_host = get_host(elem)
        if isinstance(elem_host, DB.BeamSystem):
            beam_system_ids.add(elem_host.Id)
    return beam_system_ids


def get_host(elem):
    # type: (DB.FamilyInstance) -> DB.Element
    if isinstance(elem, DB.FamilyInstance) \
            and hasattr(elem, 'Host'):
        return elem.Host


if not selection.is_empty:
    beam_system_ids = get_beam_systems(selection)

if not beam_system_ids:
    with forms.WarningBar(title='Select Beam(s)'):
        beams = revit.pick_elements_by_category(
            DB.BuiltInCategory.OST_StructuralFraming)
        if beams is not None:
            if hasattr(beams, '__iter__'):
                beam_system_ids.update(get_beam_systems(beams))
            else:
                beam_system_ids.update(get_beam_systems([beams]))
            if not beam_system_ids:
                forms.alert('Selected beams do not belong to any beam system')

if beam_system_ids:
    selection.set_to(beam_system_ids)
