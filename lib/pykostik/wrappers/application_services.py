import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit import DB
from Autodesk.Revit.ApplicationServices import Application

from pykostik.wrappers import BasePKWrapper


class PkApplication(BasePKWrapper):
    _RVT_TYPE = Application

    def __init__(self, app):
        # type: (Application) -> None
        self._validate_type(app, self._RVT_TYPE)
        self._rvt_obj = app  # type: Application

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def short_curve_tolerance(self):
        # type: () -> float
        return self._rvt_obj.ShortCurveTolerance
