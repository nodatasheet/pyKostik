"""Saves and zips active document file to specified folder.
Workshared local document will be synchronized
 and its central file will be zipped.
Optionally can pack files linked to the document.
"""

from itertools import groupby
from operator import itemgetter
from os import path as op
from zipfile import ZipFile
from datetime import date
from pyrevit import DB, forms, revit, script
from System.Windows.Forms import SaveFileDialog, DialogResult


def propose_zipfilename(source_name):
    """Provides backup file name using current date and source file name.
    Example: 2022.08.24_source name"""
    # type: (str) -> str
    today = date.today().strftime("%Y.%m.%d")
    return '_'.join((today, source_name))


def call_export_dialog(proposed_path=None, proposed_name=None):
    # type: (str|None, str|None) -> tuple[DialogResult, str]
    """Shows dialog for exporting to zip archive.
    Returns tuple of DialogResult and File Path."""
    save_dialog = SaveFileDialog()
    if proposed_path is not None:
        save_dialog.InitialDirectory = proposed_path
    if proposed_name is not None:
        save_dialog.FileName = proposed_name
    save_dialog.DefaultExt = ".zip"
    save_dialog.Filter = "Zip archive|*.zip"
    save_dialog.Title = "Save archive to target folder"
    show_dialog = save_dialog.ShowDialog()
    file_path = None
    if show_dialog == DialogResult.OK:
        file_path = save_dialog.FileName
    return (show_dialog, file_path)


def collect_image_types(doc):
    return DB.FilteredElementCollector(doc)\
        .OfClass(DB.ImageType)\
        .ToElements()


def get_duplicates(items):
    # type: (list | tuple) -> set
    duplicates = set()
    seen = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return duplicates


def output_the_conflicts(conflicts):
    # type: (dict[str:list[str]]) -> None
    output = script.get_output()
    output.print_md('#<span style="color:red">File names conflict.'
                    ' Zip canceled.</span>#')
    output.print_md('<span style="color:red">'
                    'Some files would conflict with each other'
                    ' as they lead to the same path in archive.'
                    ' Consider renaming them.'
                    '</span>')
    for k in sorted(conflicts.keys()):
        output.print_md('<span style="color:red">'
                        '**Following paths'
                        ' lead to the same file in archive ({}):'
                        '</span>**'.format(k))
        for v in sorted(conflicts[k]):
            output.print_md('<span style="color:red"> - {}</span>'.format(v))


output = script.get_output()
output.close_others()

doc = revit.doc  # type: DB.Document
file_path = doc.PathName

if op.isfile(file_path):
    # Prepare active document
    file_info = DB.BasicFileInfo.Extract(file_path)
    if doc.IsWorkshared and not doc.IsDetached:
        file_path = file_info.CentralPath
        sync_request = forms.alert(
            'Synchronize with central before archiving?',
            yes=True,
            no=True)
        if sync_request is True:
            transact_options = DB.TransactWithCentralOptions()
            sync_options = DB.SynchronizeWithCentralOptions()
            relinquish_options = DB.RelinquishOptions(True)
            sync_options.SetRelinquishOptions(relinquish_options)
            sync_options.Comment = "Backup"
            doc.SynchronizeWithCentral(transact_options, sync_options)
    else:
        save_request = forms.alert('Save file before archiving?',
                                   yes=True,
                                   no=True)
        if save_request is True:
            doc.Save()

    file_dir_path = op.split(file_path)[0]
    paths_and_names = []
    paths_and_names.append((file_path, op.basename(file_path)))

    # Get linked files
    xref_ids = DB.ExternalFileUtils.GetAllExternalFileReferences(doc)
    image_types = collect_image_types(doc)

    types_and_paths = []
    for id in xref_ids:
        xref = doc.GetElement(id).GetExternalFileReference()
        abs_path = xref.GetAbsolutePath()
        if isinstance(abs_path, DB.FilePath) and not abs_path.Empty:
            xref_file_path = DB.ModelPathUtils\
                .ConvertModelPathToUserVisiblePath(abs_path)
            types_and_paths.append(
                (str(xref.ExternalFileReferenceType), xref_file_path)
            )

    for image_type in image_types:
        if image_type.Source == DB.ImageTypeSource.Link:
            types_and_paths.append((image_type.FamilyName, image_type.Path))

    if types_and_paths:
        types_and_paths.sort(key=itemgetter(0))
        groupped_paths = {}
        for key, group in groupby(types_and_paths, key=itemgetter(0)):
            type_group = []
            for type_and_path in group:
                type_group.append(type_and_path[1])
            groupped_paths[key] = type_group

        ask_to_add_xrefs = forms.alert('Include linked files to archive?',
                                       yes=True,
                                       no=True)

        if ask_to_add_xrefs:
            selected_types = forms.SelectFromList.show(
                groupped_paths.keys(),
                title='Select link file types',
                button_name='Select',
                width=400,
                multiselect=True
            )

            if selected_types:
                LINKS_FOLDER = 'Linked Files'
                for xref_type in selected_types:
                    for xref_file_path in groupped_paths[xref_type]:
                        xref_dir_path = op.split(xref_file_path)[0]
                        xref_filename = op.basename(xref_file_path)
                        xref_splitdrive = op.splitdrive(xref_file_path)
                        is_same_drive = xref_splitdrive[0] == \
                            op.splitdrive(file_path)[0]
                        if is_same_drive:
                            relpath = op.relpath(xref_file_path,
                                                 file_path).replace('..\\', '')
                            xref_rel_path = op.join(LINKS_FOLDER,
                                                    relpath)
                        else:
                            comb_path = '\\'.join((LINKS_FOLDER,
                                                   xref_splitdrive[0][:1],
                                                   xref_splitdrive[1]))
                            xref_rel_path = op.normpath(comb_path)
                        paths_and_names.append((xref_file_path, xref_rel_path))

    # Call export dialog
    file_title = op.splitext(op.basename(file_path))[0]
    proposed_zipname = propose_zipfilename(file_title)
    export_dialog = call_export_dialog(file_dir_path, proposed_zipname)
    if export_dialog[0] == DialogResult.OK:
        zip_file_path = export_dialog[1]

        # Process missing files
        skipped_files = []
        for i, path_and_name in enumerate(paths_and_names):
            path_to_test = path_and_name[0]
            if not op.isfile(path_to_test):
                ask_missing_file = forms.alert(
                    'Could not get path for: \n{}'.format(path_to_test),
                    options=['Skip this file', 'Abort backing-up'])
                if ask_missing_file == 'Skip this file':
                    paths_and_names.pop(i)
                    skipped_files.append(path_to_test)
                else:
                    script.exit()

        # Check for file path conflicts in zip archive
        file_names = [x[1] for x in paths_and_names]
        if len(set(file_names)) != len(file_names):
            conflicts = {name: [] for name in get_duplicates(file_names)}
            for path, name in paths_and_names:
                if name in conflicts.keys():
                    conflicts[name].append(path)
            output_the_conflicts(conflicts)
            script.exit()

        # Zip files
        output.print_md(
            "**Zipping files to:** `{}`".format(zip_file_path))
        with ZipFile(zip_file_path, mode='w') as zip_obj:
            for file_path, file_name in paths_and_names:
                zip_obj.write(file_path, file_name)
                output.print_md('- `{}`'.format(file_path))
        if skipped_files:
            output.print_md('**Skipped files:** \n\n')
            [output.print_md('- `{}`'.format(x)) for x in skipped_files]
        output.print_md('**Done**')

else:
    forms.alert("The active document does not have a valid file path."
                " Save it at least once before making back up.")
