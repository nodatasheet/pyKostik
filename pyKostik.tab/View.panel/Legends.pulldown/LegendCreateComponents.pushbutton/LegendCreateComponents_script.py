"""Creates Legend Components from selected Elements
author: Konstantin (https://github.com/nodatasheet)
"""

from System import EventHandler
from pyrevit import DB, UI, forms, revit, script


def length_to_internal_units(length):
    # type: (float) -> float
    """Converts Length from document units to Revit's internal units"""
    revit_ver = int(app.VersionNumber)
    doc_units = doc.GetUnits()
    if revit_ver < 2021:
        ui_unit = doc_units.GetFormatOptions(DB.UnitType.UT_Length)\
            .DisplayUnits
    else:
        ui_unit = doc_units.GetFormatOptions(DB.SpecTypeId.Length)\
            .GetUnitTypeId()
    return DB.UnitUtils.ConvertToInternalUnits(length, ui_unit)


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


def sort_types_by_family_and_param(family_types):
    # type: (list[FamilyTypeWrapper]) -> list[FamilyTypeWrapper]
    return sorted(
        family_types,
        key=cmp_to_key_by_attrs(names_comparer,
                                ['family_name', 'sorting_param_value'])
    )


def sort_types_by_param(family_types):
    # type: (list[FamilyTypeWrapper]) -> list[FamilyTypeWrapper]
    return sorted(
        family_types,
        key=cmp_to_key_by_attrs(names_comparer, ['sorting_param_value'])
    )


def on_failure_processing(sender, event_args, failed_ids):
    """Swallows LegendComponentNotVisible failures
    and gets failed legend components.
    """
    try:
        failure_accesssor = event_args.GetFailuresAccessor()
        failures = failure_accesssor.GetFailureMessages()
        not_vis_failures = []
        for failure in failures:
            if DB.BuiltInFailures.LegendFailures.LegendComponentNotVisible ==\
                    failure.GetFailureDefinitionId():
                not_vis_failures.append(True)
                failed_ids.extend(failure.GetFailingElementIds())
            else:
                not_vis_failures.append(False)
        if all(not_vis_failures):
            failure_swallower = revit.failure.FailureSwallower()
            result = failure_swallower.preprocess_failures(failure_accesssor)
            event_args.SetProcessingResult(result)
        else:
            failed_ids = []
    except Exception as fpex:
        raise Exception('Error occurred while processing failures. | %s', fpex)


def distribute_left_to_right(legcomps, gap):
    # type: (list[LegendComponent], float) -> None
    for i, legcomp in enumerate(legcomps[1:], 1):
        offset = legcomps[i-1].width / 2 + legcomp.width / 2 + gap  # noqa
        translation = legcomps[i-1].location \
            - legcomp.location \
            + DB.XYZ(offset, 0, 0)  # noqa
        legcomp.move(translation)


def distribute_bottom_to_top(legcomps, gap):
    # type: (list[LegendComponent], float) -> None
    for i, legcomp in enumerate(legcomps[1:], 1):
        offset = legcomps[i-1].height / 2 + legcomp.height / 2 + gap  # noqa
        translation = legcomps[i-1].location \
            - legcomp.location \
            + DB.XYZ(0, offset, 0)  # noqa
        legcomp.move(translation)


def distribute_top_to_bottom(legcomps, gap):
    # type: (list[LegendComponent], float) -> None
    for i, legcomp in enumerate(legcomps[1:], 1):
        offset = legcomps[i-1].height / 2 + legcomp.height / 2 + gap  # noqa
        translation = legcomps[i-1].location \
            - legcomp.location \
            - DB.XYZ(0, offset, 0)  # noqa
        legcomp.move(translation)


def alert_no_components_in_view():
    forms.alert(
        'At least one Legend Component should present in the Legend View',
        exitscript=True)


