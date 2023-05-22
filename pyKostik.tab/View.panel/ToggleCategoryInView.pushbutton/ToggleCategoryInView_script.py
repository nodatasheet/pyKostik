import re
import itertools
from abc import ABCMeta
from operator import attrgetter

from pyrevit import DB, revit, script, forms
from pykostik import exceptions as pke

try:
    # for type hinting
    from typing import Iterable
except Exception:
    pass

doc = revit.doc  # type: DB.Document
logger = script.get_logger()


class AttemptFailure(Exception):
    pass


class UnexpectedAttemptFailure(Exception):
    pass


class Sorter(object):

    def sort_by_attrs(self, iterable, attrs):
        # type: (Iterable, Iterable[str]) -> Iterable
        return sorted(
            iterable,
            key=self._cmp_to_key_by_attrs(self._names_comparer, attrs)
        )

    def _cmp_to_key_by_attrs(self, comparer, attrs):
        """Converts a comparer into a key= function
        for multilevel sorting or ordering by supplied attributes.

        Refer to functools.cmp_to_key() and operator.attrgetter().

        Args:
            comparer: a function that compares two arguments and then returns
                a negative value for '<', zero for '==', or a positive for '>'
            attrs (optional): list of attribute strings

        Returns:
            key function:
            a callable that returns a value for sorting or ordering
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

    def _names_comparer(self, name1, name2):
        # type: (object, object) -> int
        """Compares two objects as strings using Revit's comparison rules"""
        return DB.NamingUtils.CompareNames(str(name1), str(name2))


class BaseCategoryWrap(object):
    __metaclass__ = ABCMeta

    def __init__(self, category):
        # type: (DB.Category) -> None
        self._cat = category

    @property
    def is_annotation(self):
        # type: () -> bool
        return self._cat.CategoryType == DB.CategoryType.Annotation

    @property
    def is_model(self):
        # type: () -> bool
        return self._cat.CategoryType == DB.CategoryType.Model

    @property
    def is_analytical(self):
        # type: () -> bool
        return self._cat.CategoryType == DB.CategoryType.AnalyticalModel

    @property
    def id(self):
        # type: () -> DB.ElementId
        return self._cat.Id


class CategoryWrap(BaseCategoryWrap):
    @property
    def name(self):
        # type: () -> str
        return self._cat.Name

    @property
    def is_visible_in_ui(self):
        # type: () -> bool
        return self._cat.IsVisibleInUI

    @property
    def has_subcategories(self):
        # type: () -> bool
        return not self._cat.SubCategories.IsEmpty

    @property
    def sub_categories(self):
        # type: () -> list[SubCategoryWrap]
        sub_categories = []
        for cat in self._cat.SubCategories:
            sub_categories.append(SubCategoryWrap(cat))
        return sub_categories


class SubCategoryWrap(BaseCategoryWrap):
    @property
    def name(self):
        # type: () -> str
        return '    {}'.format(self._cat.Name)


class BaseCategorySelectrionGroup(object):
    __metaclass__ = ABCMeta

    _NAME = None

    def __init__(self):
        self._cats = []

    def add_cat_and_subcats(self, cat_wrap):
        # type: (list, CategoryWrap) -> None
        self._cats.append(cat_wrap)
        if cat_wrap.has_subcategories:
            sorted_subcats = sorted(
                cat_wrap.sub_categories, key=attrgetter('name')
            )
            self._cats.extend(sorted_subcats)

    @property
    def cats(self):
        # type: () -> list[BaseCategoryWrap]
        return self._cats

    @property
    def name(self):
        # type: () -> str
        return self._NAME


class ModelCategorySelectionGroup(BaseCategorySelectrionGroup):
    _NAME = 'Model Categories'


class AnnotationCategorySelectionGroup(BaseCategorySelectrionGroup):
    _NAME = 'Annotation Categories'


class AnalyticalCategorySelectionGroup(BaseCategorySelectrionGroup):
    _NAME = 'Analytical Model Categories'


class ImportedCategorySelectionGroup(BaseCategorySelectrionGroup):
    _NAME = 'Imported Categories'


class AllCategorySelectionGroup(BaseCategorySelectrionGroup):
    _NAME = 'All Categories'


