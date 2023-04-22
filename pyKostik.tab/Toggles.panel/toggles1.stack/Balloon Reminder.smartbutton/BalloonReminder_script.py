"""Shows Balloon Tip instead of modal Save/Sync reminding TaskDialog.
"""

import traceback

from System import EventHandler
from Autodesk.Revit import UI, DB

from pyrevit import forms, script
from pyrevit.extensions.components import SmartButton
from pyrevit.coreutils.configparser import PyRevitConfigSectionParser

from balloontip import InfoCenterPaletteManager
from balloontip import BalloonTip, ResultClickEventArgs

logger = script.get_logger()


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # type: (SmartButton, UI.PushButton, UI.UIApplication) -> bool
    """pyRevit smart button init.
    This function is called at the extension startup.
    """
    try:
        from pyrevit import script

        cfg_section_name = get_cfg_section_name(script_cmp.name)
        config = script.get_config(cfg_section_name)
        set_current_state(script_cmp, ui_button_cmp, config)
        subscribe_to_reminder_dialogbox(__rvt__, config)
        return True
    except Exception as err:
        logger.exception(err)
        return False


def get_cfg_section_name(command_name):
    # type: (str) -> str
    """Gets config section name.
    Same way as it is done in pyrevit.script.get_config()
    """
    SCRIPT_CFG_POSTFIX = 'config'
    config_section_name = command_name + SCRIPT_CFG_POSTFIX
    return config_section_name


def set_current_state(script_cmp, ui_button_cmp, config):
    # type: (SmartButton, UI.PushButton, PyRevitConfigSectionParser) -> None
    """Sets current state of the smart button using config."""

    # following constants had to be declared twice in this code
    # keep it in mind in case of changes
    # TODO: figure out a better way
    BALLOON_STATE_ENV_VAR = 'ENABLE_SAVE_BALLOONTIP'
    BALLOON_STATE_OPTION_NAME = 'balloontip_enabled'

    set_default_config_option(config, BALLOON_STATE_OPTION_NAME, False)

    current_state = config.get_option(BALLOON_STATE_OPTION_NAME, False)
    script.set_envvar(BALLOON_STATE_ENV_VAR, current_state)

    if current_state:
        icon_path = script_cmp.get_bundle_file('on.png')
        ui_button_cmp.set_icon(icon_path)


def set_default_config_option(config, option_name, option_value):
    # type: (PyRevitConfigSectionParser, str, bool) -> None
    """Creates config option and sets its value
    if this option does not exist yet
    """
    if not config.has_option(option_name):
        config.set_option(option_name, option_value)
        script.save_config()


def subscribe_to_reminder_dialogbox(uiapp, config):
    # type: (UI.UIApplication, PyRevitConfigSectionParser) -> None
    uiapp.DialogBoxShowing += \
        EventHandler[UI.Events.DialogBoxShowingEventArgs](
            lambda sender, args: show_reminder_balloon(sender, args, config))


def show_reminder_balloon(sender, args, config):
    # type: (UI.UIApplication, UI.Events.DialogBoxShowingEventArgs, PyRevitConfigSectionParser) -> None
    try:
        if script.get_envvar(BALLOON_STATE_ENV_VAR):
            dialog_id = args.DialogId
            doc = sender.ActiveUIDocument.Document

            if dialog_id == 'TaskDialog_Project_Not_Saved_Recently':
                cancel_task_dialog(args)
                save_balloon = get_save_balloon(sender, args, doc)
                subscribe_to_save_click(sender, doc, save_balloon)
                InfoCenterPaletteManager.ShowBalloon(save_balloon)

            if dialog_id == 'TaskDialog_Changes_Not_Synchronized_With_Central':
                cancel_task_dialog(args)
                sync_balloon = get_sync_balloon(sender, args, doc)
                subscribe_to_sync_click(sender, doc, config, sync_balloon)
                InfoCenterPaletteManager.ShowBalloon(sync_balloon)
    except Exception as err:
        logger.exception(err)


def cancel_task_dialog(dialog_event_args):
    # type: (UI.Events.DialogBoxShowingEventArgs) -> bool
    return dialog_event_args.OverrideResult(int(UI.TaskDialogResult.Cancel))


def get_save_balloon(sender, args, doc):
    # type: (UI.UIApplication, UI.Events.DialogBoxShowingEventArgs, DB.Document) -> BalloonTip
    save_balloontip = BalloonTip(
        'Document \n"{}"\n has not been saved recently'.format(doc.Title),
        '\nSave now')
    return save_balloontip


def subscribe_to_save_click(_uiapp, doc, save_balloontip):
    # type: (UI.UIApplication, DB.Document, BalloonTip) -> None
    save_balloontip.ResultClicked += EventHandler[ResultClickEventArgs](
        lambda sender, args: save_document(sender, args, _uiapp, doc))


