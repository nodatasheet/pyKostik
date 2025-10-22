from Autodesk.Revit import DB
from Autodesk.Revit.DB import Mechanical as MECH

from pykostik.wrappers import BasePKWrapper, BasePKObject, db


class PkDuct(db.PkMEPCurve):
    _RVT_TYPE = MECH.Duct

    def __init__(self, rvt_obj):
        # type: (MECH.Duct) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: MECH.Duct

    @property
    def unwrap(self):
        return self._rvt_obj
