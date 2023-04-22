"""Selects beams of beam system"""

from itertools import chain
from pyrevit import DB, revit, forms

selection = revit.get_selection()

beam_systems = []  # type: list[DB.BeamSystem]

if not selection.is_empty:
    beam_systems = filter(
        lambda elem: isinstance(elem, DB.BeamSystem), selection
    )

if not beam_systems:
    with forms.WarningBar(title='Select Beam System(s)'):
        beam_systems = revit.pick_elements_by_category(
            DB.BuiltInCategory.OST_StructuralFramingSystem)

if beam_systems:
    selection.set_to(
        chain.from_iterable(bs.GetBeamIds() for bs in beam_systems)
    )
