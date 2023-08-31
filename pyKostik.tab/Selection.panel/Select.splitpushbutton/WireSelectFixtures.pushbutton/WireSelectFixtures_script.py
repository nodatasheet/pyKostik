"""Selects elements that are connected to wires."""

from pyrevit import revit, DB, forms
from Autodesk.Revit.DB import Electrical as DBE

doc = revit.doc  # type: DB.Document
selection = revit.get_selection()


class WireWrap(object):
    def __init__(self, wire):
        # type: (DBE.Wire) -> None
        self.id = wire.Id
        self.wire = wire
        self.manager = self.wire.ConnectorManager  # type: DB.ConnectorManager
        self._wire_connectors = None
        self._model_connectors = None
        self._connected_elems = None

    @property
    def connected_elems(self):
        if self._connected_elems is None:
            self._connected_elems = tuple(
                mc.elec_elem for mc in self.model_connecors
            )
        return self._connected_elems

    @property
    def model_connecors(self):
        # type: () -> tuple[ElecElemConnectorWrap]
        if self._model_connectors is None:
            model_connectors = self._get_model_connectors()
            self._model_connectors = tuple(model_connectors)
        return self._model_connectors

    def _get_model_connectors(self):
        # type: () -> list[ElecElemConnectorWrap]
        model_connectors = []
        for wc in self.wire_connectors:
            model_connector = wc.elem_connector
            if model_connector is not None:
                model_connectors.append(model_connector)
        return model_connectors

    @property
    def wire_connectors(self):
        if self._wire_connectors is None:
            self._wire_connectors = self._get_wire_connectors()
        return self._wire_connectors

    def _get_wire_connectors(self):
        # type: () -> tuple[WireConnectorWrap]
        return tuple(
            WireConnectorWrap(conn) for conn in self.manager.Connectors
        )


class ConnectorWrap(object):
    def __init__(self, connector):
        # type: (DB.Connector) -> None
        self.conn = connector
        self.owner = connector.Owner
        self.id = connector.Id

    @property
    def origin(self):
        return self.conn.Origin

    @property
    def elec_sys_type(self):
        # type: () -> DBE.ElectricalSystemType
        return self.conn.ElectricalSystemType


class WireConnectorWrap(ConnectorWrap):
    def __init__(self, connector):
        # type: (DB.Connector) -> None
        super(WireConnectorWrap, self).__init__(connector)
        self._elem_connector_flag = False

    @property
    def elem_connector(self):
        if self._elem_connector_flag is False:
            self._elem_connector = self._get_elem_connector()
            self._elem_connector_flag = True
        return self._elem_connector

    def _get_elem_connector(self):
        UNDEFINED_SYS = DBE.ElectricalSystemType.UndefinedSystemType
        for ref in self.conn.AllRefs:
            conn = ConnectorWrap(ref)
            if conn.elec_sys_type != UNDEFINED_SYS:
                return ElecElemConnectorWrap(ref)


class ElecElemConnectorWrap(ConnectorWrap):
    @property
    def elec_elem(self):
        return self.owner


wires = []
elements_to_select = []

if not selection.is_empty:
    for elem in selection.elements:
        if isinstance(elem, DBE.Wire):
            wires.append(elem)

if not wires:
    with forms.WarningBar(title='Select Wires'):
        wires = revit.pick_elements_by_category(
            DB.BuiltInCategory.OST_Wire)

if wires:
    for wire in wires:
        wire_wrap = WireWrap(wire)
        elements_to_select.extend(wire_wrap.connected_elems)


selection.set_to(elements_to_select)
