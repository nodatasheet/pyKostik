import itertools

from pykostik.utils import callables

try:
    # for type hints
    from typing import Iterable, TypeVar

    T = TypeVar('T')

except ImportError:
    pass


def pairwise(iterable):
    # type: (Iterable[T]) -> tuple[T, T]
    """
    pairwise('ABCD') --> AB BC CD

    Similar to `itertools.pairwise` that was added in python 3.10
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def circular_pairwise(iterable):
    # type: (Iterable[T]) -> tuple[T]
    """
    circular_pairwise('ABCD') --> AB BC CD DA

    https://stackoverflow.com/a/36927946
    """
    a, b = itertools.tee(iterable)
    first = next(b, None)
    return zip(a, itertools.chain(b, (first,)))


def natural_sort(items, reverse=False):
    # type: (Iterable[T], bool) -> list[T]
    return sorted(
        items,
        key=callables.cmp_to_k(callables.compare_as_stings),
        reverse=reverse
    )


def natural_sort_by_attr(items, attr_name, reverse=False):
    # type: (Iterable[T], str, bool) -> list[T]
    return sorted(
        items,
        key=callables.natural_cmp_to_k_by_attr(attr_name),
        reverse=reverse
    )


def natural_sort_by_attrs(items, attr_names, reverse=False):
    # type: (Iterable[T], Iterable[str], bool) -> list[T]
    return sorted(
        items,
        key=callables.natural_cmp_to_k_by_attrs(attr_names),
        reverse=reverse
    )
