import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit import DB

from pykostik.wrappers import BasePKObject
import pykostik as pk
from pykostik import exceptions as pke


class PkParameter(BasePKObject):
    def __init__(self, param):
        # type: (DB.Parameter) -> None
        pk.validate_type(param, DB.Parameter)
        self.param = param
        self.name = param.Definition.Name

    @property
    def has_value(self):
        return self.param.HasValue

    @property
    def value(self):
        # type: () -> int | float | str | DB.ElementId | None
        storage_type = self.param.StorageType
        if storage_type == DB.StorageType.Integer:
            return self.param.AsInteger()

        if storage_type == DB.StorageType.Double:
            return self.param.AsDouble()

        if storage_type == DB.StorageType.String:
            return self.param.AsString()

        if storage_type == DB.StorageType.ElementId:
            return self.param.AsElementId()

    @value.setter
    def value(self, new_value):
        # type: (int | float | str | DB.ElementId) -> bool
        if self.param.IsReadOnly:
            raise pke.ParameterIsReadOnlyError(
                'parameter "{}" is read only'.format(self.name)
            )

        return self.param.Set(new_value)