class FamilyTypeWrapper(object):
    """Class for Family Type."""
    _sorting_param = None

    def __init__(self, family_type):
        # type: (DB.ElementType) -> None
        self._validate_type(family_type)
        self._family_type = family_type
        self._wrapped_params = self._wrap_parameters()

    def _validate_type(self, elem_type):
        if not isinstance(elem_type, DB.ElementType):
            raise TypeError(
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
            raise AttributeError(
                'Failed setting sorting parameter:'
                '(no match to name "{}")'.format(param_unique_name))

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
        return [param.unique_name for param in self._wrapped_params]

    @property
    def sorting_param_value(self):
        return self._sorting_param.get_param_value_or_empty_str()


class LegendView(object):
    """Class for Legend View."""

    def __init__(self, legend_view):
        # type: (DB.View) -> None
        self._validate_view(legend_view)
        self._legend_view = legend_view

    def _validate_view(self, legend_view):
        # type: (DB.View) -> None
        self._assure_view(legend_view)
        self._assure_legend_view(legend_view)

    def _assure_view(self, view):
        # type: (DB.View) -> None
        if not isinstance(view, DB.View):
            raise TypeError(
                'Expected <{}>, got <{}>'.format(DB.View.__name__,
                                                 type(view).__name__))

    def _assure_legend_view(self, legend_view):
        # type: (DB.View) -> None
        if not legend_view.ViewType == DB.ViewType.Legend:
            raise TypeError('ViewType should be Legend')

    def get_first_legcomp(self):
        # type: () -> LegendComponent
        """Attempts to get the first Legend Component in the Legend View."""
        first_comp = DB.FilteredElementCollector(doc, self._legend_view.Id)\
            .OfCategory(DB.BuiltInCategory.OST_LegendComponents)\
            .FirstElement()
        if first_comp:
            return LegendComponent(first_comp)

    def request_view_activation(self):
        """Requests an asynchronous activation of Legend View."""
        uidoc.RequestViewChange(self._legend_view)

    def zoom_to_fit(self):
        # type: () -> bool
        """Attempts to zoom the Legend View to fit its contents.
        Succeeds if Legend View is open.
        """
        legend_uiview = self._get_legend_uiview()
        if legend_uiview is not None:
            legend_uiview.ZoomToFit()
            return True
        else:
            return False

    def _get_legend_uiview(self):
        # type: () -> UI.UIView
        for uiview in uidoc.GetOpenUIViews():
            if uiview.ViewId == self._legend_view.Id:
                return uiview


class LegendComponent(object):
    """Class for Legend Component."""
    _id = None
    _component_type = None

    def __init__(self, legcomp):
        # type: (DB.Element) -> None
        self._validate_legcomp(legcomp)
        self._legcomp = legcomp
        self._legend_view = self._get_owner_view(legcomp)
        self._id = self._legcomp.Id
        self._component_type = self._get_component_type()

    def _get_component_type(self):
        return doc.GetElement(self.component_type_param.AsElementId())

    def _get_owner_view(self, legcomp):
        return doc.GetElement(legcomp.OwnerViewId)

    def _validate_legcomp(self, legcomp):
        # type: (DB.Element) -> None
        self._validate_element(legcomp)
        self._assure_has_category(legcomp)
        self._assure_legcomp(legcomp)

    def _validate_element(self, elem):
        # type: (DB.Element) -> None
        if not isinstance(elem, DB.Element):
            raise TypeError(
                'Expected <{}>, got <{}>'.format(DB.Element.__name__,
                                                 type(elem).__name__))

    def _assure_has_category(self, elem):
        # type: (DB.Element) -> None
        if not hasattr(elem, 'Category'):
            raise AttributeError('Element has no Category')

    def _assure_legcomp(self, legcomp):
        # type: (DB.Element) -> None
        if legcomp.Category.Id != \
                DB.ElementId(DB.BuiltInCategory.OST_LegendComponents):
            raise TypeError(
                'Element Category should be OST_LegendComponents')

    def _validate_family_type(self, elem_type):
        # type: (DB.ElementType) -> None
        if not isinstance(elem_type, DB.ElementType):
            raise TypeError(
                'Expected <{}>, got <{}>'.format(DB.ElementType.__name__,
                                                 type(elem_type).__name__))

    def copy(self, destination_location):
        """Copies Legend Component to a given location in Legend View."""
        # type: (DB.XYZ) -> LegendComponent
        copied_elem_ids = DB.ElementTransformUtils.CopyElement(
            doc,
            self._legcomp.Id,
            self.location - destination_location)
        if copied_elem_ids:
            return LegendComponent(doc.GetElement(copied_elem_ids[0]))
        else:
            raise Exception('Could not copy Legend Component')

    def move(self, translation):
        """Moves Legend Component by translation vector."""
        # type: (DB.XYZ) -> None
        DB.ElementTransformUtils.MoveElement(
            doc, self._legcomp.Id, translation)

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

    @component_type.setter
    def component_type(self, family_type):
        # type: (DB.ElementType) -> None
        self._validate_family_type(family_type)
        self.component_type_param = family_type.Id
        self._component_type = family_type

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


class ParameterWrapper(object):
    """Class for Parameter"""

    def __init__(self, parameter):
        self._parameter = parameter

    def get_param_value_or_empty_str(self):
        # type: (None) -> int | float | str | DB.ElementId
        """Gets parameter value converting None value to an empty string"""
        param_val = self._get_param_value()
        return param_val if param_val else str()

    def _get_param_value(self):
        # type: (DB.Parameter) -> int | float | str | DB.ElementId | None
        storage_type = self._parameter.StorageType
        if storage_type == DB.StorageType.Integer:
            return self._parameter.AsInteger()
        elif storage_type == DB.StorageType.Double:
            return self._parameter.AsDouble()
        elif storage_type == DB.StorageType.String:
            as_string = self._parameter.AsString()
            return as_string if as_string else self._parameter.AsValueString()
        elif storage_type == DB.StorageType.ElementId:
            return self._parameter.AsElementId()
        else:
            return None

    @property
    def parameter(self):
        return self._parameter

    @property
    def unique_name(self):
        return self._name + ' <' + str(self._id) + '>'

    @property
    def _name(self):
        return self._parameter.Definition.Name

    @property
    def _id(self):
        return self._parameter.Id


app = revit.HOST_APP.app
doc = revit.doc  # type: DB.Document
uidoc = revit.uidoc  # type: UI.Document
uiapp = revit.HOST_APP.uiapp  # type: UI.UIApplication
selection = revit.get_selection()
config = script.get_config()

gap_btw_components = \
    length_to_internal_units(
        config.get_option('gap_btw_components', 0))

legcomps_distribution = \
    config.get_option('legcomps_distribution', 'left_to_right')

sorting_param = None
legend_view = None
no_common_params = False
family_type_ids = set()  # type: set[DB.ElementId]
common_param_names = set()  # type: set[str]
failed_legcomp_ids = []  # type: list[DB.ElementId]
family_types = []  # type: list[DB.ElementType]
sorted_family_types = []  # type: list[DB.ElementType]

pick_message = 'Select Elements for adding to Legend and press "Finish"'
with forms.WarningBar(title=pick_message):
    picked_elems = revit.pick_elements(pick_message)
    uidoc.RefreshActiveView()

if picked_elems:
    for elem in picked_elems:
        family_type_ids.add(elem.GetTypeId())

    ask_for_legend_view = forms.select_views(
        'Select Legend View with at least one Legend Component',
        filterfunc=lambda view: view.ViewType == DB.ViewType.Legend,
        multiple=False
    )

    if ask_for_legend_view:
        legend_view = LegendView(ask_for_legend_view)
        source_legcomp = legend_view.get_first_legcomp()
        if source_legcomp is None:
            alert_no_components_in_view()

if picked_elems and ask_for_legend_view:
    for type_id in family_type_ids:
        family_type = doc.GetElement(type_id)
        if family_type is not None:
            wrapped_family_type = FamilyTypeWrapper(family_type)
            family_types.append(wrapped_family_type)
            unique_param_names = wrapped_family_type.unique_param_names
            if common_param_names:
                common_param_names.intersection_update(unique_param_names)
            else:
                common_param_names.update(unique_param_names)

if common_param_names:
    switch_opt_1 = 'First sort by Family'
    ask_for_sorting_param = forms.CommandSwitchWindow.show(
        sorted(common_param_names),
        message='Sort Legend Components by Parameter',
        switches=[switch_opt_1],
        config={switch_opt_1: {'background': '#7997f7'}}
    )
    sorting_param = ask_for_sorting_param[0]
elif family_types:
    no_common_params = forms.alert(
        'There is no common Parameters for selected Element Types.\n\n\
Place Legend Components without Sorting?',
        cancel=True)

if sorting_param:
    [ft.set_sorting_param(sorting_param) for ft in family_types]

    if ask_for_sorting_param[1][switch_opt_1]:
        sorted_family_types = sort_types_by_family_and_param(family_types)
    else:
        sorted_family_types = sort_types_by_param(family_types)

if sorted_family_types or no_common_params:

    app.FailuresProcessing += \
        EventHandler[DB.Events.FailuresProcessingEventArgs](
            lambda sender, args: on_failure_processing(
                sender, args, failed_legcomp_ids))

    with revit.TransactionGroup('Create Legend Components'):
        with revit.Transaction('Create Legend Components'):
            legcomps = []  # type: list[LegendComponent]
            for ft in sorted_family_types:
                legcomp = source_legcomp.copy(DB.XYZ.Zero)
                legcomp.component_type = ft.family_type
                legcomps.append(legcomp)

        with revit.Transaction('Distribute Legend Components'):
            succseed_legcomps = [
                lg for lg in legcomps if lg.id not in failed_legcomp_ids]

            if legcomps_distribution == 'left_to_right':
                distribute_left_to_right(succseed_legcomps, gap_btw_components)
            elif legcomps_distribution == 'top_to_bottom':
                distribute_top_to_bottom(succseed_legcomps, gap_btw_components)
            elif legcomps_distribution == 'bottom_to_top':
                distribute_bottom_to_top(succseed_legcomps, gap_btw_components)

        app.FailuresProcessing -= \
            EventHandler[DB.Events.FailuresProcessingEventArgs](
                lambda sender, args: on_failure_processing(
                    sender, args, failed_legcomp_ids))

    legend_view.request_view_activation()
    legend_view.zoom_to_fit()

if failed_legcomp_ids:
    failed_types = []
    for lg in legcomps:
        if lg.id in failed_legcomp_ids:
            failed_types.append(FamilyTypeWrapper(lg.component_type))

    failed_types.sort(
        key=cmp_to_key_by_attrs(names_comparer, ['family_name', 'type_name'])
    )

    output = script.get_output()
    output.print_md('###Failed creating Legend Component for:')
    for failed_type in failed_types:
        output.print_md('- {}: {}'.format(failed_type.family_name,
                                          failed_type.type_name))
