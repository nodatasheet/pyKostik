import clr
from pyrevit import script

logger = script.get_logger()

try:
    # Somehow it is not actually required in pyRevit
    # and even rised an error once
    # but i kept it just in case
    clr.AddReference('AdWindows')
except Exception as errmsg:
    logger.exception(errmsg)

from Autodesk.Windows.ComponentManager import InfoCenterPaletteManager
from Autodesk.Internal.InfoCenter import ResultItem, ResultClickEventArgs


class BalloonTip(ResultItem):
    """Class for displaying a Balloon Tip at the top right corner of Revit.
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
