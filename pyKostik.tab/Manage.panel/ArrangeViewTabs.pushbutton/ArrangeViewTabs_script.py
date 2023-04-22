import os

from pykostik.exceptions import InvalidOperationException
from pyrevit import script, revit, forms, DB, UI, HOST_APP


try:
    # for type hinting
    from typing import Iterable, Callable
except Exception:
    pass

app = HOST_APP.app
uiapp = HOST_APP.uiapp
active_view = HOST_APP.active_view
output = script.get_output()


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


class RevitDocumentType(object):
    PROJECT_TEMPLATE = 0
    PROJECT = 1
    FAMILY_TEMPLATE = 2
    FAMILY = 3
    OTHER = 4


class DocWrap(object):
    """Wrapper around Document for managing view tabs."""

    def __init__(self, doc):
        # type: (DB.Document) -> None
        self._doc = doc
        self._uidoc = UI.UIDocument(doc)

    def activate(self):
        if not uiapp.ActiveUIDocument.Document == self._doc:
            if self._doc.IsModelInCloud:
                cloud_path = self._doc.GetCloudModelPath()
                open_options = DB.OpenOptions()
                detach_and_prompt = False
                uiapp.OpenAndActivateDocument(cloud_path,
                                              open_options,
                                              detach_and_prompt)
            else:
                uiapp.OpenAndActivateDocument(self._doc.PathName)

    def get_any_other_view(self, view_tab):
        # type: (ViewTab) -> DB.View
        views = revit.query.get_all_views(self._doc)

        for view in views:
            if view.Id != view_tab.view.Id:
                return view

        raise InvalidOperationException(
            'Failed finding temporary view for {} ({})'.format(
                self._doc, self.title
            )
        )

    def get_element(self, element_id):
        # type: (DB.ElementId) -> DB.Element
        return self._doc.GetElement(element_id)

    def request_view_change(self, view):
        # type: (DB.View) -> None
        return self._uidoc.RequestViewChange(view)

    @property
    def doc(self):
        # type: () -> DB.Document
        return self._doc

    @property
    def uidoc(self):
        # type: () -> UI.UIDocument
        return self._uidoc

    @property
    def current_view_tabs(self):
        # type: () -> list[ViewTab]
        return [
            ViewTab(uiview, self) for uiview in self.current_uiviews
        ]

    @property
    def current_uiviews(self):
        # type: () -> list[UI.UIView]
        return self._uidoc.GetOpenUIViews()

    @property
    def uiviews_qty(self):
        return len(self.current_uiviews)

    @property
    def title(self):
        # type: () -> str
        return self._doc.Title

    @property
    def doc_type(self):
        # type: () -> int
        if self.file_extension == '.rte':
            return RevitDocumentType.PROJECT_TEMPLATE
        if self.file_extension == '.rvt':
            return RevitDocumentType.PROJECT
        if self.file_extension == '.rft':
            return RevitDocumentType.FAMILY_TEMPLATE
        if self.file_extension == '.rfa':
            return RevitDocumentType.FAMILY
        else:
            return RevitDocumentType.OTHER

    @property
    def path_name(self):
        # type: () -> str
        return self._doc.PathName

    @property
    def file_extension(self):
        # type: () -> str
        root, extension = os.path.splitext(self.path_name)
        return extension