class CategorySelectionGroups(object):

    def __init__(self):
        self._model_cats = ModelCategorySelectionGroup()
        self._annotation_cats = AnnotationCategorySelectionGroup()
        self._analytical_cats = AnalyticalCategorySelectionGroup()
        self._imported_cats = ImportedCategorySelectionGroup()
        self._all_cats = AllCategorySelectionGroup()

        self._all_groups = [
            self._model_cats,
            self._annotation_cats,
            self._analytical_cats,
            self._imported_cats,
            self._all_cats,
        ]

    def add_to_model_group(self, cat_wrap):
        # type: (CategoryWrap) -> None
        self._model_cats.add_cat_and_subcats(cat_wrap)
        self._all_cats.add_cat_and_subcats(cat_wrap)

    def add_to_annotation_group(self, cat_wrap):
        # type: (CategoryWrap) -> None
        self._annotation_cats.add_cat_and_subcats(cat_wrap)
        self._all_cats.add_cat_and_subcats(cat_wrap)

    def add_to_analytical_group(self, cat_wrap):
        # type: (CategoryWrap) -> None
        self._analytical_cats.add_cat_and_subcats(cat_wrap)
        self._all_cats.add_cat_and_subcats(cat_wrap)

    def add_to_imported_group(self, cat_wrap):
        # type: (CategoryWrap) -> None
        self._imported_cats.add_cat_and_subcats(cat_wrap)
        self._all_cats.add_cat_and_subcats(cat_wrap)

    def get_selection_groups(self):
        # type: () -> dict[str:list[CategoryWrap]]
        return {g.name: g.cats for g in self._all_groups}


class ViewSelectionGroup(object):

    def __init__(self, name):
        # type: (str) -> None
        self._name = name
        self._view_items = []

    def add_view_item(self, view_item):
        # type: (ViewSelectionItem) -> None
        self._view_items.append(view_item)

    @property
    def view_items(self):
        # type: () -> list[ViewSelectionItem]
        return self._view_items

    @property
    def name(self):
        # type: () -> str
        return self._name


class ViewSelectionGroups(object):
    _ALL_COMBINED_GROUP_NAME = 'All Views and Templates'

    def __init__(self):
        self._view_groups = {}  # type: dict[str: list[ViewSelectionItem]]
        self._make_all_combined()

    def _make_all_combined(self):
        self._view_groups[self._ALL_COMBINED_GROUP_NAME] = \
            ViewSelectionGroup(self._ALL_COMBINED_GROUP_NAME)

    def group_views(self, view_items):
        # type: (list[ViewSelectionItem]) -> None
        for view_item in view_items:
            self._add_view_item(view_item)

    def get_view_groups(self):
        return {
            grp.name: grp.view_items for grp in self._view_groups.values()
        }

    def _add_view_item(self, view_item):
        # type: (ViewSelectionItem) -> None
        group_name = view_item.grouping_name
        if group_name not in self._view_groups:
            self._add_new_group(group_name)
        self._add_item_to_existing_group(view_item)
        self.all_combined.add_view_item(view_item)

    def _add_new_group(self, group_name):
        # type: (str) -> None
        self._view_groups[group_name] = ViewSelectionGroup(group_name)

    def _get_group_by_name(self, group_name):
        # type: (str) -> ViewSelectionGroup
        return self._view_groups[group_name]

    def _add_item_to_existing_group(self, view_item):
        # type: (ViewSelectionItem) -> None
        existing_group = self._get_group_by_name(view_item.grouping_name)
        existing_group.add_view_item(view_item)

    @property
    def all_combined(self):
        return self._get_group_by_name(self._ALL_COMBINED_GROUP_NAME)


