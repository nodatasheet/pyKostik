"""Opens the folder containing active document"""

import os.path as op
import posixpath as pp

from pyrevit import forms, revit, DB, script, HOST_APP

from System.Diagnostics import Process

doc = revit.doc  # type: DB.Document
file_path = doc.PathName

if doc.IsModelInCloud:
    if int(HOST_APP.version) < 2022:
        forms.alert(
            msg=('Opening cloud models in Revit '
                 'versions prior to 2022 is not supported.'),
            exitscript=True
        )

    url_base = 'https://docs.b360.autodesk.com/projects/'

    project_id = doc.GetProjectId()
    project_id_prefix = 'b.'
    cloud_project_id = project_id.strip(project_id_prefix)

    force_refresh = False
    cloud_folder_id = doc.GetCloudFolderId(force_refresh)

    cloud_folder_url = pp.join(
        url_base,
        cloud_project_id,
        'folders',
        cloud_folder_id
    )

    script.open_url(cloud_folder_url)

elif op.isfile(file_path):
    file_info = DB.BasicFileInfo.Extract(file_path)

    if file_info.IsWorkshared:
        file_path = file_info.CentralPath

    Process.Start("explorer.exe",
                  "/e, /select, \"{}\"".format(file_path))

else:
    forms.alert("The active document does not have a valid folder")
