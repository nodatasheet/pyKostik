

class PyKostikException(Exception):
    """Base class for pyKostik exceptions."""


class FailedAttempt(PyKostikException):
    """Failed Attempt Exception"""
    pass


class InvalidOperationException(PyKostikException):
    """Invalid Operation Exception"""
    pass


class ValidationError(PyKostikException):
    """Base class for Validation Errors"""
    pass


class TypeValidationError(ValidationError):
    """Type Validation Error"""

    def __init__(self, message=None, expected=None, provided=None):
        # type: (str, type | tuple[type], type) -> None
        self._message = message
        self._expected = expected
        self._provided = provided

    def __str__(self):
        # type: () -> str
        if self._message is not None:
            return self._message

        message = str()

        expected = self._expected
        if expected is not None:
            if isinstance(expected, tuple):
                names = (obj_type.__name__ for obj_type in expected)
                message += ' expected: ' + ' or '.join(names) + '.'
            else:
                message += ' expected: ' + expected.__name__ + '.'

        if self._provided is not None:
            message += ' got: ' + self._provided.__name__ + '.'

        return message


class ParameterError(PyKostikException):
    pass


class ParameterNotFoundError(ParameterError):
    pass


class ParameterIsReadOnlyError(ParameterError):
    pass
