import functools
import operator
from Autodesk.Revit import DB, UI
from Autodesk.Revit.UI import Selection as UIS
from Autodesk.Revit.Exceptions import OperationCanceledException

from System.Collections.Generic import List

from pykostik.wrappers import BasePKWrapper, BasePKObject, db
from pykostik import exceptions as pke

try:
    from typing import TypeVar, Iterable
    T = TypeVar('T')
except ImportError:
    pass


class PkSelectionError(pke.PyKostikException):
    pass


class IPkSelectionFilter(BasePKObject, UIS.ISelectionFilter):
    def AllowElement(self, elem):
        # type: (DB.Element) -> bool
        return True

    def AllowReference(self, reference, position):
        # type: (DB.Reference, DB.XYZ) -> None
        return True


class BasePkPickResult(BasePKObject):
    def __init__(self, picked, pick_result):
        # type: (any, PkPickResultOpts) -> None
        self._picked = picked
        self._pick_result = pick_result
        self._empty_result = None

    @property
    def cancelled(self):
        return self._pick_result.cancelled


class PkPickPointResult(BasePkPickResult):
    def __init__(self, result, pick_result):
        # type: (db.PkXYZ | None, PkPickResultOpts) -> None
        self._validate_input(result, pick_result)
        self._result = result
        self._pick_result = pick_result

    def _validate_input(self, result, pick_result):
        # type: (db.PkXYZ | None, PkPickResultOpts) -> None
        if result is None and not pick_result.cancelled:
            raise PkSelectionError(
                'Pick result is None, but not set as cancelled.'
            )

    @property
    def point(self):
        # type: () -> db.PkXYZ
        return self._result


class PkPickObjectResult(BasePkPickResult):
    def __init__(self, result, pick_result):
        # type: (db.PkReference | None, PkPickResultOpts) -> None
        self._validate_input(result, pick_result)
        self._result = result
        self._pick_result = pick_result

    def _validate_input(self, result, pick_result):
        # type: (db.PkReference | None, PkPickResultOpts) -> None
        if result is None and not pick_result.cancelled:
            raise PkSelectionError(
                'Pick result is None, but not set as cancelled.'
            )

    @property
    def ref(self):
        return self._result

    def get_element(self, doc):
        # type: (db.PkDocument) -> db.PkElement
        if self.ref is not None:
            return self.ref.get_element(doc)

        raise PkSelectionError('Nothing was selected')

    def get_element_id(self):
        if self.ref is not None:
            return self.ref.element_id

        raise PkSelectionError('Nothing was selected')


class PkPickObjectsResult(BasePkPickResult):
    def __init__(self, result, pick_result):
        # type: (list[db.PkReference], PkPickResultOpts) -> None
        self._result = result
        self._pick_result = pick_result

    @property
    def refs(self):
        return self._result

    def get_elements(self, doc):
        # type: (db.PkDocument) -> list[db.PkElement]
        return [ref.get_element(doc) for ref in self._result]

    def get_element_ids(self):
        return [ref.element_id for ref in self._result]


class PkPickResultOpts(BasePKObject):
    def __init__(self):
        # type: () -> None
        self._cancelled = None

    @property
    def cancelled(self):
        # type: () -> bool
        cancelled = self._cancelled
        self._validate_was_set(cancelled)
        return cancelled

    @cancelled.setter
    def cancelled(self, state):
        # type: (bool) -> None
        self._cancelled = state

    def _validate_was_set(self, attr):
        if attr is None:
            raise PkSelectionError(
                'Non optional attribute was not set'
            )


class PkCatSelectionFilter(IPkSelectionFilter):
    def __init__(self, cat):
        # type: (db.PkCategory) -> None
        self._cat = cat

    def AllowElement(self, elem):
        # type: (DB.Element) -> bool
        if not hasattr(elem, 'Category'):
            return False

        if elem.Category.Id == self._cat.id.unwrap:
            return True

        return False


class PkBICSelectionFilter(IPkSelectionFilter):
    def __init__(self, bic):
        # type: (DB.BuiltInCategory) -> None
        self._bic_id = DB.ElementId(bic)

    def AllowElement(self, elem):
        # type: (DB.Element) -> bool
        if not hasattr(elem, 'Category'):
            return False

        if elem.Category.Id == self._bic_id:
            return True

        return False


class PkObjTypeSelectionFilter(IPkSelectionFilter):
    def __init__(self, obj_type_or_types):
        # type: (type | tuple[type]) -> None
        self._obj_type_or_types = obj_type_or_types

    def AllowElement(self, elem):
        # type: (DB.Element) -> bool
        type_or_types = self._obj_type_or_types

        if isinstance(self._obj_type_or_types, tuple):
            type_or_types = tuple(self._get_rvt_type(t) for t in type_or_types)
        else:
            type_or_types = self._get_rvt_type(type_or_types)

        if isinstance(elem, type_or_types):
            return True

        return False

    def _get_rvt_type(self, obj):
        if issubclass(obj, BasePKWrapper):
            return obj.get_rvt_obj_type()
        return obj