class ViewWrap(object):

    EDITABLE_VISIBILITY_SETTING_VIEW_TYPES = [
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.Elevation,
        DB.ViewType.ThreeD,
        DB.ViewType.DrawingSheet,
        DB.ViewType.DraftingView,
        DB.ViewType.Legend,
        DB.ViewType.EngineeringPlan,
        DB.ViewType.AreaPlan,
        DB.ViewType.Section,
        DB.ViewType.Detail,
        DB.ViewType.Walkthrough,
        DB.ViewType.Rendering
    ]

    def __init__(self, view):
        # type: (DB.View) -> None
        self._view = view

    def set_category_hiding_mode(self, cat_wrap, hiding_mode):
        # type: (CategoryWrap, bool) -> None
        if not self.can_hide_category(cat_wrap):
            raise AttemptFailure(
                'Hiding / un-hiding this category '
                'is prohibited in this view type '
                '(possibly locked by template or does not exist).'
            )

        is_hidden = self.is_category_hidden(cat_wrap)
        logger.info(
            'cat {}(id:{}) "is hidden" status = {} in view {}(id:{})'
            .format(cat_wrap.name,
                    cat_wrap.id,
                    is_hidden,
                    self.name,
                    self.id)
        )

        if is_hidden != hiding_mode:
            logger.info(
                'changing hiding mode with flag {}'.format(hiding_mode)
            )
            try:
                self._view.SetCategoryHidden(cat_wrap.id, hiding_mode)
            except Exception as err:
                AttemptFailure(str(err))

            new_is_hidden = self.is_category_hidden(cat_wrap)
            if new_is_hidden != hiding_mode:
                raise UnexpectedAttemptFailure(
                    'Hiding mode did not change after attempt. '
                    '"Is Hidden" should be "{}", but it is "{}"'
                    .format(hiding_mode, new_is_hidden)
                )

    def is_category_hidden(self, cat_wrap):
        # type: (CategoryWrap) -> bool
        return self._view.GetCategoryHidden(cat_wrap.id)

    def can_hide_category(self, cat_wrap):
        # type: (CategoryWrap) -> bool
        return self._view.CanCategoryBeHidden(cat_wrap.id)

    @property
    def name(self):
        # type: () -> str
        return self._view.Name

    @property
    def is_editable(self):
        return (
            self._view.ViewType in self.EDITABLE_VISIBILITY_SETTING_VIEW_TYPES
        )

    @property
    def view_type(self):
        return self._view.ViewType

    @property
    def is_template(self):
        return self._view.IsTemplate

    @property
    def family_name(self):
        # type: () -> str
        family_name_param = self._view.get_Parameter(
            DB.BuiltInParameter.VIEW_FAMILY)  # type: DB.Parameter
        if family_name_param:
            return family_name_param.AsValueString()
        raise pke.InvalidOperationException(
            'Failed getting Family Name for {}({})'.format(self.name, self.id)
        )

    @property
    def id(self):
        return self._view.Id


class ViewSelectionItem(object):
    def __init__(self, view_wrap):
        # type: (ViewWrap) -> None
        self._view_wrap = view_wrap
        self._view_name = view_wrap.name
        self._type = view_wrap.view_type
        self._is_template = view_wrap.is_template

    def _add_spaces_after_capitals(self, txt):
        # type: (str) -> str
        return re.sub(r"(\w)([A-Z])", r"\1 \2", txt)

    @property
    def readable_type_name(self):
        if self._type == DB.ViewType.ThreeD:
            return '3D View'
        return self._add_spaces_after_capitals(str(self._type))

    @property
    def grouping_name(self):
        if self._is_template:
            return 'View Templates'
        return self._view_wrap.family_name

    @property
    def name(self):
        if self._is_template:
            return self._name_for_template

        if self._type == DB.ViewType.DrawingSheet:
            return self._name_for_sheet

        return self._general_name_for_views

    @property
    def _name_for_template(self):
        return '{} ({}): {}'.format(
            self.grouping_name,
            self.readable_type_name,
            self._view_name
        )

    @property
    def _name_for_sheet(self):
        sheet_view = self._view_wrap._view  # type: DB.ViewSheet
        return '{}: {} - {}'.format(
            self.grouping_name,
            sheet_view.SheetNumber,
            sheet_view.Name
        )

    @property
    def _general_name_for_views(self):
        return '{}: {}'.format(self.grouping_name, self._view_name)

    @property
    def view_wrap(self):
        return self._view_wrap


class ElementsCollector(object):
    def __init__(self, doc):
        # type: (DB.Document) -> None
        self._doc = doc

    def collect_import_cad_ids(self):
        # type: () -> list[DB.ElementId]
        import_cat_ids = []
        for cad_link in self._collect_cad_links():
            cad_link_cat = cad_link.Category
            if hasattr(cad_link_cat, 'Id'):
                import_cat_ids.append(cad_link_cat.Id)
        return import_cat_ids

    def _collect_cad_links(self):
        # type: () -> list[DB.CADLinkType]
        return list(
            DB.FilteredElementCollector(self._doc)
            .OfClass(DB.CADLinkType)
        )

    def collect_views(self):
        # type: () -> list[DB.View]
        return list(
            DB.FilteredElementCollector(doc)
            .OfClass(DB.View)
            .WhereElementIsNotElementType()
        )


