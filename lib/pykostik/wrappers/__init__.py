import pykostik as pk
from abstracts import AbstractRevitObject
from logging import Logger
from pyrevit import script

try:
    from typing import Self
except ImportError:
    pass


logger = Logger('pyKostik')
logger = script.get_logger()


class BasePKObject(object):
    pass


class BasePKWrapper(BasePKObject):
    _RVT_TYPE = None  # type: type[AbstractRevitObject]
    _rvt_obj = None  # type: AbstractRevitObject

    def __str__(self):
        return (
            self.__class__.__name__
            + '[rvt_type <'
            + type(self._rvt_obj).__name__
            + '>]'
        )

    @classmethod
    def _validate_type(cls, obj, expected):
        # type: (object, type | tuple[type]) -> None
        pk.validate_type(obj, expected)

    @classmethod
    def wrap(cls, rvt_obj):
        # type: (AbstractRevitObject) -> Self
        """Wraps Revit API object to deepest available PKObject"""
        rvt_obj_type = type(rvt_obj)
        logger.info(
            'start wrapping {} to deepest {}.'
            .format(rvt_obj_type, cls)
        )

        if rvt_obj_type is cls._RVT_TYPE:
            logger.info(
                '{} matches rvt_obj type in {}, wrapping to it.'
                .format(rvt_obj_type, cls)
            )
            return cls(rvt_obj)

        for sub_cls in cls.__subclasses__():
            if isinstance(rvt_obj, sub_cls._RVT_TYPE):
                return sub_cls.wrap(rvt_obj)

        logger.info(
            'could not find subtype, packing {} to {}'
            .format(rvt_obj_type, cls)
        )
        return cls(rvt_obj)

    @classmethod
    def get_rvt_obj_type(cls):
        return cls._RVT_TYPE

    def _wrap_to_self(self, rvt_obj):
        # type: (AbstractRevitObject) -> Self
        """Wraps Revit object to self."""
        return self.__class__(rvt_obj)

    @property
    def unwrap(self):
        return self._rvt_obj
