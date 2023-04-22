"""Reloads all CAD Links in active document"""

from pyrevit import revit, DB
from pyrevit import script


def describe_load_result(load_result):
    # type: (DB.LinkLoadResultType) -> str
    if load_result == DB.LinkLoadResultType.LinkLoaded:
        description = ":white_heavy_check_mark: Reloaded"
    elif load_result == DB.LinkLoadResultType.LinkNotFound:
        description = ":cross_mark: The linked file could not be found."
    else:
        description = ":warning: Did not reload. \
        Error code: {}".format(load_result)
    return description


output = script.get_output()
output.close_others(True)

cad_link_types = DB.FilteredElementCollector(revit.doc)\
    .OfClass(DB.CADLinkType)\
    .ToElements()

if cad_link_types.Count:
    with revit.Transaction('Reload CAD Links'):
        load_results = []
        for link in cad_link_types:
            load_result = link.Reload()

            link_name = link.Category.Name
            link_path = load_result.\
                GetExternalResourceReference()\
                .InSessionPath
            reload_result = describe_load_result(load_result.LoadResult)

            output.print_md("**CAD Link: {}**\n\n"
                            "- File path: `{}`\n\n"
                            "- Result: {}\n\n"
                            .format(link_name,
                                    link_path,
                                    reload_result))