class OutputResult(object):
    _output = None

    def __init__(self, chosen_mode_txt, cat_name, view_name):
        # type: (str, str, str) -> None
        self._general_txt = '{} {} in {}: '.format(
            chosen_mode_txt,
            cat_name,
            view_name
        )
        if self._output is None:
            self._output = script.get_output()

    def print_result(self, symbol, fail_txt=None):
        # type: (str, str) -> None
        result = self._general_txt + symbol
        if fail_txt is not None:
            result = result + ' ' + fail_txt
        self._output.print_md(result)


collector = ElementsCollector(doc)
import_cat_ids = collector.collect_import_cad_ids()
cat_groups = CategorySelectionGroups()
sorted_doc_cats = sorted(doc.Settings.Categories, key=attrgetter('Name'))

for cat in sorted_doc_cats:
    cat_wrap = CategoryWrap(cat)
    if cat_wrap.is_visible_in_ui:
        if cat_wrap.id in import_cat_ids:
            # import cats are of DB.CategoryType.Model
            # they should be checked first so they don't go to model group
            cat_groups.add_to_imported_group(cat_wrap)
        elif cat_wrap.is_model:
            cat_groups.add_to_model_group(cat_wrap)
        elif cat_wrap.is_annotation:
            cat_groups.add_to_annotation_group(cat_wrap)
        elif cat_wrap.is_analytical:
            cat_groups.add_to_analytical_group(cat_wrap)

cat_selection_groups = cat_groups.get_selection_groups()


selected_cats = forms.SelectFromList.show(
    context=cat_selection_groups,
    title='Select Category to hide / unhide',
    multiselect=True,
    button_name='Select Categories',
    name_attr='name',
    group_selector_title='Category Types',
    default_group=AllCategorySelectionGroup().name
)  # type: list[CategoryWrap]


selected_views = []  # type: list[ViewSelectionItem]
if selected_cats:
    all_views = collector.collect_views()

    view_items = []
    for view in all_views:
        view_wrap = ViewWrap(view)
        if view_wrap.is_editable:
            view_item = ViewSelectionItem(view_wrap)
            view_items.append(view_item)

    sorted_view_items = Sorter().sort_by_attrs(
        view_items,
        ['grouping_name', 'name']
    )

    view_selection_groups = ViewSelectionGroups()
    view_selection_groups.group_views(sorted_view_items)

    selected_views = forms.SelectFromList.show(
        context=view_selection_groups.get_view_groups(),
        title='Select Views where Category should be hidden / unhidden',
        multiselect=True,
        button_name='Select Views',
        name_attr='name',
        group_selector_title='View Groups',
        default_group=view_selection_groups.all_combined.name
    )  # type: list[ViewSelectionItem]


ask_hide_unhide = str()
if selected_views:
    hiding_modes = {'Hide': True, 'Unhide': False}
    ask_hide_unhide = forms.CommandSwitchWindow.show(
        context=hiding_modes.keys(),
        message='Hide or unhide?'
    )


if ask_hide_unhide:
    chosen_mode_txt = ask_hide_unhide
    chosen_mode_value = hiding_modes[chosen_mode_txt]
    with revit.Transaction(
        '{} Categories in Views'.format(chosen_mode_txt)
    ):
        for view_item, cat_wrap in itertools.product(
                selected_views, selected_cats):
            result = OutputResult(
                chosen_mode_txt,
                cat_wrap.name,
                view_item.name
            )
            try:
                view_item.view_wrap.set_category_hiding_mode(
                    cat_wrap,
                    chosen_mode_value
                )
                success_mark = ':white_heavy_check_mark:'
                result.print_result(
                    symbol=success_mark
                )
            except AttemptFailure as failed_attempt:
                failure_mark = ':cross_mark:'
                result.print_result(
                    symbol=failure_mark,
                    fail_txt=str(failed_attempt)
                )
            except UnexpectedAttemptFailure as failed_attempt:
                warning_mark = ':warning:'
                result.print_result(
                    symbol=warning_mark,
                    fail_txt=str(failed_attempt)
                )
