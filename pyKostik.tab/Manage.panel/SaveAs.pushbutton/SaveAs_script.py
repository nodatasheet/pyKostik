from Autodesk.Revit import UI


def run_post_command(uiapp, command):
    # type: (UI.UIApplication, UI.PostableCommand) -> None
    cmd_id = UI.RevitCommandId.LookupPostableCommandId(command)
    if uiapp.CanPostCommand(cmd_id):
        uiapp.PostCommand(cmd_id)


uiapp = __revit__  # type: UI.UIApplication
doc = uiapp.ActiveUIDocument.Document

if doc.IsFamilyDocument:
    run_post_command(uiapp, UI.PostableCommand.SaveAsFamily)
else:
    run_post_command(uiapp, UI.PostableCommand.SaveAsProject)
