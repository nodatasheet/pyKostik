import clr
import datetime
import traceback

from System import EventHandler
from Autodesk.Revit import UI, DB

from pyrevit import revit, forms, script
from pyrevit.extensions.components import SmartButton

try:
    # in pyrevit it is not actually needed
    # and even rised an error once
    clr.AddReference('AdWindows')
except Exception as errmsg:
    print(errmsg)

from Autodesk.Internal.InfoCenter import ResultItem, ResultClickEventArgs
from Autodesk.Windows.ComponentManager import InfoCenterPaletteManager as ICM


doc = revit.doc
uiapp = revit.HOST_APP.uiapp
uiappa = uiapp.Application
logger = script.get_logger()


class BalloonTip(ResultItem):
    """Class for displaying a balloon tip at the top right corner of Revit.
    https://thebuildingcoder.typepad.com/blog/2014/03/using-balloon-tips-in-revit.html#3"""

    def __init__(self, tip_category, tip_title):
        self.category = tip_category
        self.title = tip_title
        self.isnew = True

    @property
    def category(self):
        return self.Category

    @category.setter
    def category(self, cat_txt):
        self.Category = cat_txt

    @property
    def title(self):
        return self.Title

    @title.setter
    def title(self, title_txt):
        self.Title = title_txt

    @property
    def isnew(self):
        return self.IsNew

    @isnew.setter
    def isnew(self, value):
        self.IsNew = value


def toggle_config(_config, _OPTION):
    """Toggle script config option"""
    new_state = not _config.get_option(_OPTION, False)
    _config.set_option(_OPTION, new_state)
    script.save_config()
    return new_state


def show_viewname(sender, args, view):
    try:
        forms.alert('View Name "{}"'.format(view.Name))
    except Exception:
        logger.exception(str(traceback.format_exc()))


def show_view_name_ballon(sender, args):
    try:
        if script.get_envvar(BALLOON_STATE_ENV_VAR):
            view = args.CurrentActiveView  # type: DB.View
            # doc = args.Document  # type: DB.Document
            b_tip = BalloonTip(view.Title, '\nClick me')
            b_tip.ResultClicked += EventHandler[ResultClickEventArgs](
                lambda sender, args: show_viewname(sender, args, view))
            ICM.ShowBalloon(b_tip)
    except Exception:
        logger.exception(str(traceback.format_exc()))


def set_default_config_option(config, option_name, option_value):
    """Creates config option and sets its value
    iff this option does not exist yet"""

    if not config.has_option(option_name):
        config.set_option(option_name, option_value)
        script.save_config()


def set_current_state(script_cmp, ui_button_cmp):
    BALLOON_STATE_ENV_VAR = 'ENABLE_VIEWACTIVATED_BALLOONTIP'
    BALLOON_STATE_OPTION_NAME = 'viewactivated_balloontip_enabled'

    from pyrevit import script

    SCRIPT_CFG_POSTFIX = 'config'  # same as in pyrevit.script.get_config()
    cfg_section_name = script_cmp.name + SCRIPT_CFG_POSTFIX
    config = script.get_config(cfg_section_name)

    set_default_config_option(config, BALLOON_STATE_OPTION_NAME, False)

    current_state = config.get_option(BALLOON_STATE_OPTION_NAME, False)
    script.set_envvar(BALLOON_STATE_ENV_VAR, current_state)

    if current_state:
        icon_path = script_cmp.get_bundle_file('on.png')
        ui_button_cmp.set_icon(icon_path)


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # type: (SmartButton, UI.PushButton, UI.UIApplication) -> bool
    """pyRevit smart button init.
    This function is called at extension startup."""

    import traceback
    try:
        set_current_state(script_cmp, ui_button_cmp)

        __rvt__.ViewActivated += EventHandler[
            UI.Events.ViewActivatedEventArgs](show_view_name_ballon)

        return True
    except Exception:
        print(traceback.format_exc())
        return False


BALLOON_STATE_ENV_VAR = 'ENABLE_VIEWACTIVATED_BALLOONTIP'
BALLOON_STATE_OPTION_NAME = 'viewactivated_balloontip_enabled'
config = script.get_config()

if __name__ == '__main__':
    new_state = toggle_config(config, BALLOON_STATE_OPTION_NAME)
    script.set_envvar(BALLOON_STATE_ENV_VAR, new_state)
    script.toggle_icon(new_state)
