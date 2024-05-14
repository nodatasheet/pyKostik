import functools
import operator

from Autodesk.Revit import DB


try:
    # for type hints
    from typing import Callable, Iterable
except ImportError:
    pass


class _ComparerToKey(object):
    __slots__ = ['_obj', '_comparer']

    def __init__(self, obj, comparer, attr_getter=None):
        # type: (any, Callable, Callable) -> None
        self._obj = attr_getter(obj) if attr_getter else obj
        self._comparer = comparer

    def __lt__(self, other):
        # type: (_ComparerToKey) -> bool
        return self._comparer(self._obj, other._obj) < 0

    def __gt__(self, other):
        # type: (_ComparerToKey) -> bool
        return self._comparer(self._obj, other._obj) > 0

    def __eq__(self, other):
        # type: (_ComparerToKey) -> bool
        return self._comparer(self._obj, other._obj) == 0

    def __le__(self, other):
        # type: (_ComparerToKey) -> bool
        return self._comparer(self._obj, other._obj) <= 0

    def __ge__(self, other):
        # type: (_ComparerToKey) -> bool
        return self._comparer(self._obj, other._obj) >= 0

    def __ne__(self, other):
        # type: (_ComparerToKey) -> bool
        return self._comparer(self._obj, other._obj) != 0

    __hash__ = None


def compare_as_stings(obj1, obj2):
    # type: (any, any) -> int
    """Compares two objects as strings using `DB.NamingUtils.CompareNames`"""
    return DB.NamingUtils.CompareNames(str(obj1), str(obj2))


def cmp_to_k(comparer):
    # type: (Callable) -> Callable[..., bool]
    """Same as `functools.cmp_to_key`"""
    return functools.cmp_to_key(comparer)


def cmp_to_k_by_attr(comparer, attr):
    # type: (Callable[[str, str], int], str) -> _ComparerToKey
    def call_cmp_to_k(obj):
        return _ComparerToKey(obj, comparer, operator.attrgetter(attr))
    return call_cmp_to_k


def cmp_to_k_by_attrs(comparer, attrs):
    # type: (Callable[[str, str], int], Iterable[str]) -> tuple[_ComparerToKey]
    getter = operator.attrgetter

    def call_cmp_to_k(obj):
        return tuple(
            _ComparerToKey(obj, comparer, getter(a)) for a in attrs
        )

    return call_cmp_to_k


def cmp_to_k_by_getter(comparer, attr_getter):
    # type: (Callable[[str, str], int], Callable) -> _ComparerToKey
    def call_cmp_to_k(obj):
        return _ComparerToKey(obj, comparer, attr_getter)
    return call_cmp_to_k


def natural_cmp_to_k():
    return cmp_to_k(compare_as_stings)


def natural_cmp_to_k_by_attr(attr):
    return cmp_to_k_by_attr(compare_as_stings, attr)


def natural_cmp_to_k_by_attrs(attrs):
    return cmp_to_k_by_attrs(compare_as_stings, attrs)