def save_document(sender, args, _uiapp, doc):
    # type: (BalloonTip, ResultClickEventArgs, UI.UIApplication, DB.Document) -> None
    try:
        if doc.IsValidObject and _uiapp.Application.Documents.Contains(doc):
            doc.Save()
        else:
            forms.alert('Could not save the Document\n'
                        'Most likely it has been closed already')
    except Exception:
        forms.alert(
            'Document "{}" could not be saved by click\n'
            'Please do it using Save button'.format(doc.Title),
            expanded=str(traceback.format_exc()))


def get_sync_balloon(sender, args, doc):
    # type: (UI.UIApplication, UI.Events.DialogBoxShowingEventArgs, DB.Document) -> BalloonTip
    sync_balloontip = BalloonTip('Project \n"{}"\n has not been synchronized'
                                 ' with central recently'.format(doc.Title),
                                 '\nSynchronize now')
    return sync_balloontip


def subscribe_to_sync_click(_uiapp, doc, script_cfg, sync_balloontip):
    # type: (UI.UIApplication, DB.Document, PyRevitConfigSectionParser, BalloonTip) -> None
    sync_balloontip.ResultClicked += \
        EventHandler[ResultClickEventArgs](
            lambda sender, args: sync_document(
                sender, args, _uiapp, doc, script_cfg))


def sync_document(sender, args, _uiapp, doc, script_cfg):
    # type: (BalloonTip, ResultClickEventArgs, UI.UIApplication, DB.Document, PyRevitConfigSectionParser) -> None
    try:
        if doc.IsValidObject and _uiapp.Application.Documents.Contains(doc):
            transact_opts = DB.TransactWithCentralOptions()
            sync_opts = get_sync_options(script_cfg)
            revit_version = int(_uiapp.Application.VersionNumber)
            if revit_version >= 2019 and doc.IsModelInCloud:
                sync_opts.SaveLocalBefore = sync_opts.SaveLocalAfter = True
            doc.SynchronizeWithCentral(transact_opts, sync_opts)
        else:
            forms.alert('Could not synchronize the Document\n'
                        'Most likely it has been closed already')
    except Exception:
        forms.alert(
            'Project "{}" could not be synchronized by click.\n'
            'Please do it using'
            ' Synchronize with Central button'.format(doc.Title),
            expanded=str(traceback.format_exc()))


def get_sync_options(script_cfg):
    # type: (PyRevitConfigSectionParser) -> DB.SynchronizeWithCentralOptions
    sync_opts = DB.SynchronizeWithCentralOptions()

    sync_opts.Compact = script_cfg.get_option('compact_central', False)
    sync_opts.Comment = script_cfg.get_option('sync_comment', '')
    sync_opts.SaveLocalBefore = sync_opts.SaveLocalAfter = \
        script_cfg.get_option('save_local', False)

    relinquish_opts = get_relinquish_opts(script_cfg)
    sync_opts.SetRelinquishOptions(relinquish_opts)

    return sync_opts


def get_relinquish_opts(script_cfg):
    # type: (PyRevitConfigSectionParser) -> DB.RelinquishOptions
    relinq_opts = DB.RelinquishOptions(False)

    relinq_opts.StandardWorksets = \
        script_cfg.get_option('relinq_proj_standards', False)
    relinq_opts.FamilyWorksets = \
        script_cfg.get_option('relinq_families', False)
    relinq_opts.CheckedOutElements = \
        script_cfg.get_option('relinq_borrowed', False)
    relinq_opts.ViewWorksets = \
        script_cfg.get_option('relinq_views', False)
    relinq_opts.UserWorksets = \
        script_cfg.get_option('relinq_user_created', False)

    return relinq_opts


def toggle_balloon_state_config(_config, _OPTION):
    # type: (PyRevitConfigSectionParser, str) -> bool
    """Toggle script config option for balloon state"""
    new_state = not _config.get_option(_OPTION, False)
    _config.set_option(_OPTION, new_state)
    script.save_config()
    return new_state


# following constants had to be declared twice in this code
# keep it in mind in case of changes
# TODO: figure out a better way
BALLOON_STATE_ENV_VAR = 'ENABLE_SAVE_BALLOONTIP'
BALLOON_STATE_OPTION_NAME = 'balloontip_enabled'

config = script.get_config()

if __name__ == '__main__':
    new_state = toggle_balloon_state_config(config, BALLOON_STATE_OPTION_NAME)
    script.set_envvar(BALLOON_STATE_ENV_VAR, new_state)
    script.toggle_icon(new_state)
