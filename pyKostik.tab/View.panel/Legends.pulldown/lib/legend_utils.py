from pyrevit import DB, UI, forms, revit, script, HOST_APP


class InvalidOperationException(Exception):
    """Invalid Operation Exception"""
    pass


class ValidationError(Exception):
    """Base class for Validation Errors"""
    pass


class CategoryValidationError(ValidationError):
    """Category Validation Error"""
    pass


class TypeValidationError(ValidationError):
    """Type Validation Error"""
    pass


class AttributeValidationError(ValidationError):
    """Attribute Validation Error"""
    pass


class LegendComponent(object):
    """Class for Legend Component."""
    _id = None
    _component_type = None

    def __init__(self, legcomp):
        # type: (DB.Element) -> None
        self._validate_legcomp(legcomp)
        self._doc = legcomp.Document
        self._legcomp = legcomp
        self._legend_view = self._get_owner_view(legcomp)
        self._id = self._legcomp.Id
        self._component_type = self._get_component_type()
        self._wrapped_type = FamilyTypeWrapper(self._component_type)

    def _get_component_type(self):
        return self._doc.GetElement(self.component_type_param.AsElementId())

    def _get_owner_view(self, legcomp):
        return self._doc.GetElement(legcomp.OwnerViewId)

    @classmethod
    def _validate_legcomp(cls, legcomp):
        # type: (DB.Element) -> None
        cls._validate_element(legcomp)
        cls._assure_has_category(legcomp)
        cls._assure_legcomp(legcomp)

    @classmethod
    def _validate_element(cls, elem):
        # type: (DB.Element) -> None
        if not isinstance(elem, DB.Element):
            raise TypeValidationError(
                'Expected <{}>, got <{}>'.format(DB.Element.__name__,
                                                 type(elem).__name__))

    @classmethod
    def _assure_has_category(cls, elem):
        # type: (DB.Element) -> None
        if not hasattr(elem, 'Category'):
            raise AttributeValidationError('Element has no Category')

    @classmethod
    def _assure_legcomp(cls, legcomp):
        # type: (DB.Element) -> None
        if legcomp.Category.Id != \
                DB.ElementId(DB.BuiltInCategory.OST_LegendComponents):
            raise CategoryValidationError(
                'Element Category should be OST_LegendComponents')

    def _validate_family_type(self, elem_type):
        # type: (DB.ElementType) -> None
        if not isinstance(elem_type, DB.ElementType):
            raise TypeValidationError(
                'Expected <{}>, got <{}>'.format(DB.ElementType.__name__,
                                                 type(elem_type).__name__))

    @classmethod
    def is_of_legcomp_cat(cls, elem):
        # type: (DB.Element) -> bool
        """Checks whether Element is of BuiltInCategory.OST_LegendComponents.
        """
        try:
            cls._validate_legcomp(elem)
            return True
        except ValidationError:
            return False

    @classmethod
    def get_legcomp_cat(cls, _doc):
        # type: (DB.Document) -> DB.Category
        """Attempts to get a Category object
        corresponding to BuiltInCategory.OST_LegendComponents.
        """
        # Could not figure out any better working way.
        first_legcomp = DB.FilteredElementCollector(_doc)\
            .OfCategory(DB.BuiltInCategory.OST_LegendComponents)\
            .WhereElementIsNotElementType()\
            .FirstElement()
        if first_legcomp is not None:
            return first_legcomp.Category

    def copy(self, destination_location):
        """Copies Legend Component to a given location in Legend View."""
        # type: (DB.XYZ) -> LegendComponent
        copied_elem_ids = DB.ElementTransformUtils.CopyElement(
            self._doc,
            self._legcomp.Id,
            self.location - destination_location)
        if copied_elem_ids:
            return LegendComponent(self._doc.GetElement(copied_elem_ids[0]))
        else:
            raise Exception('Could not copy Legend Component')

    def move(self, translation):
        """Moves Legend Component by translation vector."""
        # type: (DB.XYZ) -> None
        DB.ElementTransformUtils.MoveElement(
            self._doc, self._legcomp.Id, translation)

    @property
    def component_type_param(self):
        # type: () -> DB.Parameter
        return self._legcomp.get_Parameter(
            DB.BuiltInParameter.LEGEND_COMPONENT)

    @component_type_param.setter
    def component_type_param(self, param_value):
        # type: (DB.ElementId) -> None
        self.component_type_param.Set(param_value)

    @property
    def component_type(self):
        # type: () -> DB.ElementType
        return self._component_type

    @property
    def wrapped_type(self):
        # type: () -> FamilyTypeWrapper
        return self._wrapped_type

    @property
    def id(self):
        return self._id

    @property
    def component_type_name(self):
        # type: () -> str
        return self.component_type.get_Parameter(
            DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()

    @property
    def location(self):
        # type: () -> DB.XYZ
        return (self.bounding_box.Max + self.bounding_box.Min) / 2

    @property
    def bounding_box(self):
        # type: () -> DB.BoundingBoxXYZ
        return self._legcomp.get_BoundingBox(self._legend_view)

    @property
    def height(self):
        # type: () -> float
        return self.bounding_box.Max.Y - self.bounding_box.Min.Y

    @property
    def width(self):
        # type: () -> float
        return self.bounding_box.Max.X - self.bounding_box.Min.X

    @property
    def owner_view_id(self):
        # type: () -> DB.ElementId
        return self._legcomp.OwnerViewId


class FamilyTypeWrapper(object):
    """Class for Revit Family Type."""
    _sorting_param = None

    def __init__(self, family_type):
        # type: (DB.ElementType) -> None
        self._validate_type(family_type)
        self._family_type = family_type
        self._wrapped_params = self._wrap_parameters()

    def _validate_type(self, elem_type):
        if not isinstance(elem_type, DB.ElementType):
            raise TypeValidationError(
                'Expected <{}>, got <{}>'.format(DB.ElementType.__name__,
                                                 type(elem_type).__name__))

    def _wrap_parameters(self):
        return [
            ParameterWrapper(param) for param in self._family_type.Parameters]

    def set_sorting_param(self, param_unique_name):
        # type: (str) -> None
        for param in self._wrapped_params:
            if param.unique_name == param_unique_name:
                self._sorting_param = param
                break
        else:
            raise InvalidOperationException(
                'Failed setting sorting parameter:'
                '(no match to name "{}")'.format(param_unique_name))

    def get_param_value_by_name(self, param_name):
        # type: (str) -> int | float | str | DB.ElementId
        """Gets Parameter value by Parameter Name.\\
        If not found any matching Parameter, returns None.\\
        If Parameter's value is None, returns empty string.\\
        In case of multiple matching parameters
        the first one encountered will be returned.
        """
        wrapped_param = self.lookup_wrapped_param(param_name)
        if wrapped_param is not None:
            return wrapped_param.get_value_or_empty_str()

    def lookup_wrapped_param(self, param_name):
        # type: (str) -> ParameterWrapper
        rvt_param = self._family_type.LookupParameter(param_name)
        if rvt_param is not None:
            return ParameterWrapper(rvt_param)

    @property
    def type_name(self):
        # type: (None) -> str
        return self._family_type.get_Parameter(
            DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()

    @property
    def family_name(self):
        # type: (None) -> str
        return self._family_type.FamilyName

    @property
    def family_type(self):
        # type: (None) -> DB.ElementType
        return self._family_type

    @property
    def unique_param_names(self):
        # type: (None) -> list[str]
        """A list of unique Parameter Names for this Family Type"""
        return [param.unique_name for param in self._wrapped_params]

    @property
    def param_names(self):
        # type: (None) -> set[str]
        """A set of Parameter Names for this Family Type"""
        return set(param.name for param in self._wrapped_params)

    @property
    def sorting_param_value(self):
        if self._sorting_param is not None:
            return self._sorting_param.get_value_or_empty_str()
        raise InvalidOperationException('Sorting parameter not set')


class ParameterWrapper(object):
    """Class for Revit Parameter"""

    def __init__(self, parameter):
        # type: (DB.Parameter) -> None
        self._validate_param(parameter)
        self._parameter = parameter

    def _validate_param(self, param):
        if not isinstance(param, DB.Parameter):
            raise TypeValidationError(
                'Expected <{}>, got <{}>'.format(DB.Parameter.__name__,
                                                 type(param).__name__))

    def get_value_or_empty_str(self):
        # type: () -> int | float | str | DB.ElementId
        """Gets parameter value converting None
        and InvalidElementId value to an empty string"""
        param_val = self._get_value()
        return param_val if param_val else str()

    def _get_value(self):
        # type: () -> int | float | str | DB.ElementId | None
        if self._storage_type == DB.StorageType.Integer:
            return self._parameter.AsInteger()
        if self._storage_type == DB.StorageType.Double:
            return self._parameter.AsDouble()
        if self._storage_type == DB.StorageType.String:
            return self._parameter.AsString()
        if self._value_is_element_id and not self._value_is_invalid_element_id:
            return self._parameter.AsElementId()

    def get_value_as_string(self):
        # type: () -> str
        """Gets Parameter value as it is seen by the user."""
        if not self._value_is_invalid_element_id:
            return self._parameter.AsValueString()

    def get_value_as_unitless_string(self, _doc):
        # type: (DB.Document) -> str
        """Gets Parameter value as it is seen by the user,
        but without the units.
        """
        if self._value_is_measurable:
            doc_unit_opts = _doc.GetUnits().GetFormatOptions(self._spec_type)
            custom_opts = DB.FormatOptions(doc_unit_opts)
            empty_symbol = DB.ForgeTypeId()
            custom_opts.SetSymbolTypeId(empty_symbol)
            return self._parameter.AsValueString(custom_opts)
        return self.get_value_as_string()

    @property
    def _value_is_measurable(self):
        # type: () -> bool
        return DB.UnitUtils.IsMeasurableSpec(self._spec_type)

    @property
    def _value_is_element_id(self):
        # type: () -> bool
        return self._storage_type == DB.StorageType.ElementId

    @property
    def _value_is_invalid_element_id(self):
        # type: () -> bool
        return self._value_is_element_id \
            and self._parameter.AsElementId() == DB.ElementId.InvalidElementId

    @property
    def _spec_type(self):
        # type: () -> DB.SpecTypeId
        return self._parameter.Definition.GetDataType()

    @property
    def _unit_type(self):
        # type: () -> DB.UnitTypeId
        if self._storage_type == DB.StorageType.Double:
            return self._parameter.GetUnitTypeId()

    @property
    def _storage_type(self):
        # type: () -> DB.StorageType
        return self._parameter.StorageType

    @property
    def parameter(self):
        return self._parameter

    @property
    def unique_name(self):
        # type: () -> str
        """Unique Parameter Name. Consists of Parameter Name + Parameter Id."""
        return self.name + ' <' + str(self._id) + '>'

    @property
    def name(self):
        # type: () -> str
        """Parameter Name"""
        return self._parameter.Definition.Name

    @property
    def _id(self):
        return self._parameter.Id


class RevitUnitUtils(object):
    def __init__(self, doc):
        self._doc = doc
        self._doc_units = self._doc.GetUnits()
        self._revit_ver = int(HOST_APP.version)

    def to_internal_units(self, value, unit_type):
        # type: (float, DB.UnitType | DB.ForgeTypeId) -> float
        if self._revit_ver < 2021:
            ui_unit = self._doc_units.GetFormatOptions(unit_type)\
                .DisplayUnits
        else:
            ui_unit = self._doc_units.GetFormatOptions(unit_type)\
                .GetUnitTypeId()
        return DB.UnitUtils.ConvertFromInternalUnits(value, ui_unit)

    def get_unit_accuracy(self, unit_type):
        # type: (DB.UnitType | DB.ForgeTypeId) -> float
        """Accuracy of the given unit in Document."""
        # TODO: Handle fractional units
        return self._doc_units.GetFormatOptions(unit_type).Accuracy

    def _get_ndigits(self, accuracy):
        # type: (float) -> int
        return str(int(1 / accuracy)).count('0')


def length_to_internal_units(_doc, length):
    # type: (DB.Document, float) -> float
    """Converts Length from document units to Revit's internal units."""
    revit_ver = int(HOST_APP.version)
    doc_units = _doc.GetUnits()
    if revit_ver < 2021:
        ui_unit = doc_units.GetFormatOptions(DB.UnitType.UT_Length)\
            .DisplayUnits
    else:
        ui_unit = doc_units.GetFormatOptions(DB.SpecTypeId.Length)\
            .GetUnitTypeId()
    return DB.UnitUtils.ConvertToInternalUnits(length, ui_unit)


def length_from_internal_units(_doc, length):
    # type: (DB.Document, float) -> float
    """Converts Length from Revit's internal units to document units."""
    revit_ver = int(HOST_APP.version)
    doc_units = _doc.GetUnits()
    if revit_ver < 2021:
        ui_unit = doc_units.GetFormatOptions(DB.UnitType.UT_Length)\
            .DisplayUnits
    else:
        ui_unit = doc_units.GetFormatOptions(DB.SpecTypeId.Length)\
            .GetUnitTypeId()
    return DB.UnitUtils.ConvertFromInternalUnits(length, ui_unit)


def get_length_accuracy(_doc):
    # type: (DB.Document) -> float
    """Gets Accuracy of the Length in given Document."""
    # TODO: Handle fractional units
    revit_ver = int(HOST_APP.version)
    doc_units = _doc.GetUnits()
    if revit_ver < 2021:
        unit_type = DB.UnitType.UT_Length
    else:
        unit_type = DB.SpecTypeId.Length
    return doc_units.GetFormatOptions(unit_type).Accuracy


def cmp_to_key_by_attrs(comparer, attrs):
    """Converts a comparer into a key= function
    for multilevel sorting or ordering by supplied attributes.

    Refer to functools.cmp_to_key() and operator.attrgetter().

    Args:
        comparer: a function that compares two arguments and then returns
            a negative value for '<', zero for '==', or a positive for '>'
        attrs (optional): list of attribute strings

    Returns:
        key function: a callable that returns a value for sorting or ordering
    """

    class K(object):
        __slots__ = ['_obj']

        def __init__(self, obj, attr):
            self._validate_attr(attr)
            self._obj = self._resolve_attr(obj, attr)

        def _validate_attr(self, attr):
            if not isinstance(attr, str):
                raise TypeError(
                    'Expected string, got {}'.format(type(attr)))

        def _resolve_attr(self, obj, attr):
            for name in attr.split("."):
                obj = getattr(obj, name)
            return obj

        def __lt__(self, other):
            return comparer(self._obj, other._obj) < 0

        def __gt__(self, other):
            return comparer(self._obj, other._obj) > 0

        def __eq__(self, other):
            return comparer(self._obj, other._obj) == 0

        def __le__(self, other):
            return comparer(self._obj, other._obj) <= 0

        def __ge__(self, other):
            return comparer(self._obj, other._obj) >= 0

        def __ne__(self, other):
            return comparer(self._obj, other._obj) != 0

        __hash__ = None

    if not hasattr(attrs, '__iter__'):
        raise TypeError('Attributes must be iterable')

    if len(attrs) == 1:
        def call_k(obj):
            return K(obj, attrs[0])

    else:
        def call_k(obj):
            return tuple(K(obj, attr) for attr in attrs)

    return call_k


def names_comparer(name1, name2):
    """Compares two objects as strings using Revit's comparison rules"""
    return DB.NamingUtils.CompareNames(str(name1), str(name2))
