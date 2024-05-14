from Autodesk.Revit import DB
from Autodesk.Revit.DB import Electrical as ELEC

from pykostik.wrappers import BasePKWrapper, BasePKObject, db


class PkWire(db.PkMEPCurve):
    _RVT_TYPE = ELEC.Wire

    def __init__(self, rvt_obj):
        # type: (ELEC.Wire) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: ELEC.Wire

    @property
    def unwrap(self):
        return self._rvt_obj


class PkElectricalSystem(db.PkMEPSystem):
    _RVT_TYPE = ELEC.ElectricalSystem

    def __init__(self, rvt_obj):
        # type: (ELEC.ElectricalSystem) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: ELEC.ElectricalSystem

    @property
    def unwrap(self):
        return self._rvt_obj

    @classmethod
    def create_by_connector(cls, connector, rvt_electrical_system_type):
        # type: (db.PkConnector, ELEC.ElectricalSystemType) -> PkElectricalSystem  # noqa
        rvt_elec_system = ELEC.ElectricalSystem.Create(
            connector.unwrap,
            rvt_electrical_system_type
        )
        if rvt_elec_system is not None:
            return cls(rvt_elec_system)

    def select_panel(self, family_instance):
        # type: (db.PkFamilyInstance) -> None
        return self._rvt_obj.SelectPanel(family_instance.unwrap)

    def disconnect_panel(self):
        self._rvt_obj.DisconnectPanel()


class PkElectricalEquipment(db.PkMEPModel):
    _RVT_TYPE = ELEC.ElectricalEquipment

    def __init__(self, rvt_obj):
        # type: (ELEC.ElectricalEquipment) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: ELEC.ElectricalEquipment

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_electrical_systems(self):
        # type: () -> set[PkElectricalSystem]
        elec_systems = set()
        for s in self._rvt_obj.GetElectricalSystems():
            pk_elec_sys = PkElectricalSystem(s)
            elec_systems.add(pk_elec_sys)
        return elec_systems

    @property
    def max_num_of_ckts(self):
        # type: () -> int
        """For switchboard only"""
        return self._rvt_obj.MaxNumberOfCircuits

    @max_num_of_ckts.setter
    def max_num_of_ckts(self, value):
        # type: (int) -> None
        self._rvt_obj.MaxNumberOfCircuits = value


class PkPanelScheduleView(db.ViewsForSheet):
    _RVT_TYPE = ELEC.PanelScheduleView

    def __init__(self, rvt_obj):
        # type: (ELEC.PanelScheduleView) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: ELEC.PanelScheduleView

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_panel_id(self):
        return db.PkElementId(self._rvt_obj.GetPanel())

    def get_panel(self):
        # type: () -> db.PkFamilyInstance
        return self.get_panel_id().get_element(self.doc)

    @property
    def is_template(self):
        # type: () -> bool
        return self._rvt_obj.IsPanelScheduleTemplate()

    def set_lock_slot(self, row_num, column_number, lock):
        # type: (int, int, bool) -> None
        self._rvt_obj.SetLockSlot(row_num, column_number, lock)

    def is_row_in_ckt_table(self, row_num):
        # type: (int) -> bool
        return self._rvt_obj.IsRowInCircuitTable(row_num)
