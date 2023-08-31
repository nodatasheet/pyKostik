"""The definition of the base geometrical entity with attributes common to
all derived geometrical entities.
"""
from abc import ABCMeta
import pykostik as pk


class GeometryEntity(object):
    """The base class for all geometrical entities."""

    __metaclass__ = ABCMeta

    def __new__(cls, *args, **kwargs):
        if cls is GeometryEntity:
            raise NotImplementedError(
                'Cannot create instances of GeometryEntity '
                'because it has no public constructors.'
            )
        return super(GeometryEntity, cls).__new__(cls)

    def _validate_type(self, obj, expected_type, err_msg):
        # type: (object, type, str) -> None
        pk.validate_type(obj, expected_type, err_msg)
