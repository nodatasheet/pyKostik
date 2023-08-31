"""pyKostik root level config for all pykostik sub-modules."""

from pykostik.revit.db.transaction import *
import exceptions as pke


def validate_type(obj, expected, err_msg=None):
    # type: (object, type | tuple[type], str) -> None

    if not isinstance(obj, expected):
        raise pke.TypeValidationError(
            message=err_msg,
            expected=expected,
            provided=type(obj)
        )
