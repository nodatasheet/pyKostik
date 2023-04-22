"""Add a Text Note to Legend Components.
author: Konstantin (https://github.com/nodatasheet)
"""

from pyrevit import DB, UI, forms, revit, script
from legend_utils import LegendComponent


def get_first_text_style():
    # type: () -> DB.TextNoteType
    """Gets first found Text Note Type in current document"""
    first_text_style = DB.FilteredElementCollector(doc)\
        .OfClass(DB.TextNoteType)\
        .FirstElement()
    if first_text_style is not None:
        return first_text_style


app = revit.HOST_APP.app
doc = revit.doc  # type: DB.Document
uidoc = revit.uidoc  # type: UI.Document
uiapp = revit.HOST_APP.uiapp
selection = revit.get_selection()
config = script.get_config()

legcomp_sources = [elem for elem in selection.elements
                   if LegendComponent.is_of_legcomp_cat(elem)]

text_note_offset_value = 500 / 304.5

if legcomp_sources:
    ask_use_selection = forms.alert(
        'Use currently selected Legend Components?',
        cancel=True)
    if not ask_use_selection:
        legcomp_sources = []

if not legcomp_sources:
    legcomp_cat = LegendComponent.get_legcomp_cat(doc)
    if legcomp_cat:
        pick_message = 'Select Legend Components and press "Finish"'
        with forms.WarningBar(title=pick_message):
            picked_elems = revit.pick_elements_by_category(legcomp_cat)
            if picked_elems:
                legcomp_sources = picked_elems
                selection.clear()
    else:
        forms.alert('There is no Legend Components in this Project')

common_param_names = set()
legcomps = []  # type: list[LegendComponent]

if legcomp_sources:
    for lg in legcomp_sources:
        legcomp = LegendComponent(lg)
        legcomps.append(legcomp)
        param_names = legcomp.wrapped_type.param_names
        if common_param_names:
            common_param_names.intersection_update(param_names)
        else:
            common_param_names.update(param_names)

picked_param = None
if legcomp_sources and common_param_names:
    switch_opt_1 = 'Disable units (otherwise same as in Units settings)'
    ask_pick_param = forms.CommandSwitchWindow.show(
        sorted(common_param_names),
        message='Pick Parameter which value will be used in Text Note',
        switches=[switch_opt_1],
        config={switch_opt_1: {'background': '#7997f7'}}
    )
    if ask_pick_param:
        picked_param = ask_pick_param[0]

with revit.Transaction('Add Text to Legend Components'):
    if picked_param:
        text_note_opts = DB.TextNoteOptions()
        text_note_opts.TypeId = get_first_text_style().Id
        text_note_opts.HorizontalAlignment = DB.HorizontalTextAlignment.Center
        for legcomp in legcomps:
            param = legcomp.wrapped_type.lookup_wrapped_param(picked_param)
            if ask_pick_param[1][switch_opt_1]:
                param_value = param.get_value_as_unitless_string(doc)
            else:
                param_value = param.get_value_as_string()

            if param_value is not None and len(param_value) > 0:
                legcomp_bottom = legcomp.location \
                    - DB.XYZ(0, legcomp.height / 2, 0)
                text_note = DB.TextNote.Create(
                    doc,
                    legcomp.owner_view_id,
                    legcomp_bottom - DB.XYZ(0, text_note_offset_value, 0),
                    param_value,
                    text_note_opts
                )
