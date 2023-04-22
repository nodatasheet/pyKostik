"""Copies id(s) of selection to clipboard"""

from pyrevit import forms, script
from pyrevit.revit import uidoc

selection = uidoc.Selection.GetElementIds()
if selection.Count:
    ids_as_string = ", ".join(elem_id.ToString() for elem_id in selection)
    script.clipboard_copy(ids_as_string)
else:
    forms.alert("Could not get IDs from selection")
