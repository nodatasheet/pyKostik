from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing as PLUM

from pykostik.wrappers import BasePKWrapper, BasePKObject, db


class PkPipe(db.PkMEPCurve):
    _RVT_TYPE = PLUM.Pipe

    def __init__(self, rvt_obj):
        # type: (PLUM.Pipe) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: PLUM.Pipe

    @property
    def unwrap(self):
        return self._rvt_obj