class PkSelection(BasePKWrapper):
    _RVT_TYPE = UIS.Selection

    def __init__(self, selection):
        # type: (UIS.Selection) -> None
        self._validate_type(selection, self._RVT_TYPE)
        self._rvt_obj = selection  # type: UIS.Selection
        self._DEFAULT_PROMPT_ELEM = 'Select Element'
        self._DEFAULT_PROMPT_ELEMS = 'Select Element(s)'

    @property
    def unwrap(self):
        return self._rvt_obj

    def _get_pick_point_result(self, rvt_pick, *args, **kwargs):
        # type: (UIS.Selection.PickPoint, any, any) -> PkPickPointResult
        result_opts = PkPickResultOpts()
        try:
            result_opts.cancelled = False
            result = db.PkXYZ(rvt_pick(*args, **kwargs))

        except OperationCanceledException:
            result = None
            result_opts.cancelled = True

        return PkPickPointResult(result, result_opts)

    def _get_pick_obj_result(self, rvt_pick, *args, **kwargs):
        # type: (UIS.Selection.PickObject, any, any) -> PkPickObjectResult
        result_opts = PkPickResultOpts()
        try:
            result_opts.cancelled = False
            result = db.PkReference(rvt_pick(*args, **kwargs))

        except OperationCanceledException:
            result = None
            result_opts.cancelled = True

        return PkPickObjectResult(result, result_opts)

    def _get_pick_objs_result(self, rvt_pick, *args, **kwargs):
        # type: (UIS.Selection.PickObjects, any, any) -> PkPickObjectsResult
        result_opts = PkPickResultOpts()
        try:
            result_opts.cancelled = False
            result = [db.PkReference(ref) for ref in rvt_pick(*args, **kwargs)]

        except OperationCanceledException:
            result = []
            result_opts.cancelled = True

        return PkPickObjectsResult(result, result_opts)

    def pick_elem(self, prompt=None):
        # type: (str) -> PkPickObjectResult
        return self.pick_obj(UIS.ObjectType.Element, prompt)

    def pick_elem_by_bic(self, built_in_cat, prompt=None):
        # type: (DB.BuiltInCategory, str) -> PkPickObjectResult
        return self.pick_obj_by_filter(
            UIS.ObjectType.Element,
            PkBICSelectionFilter(built_in_cat),
            prompt
        )

    def pick_elem_by_cls(self, obj_type_or_types, prompt=None):
        # type: (type, str) -> PkPickObjectResult
        if hasattr(obj_type_or_types, '__iter__') \
                and not isinstance(obj_type_or_types, tuple):

            raise pke.TypeValidationError(
                'Expected <type> or <tuple[type]>, got <{}>'
                .format(type(obj_type_or_types).__name__)
            )

        return self.pick_obj_by_filter(
            UIS.ObjectType.Element,
            PkObjTypeSelectionFilter(obj_type_or_types),
            prompt
        )

    def pick_elem_by_cat(self, category, prompt=None):
        # type: (db.PkCategory, str) -> PkPickObjectResult
        return self.pick_obj_by_filter(
            UIS.ObjectType.Element,
            PkCatSelectionFilter(category),
            prompt
        )

    def pick_elems(self, prompt=None):
        # type: (str) -> PkPickObjectsResult
        return self.pick_objs(UIS.ObjectType.Element, prompt)

    def pick_elems_by_cat(self, category, prompt=None):
        # type: (db.PkCategory, str) -> PkPickObjectsResult
        return self.pick_objs_by_filter(
            UIS.ObjectType.Element,
            PkCatSelectionFilter(category),
            prompt
        )

    def pick_elems_by_bic(self, built_in_cat, prompt=None):
        # type: (DB.BuiltInCategory, str) -> PkPickObjectsResult
        return self.pick_objs_by_filter(
            UIS.ObjectType.Element,
            PkBICSelectionFilter(built_in_cat),
            prompt
        )

    def pick_elems_by_cls(self, obj_type_or_types, prompt=None):
        # type: (type | tuple[type], str) -> PkPickObjectsResult
        if hasattr(obj_type_or_types, '__iter__') \
                and not isinstance(obj_type_or_types, tuple):

            raise pke.TypeValidationError(
                'Expected <type> or <tuple[type]>, got <{}>'
                .format(type(obj_type_or_types).__name__)
            )

        return self.pick_objs_by_filter(
            UIS.ObjectType.Element,
            PkObjTypeSelectionFilter(obj_type_or_types),
            prompt
        )

    def pick_linked_elem_ref(self, prompt=None):
        # type: (str) -> PkPickObjectResult
        return self.pick_obj(
            obj_type=UIS.ObjectType.LinkedElement,
            prompt=prompt
        )

    def pick_linked_elem_refs(self, prompt=None):
        # type: (str) -> PkPickObjectsResult
        return self.pick_objs(
            obj_type=UIS.ObjectType.LinkedElement,
            prompt=prompt
        )

    def pick_obj(self, obj_type, prompt=None):
        # type: (UIS.ObjectType, str) -> PkPickObjectResult
        self._validate_type(obj_type, UIS.ObjectType)

        if prompt is None:
            prompt = self._DEFAULT_PROMPT_ELEM

        rvt_pick = self._rvt_obj.PickObject
        return self._get_pick_obj_result(rvt_pick, obj_type, prompt)

    def pick_obj_by_filter(self, obj_type, sfilter, prompt=None):
        # type: (UIS.ObjectType, IPkSelectionFilter, str) -> PkPickObjectResult
        self._validate_type(obj_type, UIS.ObjectType)
        self._validate_type(sfilter, IPkSelectionFilter)

        if prompt is None:
            prompt = self._DEFAULT_PROMPT_ELEM

        rvt_pick = self._rvt_obj.PickObject
        return self._get_pick_obj_result(rvt_pick, obj_type, sfilter, prompt)

    def pick_objs(self, obj_type, prompt=None):
        # type: (UIS.ObjectType, str) -> PkPickObjectsResult
        self._validate_type(obj_type, UIS.ObjectType)

        if prompt is None:
            prompt = self._DEFAULT_PROMPT_ELEMS

        rvt_pick = self._rvt_obj.PickObjects
        return self._get_pick_objs_result(rvt_pick, obj_type, prompt)

    def pick_objs_by_filter(self, obj_type, sfilter, prompt=None):
        # type: (UIS.ObjectType, IPkSelectionFilter, str) -> PkPickObjectsResult # noqa
        self._validate_type(obj_type, UIS.ObjectType)
        self._validate_type(sfilter, IPkSelectionFilter)

        if prompt is None:
            prompt = self._DEFAULT_PROMPT_ELEMS

        rvt_pick = self._rvt_obj.PickObjects
        return self._get_pick_objs_result(rvt_pick, obj_type, sfilter, prompt)

    def pick_objs_by_filter_and_preselected(self,
                                            obj_type,
                                            sfilter,
                                            pre_selected,
                                            prompt=None):
        # type: (UIS.ObjectType, IPkSelectionFilter, list[db.PkReference], str) -> PkPickObjectsResult # noqa
        self._validate_type(obj_type, UIS.ObjectType)
        self._validate_type(sfilter, IPkSelectionFilter)

        if prompt is None:
            prompt = 'Select additional Elements'

        rvt_pre_refs = List[DB.Reference]()
        for p in pre_selected:
            rvt_pre_refs.Add(p.unwrap)

        rvt_pick = self._rvt_obj.PickObjects
        return self._get_pick_objs_result(
            rvt_pick,
            obj_type,
            sfilter,
            prompt,
            rvt_pre_refs
        )

    def pick_point(self, obj_snap_types=None, prompt=None):
        # type: (Iterable[UIS.ObjectSnapTypes], str) -> PkPickPointResult
        if prompt is None:
            prompt = 'Pick Point'

        rvt_pick = self._rvt_obj.PickPoint

        if not obj_snap_types:
            return self._get_pick_point_result(rvt_pick, prompt)

        # API forces to use <OR> operator to get multiple snap types
        # I prefer using iterable for that purpose
        obj_snap_types = functools.reduce(operator.or_, obj_snap_types)

        return self._get_pick_point_result(rvt_pick, obj_snap_types, prompt)

    def get_element_ids(self):
        return [
            db.PkElementId(id) for id in self._rvt_obj.GetElementIds()
        ]

    def get_elements(self, pk_doc):
        # type: (db.PkDocument) -> list[db.PkElement]
        rvt_doc = pk_doc.unwrap
        elems = []
        for id in self._rvt_obj.GetElementIds():
            rvt_elem = rvt_doc.GetElement(id)
            pk_elem = db.PkElement.wrap(rvt_elem)
            elems.append(pk_elem)
        return elems

    def get_elems_of_cat(self, pk_doc, cat):
        # type: (db.PkDocument, db.PkCategory) -> list[db.PkElement]
        elems = self.get_elements(pk_doc)
        return [elem for elem in elems if elem.category == cat]

    def get_elems_of_cls(self, pk_doc, pk_cls):
        # type: (db.PkDocument, type[T]) -> list[T]
        elems = self.get_elements(pk_doc)
        return [elem for elem in elems if isinstance(elem, pk_cls)]

    def get_elems_of_classes(self, pk_doc, pk_classes):
        # type: (db.PkDocument, Iterable[type]) -> list[db.Element]
        elems = self.get_elements(pk_doc)
        return [elem for elem in elems if isinstance(elem, tuple(pk_classes))]

    def set_element_ids(self, ids):
        # type: (list[db.PkElementId]) -> None
        rvt_elem_ids = List[DB.ElementId]()
        for id in ids:
            rvt_elem_ids.Add(id.unwrap)
        self._rvt_obj.SetElementIds(rvt_elem_ids)

    @property
    def is_empty(self):
        return len(self._rvt_obj.GetElementIds()) > 0
