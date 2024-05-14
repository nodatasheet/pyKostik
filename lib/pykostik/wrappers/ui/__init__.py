from Autodesk.Revit import DB, UI
from Autodesk.Revit.ApplicationServices import Application

from pykostik.wrappers import BasePKWrapper, db
from pykostik.wrappers import application_services as app_svs
from pykostik.wrappers.ui import selection as uis


class PkUIApplication(BasePKWrapper):
    _RVT_TYPE = UI.UIApplication

    def __init__(self, app):
        # type: (UI.UIApplication) -> None
        self._validate_type(app, self._RVT_TYPE)
        self._rvt_obj = app  # type: UI.UIApplication

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def uidoc(self):
        return PkUIDocument(self._rvt_obj.ActiveUIDocument)

    @property
    def app(self):
        return app_svs.PkApplication(self._rvt_obj.Application)


pk_uiapp = PkUIApplication(__revit__)  # noqa


class PkUIDocument(BasePKWrapper):
    _RVT_TYPE = UI.UIDocument

    def __init__(self, app):
        # type: (UI.UIDocument) -> None
        self._validate_type(app, self._RVT_TYPE)
        self._rvt_obj = app  # type: UI.UIDocument

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def doc(self):
        return db.PkDocument(self._rvt_obj.Document)

    def refresh_active_view(self):
        self._rvt_obj.RefreshActiveView()

    @property
    def selection(self):
        return uis.PkSelection(self._rvt_obj.Selection)

    def request_view_change(self, view):
        # type: (db.PkView) -> None
        self._rvt_obj.RequestViewChange(view.unwrap)