class ViewTab(object):

    _ZOOMABLE_VIEWTYPES = [
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
        DB.ViewType.ColumnSchedule,
        DB.ViewType.PanelSchedule,
        DB.ViewType.Walkthrough,
        DB.ViewType.Rendering
    ]

    def __init__(self, uiview, doc_wrap):
        # type: (UI.UIView, DocWrap) -> None
        self._uiview = uiview
        self._doc_wrap = doc_wrap
        self._view = self._doc_wrap.get_element(uiview.ViewId)  # type: DB.View

    def get_zoom_corners(self):
        # type: () -> list[DB.XYZ]
        return self._uiview.GetZoomCorners()

    def set_zoom_corners(self, zoom_corners):
        # type: (list[DB.XYZ]) -> None
        self._uiview.ZoomAndCenterRectangle(*zoom_corners)

    def close(self):
        self._uiview.Close()

    def request_activation(self):
        self._doc_wrap.request_view_change(self._view)

    def reassing_uiview(self):
        """Reassigns `UIView` for current View Tab instance
        after closing and then reopening the tab.
        """
        self._uiview = self._get_new_uiview()

    def _get_new_uiview(self):
        for uiview in self._doc_wrap.current_uiviews:
            if uiview.ViewId == self._view.Id:
                return uiview
        raise InvalidOperationException(
            'Failed getting the ui-view for {}'.format(self.view_name)
        )

    @property
    def doc_wrap(self):
        return self._doc_wrap

    @property
    def view_name(self):
        name_param = self._view.get_Parameter(DB.BuiltInParameter.VIEW_NAME)
        if name_param:
            return name_param.AsString()

    @property
    def view_type(self):
        return self._view.ViewType

    @property
    def view(self):
        return self._view

    @property
    def zoomable(self):
        return self.view_type in self._ZOOMABLE_VIEWTYPES


def uiview_by_view(view):
    # type: (DB.View) -> UI.UIView
    uidoc = UI.UIDocument(view.Document)
    for uiview in uidoc.GetOpenUIViews():
        if uiview.ViewId == view.Id:
            return uiview

    raise InvalidOperationException(
        '{} ({}) is not listed in open views'.format(view, view.Title)
    )


doc_wraps = []
invalid_path_docs = []
for active_doc in app.Documents:
    if not active_doc.PathName:
        invalid_path_docs.append(active_doc)
    elif not active_doc.IsLinked:
        doc_wraps.append(
            DocWrap(active_doc)
        )

if invalid_path_docs:
    forms.alert(
        msg=('Some documents do not have a valid path.\n\n'
             'In order to arrange the view tabs, initial documents '
             'must be stored in a folder or on the server.'),
        expanded=('Documents with invalid path:\n'
                  + '\n'.join(str(d.Title) for d in invalid_path_docs)),
        exitscript=True
    )

sorter = Sorter()
sorted_docs = sorter.sort_by_attrs(
    doc_wraps, ['doc_type', 'title']
)  # type: list[DocWrap]

progress_total = sum(doc_wrap.uiviews_qty for doc_wrap in sorted_docs)

with forms.ProgressBar(title='Arranging view tabs') as progress_bar:
    # progress bar is to activate the view after `uidoc.RequestViewChange()`
    progress_count = 0

    all_view_tabs = []  # type: list[ViewTab]
    for doc_wrap in sorted_docs:
        doc_view_tabs = doc_wrap.current_view_tabs
        all_view_tabs.extend(doc_view_tabs)

        sorted_view_tabs = sorter.sort_by_attrs(
            doc_view_tabs,
            ['view_type', 'view_name']
        )  # type: list[ViewTab]

        first_tab = sorted_view_tabs[0]
        rest_tabs = sorted_view_tabs[1:]

        tmp_view = None
        if len(sorted_view_tabs) < 2:
            tmp_view = doc_wrap.get_any_other_view(first_tab)
            doc_wrap.activate()
            doc_wrap.uidoc.RequestViewChange(tmp_view)
            progress_bar.update_progress(progress_count, progress_total)

        if first_tab.zoomable:
            zoom_corners = first_tab.get_zoom_corners()

        first_tab.close()
        doc_wrap.activate()
        first_tab.request_activation()

        progress_count += 1
        progress_bar.update_progress(progress_count, progress_total)

        first_tab.reassing_uiview()

        if first_tab.zoomable:
            first_tab.set_zoom_corners(zoom_corners)

        if tmp_view is not None:
            tmp_uiview = uiview_by_view(tmp_view)
            tmp_uiview.Close()

        for tab in rest_tabs:
            if tab.zoomable:
                zoom_corners = tab.get_zoom_corners()

            tab.close()
            tab.request_activation()

            progress_count += 1
            progress_bar.update_progress(progress_count, progress_total)

            tab.reassing_uiview()

            if tab.zoomable:
                tab.set_zoom_corners(zoom_corners)

# activate initially active view
for view_tab in all_view_tabs:
    if view_tab.view.Id == active_view.Id:
        view_tab.doc_wrap.activate()
        view_tab.request_activation()
