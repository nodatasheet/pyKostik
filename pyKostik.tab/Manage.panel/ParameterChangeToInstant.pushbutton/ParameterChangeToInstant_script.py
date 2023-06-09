import traceback

from System import Guid
from System.Collections.Generic import List, ISet

from operator import attrgetter
from itertools import product

from pyrevit import DB, HOST_APP, revit, script, forms
from pyrevit.output import PyRevitOutputWindow
from pykostik import exceptions as pke

project_doc = HOST_APP.doc
logger = script.get_logger()
output = script.get_output()


class GettingFamilySymbolError(pke.PyKostikException):

    def __init__(self, message=None, family_wrap=None):
        # type: (str, FamilyWrap) -> None
        self._message = str(message)
        self._family_wrap = family_wrap

    def __str__(self):
        # type: () -> str
        if self._message is None:
            return ''
        return self._message

    @property
    def family_wrap(self):
        return self._family_wrap


class FamilyLoadOptions(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        return True

    def OnSharedFamilyFound(sharedFamily, familyInUse):
        return True


class FamilyWrap(object):
    def __init__(self, family):
        # type: (DB.Family) -> None
        self._family = family
        self._doc = self._family.Document
        self._category = self._family.FamilyCategory

    def _get_first_or_none(self, iset):
        # type: (ISet) -> object
        if iset.Count:
            for item in iset:
                return item

    def _get_first_instance(self):
        # type: () -> DB.FamilySymbol
        family_bip = DB.BuiltInParameter.ELEM_FAMILY_PARAM
        filter_rule = DB.HasValueFilterRule(family_bip)
        elems = list(
            DB.FilteredElementCollector(self._doc)
            .OfCategory(self._category.Id)
            .WhereElementIsElementType()
            .WherePasses(filter_rule)
        )  # type: list[DB.Element]
        if elems:
            for elem in elems:
                family_param = elem.get_Parameter(family_bip)
                if family_param.AsElementId() == self._family.Id:
                    return elem

    @property
    def first_symbol(self):
        # type: () -> DB.FamilySymbol
        family_types = self._family.GetFamilySymbolIds()
        first = self._get_first_or_none(family_types)
        if first is not None:
            return self._doc.GetElement(first)
        raise GettingFamilySymbolError(
            message='Failed getting first symbol from family',
            family_wrap=self
        )

    @property
    def type_parameters(self):
        parameters = self.first_symbol.Parameters
        if parameters:
            return [ParameterWrap(param) for param in parameters]

        raise pke.InvalidOperationException(
            'Failed retrieving parameters from {}: {} ({})'
            .format(self.cat_name, self.name, self._family.Id)
        )

    @property
    def name(self):
        return self._family.Name

    @property
    def cat_name(self):
        # type: () -> str
        return self._category.Name

    @property
    def id(self):
        return self._family.Id

    @property
    def family(self):
        return self._family

    @property
    def category_id(self):
        # type: () -> DB.ElementId
        return self._family.FamilyCategoryId


class FamilySelectionItem(object):
    def __init__(self, family_wrap):
        # type: (FamilyWrap) -> None
        self._family_wrap = family_wrap
        self._name = self._get_name()

    @property
    def name(self):
        return self._name

    def _get_name(self):
        return self._family_wrap.cat_name + ': ' + self._family_wrap.name

    @property
    def item(self):
        return self._family_wrap


class ParameterWrap(object):
    def __init__(self, parameter):
        # type: (DB.Parameter) -> None
        self._param = parameter

    @property
    def id(self):
        return self._param.Id

    @property
    def id_or_guid(self):
        if self.is_shared:
            return self.guid
        return self.id

    @property
    def guid(self):
        # type: () -> Guid
        return self._param.GUID

    @property
    def name(self):
        return self._param.Definition.Name

    @property
    def is_shared(self):
        return self._param.IsShared

    @property
    def is_builtin(self):
        if not self.is_shared:
            return self.id.IntegerValue < 0
        return False


class ParameterElementWrap(object):
    def __init__(self, parameter):
        # type: (DB.ParameterElement) -> None
        self._param = parameter

    @property
    def id(self):
        return self._param.Id

    @property
    def id_or_guid(self):
        if self.is_shared:
            return self.guid
        return self.id

    @property
    def guid(self):
        # type: () -> Guid
        return self._param.GuidValue

    @property
    def name(self):
        return self._param.Name

    @property
    def is_shared(self):
        return isinstance(self._param, DB.SharedParameterElement)

    @property
    def is_builtin(self):
        if not self.is_shared:
            return self.id.IntegerValue < 0
        return False


class ParameterSelectionItem(object):
    def __init__(self, param_wrap):
        # type: (ParameterWrap) -> None
        self._param_wrap = param_wrap
        self._item_name = self._get_item_name()

    def _get_item_name(self):
        param_name = self._param_wrap.name
        id_number = self._param_wrap.id.IntegerValue
        suffix = ' <id={}>'.format(id_number)
        if self._param_wrap.is_shared:
            suffix = ' (Shared) <guid={}>'.format(self._param_wrap.guid)
        if self._param_wrap.is_builtin:
            suffix = ' (Built-In) <id={}>'.format(id_number)
        return param_name + suffix

    @property
    def name(self):
        return self._item_name

    @property
    def item(self):
        return self._param_wrap


class FamilyParameterWrap(object):
    def __init__(self, family_param):
        # type: (DB.FamilyParameter) -> None
        self._family_param = family_param

    @property
    def id(self):
        return self._family_param.Id

    @property
    def id_or_guid(self):
        if self.is_shared:
            return self.guid
        return self.id

    @property
    def guid(self):
        # type: () -> Guid
        return self._family_param.GUID

    @property
    def is_shared(self):
        return self._family_param.IsShared

    @property
    def parameter(self):
        return self._family_param


class BoundParameter(object):
    _bound_families = []
    _bound_schedules = []
    _bound_views = []
    _bound_cat_groups = {}

    def __init__(self, doc, definition, binding):
        # type: (DB.Document, DB.InternalDefinition, DB.ElementBinding) -> None
        self._doc = doc
        self._definition = definition
        self._binding = binding
        self._categories = self._binding.Categories
        self._category_ids = self._get_category_ids()

    def _get_category_ids(self):
        # type: () -> List[DB.ElementId]
        cat_ids = List[DB.ElementId]()
        for cat in self.categories:
            cat_ids.Add(cat.Id)
        return cat_ids

    def is_bound_to_family_types(self, family_wrap):
        # type: (FamilyWrap) -> bool
        if self.is_bound_to_category(family_wrap.category_id):
            return self.is_bound_to_element(family_wrap.first_symbol)
        return False

    def is_bound_to_category(self, category_id):
        # type: (DB.ElementId) -> bool
        return category_id in self._category_ids

    def is_bound_to_element(self, element):
        # type: (DB.Element) -> bool
        """Checks whether element has this parameter."""
        return element.get_Parameter(self.id) is not None

    @property
    def name(self):
        # type: () -> str
        return self._definition.Name

    @property
    def id(self):
        # type: () -> DB.ElementId
        return self._definition.Id

    @property
    def parameter_element_wrap(self):
        parameter_element = self._doc.GetElement(self.id)
        return ParameterElementWrap(parameter_element)

    @property
    def is_shared(self):
        # type: () -> bool
        # TODO: use collector to get first id
        return self.id in (
            DB.FilteredElementCollector(self._doc)
            .OfClass(DB.SharedParameterElement)
            .ToElementIds()
        )

    @property
    def category_ids(self):
        return self._category_ids

    @property
    def categories(self):
        # type: () -> DB.CategorySet
        return self._categories


class FamilyEditor(object):
    _family_doc = None  # type: DB.Document
    _family_manager = None  # type: DB.FamilyManager
    _family_param_wraps = None  # type: list[FamilyParameterWrap]

    def __init__(self, family_wrap):
        # type: (FamilyWrap) -> None
        self._family_wrap = family_wrap
        self._project_doc = family_wrap.family.Document

    def enter_edit_mode(self):
        # TODO: replace to __enter__
        self._family_doc = \
            self._project_doc.EditFamily(self._family_wrap.family)

        logger.info(
            'opened {} ({})'
            .format(self._family_wrap.name, self._family_wrap.id)
        )

        self._family_manager = self._family_doc.FamilyManager
        self._family_param_wraps = self._get_family_param_wraps()

    def _get_family_param_wraps(self):
        family_params = self._family_manager.Parameters

        return list(
            FamilyParameterWrap(param) for param in family_params
        )

    def try_changing_to_instance(self, param_wrap):
        # type: (ParameterWrap) -> tuple[bool, str]
        result_succeed = False
        result_comment = 'parameter not found'

        try:
            matching_family_param = self._find_matching_param(param_wrap)
            if matching_family_param is not None:
                self._family_manager.MakeInstance(matching_family_param)
                logger.info('changed parameter {}'.format(param_wrap.name))
                result_succeed = True
                result_comment = 'changed to instance'
                return result_succeed, result_comment
            logger.info('parameter {} not found'.format(param_wrap.name))
            return result_succeed, result_comment

        except Exception as err:
            logger.info(
                'failed changing parameter {}: {}'
                .format(param_wrap.name, traceback.format_exc())
            )
            result_comment = str(err)
            return result_succeed, result_comment

    def _find_matching_param(self, param_wrap):
        # type: (ParameterWrap) -> DB.FamilyParameter
        logger.info('searching param matching to {}'.format(param_wrap.name))
        for family_param_wrap in self._family_param_wraps:
            if family_param_wrap.id_or_guid == param_wrap.id_or_guid:
                logger.info(
                    'found param with id={}'.format(param_wrap.id_or_guid)
                )
                return family_param_wrap.parameter

    def load_back_to_project(self):
        # type: () -> FamilyWrap
        new_family = self._family_doc.LoadFamily(
            self._project_doc,
            FamilyLoadOptions()
        )

        new_family_wrap = FamilyWrap(new_family)

        logger.info(
            'loaded family back as {} ({})'
            .format(new_family_wrap.name, new_family_wrap.id)
        )

        return new_family_wrap

    def try_closing_family(self):
        # type: () -> bool
        return self._family_doc.Close(False)


class BaseReportItem(object):
    _item = None
    _succeed = None
    _comment = str()

    @property
    def succeed(self):
        # type: () -> bool
        if self._succeed is None:
            raise AttributeError(
                'Success status has not been set: "{}"'
                .format(self._item.name)
            )
        return self._succeed

    @succeed.setter
    def succeed(self, status):
        # type: (bool) -> None
        self._succeed = status

    @property
    def comment(self):
        # type: () -> str
        return self._comment

    @comment.setter
    def comment(self, txt):
        # type: (str) -> None
        self._comment = txt


class ReportParameterItem(BaseReportItem):

    def __init__(self, parameter_selection_item):
        # type: (ParameterSelectionItem) -> None
        self._item = parameter_selection_item

    @property
    def item(self):
        return self._item


class ReportFamilyItem(BaseReportItem):
    _closed = False

    def __init__(self, family_selection_item):
        # type: (FamilySelectionItem) -> None
        self._item = family_selection_item
        self._params = []  # type: list[ReportParameterItem]

    def add_report_param(self, report_parameter):
        # type: (ReportParameterItem) -> None
        self._params.append(report_parameter)

    def update_status(self):
        # type: () -> None
        if self._succeed is None:
            if self.all_params_succeed:
                self._succeed = True
                self.comment += '## All parameters changed'
            else:
                self._succeed = False
                self.comment += '## Some parameters failed'

        if not self.closed:
            self._succeed = False
            self._comment += (
                '<br><br> Family was opened in background '
                'and possibly not properly closed afterwards <br>'
                'It is recommended editing it and closing manually. <br>'
                'If too many families have same issue, '
                'save your data and reload Revit.'
            )

    @property
    def closed(self):
        return self._closed

    @closed.setter
    def closed(self, is_closd):
        # type: (bool) -> None
        self._closed = is_closd

    @property
    def succeed(self):
        return self._succeed

    @property
    def item(self):
        return self._item

    @property
    def parameters(self):
        return self._params

    @property
    def any_param_succeed(self):
        return any(param.succeed for param in self.parameters)

    @property
    def all_params_succeed(self):
        return all(param.succeed for param in self.parameters)


class ResultReport(object):
    _SUCCESS_SYMBOL = ':white_heavy_check_mark:'
    _FAILURE_SYMBOL = ':cross_mark:'
    _WARNING_SYMBOL = ':warning:'

    def __init__(self):
        self._output = script.get_output()
        self._report_families = []  # type: list[ReportFamilyItem]

    def add_family(self, report_family):
        # type: (ReportFamilyItem) -> None
        self._report_families.append(report_family)

    def print_report(self):
        for family in self._report_families:
            self._print_family_report(family)

            for param in family.parameters:
                self._print_param_report(param)

    def _print_family_report(self, family):
        # type: (ReportFamilyItem) -> None
        if family.succeed:
            result_symbol = self._SUCCESS_SYMBOL

        else:
            result_symbol = self._FAILURE_SYMBOL

        if not family.closed:
            result_symbol = self._WARNING_SYMBOL

        self._output.print_md(
            '#{} {}'.format(result_symbol, family.item.name)
        )

        if not family.succeed:
            self._output.print_md(
                '##{}'.format(family.comment)
            )

    def _print_param_report(self, param):
        # type: (ReportParameterItem) -> None
        result_symbol = self._SUCCESS_SYMBOL

        if not param.succeed:
            result_symbol = self._FAILURE_SYMBOL

        print(
            '{} {}: {}'.format(result_symbol, param.item.name, param.comment)
        )


def get_family(element):
    # type: (DB.Element) -> DB.Family
    family_param = element.get_Parameter(
        DB.BuiltInParameter.ELEM_FAMILY_PARAM
    )  # type: DB.Parameter
    if family_param:
        family_symbol = element.Document.GetElement(family_param.AsElementId())
        if family_symbol:
            return family_symbol.Family
    raise Exception('Failed getting family for {}'.format(element.Name))


def get_bound_parameters(_doc):
    # type: (DB.Document) -> list[BoundParameter]
    iterator = _doc.ParameterBindings.ForwardIterator()
    parameters = []
    while iterator.MoveNext():
        parameters.append(BoundParameter(_doc, iterator.Key, iterator.Current))
    return parameters


def collect_family_selection_items(doc):
    families = list(
        DB.FilteredElementCollector(doc).OfClass(DB.Family)
    )  # type: list[DB.Family]

    selection_items = []
    for family in families:
        if family.IsEditable:
            family_wrap = FamilyWrap(family)
            selection_item = FamilySelectionItem(family_wrap)
            selection_items.append(selection_item)
    return selection_items


def item_groups_intersect_by_attr(item_groups, attr_name):
    # type: (list[list], str) -> list
    """
    Intersects groups of items by item attribute.
    Returns items with common attribute values.
    """
    intersect_attrs = set()
    unique_attrs = set()
    intersect_items = []

    for group in item_groups:
        attrs = [getattr(item, attr_name) for item in group]
        if intersect_attrs:
            intersect_attrs.intersection_update(attrs)
        else:
            intersect_attrs.update(attrs)

    for group, item in product(item_groups, group):
        attr = getattr(item, attr_name)
        if (attr in intersect_attrs) and (attr not in unique_attrs):
            intersect_items.append(item)
            unique_attrs.add(attr)
    return intersect_items


def print_result(output_window, family_name, symbol, fail_txt=None):
    # type: (PyRevitOutputWindow, str, str, str) -> None
    _general_txt = (
        'Change parameter types in {} to Instance:'.format(family_name)
    )
    output_window.print_md(' '.join([_general_txt, symbol, fail_txt or '']))


family_selection_items = collect_family_selection_items(project_doc)

selected_families = forms.SelectFromList.show(
    context=sorted(family_selection_items, key=attrgetter('name')),
    name_attr='name',
    title="Select Families",
    multiselect=True,
)  # type: list[FamilySelectionItem]

if not selected_families:
    script.exit()

symbolless_families = []  # type: list[FamilyWrap]
parameter_groups = []

for family in selected_families:
    try:
        parameter_groups.append(family.item.type_parameters)
    except GettingFamilySymbolError as fam_error:
        symbolless_families.append(fam_error.family_wrap)

if symbolless_families:
    forms.alert(
        msg=(
            'Some of the selected families\n'
            'do not have any type.\n\n'
            'Their type parameters will not be shown.'
        ),
        expanded=(
            'Families without type:\n'
            + ' \n'.join([fam.name for fam in symbolless_families])
        )
    )

parameter_groups = item_groups_intersect_by_attr(
    parameter_groups,
    'id_or_guid'
)

param_selection_items = [
    ParameterSelectionItem(param) for param in parameter_groups
]
if param_selection_items:
    param_selection_items.sort(key=attrgetter('name'))


shared_param_selection_items = []
for bound_param in get_bound_parameters(project_doc):
    if bound_param.is_shared:
        shared_param_selection_items.append(
            ParameterSelectionItem(bound_param.parameter_element_wrap)
        )

if shared_param_selection_items:
    shared_param_selection_items.sort(key=attrgetter('name'))

if not any((param_selection_items, shared_param_selection_items)):
    forms.alert(
        msg=(
            'There are neither shared project parameters '
            'nor common parameters among selected family types.\n\n'
            'Nothing to select.'
        ),
        exitscript=True
    )

param_selection_groups = {
    'Family Type Parameters': param_selection_items,
    'Project Shred Parameters': shared_param_selection_items
}

selected_parameters = []
if selected_families:
    selected_parameters = forms.SelectFromList.show(
        context=param_selection_groups,
        name_attr='name',
        title='Select Parameters',
        multiselect=True,
        group_selector_title='Project or Family Parameters',
        default_group='Family Type Parameters',
        button_name='Change Selected Parameters Type To Instance'
    )  # type: list[ParameterSelectionItem]

if not selected_parameters:
    script.exit()

progress_total = len(selected_families)
progress_count = 0
report = ResultReport()

with forms.ProgressBar(cancellable=True) as progress_bar:
    progress_bar.title = 'Process Families'
    transaction_name = 'Change Family Type Parameters to Instance'

    with revit.TransactionGroup(transaction_name, doc=project_doc) as tr_gr:
        for family_item in selected_families:
            if progress_bar.cancelled:
                tr_gr._rvtxn_grp.RollBack()
                forms.alert('Cancelled')
                output.close()
                break

            family_wrap = family_item.item
            report_family = ReportFamilyItem(family_item)
            family_editor = FamilyEditor(family_wrap)
            family_editor.enter_edit_mode()

            try:
                with revit.Transaction(doc=family_editor._family_doc):
                    for selected_param in selected_parameters:
                        report_param = ReportParameterItem(selected_param)
                        param_wrap = selected_param.item

                        report_param.succeed, report_param.comment = \
                            family_editor.try_changing_to_instance(param_wrap)

                        report_family.add_report_param(report_param)

                if report_family.any_param_succeed:
                    new_family_wrap = family_editor.load_back_to_project()
                else:
                    logger.info('no changed parameters, don\'t load back')

            except Exception as err:
                logger.info(
                    'failed editing family: {}'.format(traceback.format_exc())
                )
                report_family.succeed = False
                report_family.comment = str(err)

            report_family.closed = family_editor.try_closing_family()
            report_family.update_status()
            report.add_family(report_family)

            progress_count += 1
            progress_bar.update_progress(progress_count, progress_total)

report.print_report()
